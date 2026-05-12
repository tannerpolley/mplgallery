use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};
use tauri_plugin_dialog::DialogExt;
use walkdir::{DirEntry, WalkDir};

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct UpdateInfo {
    checked: bool,
    available: bool,
    current_version: Option<String>,
    latest_version: Option<String>,
    error: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct AppInfo {
    name: String,
    version: String,
    app_id: String,
    can_install_updates: bool,
    update: UpdateInfo,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct UserSettings {
    remember_recent_projects: bool,
    restore_last_project_on_startup: bool,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RootContext {
    active_root: String,
    recent_roots: Vec<String>,
    error: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct AppBootstrap {
    app_info: AppInfo,
    user_settings: UserSettings,
    root_context: RootContext,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct FolderNode {
    id: String,
    label: String,
    path: String,
    child_count: usize,
    asset_count: usize,
    children: Vec<FolderNode>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct AssetRef {
    id: String,
    relative_path: String,
    kind: String,
    size_bytes: Option<u64>,
    modified_at: Option<String>,
    width_px: Option<u32>,
    height_px: Option<u32>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct CsvDataset {
    id: String,
    display_name: String,
    relative_path: String,
    folder_path: String,
    row_count_sampled: usize,
    columns: Vec<String>,
    numeric_columns: Vec<String>,
    categorical_columns: Vec<String>,
    preview_columns: Vec<String>,
    preview_rows: Vec<BTreeMap<String, String>>,
    preview_truncated: bool,
    preview_error: Option<String>,
    linked_image_ids: Vec<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct PlotSetCard {
    id: String,
    title: String,
    folder_path: String,
    classification: String,
    attachments: Vec<AssetRef>,
    preferred_figure_id: Option<String>,
    render_status: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct LooseImageCard {
    id: String,
    title: String,
    folder_path: String,
    classification: String,
    image: AssetRef,
    sibling_csv_ids: Vec<String>,
    image_format: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct FileRow {
    id: String,
    title: String,
    folder_path: String,
    classification: String,
    attachment_kinds: Vec<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ScanResult {
    root_path: String,
    browse_mode: String,
    folder_tree: Vec<FolderNode>,
    file_rows: Vec<FileRow>,
    plot_sets: Vec<PlotSetCard>,
    loose_images: Vec<LooseImageCard>,
    datasets: Vec<CsvDataset>,
    warnings: Vec<String>,
    ignored_dir_count: usize,
}

#[derive(Clone)]
struct DiscoveredAsset {
    absolute_path: PathBuf,
    relative_path: String,
    kind: String,
    size_bytes: u64,
    width_px: Option<u32>,
    height_px: Option<u32>,
}

const SUPPORTED_SUFFIXES: [&str; 3] = [".csv", ".png", ".svg"];
const DEFAULT_IGNORE_DIRS: [&str; 14] = [
    ".git",
    ".dvc",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "mlruns",
    "node_modules",
    "venv",
    "test-results",
];

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("src-tauri must live under the repo root")
        .to_path_buf()
}

fn default_examples_root() -> String {
    repo_root().join("examples").to_string_lossy().replace('\\', "/")
}

fn bootstrap_root() -> String {
    let configured = env::var("MPLGALLERY_ACTIVE_ROOT").unwrap_or_default();
    let trimmed = configured.trim();
    if !trimmed.is_empty() {
        return trimmed.replace('\\', "/");
    }
    default_examples_root()
}

fn should_skip_dir(entry: &DirEntry, root: &Path) -> bool {
    let name = entry.file_name().to_string_lossy();
    let path = entry.path();
    if name == ".mplgallery" {
        return false;
    }
    if DEFAULT_IGNORE_DIRS.contains(&name.as_ref()) {
        return true;
    }
    if name.starts_with('.') {
        return true;
    }
    if let Ok(relative) = path.strip_prefix(root) {
        let parts: Vec<_> = relative.components().collect();
        if parts.len() >= 2
            && parts[parts.len() - 2] == Component::Normal(".mplgallery".as_ref())
            && parts[parts.len() - 1] == Component::Normal("cache".as_ref())
        {
            return true;
        }
    }
    false
}

fn read_png_dimensions(path: &Path) -> (Option<u32>, Option<u32>) {
    let Ok(mut file) = fs::File::open(path) else {
        return (None, None);
    };
    let mut header = [0_u8; 24];
    if file.read_exact(&mut header).is_err() {
        return (None, None);
    }
    let png_signature = [137, 80, 78, 71, 13, 10, 26, 10];
    if header[0..8] != png_signature {
        return (None, None);
    }
    let width = u32::from_be_bytes([header[16], header[17], header[18], header[19]]);
    let height = u32::from_be_bytes([header[20], header[21], header[22], header[23]]);
    (Some(width), Some(height))
}

fn discover_assets(root: &Path) -> Result<(Vec<DiscoveredAsset>, usize), String> {
    let mut assets = Vec::new();
    let mut ignored_dir_count = 0;
    let walker = WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|entry| {
            let keep = if entry.depth() == 0 || !entry.file_type().is_dir() {
                true
            } else {
                !should_skip_dir(entry, root)
            };
            if entry.depth() > 0 && entry.file_type().is_dir() && !keep {
                ignored_dir_count += 1;
            }
            keep
        });

    for entry in walker {
        let entry = entry.map_err(|error| error.to_string())?;
        if !entry.file_type().is_file() {
            continue;
        }
        let path = entry.path();
        let suffix = path
            .extension()
            .and_then(|value| value.to_str())
            .map(|value| format!(".{}", value.to_ascii_lowercase()))
            .unwrap_or_default();
        if !SUPPORTED_SUFFIXES.contains(&suffix.as_str()) {
            continue;
        }
        let metadata = fs::metadata(path).map_err(|error| error.to_string())?;
        let relative = path
            .strip_prefix(root)
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        let (width_px, height_px) = if suffix == ".png" {
            read_png_dimensions(path)
        } else {
            (None, None)
        };
        assets.push(DiscoveredAsset {
            absolute_path: path.to_path_buf(),
            relative_path: relative,
            kind: suffix.trim_start_matches('.').to_string(),
            size_bytes: metadata.len(),
            width_px,
            height_px,
        });
    }

    assets.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok((assets, ignored_dir_count))
}

fn summarize_csv(path: &Path) -> (usize, Vec<String>, Vec<String>, Vec<String>, Vec<BTreeMap<String, String>>, bool, Option<String>) {
    let mut reader = match csv::Reader::from_path(path) {
        Ok(reader) => reader,
        Err(error) => {
          return (
            0,
            vec![],
            vec![],
            vec![],
            vec![],
            false,
            Some(error.to_string()),
          );
        }
    };
    let headers = match reader.headers() {
        Ok(headers) => headers.iter().map(|value| value.to_string()).collect::<Vec<_>>(),
        Err(error) => {
            return (
                0,
                vec![],
                vec![],
                vec![],
                vec![],
                false,
                Some(error.to_string()),
            );
        }
    };

    let mut row_count_sampled = 0;
    let mut preview_rows = Vec::<BTreeMap<String, String>>::new();
    let mut numeric_candidates = vec![true; headers.len()];
    let mut seen_nonempty = vec![false; headers.len()];
    let mut preview_truncated = false;

    for record_result in reader.records().take(200) {
        let record = match record_result {
            Ok(record) => record,
            Err(error) => {
                return (
                    row_count_sampled,
                    headers.clone(),
                    vec![],
                    vec![],
                    preview_rows,
                    preview_truncated,
                    Some(error.to_string()),
                );
            }
        };
        row_count_sampled += 1;
        if preview_rows.len() < 12 {
            let mut row = BTreeMap::new();
            for (index, header) in headers.iter().enumerate() {
                row.insert(header.clone(), record.get(index).unwrap_or_default().to_string());
            }
            preview_rows.push(row);
        } else {
            preview_truncated = true;
        }

        for (index, value) in record.iter().enumerate() {
            let trimmed = value.trim();
            if trimmed.is_empty() {
                continue;
            }
            seen_nonempty[index] = true;
            if trimmed.parse::<f64>().is_err() {
                numeric_candidates[index] = false;
            }
        }
    }

    let numeric_columns = headers
        .iter()
        .enumerate()
        .filter_map(|(index, header)| (seen_nonempty[index] && numeric_candidates[index]).then(|| header.clone()))
        .collect::<Vec<_>>();
    let categorical_columns = headers
        .iter()
        .enumerate()
        .filter_map(|(index, header)| (seen_nonempty[index] && !numeric_candidates[index]).then(|| header.clone()))
        .collect::<Vec<_>>();

    (
        row_count_sampled,
        headers.clone(),
        numeric_columns,
        categorical_columns,
        preview_rows,
        preview_truncated,
        None,
    )
}

fn asset_ref(asset: &DiscoveredAsset) -> AssetRef {
    AssetRef {
        id: asset.relative_path.clone(),
        relative_path: asset.relative_path.clone(),
        kind: asset.kind.clone(),
        size_bytes: Some(asset.size_bytes),
        modified_at: None,
        width_px: asset.width_px,
        height_px: asset.height_px,
    }
}

fn collect_folder_tree(paths: impl Iterator<Item = String>) -> Vec<FolderNode> {
    #[derive(Default)]
    struct TempNode {
        path: String,
        asset_count: usize,
        children: BTreeMap<String, TempNode>,
    }

    fn insert(root: &mut BTreeMap<String, TempNode>, path: &str) {
        let mut current = root;
        let mut built = String::new();
        for part in path.split('/').filter(|part| !part.is_empty() && *part != ".") {
            if !built.is_empty() {
                built.push('/');
            }
            built.push_str(part);
            let node = current.entry(part.to_string()).or_insert_with(|| TempNode {
                path: built.clone(),
                asset_count: 0,
                children: BTreeMap::new(),
            });
            node.asset_count += 1;
            current = &mut node.children;
        }
    }

    fn materialize(map: BTreeMap<String, TempNode>) -> Vec<FolderNode> {
        map.into_iter()
            .map(|(label, node)| {
                let children = materialize(node.children);
                FolderNode {
                    id: node.path.clone(),
                    label,
                    path: node.path,
                    child_count: children.len(),
                    asset_count: node.asset_count,
                    children,
                }
            })
            .collect()
    }

    let mut root = BTreeMap::<String, TempNode>::new();
    for path in paths {
        insert(&mut root, &path);
    }
    materialize(root)
}

#[tauri::command]
fn get_app_bootstrap() -> AppBootstrap {
    let active_root = bootstrap_root();
    AppBootstrap {
        app_info: AppInfo {
            name: "MPLGallery".to_string(),
            version: "0.2.0-preview".to_string(),
            app_id: "com.mplgallery.desktop".to_string(),
            can_install_updates: false,
            update: UpdateInfo {
                checked: true,
                available: false,
                current_version: Some("0.2.0-preview".to_string()),
                latest_version: Some("0.2.0-preview".to_string()),
                error: None,
            },
        },
        user_settings: UserSettings {
            remember_recent_projects: true,
            restore_last_project_on_startup: false,
        },
        root_context: RootContext {
            active_root: active_root.clone(),
            recent_roots: vec![active_root],
            error: None,
        },
    }
}

#[tauri::command]
fn scan_project(root_path: String) -> Result<ScanResult, String> {
    let root = PathBuf::from(root_path);
    if !root.exists() {
        return Err(format!("Project root does not exist: {}", root.display()));
    }
    if !root.is_dir() {
        return Err(format!("Project root is not a directory: {}", root.display()));
    }

    let (assets, ignored_dir_count) = discover_assets(&root)?;
    let mut grouped_plot_sets: BTreeMap<String, Vec<DiscoveredAsset>> = BTreeMap::new();
    let mut loose_images = Vec::<DiscoveredAsset>::new();
    let mut folder_paths = BTreeSet::<String>::new();
    let mut warnings = Vec::<String>::new();

    for asset in assets {
        let parts: Vec<&str> = asset.relative_path.split('/').collect();
        if parts.first() == Some(&"results") && parts.len() >= 3 {
            let plot_set_key = format!("results/{}", parts[1]);
            folder_paths.insert(plot_set_key.clone());
            grouped_plot_sets.entry(plot_set_key).or_default().push(asset);
            continue;
        }
        if asset.kind == "png" || asset.kind == "svg" {
            if let Some(parent) = Path::new(&asset.relative_path).parent() {
                folder_paths.insert(parent.to_string_lossy().replace('\\', "/"));
            }
            loose_images.push(asset);
        }
    }

    let mut datasets = Vec::<CsvDataset>::new();
    let mut plot_sets = Vec::<PlotSetCard>::new();
    let mut file_rows = Vec::<FileRow>::new();

    for (folder_path, mut members) in grouped_plot_sets {
        members.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
        let mut attachments = Vec::<AssetRef>::new();
        let mut linked_image_ids = Vec::<String>::new();
        let mut csv_names = Vec::<String>::new();
        let title = folder_path
            .split('/')
            .next_back()
            .unwrap_or(folder_path.as_str())
            .replace('_', " ");
        let plot_set_id = format!("plotset:{}", folder_path);

        for member in &members {
            attachments.push(asset_ref(member));
            if member.kind == "csv" {
                csv_names.push(
                    Path::new(&member.relative_path)
                        .file_name()
                        .and_then(|value| value.to_str())
                        .unwrap_or("dataset.csv")
                        .to_string(),
                );
            } else {
                linked_image_ids.push(member.relative_path.clone());
            }
        }

        for member in &members {
            if member.kind != "csv" {
                continue;
            }
            let (
                row_count_sampled,
                columns,
                numeric_columns,
                categorical_columns,
                preview_rows,
                preview_truncated,
                preview_error,
            ) = summarize_csv(&member.absolute_path);
            let display_name = Path::new(&member.relative_path)
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or("dataset.csv")
                .to_string();
            datasets.push(CsvDataset {
                id: format!("dataset:{}", member.relative_path),
                display_name,
                relative_path: member.relative_path.clone(),
                folder_path: folder_path.clone(),
                row_count_sampled,
                preview_columns: columns.clone(),
                columns,
                numeric_columns,
                categorical_columns,
                preview_rows,
                preview_truncated,
                preview_error,
                linked_image_ids: linked_image_ids.clone(),
            });
        }

        let preferred_figure_id = attachments
            .iter()
            .find(|attachment| attachment.kind == "svg")
            .or_else(|| attachments.iter().find(|attachment| attachment.kind == "png"))
            .map(|attachment| attachment.id.clone());
        let has_figure = attachments.iter().any(|attachment| attachment.kind == "svg" || attachment.kind == "png");
        let attachment_kinds: Vec<String> = attachments.iter().map(|attachment| attachment.kind.clone()).collect();

        file_rows.push(FileRow {
            id: plot_set_id.clone(),
            title: if csv_names.is_empty() {
                title.clone()
            } else {
                title.clone()
            },
            folder_path: folder_path.clone(),
            classification: "analysis-linked".to_string(),
            attachment_kinds: attachment_kinds.clone(),
        });

        plot_sets.push(PlotSetCard {
            id: plot_set_id,
            title,
            folder_path,
            classification: "analysis-linked".to_string(),
            attachments,
            preferred_figure_id,
            render_status: if has_figure {
                "ready".to_string()
            } else {
                warnings.push("Some results plot sets have CSV files but no figure asset yet.".to_string());
                "missing_figure".to_string()
            },
        });
    }

    let mut loose_cards = Vec::<LooseImageCard>::new();
    for image in loose_images {
        let folder_path = Path::new(&image.relative_path)
            .parent()
            .map(|value| value.to_string_lossy().replace('\\', "/"))
            .unwrap_or_else(|| ".".to_string());
        let title = Path::new(&image.relative_path)
            .file_stem()
            .and_then(|value| value.to_str())
            .unwrap_or("image")
            .replace('_', " ");
        file_rows.push(FileRow {
            id: format!("loose:{}", image.relative_path),
            title: title.clone(),
            folder_path: folder_path.clone(),
            classification: "loose-image".to_string(),
            attachment_kinds: vec![image.kind.clone()],
        });
        loose_cards.push(LooseImageCard {
            id: format!("loose:{}", image.relative_path),
            title,
            folder_path,
            classification: "loose-image".to_string(),
            image_format: Some(image.kind.to_uppercase()),
            sibling_csv_ids: vec![],
            image: asset_ref(&image),
        });
    }

    let browse_mode = if plot_sets.is_empty() && !loose_cards.is_empty() {
        "image-library".to_string()
    } else {
        "plot-set-manager".to_string()
    };

    Ok(ScanResult {
        root_path: root.to_string_lossy().replace('\\', "/"),
        browse_mode,
        folder_tree: collect_folder_tree(folder_paths.into_iter()),
        file_rows,
        plot_sets,
        loose_images: loose_cards,
        datasets,
        warnings,
        ignored_dir_count,
    })
}

#[tauri::command]
fn pick_project_root(app: tauri::AppHandle, current_root: Option<String>) -> Result<Option<String>, String> {
    let mut dialog = app.dialog().file().set_title("Open MPLGallery project");
    if let Some(root) = current_root.as_deref().map(str::trim).filter(|value| !value.is_empty()) {
        dialog = dialog.set_directory(root);
    }
    let selected = dialog
        .blocking_pick_folder()
        .map(|path| path.into_path())
        .transpose()
        .map_err(|error| error.to_string())?;
    Ok(selected.map(|path| path.to_string_lossy().replace('\\', "/")))
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![get_app_bootstrap, scan_project, pick_project_root])
        .run(tauri::generate_context!())
        .expect("failed to run mplgallery tauri app");
}
