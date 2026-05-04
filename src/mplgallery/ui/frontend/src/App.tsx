import { useEffect, useMemo, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import type { BrowserPayload, PlotRecord, RedrawMetadata, SeriesStyle, TreeNode } from "./types";
import { buildTree, eventId, filterRecords, normalizeRedraw, parseLimits } from "./utils";
import "./App.css";

type StreamlitProps = {
  payload?: BrowserPayload;
};

const emptyPayload: BrowserPayload = {
  projectRoot: "",
  selectedPlotId: null,
  records: [],
  options: { lineStyles: [], markers: [], scales: ["linear", "log", "symlog", "logit"] },
  errors: {},
};

function App(props: StreamlitProps) {
  const payload = props.payload ?? emptyPayload;
  const [selectedPlotId, setSelectedPlotId] = useState<string | null>(
    payload.selectedPlotId ?? payload.records[0]?.id ?? null,
  );
  const [selectedFolder, setSelectedFolder] = useState(".");
  const [query, setQuery] = useState("");
  const [tileSize, setTileSize] = useState(230);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  useEffect(() => {
    setSelectedPlotId(payload.selectedPlotId ?? payload.records[0]?.id ?? null);
  }, [payload.selectedPlotId, payload.records]);

  const tree = useMemo(() => buildTree(payload.records), [payload.records]);
  const visibleRecords = useMemo(
    () => filterRecords(payload.records, query, selectedFolder),
    [payload.records, query, selectedFolder],
  );
  const selectedRecord =
    payload.records.find((record) => record.id === selectedPlotId) ?? payload.records[0] ?? null;

  function selectPlot(plotId: string) {
    setSelectedPlotId(plotId);
    Streamlit.setComponentValue({
      event: { id: eventId("select_plot"), type: "select_plot", plot_id: plotId },
    });
  }

  function updateQuery(value: string) {
    setQuery(value);
    Streamlit.setComponentValue({
      event: { id: eventId("set_tree_filter"), type: "set_tree_filter", value },
    });
  }

  function updateTileSize(value: number) {
    setTileSize(value);
    Streamlit.setComponentValue({
      event: { id: eventId("set_tile_size"), type: "set_tile_size", value },
    });
  }

  return (
    <div className="mg-shell">
      <aside className="mg-tree-panel" aria-label="Output tree">
        <div className="mg-panel-title">Output tree</div>
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
          selectedFolder={selectedFolder}
          onSelectFolder={setSelectedFolder}
        />
      </aside>

      <main className="mg-workspace" aria-label="Plot workspace">
        <div className="mg-workspace-header">
          <div>
            <div className="mg-eyebrow">{payload.records.length} indexed plots</div>
            <h2>{selectedRecord?.name ?? "No plot selected"}</h2>
          </div>
          <button
            className="mg-inspector-toggle"
            type="button"
            onClick={() => setInspectorOpen((open) => !open)}
          >
            {inspectorOpen ? "Hide inspector" : "Show inspector"}
          </button>
        </div>
        <SelectedPlot record={selectedRecord} error={selectedRecord ? payload.errors[selectedRecord.id] : ""} />
        <section className="mg-gallery" aria-label="Plot gallery">
          <div className="mg-gallery-toolbar">
            <strong>
              {visibleRecords.length} plot{visibleRecords.length === 1 ? "" : "s"}
            </strong>
            <label>
              Tile size
              <input
                type="range"
                min="160"
                max="360"
                value={tileSize}
                onChange={(event) => updateTileSize(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="mg-card-grid" style={{ ["--tile-size" as string]: `${tileSize}px` }}>
            {visibleRecords.map((record) => (
              <PlotCard
                key={record.id}
                record={record}
                selected={record.id === selectedRecord?.id}
                onSelect={() => selectPlot(record.id)}
              />
            ))}
          </div>
        </section>
      </main>

      <Inspector
        payload={payload}
        record={selectedRecord}
        open={inspectorOpen}
        onSave={(redraw) => {
          if (!selectedRecord) return;
          Streamlit.setComponentValue({
            event: {
              id: eventId("save_redraw_metadata"),
              type: "save_redraw_metadata",
              plot_id: selectedRecord.id,
              redraw,
            },
          });
        }}
      />
    </div>
  );
}

function Tree({
  node,
  selectedFolder,
  onSelectFolder,
}: {
  node: TreeNode;
  selectedFolder: string;
  onSelectFolder: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["."]));

  function toggle(path: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function renderNode(current: TreeNode, depth = 0) {
    const isExpanded = expanded.has(current.path);
    const isSelected = selectedFolder === current.path;
    return (
      <div key={current.path} className="mg-tree-node">
        <div
          className={`mg-tree-row ${isSelected ? "is-selected" : ""}`}
          style={{ paddingLeft: `${depth * 14 + 4}px` }}
          role="treeitem"
          aria-selected={isSelected}
          aria-expanded={current.children.length ? isExpanded : undefined}
        >
          <button
            type="button"
            className="mg-tree-twisty"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${current.label}`}
            disabled={!current.children.length}
            onClick={() => toggle(current.path)}
          >
            {current.children.length ? (isExpanded ? "▾" : "▸") : ""}
          </button>
          <button
            type="button"
            className="mg-tree-label"
            onClick={() => onSelectFolder(current.path)}
          >
            <span>{current.label}</span>
            <span className="mg-count">{current.count}</span>
          </button>
        </div>
        {isExpanded && current.children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  }

  return <div role="tree">{renderNode(node)}</div>;
}

function SelectedPlot({ record, error }: { record: PlotRecord | null; error?: string }) {
  if (!record) {
    return <div className="mg-empty">No plots discovered.</div>;
  }
  return (
    <section className="mg-canvas" aria-label={`Selected plot ${record.name}`}>
      {error || record.renderError ? (
        <div className="mg-error" role="alert">
          {error || record.renderError}
        </div>
      ) : null}
      <img src={record.imageSrc} alt={record.name} />
      <div className="mg-caption">{record.imagePath}</div>
    </section>
  );
}

function PlotCard({
  record,
  selected,
  onSelect,
}: {
  record: PlotRecord;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <article className={`mg-card ${selected ? "is-selected" : ""}`}>
      <button type="button" className="mg-card-image" onClick={onSelect}>
        <img src={record.imageSrc} alt={record.name} />
      </button>
      <div className="mg-card-body">
        <div className="mg-card-title">{record.name}</div>
        <div className="mg-badges">
          <span>{record.kind}</span>
          <span className={record.csvPath ? "good" : "bad"}>
            {record.csvPath ? "CSV matched" : "CSV missing"}
          </span>
          <span>{record.confidence}</span>
        </div>
        <button type="button" className="mg-edit-button" onClick={onSelect}>
          Edit setup
        </button>
      </div>
    </article>
  );
}

function Inspector({
  payload,
  record,
  open,
  onSave,
}: {
  payload: BrowserPayload;
  record: PlotRecord | null;
  open: boolean;
  onSave: (redraw: RedrawMetadata) => void;
}) {
  const [redraw, setRedraw] = useState<RedrawMetadata>({});
  const [series, setSeries] = useState<SeriesStyle[]>([]);
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    setRedraw(record?.redraw ?? {});
    setSeries(record?.series ?? []);
    setLocalError("");
  }, [record]);

  if (!open) return null;
  if (!record) {
    return (
      <aside className="mg-inspector" aria-label="Plot look inspector">
        <div className="mg-panel-title">Plot look</div>
        <p className="mg-muted">Select a plot to edit metadata.</p>
      </aside>
    );
  }

  const xlim = redraw.xlim ?? null;
  const ylim = redraw.ylim ?? null;
  const figure = redraw.figure ?? {};

  function updateRedraw(patch: RedrawMetadata) {
    setRedraw((current) => ({ ...current, ...patch }));
  }

  function updateSeries(index: number, patch: Partial<SeriesStyle>) {
    setSeries((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
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

      <details open>
        <summary>Axes</summary>
        <label>
          Title
          <input value={redraw.title ?? ""} onChange={(event) => updateRedraw({ title: event.target.value })} />
        </label>
        <div className="mg-field-grid two">
          <label>
            X label
            <input value={redraw.xlabel ?? ""} onChange={(event) => updateRedraw({ xlabel: event.target.value })} />
          </label>
          <label>
            Y label
            <input value={redraw.ylabel ?? ""} onChange={(event) => updateRedraw({ ylabel: event.target.value })} />
          </label>
          <label>
            X scale
            <select value={redraw.xscale ?? "linear"} onChange={(event) => updateRedraw({ xscale: event.target.value })}>
              {payload.options.scales.map((scale) => (
                <option key={scale} value={scale}>
                  {scale}
                </option>
              ))}
            </select>
          </label>
          <label>
            Y scale
            <select value={redraw.yscale ?? "linear"} onChange={(event) => updateRedraw({ yscale: event.target.value })}>
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
          onChange={(value) => updateRedraw({ xlim: value })}
        />
        <LimitEditor
          label="Y limits"
          value={ylim}
          onChange={(value) => updateRedraw({ ylim: value })}
        />
      </details>

      <details>
        <summary>Figure</summary>
        <label className="mg-checkbox">
          <input
            type="checkbox"
            checked={redraw.grid ?? true}
            onChange={(event) => updateRedraw({ grid: event.target.checked })}
          />
          Grid
        </label>
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
      </details>

      <details open>
        <summary>Series</summary>
        {series.map((style, index) => (
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
            <div className="mg-field-grid two">
              <label>
                Color
                <input
                  type="color"
                  value={style.color ?? "#1f77b4"}
                  onChange={(event) => updateSeries(index, { color: event.target.value })}
                />
              </label>
              <label>
                Width
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
              <label>
                Line
                <select value={style.linestyle ?? "-"} onChange={(event) => updateSeries(index, { linestyle: event.target.value })}>
                  {payload.options.lineStyles.map((option) => (
                    <option key={option.label} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Marker
                <select value={style.marker ?? "o"} onChange={(event) => updateSeries(index, { marker: event.target.value })}>
                  {payload.options.markers.map((option) => (
                    <option key={option.label} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </fieldset>
        ))}
      </details>

      <details>
        <summary>Provenance</summary>
        <dl className="mg-provenance">
          <dt>Raw CSV</dt>
          <dd>{record.rawCsvPath ?? "Not configured"}</dd>
          <dt>Render CSV</dt>
          <dd>{record.csvPath ?? "Unmatched"}</dd>
          <dt>Cache</dt>
          <dd>{record.cachePath ?? "Not rendered"}</dd>
          <dt>Match</dt>
          <dd>{record.reason ?? record.confidence}</dd>
        </dl>
      </details>
    </aside>
  );
}

function LimitEditor({
  label,
  value,
  onChange,
}: {
  label: string;
  value: [number, number] | null;
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
      <div className="mg-label">{label}</div>
      <div className="mg-field-grid two">
        <label>
          Min
          <input value={minValue} onChange={(event) => commit(event.target.value, maxValue)} />
        </label>
        <label>
          Max
          <input value={maxValue} onChange={(event) => commit(minValue, event.target.value)} />
        </label>
      </div>
    </div>
  );
}

export default App;
