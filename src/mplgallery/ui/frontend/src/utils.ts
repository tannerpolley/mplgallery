import type { FileItem, PlotRecord, RedrawMetadata, SeriesStyle, SubplotMetadata, TreeNode } from "./types";

export type GalleryStatus = {
  totalPlots: number;
  matchedCsvs: number;
  missingCsvs: number;
  renderErrors: number;
};

export function plotIdSet(records: PlotRecord[]): Set<string> {
  return new Set(records.map((record) => record.id));
}

export function reconcileCheckedPlotIds(
  records: PlotRecord[],
  current: Set<string>,
  hasUserFilter: boolean,
): Set<string> {
  const validIds = plotIdSet(records);
  if (!hasUserFilter) return new Set();
  return new Set([...current].filter((plotId) => validIds.has(plotId)));
}

export function galleryStatus(records: PlotRecord[]): GalleryStatus {
  const matchedCsvs = records.filter((record) => Boolean(record.csvPath)).length;
  return {
    totalPlots: records.length,
    matchedCsvs,
    missingCsvs: records.length - matchedCsvs,
    renderErrors: records.filter((record) => Boolean(record.renderError)).length,
  };
}

export function emptyGalleryMessage(
  records: PlotRecord[],
  query: string,
  checkedPlotIds: Set<string>,
  hasUserFilter: boolean,
  itemNoun = "plot sets",
): string {
  if (records.length === 0) {
    return "No plot image files were found. If a manifest exists, the generated artifacts may still need to be built.";
  }
  if (query.trim()) return "No plots match this search.";
  if (checkedPlotIds.size === 0) {
    return `Select ${itemNoun} from Files to build a gallery.`;
  }
  return "No visible plots for the current filters.";
}

export function foldersFor(record: PlotRecord): string[] {
  const parts = record.imagePath.split("/");
  const folders = ["."];
  let current = "";
  for (let index = 0; index < parts.length - 1; index += 1) {
    current = current ? `${current}/${parts[index]}` : parts[index];
    folders.push(current);
  }
  return folders;
}

export function buildTree(files: FileItem[], rootLabel: string): TreeNode {
  const folderCounts = new Map<string, number>();
  files.forEach((file) => {
    foldersForFile(file).forEach((folder) => {
      folderCounts.set(folder, (folderCounts.get(folder) ?? 0) + 1);
    });
  });

  const makeNode = (path: string): TreeNode => {
    const prefix = path === "." ? "" : `${path}/`;
    const children = [...folderCounts.keys()]
      .filter((folder) => folder !== path && folder.startsWith(prefix))
      .filter((folder) => !folder.slice(prefix.length).includes("/"))
      .sort()
      .map(makeNode);
    const directFiles = files
      .filter((file) => parentFolderForPath(file.path) === path)
      .sort((left, right) => left.name.localeCompare(right.name));
    return {
      path,
      label: path === "." ? rootLabel : (path.split("/").pop() ?? path),
      count: folderCounts.get(path) ?? 0,
      children,
      autoExpand: path !== "." && directFiles.length === 0 && children.length === 1,
      files: directFiles,
    };
  };
  return makeNode(".");
}

export function projectRootName(rootPath: string): string {
  const normalized = rootPath.replace(/\\/g, "/").replace(/\/+$/, "");
  const parts = normalized.split("/").filter(Boolean);
  return parts.at(-1) ?? "Project root";
}

export function filterRecords(
  records: PlotRecord[],
  query: string,
  selectedPlotIds: Set<string>,
): PlotRecord[] {
  const normalized = query.trim().toLowerCase();
  return records.filter((record) => {
    if (!selectedPlotIds.has(record.id)) return false;
    if (!normalized) return true;
    return [record.name, record.imagePath, record.csvPath, record.rawCsvPath]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(normalized);
  });
}

export function normalizeRedraw(redraw: RedrawMetadata, series: SeriesStyle[]): RedrawMetadata {
  return {
    kind: redraw.kind ?? "line",
    x: redraw.x,
    y: series.filter((style) => style.y.trim()).map((style) => style.y),
    title: emptyToUndefined(redraw.title),
    xlabel: emptyToUndefined(redraw.xlabel),
    xlabel_unit: emptyToUndefined(redraw.xlabel_unit),
    ylabel: emptyToUndefined(redraw.ylabel),
    ylabel_unit: emptyToUndefined(redraw.ylabel_unit),
    xscale: redraw.xscale ?? "linear",
    yscale: redraw.yscale ?? "linear",
    xlim: redraw.xlim ?? null,
    ylim: redraw.ylim ?? null,
    grid: redraw.grid ?? true,
    grid_axis: redraw.grid_axis ?? "both",
    grid_alpha: redraw.grid_alpha ?? 0.25,
    legend_title: emptyToUndefined(redraw.legend_title),
    legend_location: redraw.legend_location ?? "best",
    bins: redraw.bins ?? undefined,
    figure: {
      width_inches: Number(redraw.figure?.width_inches ?? 6),
      height_inches: Number(redraw.figure?.height_inches ?? 4),
      dpi: Number(redraw.figure?.dpi ?? 150),
      facecolor: emptyToUndefined(redraw.figure?.facecolor),
      constrained_layout: redraw.figure?.constrained_layout ?? false,
    },
    series: series.filter((style) => style.y.trim()),
    subplots: redraw.subplots?.map(normalizeSubplot) ?? [],
    subplot_rows: redraw.subplot_rows,
    subplot_cols: redraw.subplot_cols,
    sharex: redraw.sharex ?? false,
    sharey: redraw.sharey ?? false,
  };
}

function normalizeSubplot(subplot: SubplotMetadata): SubplotMetadata {
  return {
    subplot_id: subplot.subplot_id,
    kind: subplot.kind ?? "line",
    x: subplot.x,
    title: emptyToUndefined(subplot.title),
    xlabel: emptyToUndefined(subplot.xlabel),
    xlabel_unit: emptyToUndefined(subplot.xlabel_unit),
    ylabel: emptyToUndefined(subplot.ylabel),
    ylabel_unit: emptyToUndefined(subplot.ylabel_unit),
    xscale: subplot.xscale ?? "linear",
    yscale: subplot.yscale ?? "linear",
    xlim: subplot.xlim ?? null,
    ylim: subplot.ylim ?? null,
    grid: subplot.grid ?? true,
    grid_axis: subplot.grid_axis ?? "both",
    grid_alpha: subplot.grid_alpha ?? 0.25,
    legend_title: emptyToUndefined(subplot.legend_title),
    legend_location: subplot.legend_location ?? "best",
    bins: subplot.bins ?? undefined,
    series: subplot.series?.filter((style) => style.y.trim()) ?? [],
  };
}

export function parseLimits(minValue: string, maxValue: string): [number, number] | null {
  const minText = minValue.trim();
  const maxText = maxValue.trim();
  if (!minText && !maxText) return null;
  const min = Number(minText);
  const max = Number(maxText);
  if (!Number.isFinite(min) || !Number.isFinite(max) || min >= max) {
    throw new Error("Limits need numeric min and max values, with min less than max.");
  }
  return [min, max];
}

export function clampNumber(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function shortRootLabel(rootPath: string): string {
  const normalized = rootPath.replace(/\\/g, "/").replace(/\/+$/, "");
  if (!normalized) return "No root";
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length <= 2) return normalized;
  return `…/${parts.slice(-2).join("/")}`;
}

function foldersForFile(file: FileItem): string[] {
  const parts = file.path.split("/");
  const folders = ["."];
  let current = "";
  for (let index = 0; index < parts.length - 1; index += 1) {
    current = current ? `${current}/${parts[index]}` : parts[index];
    folders.push(current);
  }
  return folders;
}

function parentFolderForPath(path: string): string {
  const parts = path.split("/");
  if (parts.length <= 1) return ".";
  return parts.slice(0, -1).join("/");
}

export function visibleRecentRoots(activeRoot: string, recentRoots: string[]): string[] {
  const activeKey = rootKey(activeRoot);
  const seen = new Set<string>();
  const roots: string[] = [];
  recentRoots.forEach((root) => {
    const key = rootKey(root);
    if (!key || key === activeKey || seen.has(key)) return;
    seen.add(key);
    roots.push(root);
  });
  return roots;
}

export function eventId(type: string): string {
  return `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyToUndefined(value: string | undefined): string | undefined {
  const trimmed = value?.trim() ?? "";
  return trimmed ? trimmed : undefined;
}

function rootKey(rootPath: string): string {
  return rootPath.trim().replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}
