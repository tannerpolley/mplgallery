# T002 Tauri data contract

## Target command surface

The first Tauri app should replace the Streamlit payload/event bridge with direct desktop commands and local React state.

Recommended commands:

- `get_app_bootstrap()`
  - Returns app name/version, current settings, recent roots, active root if any, and update-check status.
- `open_project_dialog()`
  - Opens the native folder picker and returns the chosen root or cancellation.
- `scan_project(root_path, mode_hint?)`
  - Main scan/index command.
  - Returns the classified project tree, records, lightweight file metadata, and inferred browse mode.
- `set_active_root(root_path)`
  - Persists the active root according to settings and returns a refreshed bootstrap/scan result.
- `refresh_scan(root_path)`
  - Explicit rescan for the active project.
- `forget_recent_root(root_path)`
  - Removes one recent root from memory.
- `clear_recent_roots()`
  - Clears recent roots and last-active-root state.
- `set_user_settings(remember_recent_projects, restore_last_project_on_startup)`
  - Persists project-memory settings.
- `get_csv_preview(asset_id, max_rows, max_columns)`
  - Returns a tight preview table for one CSV without requiring full app rerender payload rebuild.
- `get_csv_summary(asset_id)`
  - Returns lightweight summary information for the CSV pane/card.
- `read_text_attachment(asset_id, max_bytes)`
  - Optional compatibility command for plain-text sidecars that survive scope review.
- `check_for_updates()`
  - Refreshes release/update status for the desktop app.
- `install_update(download_url or release_id)`
  - Preserves the installed-app update path as a desktop command rather than a Streamlit event.

## Data shapes

### App bootstrap

```ts
type AppBootstrap = {
  appInfo: {
    name: string;
    version: string;
    appId: string;
    canInstallUpdates: boolean;
    update?: UpdateInfo;
  };
  userSettings: {
    rememberRecentProjects: boolean;
    restoreLastProjectOnStartup: boolean;
  };
  rootContext: {
    activeRoot: string;
    recentRoots: string[];
    error?: string | null;
  };
};
```

### Project scan result

```ts
type ProjectScanResult = {
  rootPath: string;
  browseMode: "plot-set-manager" | "image-library";
  folderTree: FolderNode[];
  fileRows: FileRow[];
  plotSets: PlotSetCard[];
  looseImages: ImageCard[];
  datasets: CsvDataset[];
  warnings: string[];
  ignoredDirCount: number;
};
```

### Shared asset identity

Every returned entity should carry a stable app-owned id rather than exposing path strings as the only join key.

```ts
type AssetRef = {
  id: string;
  relativePath: string;
  absolutePath?: string; // backend only if needed
  kind: "csv" | "png" | "svg";
  sizeBytes?: number | null;
  modifiedAt?: string | null;
};
```

### Classified project entities

```ts
type CsvDataset = {
  id: string;
  displayName: string;
  relativePath: string;
  folderPath: string;
  rowCountSampled: number;
  columns: string[];
  numericColumns: string[];
  categoricalColumns: string[];
  linkedImageIds: string[];
};

type PlotSetCard = {
  id: string;
  title: string;
  folderPath: string;
  classification: "analysis-linked";
  attachments: AssetRef[];
  preferredFigureId?: string | null;
  renderStatus: "ready" | "missing_figure" | "error";
};

type ImageCard = {
  id: string;
  title: string;
  folderPath: string;
  classification: "loose-image";
  image: AssetRef;
  siblingCsvIds: string[];
  widthPx?: number | null;
  heightPx?: number | null;
  imageFormat?: string | null;
};
```

## Classification rules

1. `analysis-linked`
   - Prefer folders under `results/**`.
   - Group CSV and image attachments when they share the current plot-set folder structure or current dataset/linking heuristics.
   - Preserve folder tree and plot-set grouping behavior from the current app where that behavior is about discovery, not editing.
2. `loose-image`
   - PNG/SVG files outside recognized plot-set organization remain discoverable.
   - These must not pollute the analysis-linked plot-set list by default.
   - Pictures mode can show only image-backed rows/cards from this class plus image attachments from linked plot sets, depending on UX decision later.
3. `image-library` browse mode
   - Auto-enable when no CSV roots and no recognized plot-set folders exist but image assets do.
4. Unsupported or unreadable files
   - Exclude from normal rows/cards.
   - Return warnings or per-asset errors instead of failing the entire scan.

## CSV minimum behavior

The new app scope is browsing, not plotting.

Minimum preview fields:

- `previewColumns`
- `previewRows`
- `previewTruncated`
- `previewError`

Minimum summary fields:

- `rowCountSampled`
- `columnCount`
- `numericColumns`
- `categoricalColumns`
- `missingValueCounts` for sampled rows or capped scan
- `numericRanges` for numeric columns when cheap

Large CSV behavior:

- Cap preview rows and columns.
- Avoid reading the full file for every card during project scan.
- Defer summary work until the CSV tab or inspector actually opens.

## Image loading guidance

- Do not use Streamlit-style base64 payload hydration for all images.
- Prefer native file-path loading through Tauri-safe asset URLs so unchanged PNG/SVG files are not copied into every payload.
- Preserve width/height/format metadata in scan results, but keep binary image loading separate from the main scan payload.

## Failure modes and fallback behavior

- Missing root: return root-context error and blank project state.
- Unreadable directory: return scan error for the root, not a crash.
- Malformed CSV: preview/summary returns `previewError`; keep the file visible.
- Corrupt PNG: keep the image row/card with missing dimensions plus warning.
- Oversized projects: allow progressive or deferred hydration later; do not require full preview generation in `scan_project`.
- Existing sidecars/YAML: treat as optional read-only compatibility attachments unless later scope explicitly reintroduces them.

## Scope exclusions carried into Judge review

- No Matplotlib redraw metadata in the new contract.
- No YAML editing or save commands.
- No draft generation, rerender, or generated-plot controls.
- No pandas- or Python-required runtime contract for the installed app.
