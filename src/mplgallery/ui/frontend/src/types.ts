export type RedrawMetadata = {
  kind?: string;
  x?: string;
  y?: string[];
  title?: string;
  xlabel?: string;
  ylabel?: string;
  xscale?: string;
  yscale?: string;
  xlim?: [number, number] | null;
  ylim?: [number, number] | null;
  grid?: boolean;
  figure?: {
    width_inches?: number;
    height_inches?: number;
    dpi?: number;
  };
  series?: SeriesStyle[];
};

export type SeriesStyle = {
  y: string;
  label?: string;
  color?: string;
  linewidth?: number;
  linestyle?: string;
  marker?: string;
  alpha?: number;
};

export type PlotRecord = {
  id: string;
  name: string;
  kind: string;
  imagePath: string;
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
};

export type SelectOption = {
  value: string;
  label: string;
};

export type BrowserPayload = {
  projectRoot: string;
  selectedPlotId?: string | null;
  records: PlotRecord[];
  options: {
    lineStyles: SelectOption[];
    markers: SelectOption[];
    scales: string[];
  };
  errors: Record<string, string>;
};

export type ComponentEvent =
  | { id: string; type: "select_plot"; plot_id: string }
  | { id: string; type: "save_redraw_metadata"; plot_id: string; redraw: RedrawMetadata }
  | { id: string; type: "request_rerender"; plot_id: string }
  | { id: string; type: "set_tree_filter"; value: string }
  | { id: string; type: "set_tile_size"; value: number };

export type TreeNode = {
  path: string;
  label: string;
  count: number;
  children: TreeNode[];
};
