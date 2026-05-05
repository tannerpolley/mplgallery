import type { PlotRecord, RedrawMetadata, SeriesStyle, SubplotMetadata, TreeNode } from "./types";

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

export function buildTree(records: PlotRecord[]): TreeNode {
  const folderCounts = new Map<string, number>();
  records.forEach((record) => {
    foldersFor(record).forEach((folder) => {
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
    return {
      path,
      label: path === "." ? "All plots" : (path.split("/").pop() ?? path),
      count: folderCounts.get(path) ?? 0,
      children,
    };
  };
  return makeNode(".");
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

export function eventId(type: string): string {
  return `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyToUndefined(value: string | undefined): string | undefined {
  const trimmed = value?.trim() ?? "";
  return trimmed ? trimmed : undefined;
}
