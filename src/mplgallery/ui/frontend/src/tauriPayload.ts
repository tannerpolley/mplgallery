import { convertFileSrc } from "@tauri-apps/api/core";
import type { BrowserPayload, DatasetRecord, PlotRecord, PlotSetAttachment, PlotSetEntity } from "./types";
import type { TauriBootstrap, TauriCsvDataset, TauriLooseImageCard, TauriPlotSetCard, TauriScanResult } from "./tauri-types";

function joinPath(rootPath: string, relativePath: string): string {
  const normalizedRoot = rootPath.replace(/\\/g, "/").replace(/\/+$/, "");
  const normalizedRelative = relativePath.replace(/\\/g, "/").replace(/^\/+/, "");
  return `${normalizedRoot}/${normalizedRelative}`;
}

function maybeImageSrc(fullPath: string): string | null {
  try {
    const converted = convertFileSrc(fullPath);
    if (converted) return converted;
  } catch {
    // Fallback for non-Tauri browser preview mode.
  }
  return fileUrlFromPath(fullPath);
}

function fileUrlFromPath(fullPath: string): string {
  const normalized = fullPath.replace(/\\/g, "/");
  if (/^[A-Za-z]:\//.test(normalized)) {
    return `file:///${encodeURI(normalized)}`;
  }
  if (normalized.startsWith("/")) {
    return `file://${encodeURI(normalized)}`;
  }
  return `file://${encodeURI(normalized)}`;
}

function lastPathSegment(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] ?? path;
}

function attachmentToPlotRecord(
  rootPath: string,
  attachment: TauriPlotSetCard["attachments"][number],
  sourceDatasetId: string | null,
): PlotRecord | null {
  if (attachment.kind !== "png" && attachment.kind !== "svg") return null;
  const fullPath = joinPath(rootPath, attachment.relativePath);
  return {
    id: attachment.id,
    name: lastPathSegment(attachment.relativePath),
    kind: attachment.kind.toUpperCase(),
    imagePath: attachment.relativePath,
    sourceDatasetId,
    csvPath: null,
    rawCsvPath: null,
    confidence: "exact",
    imageSrc: maybeImageSrc(fullPath),
    cachePath: null,
    renderError: null,
    csvPreview: null,
    csvColumns: [],
    previewColumns: [],
    previewRows: [],
    previewTruncated: false,
    previewError: null,
    editable: false,
    redraw: {},
    series: [],
    widthPx: attachment.widthPx ?? null,
    heightPx: attachment.heightPx ?? null,
    sizeBytes: attachment.sizeBytes ?? null,
    imageFormat: attachment.kind.toUpperCase(),
    modifiedAt: attachment.modifiedAt ?? null,
  };
}

function toDataset(dataset: TauriCsvDataset): DatasetRecord {
  return {
    id: dataset.id,
    displayName: dataset.displayName,
    path: dataset.relativePath,
    csvRootId: dataset.folderPath,
    csvRootPath: dataset.folderPath,
    draftStatus: "not_initialized",
    associatedPlotIds: dataset.linkedImageIds,
    associatedPlotId: dataset.linkedImageIds[0] ?? null,
    rowCountSampled: dataset.rowCountSampled,
    columns: dataset.columns,
    numericColumns: dataset.numericColumns,
    categoricalColumns: dataset.categoricalColumns,
    previewColumns: dataset.previewColumns,
    previewRows: dataset.previewRows,
    previewTruncated: dataset.previewTruncated,
    previewError: dataset.previewError ?? null,
  };
}

function toPlotSet(plotSet: TauriPlotSetCard): PlotSetEntity {
  const attachments: PlotSetAttachment[] = plotSet.attachments.map((attachment) => ({
    id: attachment.id,
    type: attachment.kind === "csv" ? "csv" : attachment.kind,
    displayName: lastPathSegment(attachment.relativePath),
    sourcePath: attachment.relativePath,
    datasetId: attachment.kind === "csv" ? `dataset:${attachment.relativePath}` : null,
    plotId: attachment.kind === "csv" ? null : attachment.id,
  }));
  const preferredFigure = attachments.find((attachment) => attachment.id === plotSet.preferredFigureId) ?? null;
  return {
    plotSetId: plotSet.id,
    title: plotSet.title,
    folderPath: plotSet.folderPath,
    attachments,
    preferredFigure,
    editable: false,
    checked: false,
    renderStatus: plotSet.renderStatus,
  };
}

function toLooseImagePlotSet(card: TauriLooseImageCard): PlotSetEntity {
  return {
    plotSetId: card.id,
    title: card.title,
    folderPath: card.folderPath,
    attachments: [
      {
        id: card.image.id,
        type: card.image.kind,
        displayName: lastPathSegment(card.image.relativePath),
        sourcePath: card.image.relativePath,
        datasetId: null,
        plotId: card.image.id,
      },
    ],
    preferredFigure: {
      id: card.image.id,
      type: card.image.kind,
      displayName: lastPathSegment(card.image.relativePath),
      sourcePath: card.image.relativePath,
      datasetId: null,
      plotId: card.image.id,
    },
    editable: false,
    checked: false,
    renderStatus: "ready",
  };
}

export function tauriToBrowserPayload(
  bootstrap: TauriBootstrap,
  scan: TauriScanResult,
  browseModeOverride?: "plot-set-manager" | "image-library",
): BrowserPayload {
  const datasets = scan.datasets.map(toDataset);
  const datasetByFolder = new Map<string, TauriCsvDataset[]>();
  scan.datasets.forEach((dataset) => {
    const linked = datasetByFolder.get(dataset.folderPath) ?? [];
    linked.push(dataset);
    datasetByFolder.set(dataset.folderPath, linked);
  });

  const linkedRecords = scan.plotSets.flatMap((plotSet) => {
    const linkedDatasetId = datasetByFolder.get(plotSet.folderPath)?.[0]?.id ?? null;
    return plotSet.attachments
      .map((attachment) => attachmentToPlotRecord(scan.rootPath, attachment, linkedDatasetId))
      .filter((record): record is PlotRecord => Boolean(record));
  });
  const looseRecords = scan.looseImages.map((card) => ({
    id: card.image.id,
    name: lastPathSegment(card.image.relativePath),
    kind: card.image.kind.toUpperCase(),
    imagePath: card.image.relativePath,
    sourceDatasetId: null,
    csvPath: null,
    rawCsvPath: null,
    confidence: "exact",
    imageSrc: maybeImageSrc(joinPath(scan.rootPath, card.image.relativePath)),
    cachePath: null,
    renderError: null,
    csvPreview: null,
    csvColumns: [],
    previewColumns: [],
    previewRows: [],
    previewTruncated: false,
    previewError: null,
    editable: false,
    redraw: {},
    series: [],
    widthPx: card.image.widthPx ?? null,
    heightPx: card.image.heightPx ?? null,
    sizeBytes: card.image.sizeBytes ?? null,
    imageFormat: card.imageFormat ?? card.image.kind.toUpperCase(),
    modifiedAt: card.image.modifiedAt ?? null,
  }));
  const plotSets = [...scan.plotSets.map(toPlotSet), ...scan.looseImages.map(toLooseImagePlotSet)];

  return {
    projectRoot: scan.rootPath,
    browseMode: browseModeOverride ?? scan.browseMode,
    appInfo: {
      ...bootstrap.appInfo,
      updateInstall: undefined,
    },
    userSettings: bootstrap.userSettings,
    rootContext: {
      activeRoot: bootstrap.rootContext.activeRoot,
      launchRoot: bootstrap.rootContext.activeRoot,
      recentRoots: bootstrap.rootContext.recentRoots,
      error: bootstrap.rootContext.error ?? null,
      showRootChooser: false,
    },
    selectedPlotId: null,
    datasets,
    plotSets,
    folderView: { nodes: [], rootId: ".", defaultSelectedPath: "." },
    filesView: { rows: [] },
    records: [...linkedRecords, ...looseRecords],
    files: [],
    options: {
      plotKinds: [],
      lineStyles: [],
      markers: [],
      colors: [],
      units: [],
      scales: ["linear"],
      gridAxes: ["both"],
      legendLocations: ["best"],
      hatches: [],
    },
    errors: {},
  };
}
