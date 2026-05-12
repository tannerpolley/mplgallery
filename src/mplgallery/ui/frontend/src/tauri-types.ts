export type TauriBootstrap = {
  appInfo: {
    name: string;
    version: string;
    appId: string;
    canInstallUpdates: boolean;
    update?: {
      checked: boolean;
      available: boolean;
      currentVersion?: string | null;
      latestVersion?: string | null;
      error?: string | null;
    };
  };
  userSettings: {
    rememberRecentProjects: boolean;
    restoreLastProjectOnStartup: boolean;
  };
  rootContext: {
    activeRoot: string;
    recentRoots: string[];
    error?: string | null;
  };
};

export type TauriFolderNode = {
  id: string;
  label: string;
  path: string;
  childCount: number;
  assetCount: number;
  children: TauriFolderNode[];
};

export type TauriAssetRef = {
  id: string;
  relativePath: string;
  kind: "csv" | "png" | "svg";
  sizeBytes?: number | null;
  modifiedAt?: string | null;
  widthPx?: number | null;
  heightPx?: number | null;
};

export type TauriCsvDataset = {
  id: string;
  displayName: string;
  relativePath: string;
  folderPath: string;
  rowCountSampled: number;
  columns: string[];
  numericColumns: string[];
  categoricalColumns: string[];
  previewColumns: string[];
  previewRows: Array<Record<string, string>>;
  previewTruncated: boolean;
  previewError?: string | null;
  linkedImageIds: string[];
};

export type TauriPlotSetCard = {
  id: string;
  title: string;
  folderPath: string;
  classification: "analysis-linked";
  attachments: TauriAssetRef[];
  preferredFigureId?: string | null;
  renderStatus: "ready" | "missing_figure" | "error";
};

export type TauriLooseImageCard = {
  id: string;
  title: string;
  folderPath: string;
  classification: "loose-image";
  image: TauriAssetRef;
  siblingCsvIds: string[];
  imageFormat?: string | null;
};

export type TauriFileRow = {
  id: string;
  title: string;
  folderPath: string;
  classification: "analysis-linked" | "loose-image";
  attachmentKinds: Array<"csv" | "png" | "svg">;
};

export type TauriScanResult = {
  rootPath: string;
  browseMode: "plot-set-manager" | "image-library";
  folderTree: TauriFolderNode[];
  fileRows: TauriFileRow[];
  plotSets: TauriPlotSetCard[];
  looseImages: TauriLooseImageCard[];
  datasets: TauriCsvDataset[];
  warnings: string[];
  ignoredDirCount: number;
};
