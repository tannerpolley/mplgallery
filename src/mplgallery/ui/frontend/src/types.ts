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
  imageSrc?: string | null;
  cachePath?: string | null;
  renderError?: string | null;
  csvPreview?: string | null;
  csvColumns: string[];
  previewColumns?: string[];
  previewRows?: Array<Record<string, string | number | boolean | null>>;
  previewTruncated?: boolean;
  previewError?: string | null;
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
  associatedPlotIds?: string[];
  rowCountSampled: number;
  columns: string[];
  numericColumns: string[];
  categoricalColumns: string[];
  previewColumns: string[];
  previewRows: Array<Record<string, string | number | null>>;
  previewTruncated: boolean;
  previewError?: string | null;
};

export type FileItem = {
  id: string;
  kind: "csv" | "image";
  path: string;
  name: string;
  parentPath: string;
  iconKind: "csv" | "csv-drafted" | "image";
  suffix?: string | null;
  visibilityRole?: string | null;
  draftStatus?: string | null;
  plotId?: string | null;
  datasetId?: string | null;
};

export type PlotSetAttachment = {
  id: string;
  type: "csv" | "svg" | "png" | "mpl_yaml" | "other" | string;
  displayName: string;
  sourcePath: string;
  plotId?: string | null;
  datasetId?: string | null;
  textPreview?: string | null;
  textPreviewTruncated?: boolean;
};

export type PlotSetEntity = {
  plotSetId: string;
  title: string;
  folderPath: string;
  attachments: PlotSetAttachment[];
  preferredFigure?: PlotSetAttachment | null;
  editable: boolean;
  checked?: boolean;
  renderStatus?: string;
};

export type FolderViewNode = {
  id: string;
  path: string;
  label: string;
  parentId?: string | null;
  depth: number;
  childCount: number;
  plotSetCount: number;
  autoFlatten?: boolean;
};

export type FolderView = {
  nodes: FolderViewNode[];
  rootId: string;
  defaultSelectedPath: string;
};

export type FilesViewRow = {
  plotSetId: string;
  title: string;
  folderPath: string;
  attachmentTypes: string[];
  figureCount: number;
  csvCount: number;
  editable: boolean;
  renderStatus: string;
};

export type FilesView = {
  rows: FilesViewRow[];
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
  rootContext?: RootContext;
  selectedPlotId?: string | null;
  datasets: DatasetRecord[];
  plotSets?: PlotSetEntity[];
  folderView?: FolderView;
  filesView?: FilesView;
  records: PlotRecord[];
  files: FileItem[];
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
  | { id: string; type: "draft_dataset_with_preferences"; dataset_id: string; redraw: RedrawMetadata; output_format: "svg" | "png" }
  | { id: string; type: "draft_checked_datasets"; dataset_ids: string[] }
  | { id: string; type: "select_folder"; folder_path: string }
  | { id: string; type: "toggle_plot_set_checked"; plot_set_id: string; checked: boolean }
  | { id: string; type: "set_checked_plot_sets"; plot_set_ids: string[] }
  | { id: string; type: "select_plot_set"; plot_set_id: string }
  | { id: string; type: "set_preferred_attachment_view"; plot_set_id: string; attachment_id: string }
  | { id: string; type: "toggle_show_ungrouped"; show: boolean }
  | { id: string; type: "refresh_index" }
  | { id: string; type: "browse_project_root" }
  | { id: string; type: "change_project_root"; root_path: string }
  | { id: string; type: "reset_project_root" }
  | { id: string; type: "forget_recent_root"; root_path: string };

export type RootContext = {
  activeRoot: string;
  launchRoot: string;
  recentRoots: string[];
  error?: string | null;
  showRootChooser?: boolean;
};

export type TreeNode = {
  path: string;
  label: string;
  count: number;
  autoExpand?: boolean;
  children: TreeNode[];
  files: FileItem[];
};
