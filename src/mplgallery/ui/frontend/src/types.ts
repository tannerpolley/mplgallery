export type RedrawMetadata = {
  kind?: string;
  x?: string;
  y?: string[];
  title?: string;
  xlabel?: string;
  xlabel_unit?: string;
  ylabel?: string;
  ylabel_unit?: string;
  xscale?: string;
  yscale?: string;
  xlim?: [number, number] | null;
  ylim?: [number, number] | null;
  grid?: boolean;
  grid_axis?: string;
  grid_alpha?: number;
  legend_title?: string;
  legend_location?: string;
  bins?: number;
  figure?: {
    width_inches?: number;
    height_inches?: number;
    dpi?: number;
    facecolor?: string;
    constrained_layout?: boolean;
  };
  series?: SeriesStyle[];
  subplots?: SubplotMetadata[];
  subplot_rows?: number;
  subplot_cols?: number;
  sharex?: boolean;
  sharey?: boolean;
};

export type SubplotMetadata = Omit<RedrawMetadata, "figure" | "subplots" | "subplot_rows" | "subplot_cols" | "sharex" | "sharey"> & {
  subplot_id: string;
};

export type SeriesStyle = {
  y: string;
  label?: string;
  color?: string;
  edgecolor?: string;
  linewidth?: number;
  linestyle?: string;
  marker?: string;
  markersize?: number;
  hatch?: string;
  bar_width?: number;
  alpha?: number;
  zorder?: number;
};

export type PlotRecord = {
  id: string;
  name: string;
  kind: string;
  imagePath: string;
  sourceDatasetId?: string | null;
  ownedByMplgallery?: boolean;
  visibilityRole?: "draft" | "reference" | "imported" | string;
  csvPath?: string | null;
  rawCsvPath?: string | null;
  confidence: string;
  reason?: string | null;
  imageSrc: string;
  cachePath?: string | null;
  renderError?: string | null;
  csvPreview?: string | null;
  csvColumns: string[];
  editable: boolean;
  redraw: RedrawMetadata;
  series: SeriesStyle[];
  axisDefaults?: AxisDefaults;
};

export type DatasetRecord = {
  id: string;
  displayName: string;
  path: string;
  csvRootId: string;
  csvRootPath: string;
  draftStatus: string;
  associatedPlotId?: string | null;
  rowCountSampled: number;
  columns: string[];
  numericColumns: string[];
  categoricalColumns: string[];
};

export type AxisDefaults = {
  x?: [number, number] | null;
  y?: [number, number] | null;
  subplots?: Record<string, { x?: [number, number] | null; y?: [number, number] | null }>;
};

export type SelectOption = {
  value: string;
  label: string;
};

export type BrowserPayload = {
  projectRoot: string;
  selectedPlotId?: string | null;
  datasets: DatasetRecord[];
  records: PlotRecord[];
  options: {
    plotKinds: string[];
    lineStyles: SelectOption[];
    markers: SelectOption[];
    colors: SelectOption[];
    units: string[];
    scales: string[];
    gridAxes: string[];
    legendLocations: string[];
    hatches: SelectOption[];
  };
  errors: Record<string, string>;
};

export type ComponentEvent =
  | { id: string; type: "save_redraw_metadata"; plot_id: string; redraw: RedrawMetadata }
  | { id: string; type: "request_rerender"; plot_id: string }
  | { id: string; type: "select_dataset"; dataset_id: string }
  | { id: string; type: "draft_dataset"; dataset_id: string }
  | { id: string; type: "draft_checked_datasets"; dataset_ids: string[] };

export type TreeNode = {
  path: string;
  label: string;
  count: number;
  children: TreeNode[];
};
