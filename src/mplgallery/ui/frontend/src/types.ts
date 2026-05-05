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
  | { id: string; type: "request_rerender"; plot_id: string };

export type TreeNode = {
  path: string;
  label: string;
  count: number;
  children: TreeNode[];
};
