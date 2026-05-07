import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileImage,
  Folder,
  FolderOpen,
  Menu,
  Table2,
} from "lucide-react";
import { Streamlit } from "streamlit-component-lib";
import type {
  BrowserPayload,
  DatasetRecord,
  FileItem,
  PlotRecord,
  RedrawMetadata,
  SeriesStyle,
  SubplotMetadata,
  TreeNode,
} from "./types";
import {
  buildTree,
  clampNumber,
  emptyGalleryMessage,
  eventId,
  filterRecords,
  galleryStatus,
  normalizeRedraw,
  parseLimits,
  projectRootName,
  reconcileCheckedPlotIds,
} from "./utils";
import "./App.css";

type StreamlitProps = {
  payload?: BrowserPayload;
};

const emptyPayload: BrowserPayload = {
  projectRoot: "",
  rootContext: {
    activeRoot: "",
    launchRoot: "",
    recentRoots: [],
    error: null,
    showRootChooser: false,
  },
  selectedPlotId: null,
  datasets: [],
  records: [],
  files: [],
  options: {
    plotKinds: ["line", "scatter", "bar", "barh", "area", "hist", "step"],
    lineStyles: [],
    markers: [],
    colors: [],
    units: [],
    scales: ["linear", "log", "symlog", "logit"],
    gridAxes: ["both", "x", "y"],
    legendLocations: ["best"],
    hatches: [],
  },
  errors: {},
};

const defaultLayout = {
  treeWidth: 240,
};

const layoutBounds = {
  treeMin: 170,
  treeMax: 380,
};

function App(props: StreamlitProps) {
  const payload = props.payload ?? emptyPayload;
  const rootContext = payload.rootContext ?? {
    activeRoot: payload.projectRoot,
    launchRoot: payload.projectRoot,
    recentRoots: [],
    error: null,
    showRootChooser: false,
  };
  const [selectedPlotId, setSelectedPlotId] = useState<string | null>(payload.selectedPlotId ?? null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState(".");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [checkedPlotIds, setCheckedPlotIds] = useState<Set<string>>(() => new Set());
  const [checkedDatasetIds, setCheckedDatasetIds] = useState<Set<string>>(() => new Set());
  const [hasUserFilter, setHasUserFilter] = useState(false);
  const [query, setQuery] = useState("");
  const [tileSize, setTileSize] = useState(230);
  const [maximizedPlotId, setMaximizedPlotId] = useState<string | null>(null);
  const [expandedCardIds, setExpandedCardIds] = useState<Set<string>>(new Set());
  const [layout, setLayout] = useState(defaultLayout);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const [draftPreferencesDatasetId, setDraftPreferencesDatasetId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedPlotId(payload.selectedPlotId ?? null);
  }, [payload.selectedPlotId]);

  useEffect(() => {
    setSelectedDatasetId(null);
    setSelectedFileId(null);
    setSelectedPlotId(payload.selectedPlotId ?? null);
    setCheckedPlotIds(new Set());
    setCheckedDatasetIds(new Set());
    setHasUserFilter(false);
    setExpandedCardIds(new Set());
    setMaximizedPlotId(null);
  }, [rootContext.activeRoot, payload.selectedPlotId]);

  useEffect(() => {
    setCheckedPlotIds((current) => reconcileCheckedPlotIds(payload.records, current, hasUserFilter));
  }, [payload.records, hasUserFilter]);

  useEffect(() => {
    setCheckedDatasetIds((current) => {
      if (!hasUserFilter) return new Set();
      const validIds = new Set(payload.datasets.map((dataset) => dataset.id));
      return new Set([...current].filter((datasetId) => validIds.has(datasetId)));
    });
  }, [payload.datasets, hasUserFilter]);

  const tree = useMemo(
    () => buildTree(payload.files, projectRootName(rootContext.activeRoot)),
    [payload.files, rootContext.activeRoot],
  );
  const effectiveCheckedPlotIds = useMemo(
    () => checkedPlotIds,
    [checkedPlotIds],
  );
  const selectedDataset = payload.datasets.find((dataset) => dataset.id === selectedDatasetId) ?? null;
  const draftPreferencesDataset = payload.datasets.find((dataset) => dataset.id === draftPreferencesDatasetId) ?? null;
  const checkedCsvCards = useMemo(
    () =>
      payload.datasets.filter((dataset) => {
        if (!checkedDatasetIds.has(dataset.id)) return false;
        if (!query.trim()) return true;
        const haystack = [dataset.displayName, dataset.path, dataset.csvRootPath].join(" ").toLowerCase();
        return haystack.includes(query.trim().toLowerCase());
      }),
    [payload.datasets, checkedDatasetIds, query],
  );
  const selectedPlotRecord = selectedPlotId
    ? payload.records.find((record) => record.id === selectedPlotId) ?? null
    : null;
  const visibleRecords = useMemo(
    () => filterRecords(payload.records, query, effectiveCheckedPlotIds),
    [payload.records, query, effectiveCheckedPlotIds],
  );
  const status = useMemo(() => galleryStatus(payload.records), [payload.records]);
  const noVisiblePlotsMessage = emptyGalleryMessage(
    payload.records,
    query,
    effectiveCheckedPlotIds,
    hasUserFilter,
  );
  const selectedRecord = selectedPlotRecord ?? null;
  const maximizedRecord =
    payload.records.find((record) => record.id === maximizedPlotId) ?? selectedRecord;
  function selectPlot(plotId: string) {
    setSelectedDatasetId(null);
    setSelectedFileId(`plot:${plotId}`);
    setSelectedPlotId(plotId);
  }

  function selectDataset(datasetId: string) {
    if (selectedDatasetId === datasetId) {
      setSelectedDatasetId(null);
      setSelectedFileId(null);
      return;
    }
    setSelectedDatasetId(datasetId);
    setSelectedFileId(`csv:${datasetId}`);
  }

  function draftDataset(datasetId: string) {
    setDraftPreferencesDatasetId(datasetId);
  }

  function draftDatasetWithPreferences(datasetId: string, redraw: RedrawMetadata, outputFormat: "svg" | "png") {
    Streamlit.setComponentValue({
      event: {
        id: eventId("draft_dataset_with_preferences"),
        type: "draft_dataset_with_preferences",
        dataset_id: datasetId,
        redraw,
        output_format: outputFormat,
      },
    });
    setDraftPreferencesDatasetId(null);
  }

  function draftCheckedDatasets() {
    Streamlit.setComponentValue({
      event: {
        id: eventId("draft_checked_datasets"),
        type: "draft_checked_datasets",
        dataset_ids: [...checkedDatasetIds],
      },
    });
  }

  function maximizePlot(plotId: string) {
    selectPlot(plotId);
    setMaximizedPlotId(plotId);
  }

  function updateQuery(value: string) {
    setQuery(value);
  }

  function updateTileSize(value: number) {
    setTileSize(value);
  }

  function startTreeResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = layout.treeWidth;
    const handlePointerMove = (moveEvent: PointerEvent) => {
      const nextWidth = clampNumber(
        startWidth + moveEvent.clientX - startX,
        layoutBounds.treeMin,
        layoutBounds.treeMax,
      );
      setLayout((current) => ({ ...current, treeWidth: nextWidth }));
    };
    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      document.body.classList.remove("mg-is-resizing");
    };

    document.body.classList.add("mg-is-resizing");
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp, { once: true });
  }

  function resizeTreeWithKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 16 : -16;
    setLayout((current) => ({
      ...current,
      treeWidth: clampNumber(current.treeWidth + delta, layoutBounds.treeMin, layoutBounds.treeMax),
    }));
  }

  const shellStyle = {
    "--tree-width": `${layout.treeWidth}px`,
  } as CSSProperties;

  return (
    <div className={`mg-shell ${treeCollapsed ? "is-tree-collapsed" : ""}`} style={shellStyle}>
      <aside className="mg-tree-panel" aria-label="Output tree">
        <div className="mg-tree-head">
          {treeCollapsed ? null : <div className="mg-panel-title">Output tree</div>}
          <button
            type="button"
            className="mg-tree-collapse"
            aria-expanded={!treeCollapsed}
            aria-label={treeCollapsed ? "Show output tree" : "Hide output tree"}
            onClick={() => setTreeCollapsed((current) => !current)}
          >
            <Menu aria-hidden="true" size={15} />
          </button>
        </div>
        {treeCollapsed ? null : (
          <>
            <label className="mg-sr-only" htmlFor="plot-search">
              Search plots or CSV files
            </label>
            <input
              id="plot-search"
              className="mg-search"
              value={query}
              placeholder="Search plots or CSV files"
              onChange={(event) => updateQuery(event.target.value)}
            />
            <Tree
              node={tree}
              files={payload.files}
              records={payload.records}
              selectedFolder={selectedFolder}
              selectedPlotId={selectedPlotId}
              selectedDatasetId={selectedDatasetId}
              selectedFileId={selectedFileId}
              checkedPlotIds={effectiveCheckedPlotIds}
              checkedDatasetIds={checkedDatasetIds}
              onSelectFolder={setSelectedFolder}
              onSelectPlot={selectPlot}
              onSelectDataset={selectDataset}
              onToggleFolder={(path, checked, plotIds, datasetIds) => {
                setHasUserFilter(true);
                setCheckedPlotIds((current) => {
                  const next = new Set(current);
                  plotIds.forEach((plotId) => {
                    if (checked) next.add(plotId);
                    else next.delete(plotId);
                  });
                  return next;
                });
                setCheckedDatasetIds((current) => {
                  const next = new Set(current);
                  datasetIds.forEach((datasetId) => {
                    if (checked) next.add(datasetId);
                    else next.delete(datasetId);
                  });
                  return next;
                });
              }}
              onTogglePlot={(plotId, checked) => {
                setHasUserFilter(true);
                setCheckedPlotIds((current) => {
                  const next = new Set(current);
                  if (checked) next.add(plotId);
                  else next.delete(plotId);
                  return next;
                });
              }}
              onToggleDataset={(datasetId, checked) => {
                setHasUserFilter(true);
                setCheckedDatasetIds((current) => {
                  const next = new Set(current);
                  if (checked) next.add(datasetId);
                  else next.delete(datasetId);
                  return next;
                });
              }}
            />
          </>
        )}
      </aside>

      <div
        className="mg-resizer"
        role="separator"
        aria-label="Resize output tree"
        aria-orientation="vertical"
        aria-valuemin={layoutBounds.treeMin}
        aria-valuemax={layoutBounds.treeMax}
        aria-valuenow={layout.treeWidth}
        tabIndex={0}
        onKeyDown={resizeTreeWithKeyboard}
        onPointerDown={startTreeResize}
      />

      <main className="mg-workspace" aria-label="Plot workspace">
        <div className="mg-workspace-header">
          <div className="mg-workspace-heading">
            <div className="mg-eyebrow">{payload.files.length} files</div>
            <div className="mg-workspace-title">Plot file explorer</div>
          </div>
          <div className="mg-header-actions">
            {checkedDatasetIds.size ? (
              <button className="mg-inspector-toggle" type="button" onClick={draftCheckedDatasets}>
                Draft checked CSVs
              </button>
            ) : null}
            <details className="mg-status-menu">
              <summary>Status</summary>
              <div className="mg-status-popover" aria-label="Project status">
                <span>{status.totalPlots} plots</span>
                <span>{status.matchedCsvs} CSV matched</span>
                <span className={status.missingCsvs ? "is-warning" : ""}>{status.missingCsvs} missing CSV</span>
                <span className={status.renderErrors ? "is-warning" : ""}>{status.renderErrors} render errors</span>
              </div>
            </details>
            <button className="mg-inspector-toggle" type="button" onClick={() => setLayout(defaultLayout)}>
              Reset layout
            </button>
          </div>
        </div>
        <div className={`mg-workspace-body ${selectedDataset ? "has-drawer" : ""}`}>
          <section className="mg-gallery" aria-label="Plot gallery">
            <div className="mg-gallery-toolbar">
              <strong>{`${visibleRecords.length} plot${visibleRecords.length === 1 ? "" : "s"}`}</strong>
              <label>
                Tile size
                <input
                  type="range"
                  min="160"
                  max="1400"
                  step="20"
                  value={tileSize}
                  onChange={(event) => updateTileSize(Number(event.target.value))}
                />
              </label>
            </div>
            <div className="mg-card-grid" style={{ ["--tile-size" as string]: `${tileSize}px` }}>
              {visibleRecords.length || checkedCsvCards.length ? (
                <>
                  {visibleRecords.map((record) => (
                    <PlotCard
                      key={record.id}
                      record={record}
                      selected={record.id === selectedRecord?.id}
                      onMaximize={() => maximizePlot(record.id)}
                      expanded={expandedCardIds.has(record.id)}
                      onToggleExpanded={() => {
                        setExpandedCardIds((current) => {
                          const next = new Set(current);
                          if (next.has(record.id)) next.delete(record.id);
                          else next.add(record.id);
                          return next;
                        });
                      }}
                    />
                  ))}
                  {checkedCsvCards
                    .map((dataset) => (
                      <CsvDraftCard
                        key={dataset.id}
                        dataset={dataset}
                        selected={dataset.id === selectedDatasetId}
                        onSelect={() => selectDataset(dataset.id)}
                        onDraft={() => draftDataset(dataset.id)}
                      />
                    ))}
                </>
              ) : (
                <EmptyGallery message={noVisiblePlotsMessage} />
              )}
            </div>
          </section>
          {selectedDataset ? (
            <CsvPreviewDrawer
              dataset={selectedDataset}
              onClose={() => {
                setSelectedDatasetId(null);
                setSelectedFileId(null);
              }}
              onDraft={() => draftDataset(selectedDataset.id)}
            />
          ) : null}
        </div>
      </main>

      {maximizedPlotId && maximizedRecord ? (
        <PlotLookModal
          payload={payload}
          record={maximizedRecord}
          error={payload.errors[maximizedRecord.id]}
          onClose={() => setMaximizedPlotId(null)}
          onSave={(redraw) => {
            Streamlit.setComponentValue({
              event: {
                id: eventId("save_redraw_metadata"),
                type: "save_redraw_metadata",
                plot_id: maximizedRecord.id,
                redraw,
              },
            });
          }}
        />
      ) : null}

      {draftPreferencesDataset ? (
        <CsvDraftPreferencesModal
          payload={payload}
          dataset={draftPreferencesDataset}
          onClose={() => setDraftPreferencesDatasetId(null)}
          onGenerate={(redraw, outputFormat) => draftDatasetWithPreferences(draftPreferencesDataset.id, redraw, outputFormat)}
        />
      ) : null}
    </div>
  );
}

function EmptyGallery({
  message,
  actionLabel,
  onAction,
}: {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="mg-empty">
      <span>{message}</span>
      {actionLabel && onAction ? (
        <button type="button" className="mg-primary" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

function CsvPreviewDrawer({
  dataset,
  onClose,
  onDraft,
}: {
  dataset: DatasetRecord;
  onClose: () => void;
  onDraft: () => void;
}) {
  return (
    <aside className="mg-csv-drawer" aria-label={`CSV preview for ${dataset.displayName}`}>
      <div className="mg-csv-drawer-head">
        <div>
          <div className="mg-eyebrow">CSV preview</div>
          <h2>{dataset.displayName}</h2>
          <p>{dataset.path}</p>
        </div>
        <button type="button" className="mg-inspector-toggle" onClick={onClose}>
          Back to gallery
        </button>
      </div>
      <div className="mg-badges">
        <span>{dataset.columns.length} columns</span>
        <span>{dataset.previewRows.length} preview rows</span>
        <span>{dataset.previewTruncated ? "truncated" : "full preview"}</span>
        <span>{dataset.rowCountSampled} sampled rows</span>
      </div>
      {dataset.previewError ? (
        <div className="mg-error" role="alert">
          Preview failed: {dataset.previewError}
        </div>
      ) : dataset.previewColumns.length === 0 ? (
        <div className="mg-empty">No table preview available for this CSV.</div>
      ) : (
        <div className="mg-csv-table-wrap">
          <table className="mg-csv-table">
            <thead>
              <tr>
                {dataset.previewColumns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataset.previewRows.map((row, index) => (
                <tr key={`${dataset.id}-row-${index}`}>
                  {dataset.previewColumns.map((column) => (
                    <td key={`${dataset.id}-${index}-${column}`}>{row[column] == null ? "" : String(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mg-card-actions">
        <button type="button" className="mg-primary" onClick={onDraft}>
          Generate companion plot
        </button>
      </div>
    </aside>
  );
}

function CsvDraftCard({
  dataset,
  selected,
  onSelect,
  onDraft,
}: {
  dataset: DatasetRecord;
  selected: boolean;
  onSelect: () => void;
  onDraft: () => void;
}) {
  return (
    <article className={`mg-card mg-csv-card ${selected ? "is-selected" : ""}`}>
      <button type="button" className="mg-csv-card-head" aria-label={`Preview CSV ${dataset.displayName}`} onClick={onSelect}>
        <div className="mg-csv-card-icon">
          <Table2 aria-hidden="true" size={18} />
        </div>
        <div className="mg-csv-card-title" title={dataset.displayName}>{dataset.displayName}</div>
      </button>
      <div className="mg-card-body">
        <div className="mg-card-meta">
          <div className="mg-badges">
            <span>{dataset.columns.length} columns</span>
            <span>{dataset.numericColumns.length} numeric</span>
            <span>{dataset.rowCountSampled} sampled rows</span>
            <span>{dataset.draftStatus}</span>
          </div>
        </div>
        <div className="mg-card-actions">
          <button type="button" className="mg-primary" onClick={onDraft}>
            Generate plot
          </button>
        </div>
      </div>
    </article>
  );
}

function CsvDraftPreferencesModal({
  payload,
  dataset,
  onClose,
  onGenerate,
}: {
  payload: BrowserPayload;
  dataset: DatasetRecord;
  onClose: () => void;
  onGenerate: (redraw: RedrawMetadata, outputFormat: "svg" | "png") => void;
}) {
  const inferred = useMemo(() => inferDraftRedraw(dataset), [dataset]);
  const [redraw, setRedraw] = useState<RedrawMetadata>(inferred);
  const [series, setSeries] = useState<SeriesStyle[]>(inferred.series ?? []);
  const [outputFormat, setOutputFormat] = useState<"svg" | "png">("svg");

  useEffect(() => {
    setRedraw(inferred);
    setSeries(inferred.series ?? []);
  }, [inferred]);

  const columns = dataset.columns.length ? dataset.columns : [...dataset.numericColumns, ...dataset.categoricalColumns];
  const yColumn = series[0]?.y ?? dataset.numericColumns.find((column) => column !== redraw.x) ?? dataset.numericColumns[0] ?? columns[0] ?? "";
  const defaultColor = payload.options.colors[0]?.value ?? "#1f77b4";
  const activeStyle = series[0] ?? { y: yColumn, color: defaultColor };

  function updateStyle(patch: Partial<SeriesStyle>) {
    setSeries((current) => [{ ...activeStyle, ...patch }, ...current.slice(1)]);
  }

  function generate() {
    onGenerate(normalizeRedraw(redraw, [{ ...activeStyle, y: yColumn }]), outputFormat);
  }

  return (
    <div className="mg-modal-backdrop" role="dialog" aria-modal="true" aria-label={`Draft plot preferences for ${dataset.displayName}`}>
      <section className="mg-modal-card is-compact">
        <div className="mg-modal-head">
          <div>
            <div className="mg-eyebrow">Draft plot preferences</div>
            <h2>{dataset.displayName}</h2>
          </div>
          <button type="button" className="mg-inspector-toggle" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mg-draft-form">
          <div className="mg-field-grid two">
            <label>
              Plot type
              <select value={redraw.kind ?? "line"} onChange={(event) => setRedraw((current) => ({ ...current, kind: event.target.value }))}>
                {payload.options.plotKinds.map((kind) => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Output
              <select value={outputFormat} onChange={(event) => setOutputFormat(event.target.value === "png" ? "png" : "svg")}>
                <option value="svg">SVG</option>
                <option value="png">PNG</option>
              </select>
            </label>
            <label>
              X column
              <select value={redraw.x ?? ""} onChange={(event) => setRedraw((current) => ({ ...current, x: event.target.value }))}>
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Y column
              <select value={yColumn} onChange={(event) => updateStyle({ y: event.target.value })}>
                {dataset.numericColumns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input value={redraw.title ?? ""} onChange={(event) => setRedraw((current) => ({ ...current, title: event.target.value }))} />
            </label>
            <label>
              Color
              <select value={activeStyle.color ?? defaultColor} onChange={(event) => updateStyle({ color: event.target.value })}>
                {payload.options.colors.map((color) => (
                  <option key={color.value} value={color.value}>
                    {color.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mg-toggle-strip">
            <label className="mg-mini-toggle">
              <input
                type="checkbox"
                checked={redraw.grid ?? true}
                onChange={(event) => setRedraw((current) => ({ ...current, grid: event.target.checked }))}
              />
              <span>Grid</span>
            </label>
          </div>
        </div>
        <div className="mg-modal-actions">
          <button type="button" className="mg-primary" onClick={generate}>
            Generate companion
          </button>
        </div>
      </section>
    </div>
  );
}

function inferDraftRedraw(dataset: DatasetRecord): RedrawMetadata {
  const numeric = dataset.numericColumns;
  const categorical = dataset.categoricalColumns;
  const columns = dataset.columns.length ? dataset.columns : [...categorical, ...numeric];
  let kind = "line";
  let x = numeric[0] ?? columns[0];
  let y = numeric.find((column) => column !== x) ?? numeric[0] ?? columns[0];
  if (categorical.length > 0 && numeric.length === 1) {
    kind = "bar";
    x = categorical[0];
    y = numeric[0];
  }
  return {
    kind,
    x,
    y: y ? [y] : [],
    title: humanTitle(dataset.displayName.replace(/\.[^.]+$/, "")),
    xlabel: x ? humanTitle(x) : undefined,
    ylabel: y ? humanTitle(y) : undefined,
    grid: true,
    figure: { width_inches: 7, height_inches: 4.5, dpi: 150 },
    series: y ? [{ y, color: "#1f77b4", marker: kind === "line" ? "o" : undefined }] : [],
  };
}

function humanTitle(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function Tree({
  node,
  files,
  records,
  selectedFolder,
  selectedPlotId,
  selectedDatasetId,
  selectedFileId,
  checkedPlotIds,
  checkedDatasetIds,
  onSelectFolder,
  onSelectPlot,
  onSelectDataset,
  onToggleFolder,
  onTogglePlot,
  onToggleDataset,
}: {
  node: TreeNode;
  files: FileItem[];
  records: PlotRecord[];
  selectedFolder: string;
  selectedPlotId: string | null;
  selectedDatasetId: string | null;
  selectedFileId: string | null;
  checkedPlotIds: Set<string>;
  checkedDatasetIds: Set<string>;
  onSelectFolder: (path: string) => void;
  onSelectPlot: (plotId: string) => void;
  onSelectDataset: (datasetId: string) => void;
  onToggleFolder: (path: string, checked: boolean, plotIds: string[], datasetIds: string[]) => void;
  onTogglePlot: (plotId: string, checked: boolean) => void;
  onToggleDataset: (datasetId: string, checked: boolean) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set([".", ...node.children.map((child) => child.path)]));

  useEffect(() => {
    setExpanded((current) => new Set([".", ...node.children.map((child) => child.path), ...current]));
  }, [node]);

  function toggle(path: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function folderFiles(path: string) {
    if (path === ".") return files;
    return files.filter((file) => file.path === path || file.path.startsWith(`${path}/`));
  }

  function renderNode(current: TreeNode, depth = 0) {
    const isExpanded = expanded.has(current.path);
    const isSelected = selectedFolder === current.path;
    const descendantFiles = folderFiles(current.path);
    const descendantPlotIds = descendantFiles
      .map((file) => file.plotId)
      .filter((plotId): plotId is string => typeof plotId === "string");
    const descendantDatasetIds = descendantFiles
      .filter((file) => file.kind === "csv")
      .map((file) => file.datasetId)
      .filter((datasetId): datasetId is string => typeof datasetId === "string");
    const checkedPlotCount = descendantPlotIds.filter((plotId) => checkedPlotIds.has(plotId)).length;
    const checkedDatasetCount = descendantDatasetIds.filter((datasetId) => checkedDatasetIds.has(datasetId)).length;
    const totalCheckable = descendantPlotIds.length + descendantDatasetIds.length;
    const checkedCount = checkedPlotCount + checkedDatasetCount;
    const allChecked = totalCheckable > 0 && checkedCount === totalCheckable;
    const partiallyChecked = checkedCount > 0 && !allChecked;
    const hasExpandableChildren = current.children.length > 0 || current.files.length > 0;
    return (
      <div key={current.path} className="mg-tree-node">
        <div
          className={`mg-tree-row ${isSelected ? "is-selected" : ""} ${partiallyChecked ? "is-partial" : ""}`}
          style={{ paddingLeft: `${depth * 14 + 4}px` }}
          role="treeitem"
          aria-selected={isSelected}
          aria-expanded={hasExpandableChildren ? isExpanded : undefined}
        >
          <button
            type="button"
            className="mg-tree-twisty"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${current.label}`}
            disabled={!hasExpandableChildren}
            onClick={() => toggle(current.path)}
          >
            {hasExpandableChildren ? (
              isExpanded ? <ChevronDown aria-hidden="true" size={14} /> : <ChevronRight aria-hidden="true" size={14} />
            ) : ""}
          </button>
          <input
            type="checkbox"
            className="mg-tree-check"
            aria-label={`Include ${current.label}`}
            checked={allChecked}
            ref={(element) => {
              if (element) element.indeterminate = partiallyChecked;
            }}
            onChange={(event) => onToggleFolder(current.path, event.target.checked, descendantPlotIds, descendantDatasetIds)}
          />
          <button
            type="button"
            className="mg-tree-label"
            onClick={() => onSelectFolder(current.path)}
          >
            <FileIcon kind={isExpanded ? "folder-open" : "folder"} />
            <span className="mg-tree-name">{current.label}</span>
            <span className={`mg-count ${checkedCount ? "has-checked" : ""}`}>
              {checkedCount ? `${checkedCount}/` : ""}
              {current.count}
            </span>
          </button>
        </div>
        {isExpanded ? (
          <>
            {current.children.map((child) => renderNode(child, depth + 1))}
            {current.files.map((file) => (
              <FileTreeRow
                key={file.id}
                file={file}
                depth={depth + 1}
                selected={
                  selectedFileId === file.id
                  || (file.plotId != null && selectedPlotId === file.plotId)
                  || (file.datasetId != null && selectedDatasetId === file.datasetId)
                }
                checked={file.kind === "image"
                  ? Boolean(file.plotId && checkedPlotIds.has(file.plotId))
                  : Boolean(file.datasetId && checkedDatasetIds.has(file.datasetId))}
                onToggle={(checked) => {
                  if (file.plotId) onTogglePlot(file.plotId, checked);
                  if (file.datasetId) onToggleDataset(file.datasetId, checked);
                }}
                onSelect={() => {
                  onSelectFolder(current.path);
                  if (file.kind === "image" && file.plotId) onSelectPlot(file.plotId);
                  if (file.kind === "csv" && file.datasetId) onSelectDataset(file.datasetId);
                }}
              />
            ))}
          </>
        ) : null}
      </div>
    );
  }

  return <div role="tree">{renderNode(node)}</div>;
}

function FileTreeRow({
  file,
  depth,
  selected,
  checked,
  onToggle,
  onSelect,
}: {
  file: FileItem;
  depth: number;
  selected: boolean;
  checked: boolean;
  onToggle: (checked: boolean) => void;
  onSelect: () => void;
}) {
  return (
    <div
      className={`mg-tree-row mg-tree-file mg-tree-${file.kind} ${selected ? "is-selected" : ""}`}
      style={{ paddingLeft: `${depth * 14 + 4}px` }}
      role="treeitem"
      aria-selected={selected}
    >
      <span className="mg-tree-twisty" aria-hidden="true" />
      {file.kind === "image" || file.kind === "csv" ? (
        <input
          type="checkbox"
          className="mg-tree-check"
          aria-label={`Include ${file.kind === "csv" ? "CSV" : "plot"} ${file.name}`}
          checked={checked}
          onChange={(event) => onToggle(event.target.checked)}
        />
      ) : (
        <span className="mg-tree-check-spacer" aria-hidden="true" />
      )}
      <button type="button" className="mg-tree-label" onClick={onSelect}>
        <FileIcon kind={file.iconKind} />
        <span className="mg-tree-name">{file.name}</span>
        {file.iconKind === "csv-drafted" ? (
          <span className="mg-file-status" title="Companion plot generated">
            <CheckCircle2 aria-hidden="true" size={12} />
          </span>
        ) : null}
      </button>
    </div>
  );
}

function FileIcon({ kind }: { kind: "folder" | "folder-open" | FileItem["iconKind"] }) {
  if (kind === "folder") return <Folder className="mg-file-icon" aria-label="Folder" size={14} />;
  if (kind === "folder-open") return <FolderOpen className="mg-file-icon" aria-label="Folder" size={14} />;
  if (kind === "image") return <FileImage className="mg-file-icon" aria-label="Image file" size={14} />;
  return <Table2 className="mg-file-icon" aria-label="CSV file" size={14} />;
}

function SelectedPlot({
  record,
  error,
  variant = "inline",
}: {
  record: PlotRecord | null;
  error?: string;
  variant?: "inline" | "modal";
}) {
  if (!record) {
    return <div className="mg-empty">No plots discovered.</div>;
  }
  return (
    <section className={`mg-canvas ${variant === "modal" ? "is-modal" : ""}`} aria-label={`Selected plot ${record.name}`}>
      {error || record.renderError ? (
        <div className="mg-error" role="alert">
          {error || record.renderError}
        </div>
      ) : null}
      <img src={record.imageSrc} alt={record.name} />
    </section>
  );
}

function PlotCard({
  record,
  selected,
  onMaximize,
  expanded,
  onToggleExpanded,
}: {
  record: PlotRecord;
  selected: boolean;
  onMaximize: () => void;
  expanded: boolean;
  onToggleExpanded: () => void;
}) {
  return (
    <article className={`mg-card ${selected ? "is-selected" : ""}`}>
      <button type="button" className="mg-card-image" onClick={onMaximize}>
        <img src={record.imageSrc} alt={record.name} />
      </button>
      <div className="mg-card-body">
        {expanded ? (
          <div className="mg-card-meta">
            <div className="mg-card-title" title={record.name}>
              {record.name}
            </div>
            <div className="mg-badges">
              <span>{record.kind}</span>
              <span className={record.csvPath ? "good" : "bad"}>
                {record.csvPath ? "CSV matched" : "CSV missing"}
              </span>
              <span>{record.confidence}</span>
            </div>
            <button type="button" className="mg-edit-button" onClick={onMaximize}>
              Maximize / edit
            </button>
          </div>
        ) : null}
        <div className="mg-card-actions">
          <button
            type="button"
            className="mg-info-button"
            aria-expanded={expanded}
            onClick={onToggleExpanded}
          >
            {expanded ? "Hide info" : "Info"}
          </button>
        </div>
      </div>
    </article>
  );
}

function PlotLookModal({
  payload,
  record,
  error,
  onClose,
  onSave,
}: {
  payload: BrowserPayload;
  record: PlotRecord;
  error?: string;
  onClose: () => void;
  onSave: (redraw: RedrawMetadata) => void;
}) {
  return (
    <div className="mg-modal-backdrop" role="dialog" aria-modal="true" aria-label={`Plot look for ${record.name}`}>
      <section className="mg-modal-card">
        <div className="mg-modal-head">
          <div>
            <div className="mg-eyebrow">Maximized plot</div>
            <h2>{record.name}</h2>
          </div>
          <button type="button" className="mg-inspector-toggle" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mg-modal-plot">
          <SelectedPlot record={record} error={error} variant="modal" />
          <Inspector payload={payload} record={record} onSave={onSave} />
        </div>
      </section>
    </div>
  );
}

function Inspector({
  payload,
  record,
  onSave,
}: {
  payload: BrowserPayload;
  record: PlotRecord | null;
  onSave: (redraw: RedrawMetadata) => void;
}) {
  const [redraw, setRedraw] = useState<RedrawMetadata>({});
  const [series, setSeries] = useState<SeriesStyle[]>([]);
  const [activeSubplotId, setActiveSubplotId] = useState("");
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    setRedraw(record?.redraw ?? {});
    setSeries(record?.series ?? []);
    setActiveSubplotId(record?.redraw.subplots?.[0]?.subplot_id ?? "");
    setLocalError("");
  }, [record]);

  if (!record) {
    return (
      <aside className="mg-inspector" aria-label="Plot look inspector">
        <div className="mg-panel-title">Plot look</div>
        <p className="mg-muted">Select a plot to edit metadata.</p>
      </aside>
    );
  }

  const subplots = redraw.subplots ?? [];
  const hasSubplots = subplots.length > 0;
  const activeSubplot = subplots.find((subplot) => subplot.subplot_id === activeSubplotId) ?? subplots[0] ?? null;
  const editableRedraw = activeSubplot ?? redraw;
  const editableSeries = activeSubplot ? activeSubplot.series ?? [] : series;
  const activeDefaults = activeSubplot
    ? record.axisDefaults?.subplots?.[activeSubplot.subplot_id]
    : record.axisDefaults;
  const xlim = editableRedraw.xlim ?? null;
  const ylim = editableRedraw.ylim ?? null;
  const figure = redraw.figure ?? {};
  const plotKind = editableRedraw.kind ?? "line";
  const supportsLine = ["line", "step", "area"].includes(plotKind);
  const supportsMarker = ["line", "scatter"].includes(plotKind);
  const supportsHatch = ["bar", "barh", "hist"].includes(plotKind);
  const supportsBarWidth = ["bar", "barh"].includes(plotKind);
  const isHistogram = plotKind === "hist";
  const defaultColor = payload.options.colors[0]?.value ?? "#1f77b4";

  function updateRedraw(patch: RedrawMetadata) {
    setRedraw((current) => ({ ...current, ...patch }));
  }

  function updateEditableRedraw(patch: Partial<SubplotMetadata & RedrawMetadata>) {
    if (!activeSubplot) {
      setRedraw((current) => ({ ...current, ...patch }));
      return;
    }
    setRedraw((current) => ({
      ...current,
      subplots: (current.subplots ?? []).map((subplot) =>
        subplot.subplot_id === activeSubplot.subplot_id ? { ...subplot, ...patch } : subplot,
      ),
    }));
  }

  function updateSeries(index: number, patch: Partial<SeriesStyle>) {
    if (!activeSubplot) {
      setSeries((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
      return;
    }
    setRedraw((current) => ({
      ...current,
      subplots: (current.subplots ?? []).map((subplot) =>
        subplot.subplot_id === activeSubplot.subplot_id
          ? {
              ...subplot,
              series: (subplot.series ?? []).map((item, itemIndex) =>
                itemIndex === index ? { ...item, ...patch } : item,
              ),
            }
          : subplot,
      ),
    }));
  }

  function save() {
    try {
      const next = normalizeRedraw(redraw, series);
      onSave(next);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <aside className="mg-inspector" aria-label="Plot look inspector">
      <div className="mg-inspector-head">
        <div>
          <div className="mg-panel-title">Plot look</div>
          <strong>{record.name}</strong>
        </div>
        <button type="button" className="mg-primary" onClick={save}>
          Save
        </button>
      </div>
      {localError || payload.errors[record.id] ? (
        <div className="mg-error" role="alert">
          {localError || payload.errors[record.id]}
        </div>
      ) : null}

      {hasSubplots ? (
        <details>
          <summary>Subplots</summary>
          <div className="mg-subplot-tabs" role="tablist" aria-label="Subplot panels">
            {subplots.map((subplot, index) => (
              <button
                key={subplot.subplot_id}
                type="button"
                role="tab"
                aria-selected={subplot.subplot_id === activeSubplot?.subplot_id}
                className={subplot.subplot_id === activeSubplot?.subplot_id ? "is-active" : ""}
                onClick={() => setActiveSubplotId(subplot.subplot_id)}
              >
                {subplot.title || `Panel ${index + 1}`}
              </button>
            ))}
          </div>
          <p className="mg-help">Editing one axes panel inside the same Matplotlib figure object.</p>
        </details>
      ) : null}

      <details>
        <summary>Axes</summary>
        <label>
          Plot type
          <select
            value={editableRedraw.kind ?? "line"}
            onChange={(event) => updateEditableRedraw({ kind: event.target.value })}
          >
            {payload.options.plotKinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input
            value={editableRedraw.title ?? ""}
            onChange={(event) => updateEditableRedraw({ title: event.target.value })}
          />
        </label>
        <div className="mg-field-grid two">
          <label>
            X label
            <input
              value={editableRedraw.xlabel ?? ""}
              onChange={(event) => updateEditableRedraw({ xlabel: event.target.value })}
            />
          </label>
          <label>
            X unit
            <select
              value={editableRedraw.xlabel_unit ?? ""}
              onChange={(event) => updateEditableRedraw({ xlabel_unit: event.target.value || undefined })}
            >
              <option value="">None</option>
              {payload.options.units.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </label>
          <label>
            Y label
            <input
              value={editableRedraw.ylabel ?? ""}
              onChange={(event) => updateEditableRedraw({ ylabel: event.target.value })}
            />
          </label>
          <label>
            Y unit
            <select
              value={editableRedraw.ylabel_unit ?? ""}
              onChange={(event) => updateEditableRedraw({ ylabel_unit: event.target.value || undefined })}
            >
              <option value="">None</option>
              {payload.options.units.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
          </label>
          <label>
            X scale
            <select
              value={editableRedraw.xscale ?? "linear"}
              onChange={(event) => updateEditableRedraw({ xscale: event.target.value })}
            >
              {payload.options.scales.map((scale) => (
                <option key={scale} value={scale}>
                  {scale}
                </option>
              ))}
            </select>
          </label>
          <label>
            Y scale
            <select
              value={editableRedraw.yscale ?? "linear"}
              onChange={(event) => updateEditableRedraw({ yscale: event.target.value })}
            >
              {payload.options.scales.map((scale) => (
                <option key={scale} value={scale}>
                  {scale}
                </option>
              ))}
            </select>
          </label>
        </div>
        <LimitEditor
          label="X limits"
          value={xlim}
          defaultValue={activeDefaults?.x ?? null}
          onChange={(value) => updateEditableRedraw({ xlim: value })}
        />
        <LimitEditor
          label="Y limits"
          value={ylim}
          defaultValue={activeDefaults?.y ?? null}
          onChange={(value) => updateEditableRedraw({ ylim: value })}
        />
        <label>
          Legend title
          <input
            value={editableRedraw.legend_title ?? ""}
            onChange={(event) => updateEditableRedraw({ legend_title: event.target.value })}
          />
        </label>
        <label>
          Legend location
          <select
            value={editableRedraw.legend_location ?? "best"}
            onChange={(event) => updateEditableRedraw({ legend_location: event.target.value })}
          >
            {payload.options.legendLocations.map((location) => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        </label>
        {isHistogram ? (
          <label>
            Histogram bins
            <input
              type="number"
              min="1"
              step="1"
              value={editableRedraw.bins ?? ""}
              onChange={(event) =>
                updateEditableRedraw({ bins: event.target.value ? Number(event.target.value) : undefined })
              }
            />
          </label>
        ) : null}
      </details>

      <details>
        <summary>Figure</summary>
        <div className="mg-toggle-strip">
          <label className="mg-mini-toggle">
            <input
              type="checkbox"
              checked={editableRedraw.grid ?? true}
              onChange={(event) => updateEditableRedraw({ grid: event.target.checked })}
            />
            <span>Grid</span>
          </label>
          <label className="mg-mini-toggle">
            <input
              type="checkbox"
              checked={figure.constrained_layout ?? false}
              onChange={(event) =>
                updateRedraw({ figure: { ...figure, constrained_layout: event.target.checked } })
              }
            />
            <span>Tight layout</span>
          </label>
        </div>
        {(editableRedraw.grid ?? true) ? (
          <div className="mg-field-grid two">
            <label>
              Grid axis
              <select
                value={editableRedraw.grid_axis ?? "both"}
                onChange={(event) => updateEditableRedraw({ grid_axis: event.target.value })}
              >
                {payload.options.gridAxes.map((axis) => (
                  <option key={axis} value={axis}>
                    {axis}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Grid opacity
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={editableRedraw.grid_alpha ?? 0.25}
                onChange={(event) => updateEditableRedraw({ grid_alpha: Number(event.target.value) })}
              />
              <span className="mg-inline-value">{editableRedraw.grid_alpha ?? 0.25}</span>
            </label>
          </div>
        ) : null}
        <div className="mg-field-grid three">
          <label>
            Width
            <input
              type="number"
              step="0.25"
              value={figure.width_inches ?? 6}
              onChange={(event) => updateRedraw({ figure: { ...figure, width_inches: Number(event.target.value) } })}
            />
          </label>
          <label>
            Height
            <input
              type="number"
              step="0.25"
              value={figure.height_inches ?? 4}
              onChange={(event) => updateRedraw({ figure: { ...figure, height_inches: Number(event.target.value) } })}
            />
          </label>
          <label>
            DPI
            <input
              type="number"
              step="10"
              value={figure.dpi ?? 150}
              onChange={(event) => updateRedraw({ figure: { ...figure, dpi: Number(event.target.value) } })}
            />
          </label>
        </div>
        <div>
          <div className="mg-label">Figure background</div>
          <VisualPicker
            value={figure.facecolor ?? "#ffffff"}
            options={[{ value: "#ffffff", label: "White" }, ...payload.options.colors]}
            kind="color"
            onChange={(value) => updateRedraw({ figure: { ...figure, facecolor: value } })}
          />
        </div>
      </details>

      <details>
        <summary>Series</summary>
        {editableSeries.map((style, index) => (
          <fieldset key={`${style.y}-${index}`} className="mg-series">
            <legend>{style.label || style.y}</legend>
            <label>
              Y column
              <select value={style.y} onChange={(event) => updateSeries(index, { y: event.target.value })}>
                {record.csvColumns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Label
              <input value={style.label ?? ""} onChange={(event) => updateSeries(index, { label: event.target.value })} />
            </label>
            <div className="mg-series-stack">
              <div>
                <div className="mg-label">{supportsHatch ? "Fill" : "Color"}</div>
                <VisualPicker
                  value={style.color ?? defaultColor}
                  options={payload.options.colors}
                  kind="color"
                  onChange={(value) => updateSeries(index, { color: value })}
                />
              </div>
              {supportsHatch ? (
                <div>
                  <div className="mg-label">Edge</div>
                  <VisualPicker
                    value={style.edgecolor ?? "#17202f"}
                    options={[{ value: "", label: "None" }, ...payload.options.colors]}
                    kind="color"
                    onChange={(value) => updateSeries(index, { edgecolor: value || undefined })}
                  />
                </div>
              ) : null}
              <div className="mg-field-grid two">
                <label>
                  {supportsHatch ? "Stroke" : "Width"}
                  <input
                    type="number"
                    step="0.1"
                    value={style.linewidth ?? 1.5}
                    onChange={(event) => updateSeries(index, { linewidth: Number(event.target.value) })}
                  />
                </label>
                <label>
                  Opacity
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={style.alpha ?? 1}
                    onChange={(event) => updateSeries(index, { alpha: Number(event.target.value) })}
                  />
                  <span className="mg-inline-value">{style.alpha ?? 1}</span>
                </label>
              </div>
              {supportsLine ? (
                <div>
                  <div className="mg-label">Line</div>
                  <VisualPicker
                    value={style.linestyle ?? "-"}
                    options={payload.options.lineStyles}
                    kind="line"
                    onChange={(value) => updateSeries(index, { linestyle: value })}
                  />
                </div>
              ) : null}
              {supportsMarker ? (
                <div>
                  <div className="mg-label">Marker</div>
                  <VisualPicker
                    value={style.marker ?? "o"}
                    options={payload.options.markers}
                    kind="marker"
                    onChange={(value) => updateSeries(index, { marker: value })}
                  />
                </div>
              ) : null}
              {supportsMarker ? (
                <label>
                  Marker size
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={style.markersize ?? 5}
                    onChange={(event) => updateSeries(index, { markersize: Number(event.target.value) })}
                  />
                </label>
              ) : null}
              {supportsHatch ? (
                <div>
                  <div className="mg-label">Hatch</div>
                  <VisualPicker
                    value={style.hatch ?? ""}
                    options={payload.options.hatches}
                    kind="hatch"
                    onChange={(value) => updateSeries(index, { hatch: value })}
                  />
                </div>
              ) : null}
              {supportsBarWidth ? (
                <label>
                  Bar width
                  <input
                    type="number"
                    min="0.05"
                    step="0.05"
                    value={style.bar_width ?? ""}
                    placeholder="auto"
                    onChange={(event) =>
                      updateSeries(index, { bar_width: event.target.value ? Number(event.target.value) : undefined })
                    }
                  />
                </label>
              ) : null}
              <label>
                Draw order
                <input
                  type="number"
                  step="1"
                  value={style.zorder ?? ""}
                  placeholder="auto"
                  title="Matplotlib zorder: higher numbers draw on top of lower numbers."
                  onChange={(event) =>
                    updateSeries(index, { zorder: event.target.value ? Number(event.target.value) : undefined })
                  }
                />
                <span className="mg-help">Higher draws on top.</span>
              </label>
            </div>
          </fieldset>
        ))}
      </details>

      <details>
        <summary>Provenance</summary>
        <dl className="mg-provenance">
          <dt>Raw CSV</dt>
          <dd>{record.rawCsvPath ? "Configured" : "Not configured"}</dd>
          <dt>Render CSV</dt>
          <dd>{record.csvPath ? "Matched" : "Unmatched"}</dd>
          <dt>Cache</dt>
          <dd>{record.cachePath ? "Rendered" : "Not rendered"}</dd>
          <dt>Match</dt>
          <dd>{record.reason ?? record.confidence}</dd>
        </dl>
      </details>
    </aside>
  );
}

function VisualPicker({
  value,
  options,
  kind,
  onChange,
}: {
  value: string;
  options: { value: string; label: string }[];
  kind: "color" | "line" | "marker" | "hatch";
  onChange: (value: string) => void;
}) {
  const active = options.find((option) => option.value === value) ?? (kind === "color" && value
    ? { value, label: "Custom color" }
    : options[0]);
  const label = active?.label ?? "None";
  return (
    <details className={`mg-picker mg-picker-${kind}`}>
      <summary aria-label={`Selected ${kind}: ${label}`}>
        <VisualOption value={active?.value ?? value} label={label} kind={kind} />
      </summary>
      <div className="mg-picker-menu" role="listbox">
        {options.map((option) => (
          <button
            type="button"
            key={option.value || "none"}
            className={`mg-picker-option ${option.value === value ? "is-active" : ""}`}
            title={option.label}
            aria-label={option.label}
            aria-selected={option.value === value}
            onClick={(event) => {
              onChange(option.value);
              event.currentTarget.closest("details")?.removeAttribute("open");
            }}
          >
            <VisualOption value={option.value} label={option.label} kind={kind} compact />
          </button>
        ))}
        {kind === "color" ? (
          <label className="mg-picker-option mg-custom-color" title="Choose any color" aria-label="Choose any color">
            <span aria-hidden="true">+</span>
            <input
              type="color"
              value={value || "#1f77b4"}
              onChange={(event) => onChange(event.target.value)}
            />
            <span className="mg-sr-only">Choose any color</span>
          </label>
        ) : null}
      </div>
    </details>
  );
}

function VisualOption({
  value,
  label,
  kind,
  compact = false,
}: {
  value: string;
  label: string;
  kind: "color" | "line" | "marker" | "hatch";
  compact?: boolean;
}) {
  if (kind === "color") {
    return (
      <span className="mg-visual-option">
        <span
          className={`mg-color-chip ${value ? "" : "is-empty"}`}
          style={value ? { background: value } : undefined}
          aria-hidden="true"
        />
        {!compact ? <span className="mg-sr-only">{label}</span> : null}
      </span>
    );
  }
  if (kind === "line") {
    return (
      <span className="mg-visual-option">
        <span className={`mg-line-preview is-${lineStyleClass(value)}`} aria-hidden="true" />
        {!compact ? <span className="mg-picker-label">{label}</span> : null}
      </span>
    );
  }
  if (kind === "hatch") {
    return (
      <span className="mg-visual-option">
        <span className={`mg-hatch-preview is-${hatchClass(value)}`} aria-hidden="true">
          {value || "none"}
        </span>
        {!compact ? <span className="mg-picker-label">{label}</span> : null}
      </span>
    );
  }
  return (
    <span className="mg-visual-option">
      <span className={`mg-marker-preview is-${markerClass(value)}`} aria-hidden="true">
        {markerGlyph(value)}
      </span>
      {!compact ? <span className="mg-sr-only">{label}</span> : null}
    </span>
  );
}

function LimitEditor({
  label,
  value,
  defaultValue,
  onChange,
}: {
  label: string;
  value: [number, number] | null;
  defaultValue?: [number, number] | null;
  onChange: (value: [number, number] | null) => void;
}) {
  const [minValue, setMinValue] = useState(value?.[0]?.toString() ?? "");
  const [maxValue, setMaxValue] = useState(value?.[1]?.toString() ?? "");

  useEffect(() => {
    setMinValue(value?.[0]?.toString() ?? "");
    setMaxValue(value?.[1]?.toString() ?? "");
  }, [value]);

  function commit(nextMin: string, nextMax: string) {
    setMinValue(nextMin);
    setMaxValue(nextMax);
    try {
      onChange(parseLimits(nextMin, nextMax));
    } catch {
      // Keep partial input local; Python validates final metadata on save.
    }
  }

  return (
    <div>
      <div className="mg-limit-head">
        <div className="mg-label">{label}</div>
        {defaultValue ? (
          <button
            type="button"
            className="mg-link-button"
            onClick={() => commit(formatLimit(defaultValue[0]), formatLimit(defaultValue[1]))}
          >
            Use data range
          </button>
        ) : null}
      </div>
      <div className="mg-field-grid two">
        <label>
          Min
          <input
            value={minValue}
            placeholder={defaultValue ? formatLimit(defaultValue[0]) : "auto"}
            onChange={(event) => commit(event.target.value, maxValue)}
          />
        </label>
        <label>
          Max
          <input
            value={maxValue}
            placeholder={defaultValue ? formatLimit(defaultValue[1]) : "auto"}
            onChange={(event) => commit(minValue, event.target.value)}
          />
        </label>
      </div>
    </div>
  );
}

function formatLimit(value: number): string {
  return Number.isInteger(value) ? value.toString() : Number(value.toPrecision(6)).toString();
}

function lineStyleClass(value: string): string {
  switch (value) {
    case "--":
      return "dashed";
    case "-.":
      return "dashdot";
    case ":":
      return "dotted";
    case "":
      return "none";
    default:
      return "solid";
  }
}

function markerClass(value: string): string {
  switch (value) {
    case "s":
      return "square";
    case "D":
      return "diamond";
    case "^":
      return "triangle-up";
    case "v":
      return "triangle-down";
    case "x":
      return "x";
    case "+":
      return "plus";
    case ".":
      return "point";
    case "":
      return "none";
    default:
      return "circle";
  }
}

function hatchClass(value: string): string {
  switch (value) {
    case "/":
      return "slash";
    case "\\":
      return "backslash";
    case "|":
      return "vertical";
    case "-":
      return "horizontal";
    case "+":
      return "plus";
    case "x":
      return "cross";
    case "o":
      return "circle";
    case ".":
      return "dot";
    case "*":
      return "star";
    default:
      return "none";
  }
}

function markerGlyph(value: string): string {
  switch (value) {
    case "s":
      return "■";
    case "D":
      return "◆";
    case "^":
      return "▲";
    case "v":
      return "▼";
    case "x":
      return "×";
    case "+":
      return "+";
    case ".":
      return "•";
    case "":
      return "○";
    default:
      return "●";
  }
}

export default App;
