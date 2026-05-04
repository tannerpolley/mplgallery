import type { PlotRecord, RedrawMetadata, SeriesStyle, TreeNode } from "./types";

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
  selectedFolder: string,
): PlotRecord[] {
  const normalized = query.trim().toLowerCase();
  return records.filter((record) => {
    const folderMatch = foldersFor(record).includes(selectedFolder);
    if (!folderMatch) return false;
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
    ylabel: emptyToUndefined(redraw.ylabel),
    xscale: redraw.xscale ?? "linear",
    yscale: redraw.yscale ?? "linear",
    xlim: redraw.xlim ?? null,
    ylim: redraw.ylim ?? null,
    grid: redraw.grid ?? true,
    figure: {
      width_inches: Number(redraw.figure?.width_inches ?? 6),
      height_inches: Number(redraw.figure?.height_inches ?? 4),
      dpi: Number(redraw.figure?.dpi ?? 150),
    },
    series: series.filter((style) => style.y.trim()),
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

export function eventId(type: string): string {
  return `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function emptyToUndefined(value: string | undefined): string | undefined {
  const trimmed = value?.trim() ?? "";
  return trimmed ? trimmed : undefined;
}
