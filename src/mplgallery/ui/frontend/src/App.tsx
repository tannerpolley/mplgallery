import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type DragEvent as ReactDragEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileImage,
  Folder,
  FolderOpen,
  HelpCircle,
  Info,
  RefreshCw,
  Settings,
  Table2,
  FileCode2,
} from "lucide-react";
import { Streamlit } from "streamlit-component-lib";
import type {
  BrowserPayload,
  DatasetRecord,
  FileItem,
  FolderViewNode,
  PlotRecord,
  PlotSetAttachment,
  PlotSetEntity,
  RedrawMetadata,
  SeriesStyle,
  SubplotMetadata,
  TreeNode,
} from "./types";
import {
  clampNumber,
  emptyGalleryMessage,
  eventId,
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

type DataPlotItem = {
  id: string;
  plotSet: PlotSetEntity | null;
  dataset: DatasetRecord | null;
  records: PlotRecord[];
};

type CsvPreviewData = {
  id: string;
  label: string;
  previewColumns: string[];
  previewRows: Array<Record<string, string | number | boolean | null>>;
  previewTruncated: boolean;
  previewError?: string | null;
};

type FileFilter = "csv" | "svg" | "png" | "yaml" | "missing";
type GalleryLayoutMode = "grid" | "rows" | "columns";

const FILE_FILTERS: Array<{ value: FileFilter; label: string; title: string }> = [
  { value: "csv", label: "CSV", title: "Show plot sets with CSV files" },
  { value: "svg", label: "SVG", title: "Show plot sets with SVG figures" },
  { value: "png", label: "PNG", title: "Show plot sets with PNG figures" },
  { value: "yaml", label: "YAML", title: "Show plot sets with Matplotlib YAML metadata" },
  { value: "missing", label: "Missing", title: "Show CSV files that do not have figures yet" },
];

const emptyPayload: BrowserPayload = {
  projectRoot: "",
  browseMode: "plot-set-manager",
  appInfo: {
    name: "MPLGallery",
    version: "0.1.0",
  },
  userSettings: {
    rememberRecentProjects: true,
    restoreLastProjectOnStartup: false,
  },
  rootContext: {
    activeRoot: "",
    launchRoot: "",
    recentRoots: [],
    error: null,
    showRootChooser: false,
  },
  selectedPlotId: null,
  datasets: [],
  plotSets: [],
  folderView: { nodes: [], rootId: ".", defaultSelectedPath: "." },
  filesView: { rows: [] },
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
  treeWidth: 390,
  folderPaneWidth: 160,
};

const layoutBounds = {
  treeMin: 300,
  treeMax: 560,
  folderPaneMin: 34,
  folderPaneMax: 320,
};

function App(props: StreamlitProps) {
  const payload = props.payload ?? emptyPayload;
  const appInfo = payload.appInfo ?? emptyPayload.appInfo;
  const userSettings = payload.userSettings ?? emptyPayload.userSettings;
  const updateInfo = appInfo?.update ?? null;
  const updateInstallInfo = appInfo?.updateInstall ?? null;
  const canInstallUpdate = Boolean(appInfo?.canInstallUpdates && updateInfo?.downloadUrl);
  const [browseMode, setBrowseModeState] = useState<"plot-set-manager" | "image-library" | string>(
    payload.browseMode ?? "plot-set-manager",
  );
  const imageLibraryMode = browseMode === "image-library";
  const itemNoun = imageLibraryMode ? "images" : "plot sets";
  const workspaceTitle = imageLibraryMode ? "Images" : "Plot sets";
  const rootContext = payload.rootContext ?? {
    activeRoot: payload.projectRoot,
    launchRoot: payload.projectRoot,
    recentRoots: [],
    error: null,
    showRootChooser: false,
  };
  const hasActiveRoot = Boolean(rootContext.activeRoot.trim());
  const activeRootLabel = hasActiveRoot ? projectRootName(rootContext.activeRoot) : "No project";
  const [selectedPlotId, setSelectedPlotId] = useState<string | null>(payload.selectedPlotId ?? null);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [selectedPlotSetId, setSelectedPlotSetId] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState(payload.folderView?.defaultSelectedPath ?? ".");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [checkedPlotIds, setCheckedPlotIds] = useState<Set<string>>(() => new Set());
  const [checkedDatasetIds, setCheckedDatasetIds] = useState<Set<string>>(() => new Set());
  const [checkedPlotSetIds, setCheckedPlotSetIds] = useState<Set<string>>(
    () => new Set((payload.plotSets ?? []).filter((plotSet) => plotSet.checked).map((plotSet) => plotSet.plotSetId)),
  );
  const [hasUserFilter, setHasUserFilter] = useState(false);
  const [fileFilters, setFileFilters] = useState<Set<FileFilter>>(() => new Set());
  const [showUngrouped, setShowUngrouped] = useState(false);
  const [tileSize, setTileSize] = useState(230);
  const tileSizeRef = useRef(230);
  const [cardSizes, setCardSizes] = useState<Record<string, number>>({});
  const [maximizedPlotId, setMaximizedPlotId] = useState<string | null>(null);
  const [activeCardTabs, setActiveCardTabs] = useState<Record<string, string>>({});
  const [pendingDraftDatasetId, setPendingDraftDatasetId] = useState<string | null>(null);
  const [updateInstallPending, setUpdateInstallPending] = useState(false);
  const [layout, setLayout] = useState(defaultLayout);
  const [foldersCollapsed, setFoldersCollapsed] = useState(false);
  const [filesCollapsed, setFilesCollapsed] = useState(false);
  const [draftPreferencesDatasetId, setDraftPreferencesDatasetId] = useState<string | null>(null);
  const [rootMenuOpen, setRootMenuOpen] = useState(Boolean(rootContext.showRootChooser));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [rootDraft, setRootDraft] = useState(rootContext.activeRoot);
  const [galleryLayout, setGalleryLayout] = useState<GalleryLayoutMode>("grid");
  const [checkedPlotSetOrder, setCheckedPlotSetOrder] = useState<string[]>([]);
  const [draggingPlotSetId, setDraggingPlotSetId] = useState<string | null>(null);
  const [dropTargetPlotSetId, setDropTargetPlotSetId] = useState<string | null>(null);
  const sidebarsAutoCollapsed = foldersCollapsed && filesCollapsed;

  useEffect(() => {
    setSelectedPlotId(payload.selectedPlotId ?? null);
  }, [payload.selectedPlotId]);

  useEffect(() => {
    setBrowseModeState(payload.browseMode ?? "plot-set-manager");
  }, [payload.browseMode]);

  useEffect(() => {
    if (!updateInfo?.available || updateInstallInfo?.started || updateInstallInfo?.error) {
      setUpdateInstallPending(false);
    }
  }, [updateInfo?.available, updateInstallInfo?.started, updateInstallInfo?.error]);

  useEffect(() => {
    setSelectedDatasetId(null);
    setSelectedPlotSetId(null);
    setSelectedFileId(null);
    setSelectedPlotId(payload.selectedPlotId ?? null);
    setSelectedFolder(payload.folderView?.defaultSelectedPath ?? ".");
    setCheckedPlotIds(new Set());
    setCheckedDatasetIds(new Set());
    setCheckedPlotSetIds(new Set());
    setHasUserFilter(false);
    setActiveCardTabs({});
    setPendingDraftDatasetId(null);
    setMaximizedPlotId(null);
    setRootDraft(rootContext.activeRoot);
    setCheckedPlotSetOrder([]);
    setCardSizes({});
  }, [rootContext.activeRoot, payload.selectedPlotId, payload.folderView?.defaultSelectedPath]);

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

  const effectiveCheckedPlotIds = useMemo(
    () => checkedPlotIds,
    [checkedPlotIds],
  );
  const draftPreferencesDataset = payload.datasets.find((dataset) => dataset.id === draftPreferencesDatasetId) ?? null;
  const datasetsById = useMemo(
    () => new Map(payload.datasets.map((dataset) => [dataset.id, dataset])),
    [payload.datasets],
  );
  const recordsById = useMemo(
    () => new Map(payload.records.map((record) => [record.id, record])),
    [payload.records],
  );
  const recordsByDatasetId = useMemo(() => {
    const linked = new Map<string, PlotRecord[]>();
    payload.records.forEach((record) => {
      if (!record.sourceDatasetId) return;
      const records = linked.get(record.sourceDatasetId) ?? [];
      records.push(record);
      linked.set(record.sourceDatasetId, records);
    });
    payload.datasets.forEach((dataset) => {
      const plotIds = [...(dataset.associatedPlotIds ?? []), ...(dataset.associatedPlotId ? [dataset.associatedPlotId] : [])];
      plotIds.forEach((plotId) => {
        const record = payload.records.find((candidate) => candidate.id === plotId);
        if (!record) return;
        const records = linked.get(dataset.id) ?? [];
        if (!records.some((candidate) => candidate.id === record.id)) records.push(record);
        linked.set(dataset.id, records);
      });
    });
    return linked;
  }, [payload.datasets, payload.records]);
  const plotSets = useMemo(
    () => payload.plotSets ?? legacyPlotSets(payload.datasets, payload.records, recordsByDatasetId),
    [payload.plotSets, payload.datasets, payload.records, recordsByDatasetId],
  );
  const folderNodes = useMemo(
    () =>
      payload.folderView?.nodes?.length
        ? payload.folderView.nodes
        : folderNodesFromPlotSets(plotSets, projectRootName(rootContext.activeRoot)),
    [payload.folderView?.nodes, plotSets, rootContext.activeRoot],
  );
  const filteredPlotSets = useMemo(
    () =>
      plotSets.filter(
        (plotSet) => plotSetMatchesFolder(plotSet, selectedFolder) && plotSetMatchesFilters(plotSet, fileFilters),
      ),
    [plotSets, selectedFolder, fileFilters],
  );
  const selectedPlotRecord = selectedPlotId
    ? payload.records.find((record) => record.id === selectedPlotId) ?? null
    : null;
  const visibleItems = useMemo(
    () =>
      buildVisibleItems({
        plotSets,
        datasetsById,
        recordsById,
        recordsByDatasetId,
        checkedPlotSetIds,
        checkedPlotSetOrder,
        fileFilters,
      }),
    [plotSets, datasetsById, recordsById, recordsByDatasetId, checkedPlotSetIds, checkedPlotSetOrder, fileFilters],
  );
  const status = useMemo(() => galleryStatus(payload.records), [payload.records]);
  const noVisiblePlotsMessage = emptyGalleryMessage(
    payload.records,
    "",
    effectiveCheckedPlotIds,
    hasUserFilter,
    itemNoun,
  );
  const selectedRecord = selectedPlotRecord ?? null;
  const maximizedRecord =
    payload.records.find((record) => record.id === maximizedPlotId) ?? selectedRecord;

  useEffect(() => {
    if (!pendingDraftDatasetId) return;
    const record = recordsByDatasetId.get(pendingDraftDatasetId)?.[0];
    if (!record) return;
    setActiveCardTabs((current) => ({ ...current, [cardIdForDataset(pendingDraftDatasetId)]: record.id }));
    setActiveCardTabs((current) => ({ ...current, [pendingDraftDatasetId]: record.id }));
    setSelectedPlotId(record.id);
    setPendingDraftDatasetId(null);
  }, [pendingDraftDatasetId, recordsByDatasetId]);

  useEffect(() => {
    setCheckedPlotSetIds((current) => {
      if (!hasUserFilter) return new Set();
      const validIds = new Set(plotSets.map((plotSet) => plotSet.plotSetId));
      return new Set([...current].filter((plotSetId) => validIds.has(plotSetId)));
    });
  }, [plotSets, hasUserFilter]);

  useEffect(() => {
    const validIds = new Set(plotSets.map((plotSet) => plotSet.plotSetId));
    setCheckedPlotSetOrder((current) => current.filter((plotSetId) => validIds.has(plotSetId)));
  }, [plotSets]);

  function selectFolder(folderPath: string) {
    setSelectedFolder(folderPath);
  }

  function emitCheckedPlotSetIds(plotSetIds: Set<string>) {
    Streamlit.setComponentValue({
      event: {
        id: eventId("set_checked_plot_sets"),
        type: "set_checked_plot_sets",
        plot_set_ids: [...plotSetIds],
      },
    });
  }

  function focusPlotSet(plotSetId: string, preferredAttachmentId?: string) {
    const plotSet = plotSets.find((candidate) => candidate.plotSetId === plotSetId);
    if (!plotSet) return;
    setSelectedPlotSetId(plotSetId);
    const attachment = preferredAttachmentId
      ? plotSet.attachments.find((candidate) => candidate.id === preferredAttachmentId)
      : plotSet.preferredFigure ?? plotSet.attachments.find((candidate) => candidate.type === "csv") ?? plotSet.attachments[0];
    if (attachment) activateAttachment(plotSet, attachment);
  }

  function activateAttachment(plotSet: PlotSetEntity, attachment: PlotSetAttachment) {
    const tab = attachment.type === "csv" ? "csv" : attachment.plotId ?? attachment.id;
    setActiveCardTabs((current) => ({ ...current, [plotSet.plotSetId]: tab }));
    if (attachment.type === "csv" && attachment.datasetId) {
      setSelectedDatasetId(attachment.datasetId);
      setSelectedPlotId(null);
      setSelectedFileId(`plotset:${plotSet.plotSetId}:csv`);
      return;
    }
    if ((attachment.type === "svg" || attachment.type === "png") && attachment.plotId) {
      const record = recordsById.get(attachment.plotId);
      setSelectedPlotId(attachment.plotId);
      setSelectedDatasetId(record?.sourceDatasetId ?? null);
      setSelectedFileId(`plotset:${plotSet.plotSetId}:${attachment.plotId}`);
    }
  }

  function togglePlotSet(plotSetId: string, checked: boolean) {
    setHasUserFilter(true);
    setCheckedPlotSetIds((current) => {
      const next = new Set(current);
      if (checked) next.add(plotSetId);
      else next.delete(plotSetId);
      emitCheckedPlotSetIds(next);
      return next;
    });
    setCheckedPlotSetOrder((current) => {
      if (checked) {
        return current.includes(plotSetId) ? current : [...current, plotSetId];
      }
      return current.filter((candidate) => candidate !== plotSetId);
    });
    const plotSet = plotSets.find((candidate) => candidate.plotSetId === plotSetId);
    setCheckedDatasetIds((current) => syncLegacyDatasetChecks(current, plotSet, checked));
    setCheckedPlotIds((current) => syncLegacyPlotChecks(current, plotSet, checked));
  }

  function toggleVisiblePlotSets(visiblePlotSets: PlotSetEntity[], checked: boolean) {
    setHasUserFilter(true);
    const visibleIds = new Set(visiblePlotSets.map((plotSet) => plotSet.plotSetId));
    setCheckedPlotSetIds((current) => {
      const next = new Set(current);
      visibleIds.forEach((plotSetId) => {
        if (checked) next.add(plotSetId);
        else next.delete(plotSetId);
      });
      emitCheckedPlotSetIds(next);
      return next;
    });
    setCheckedPlotSetOrder((current) => {
      if (checked) {
        const next = [...current];
        visiblePlotSets.forEach((plotSet) => {
          if (!next.includes(plotSet.plotSetId)) next.push(plotSet.plotSetId);
        });
        return next;
      }
      return current.filter((plotSetId) => !visibleIds.has(plotSetId));
    });
    setCheckedDatasetIds((current) => {
      let next = new Set(current);
      visiblePlotSets.forEach((plotSet) => {
        next = syncLegacyDatasetChecks(next, plotSet, checked);
      });
      return next;
    });
    setCheckedPlotIds((current) => {
      let next = new Set(current);
      visiblePlotSets.forEach((plotSet) => {
        next = syncLegacyPlotChecks(next, plotSet, checked);
      });
      return next;
    });
  }

  function reorderCheckedPlotSet(draggedPlotSetId: string, targetPlotSetId: string) {
    if (draggedPlotSetId === targetPlotSetId) return;
    setCheckedPlotSetOrder((current) => {
      const draggedIndex = current.indexOf(draggedPlotSetId);
      const targetIndex = current.indexOf(targetPlotSetId);
      if (draggedIndex < 0 || targetIndex < 0) return current;
      const next = [...current];
      const [dragged] = next.splice(draggedIndex, 1);
      next.splice(targetIndex, 0, dragged);
      return next;
    });
  }

  function reorderDraggingPlotSet(draggedPlotSetId: string, targetPlotSetId: string) {
    if (
      checkedPlotSetIds.has(draggedPlotSetId)
      && checkedPlotSetIds.has(targetPlotSetId)
      && draggedPlotSetId !== targetPlotSetId
      && dropTargetPlotSetId !== targetPlotSetId
    ) {
      setDropTargetPlotSetId(targetPlotSetId);
      reorderCheckedPlotSet(draggedPlotSetId, targetPlotSetId);
    }
  }

  function selectPlot(plotId: string) {
    const record = payload.records.find((candidate) => candidate.id === plotId);
    if (record?.sourceDatasetId && datasetsById.has(record.sourceDatasetId)) {
      setSelectedDatasetId(record.sourceDatasetId);
      setActiveCardTabs((current) => ({ ...current, [cardIdForDataset(record.sourceDatasetId!)]: plotId }));
    } else {
      setSelectedDatasetId(null);
      setActiveCardTabs((current) => ({ ...current, [cardIdForPlot(plotId)]: plotId }));
    }
    setSelectedFileId(`plot:${plotId}`);
    setSelectedPlotId(plotId);
  }

  function selectDataset(datasetId: string) {
    setSelectedDatasetId(datasetId);
    setSelectedFileId(`csv:${datasetId}`);
    setSelectedPlotId(null);
    setActiveCardTabs((current) => ({ ...current, [cardIdForDataset(datasetId)]: "csv" }));
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
    setPendingDraftDatasetId(datasetId);
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

  function updateTileSize(value: number) {
    const nextTileSize = clampNumber(value, 160, 1400);
    const ratio = nextTileSize / Math.max(tileSizeRef.current, 1);
    tileSizeRef.current = nextTileSize;
    setTileSize(nextTileSize);
    setCardSizes((current) => {
      const next = Object.fromEntries(
        Object.entries(current).map(([cardId, size]) => [cardId, clampNumber(size * ratio, 180, 1400)]),
      );
      return next;
    });
  }

  function updateTileSizeFromInputClientX(input: HTMLInputElement, clientX: number) {
    const min = Number(input.min) || 160;
    const max = Number(input.max) || 1400;
    const step = Number(input.step) || 20;
    const rect = input.getBoundingClientRect();
    const fraction = rect.width > 0 ? clampNumber((clientX - rect.left) / rect.width, 0, 1) : 0;
    const rawValue = min + (max - min) * fraction;
    const steppedValue = min + Math.round((rawValue - min) / step) * step;
    updateTileSize(steppedValue);
  }

  function startTileSizeDrag(event: ReactPointerEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const pointerId = event.pointerId;
    updateTileSizeFromInputClientX(input, event.clientX);
    input.setPointerCapture?.(pointerId);
    const onPointerMove = (moveEvent: PointerEvent) => updateTileSizeFromInputClientX(input, moveEvent.clientX);
    const onPointerUp = () => {
      input.releasePointerCapture?.(pointerId);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
  }

  function startTileSizeMouseDrag(event: ReactMouseEvent<HTMLInputElement>) {
    if (event.button !== 0) return;
    const input = event.currentTarget;
    updateTileSizeFromInputClientX(input, event.clientX);
    const onMouseMove = (moveEvent: MouseEvent) => updateTileSizeFromInputClientX(input, moveEvent.clientX);
    const onMouseUp = () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp, { once: true });
  }

  function toggleFileFilter(filter: FileFilter) {
    setFileFilters((current) => {
      const next = new Set(current);
      if (next.has(filter)) next.delete(filter);
      else next.add(filter);
      return next;
    });
  }

  function resizeCard(cardId: string, size: number) {
    setCardSizes((current) => ({
      ...current,
      [cardId]: clampNumber(size, 180, 1400),
    }));
  }

  function toggleFoldersCollapsed() {
    setFoldersCollapsed((current) => !current);
  }

  function toggleFilesCollapsed() {
    setFilesCollapsed((current) => !current);
  }

  function setBrowseMode(mode: "plot-set-manager" | "image-library") {
    if (mode === browseMode) return;
    setBrowseModeState(mode);
    setCheckedPlotSetIds(new Set());
    setCheckedPlotSetOrder([]);
    setSelectedPlotSetId(null);
    setSelectedDatasetId(null);
    setSelectedFileId(null);
    setActiveCardTabs({});
    setFileFilters(new Set());
    Streamlit.setComponentValue({
      event: {
        id: eventId("set_browse_mode"),
        type: "set_browse_mode",
        browse_mode: mode,
      },
    });
  }

  function changeProjectRoot(rootPath: string) {
    Streamlit.setComponentValue({
      event: {
        id: eventId("change_project_root"),
        type: "change_project_root",
        root_path: rootPath,
      },
    });
  }

  function browseProjectRoot() {
    Streamlit.setComponentValue({
      event: {
        id: eventId("browse_project_root"),
        type: "browse_project_root",
      },
    });
  }

  function resetProjectRoot() {
    Streamlit.setComponentValue({
      event: {
        id: eventId("reset_project_root"),
        type: "reset_project_root",
      },
    });
  }

  function openUpdate() {
    const target = updateInfo?.downloadUrl || updateInfo?.releaseUrl;
    if (!target) return;
    if (canInstallUpdate && updateInfo?.downloadUrl) {
      setUpdateInstallPending(true);
      Streamlit.setComponentValue({
        event: {
          id: eventId("install_update"),
          type: "install_update",
          download_url: updateInfo.downloadUrl,
        },
      });
      return;
    }
    window.open(target, "_blank", "noopener,noreferrer");
  }

  function forgetRecentRoot(rootPath: string) {
    Streamlit.setComponentValue({
      event: {
        id: eventId("forget_recent_root"),
        type: "forget_recent_root",
        root_path: rootPath,
      },
    });
  }

  function setUserSetting(settingKey: string, settingValue: boolean) {
    Streamlit.setComponentValue({
      event: {
        id: eventId("set_user_setting"),
        type: "set_user_setting",
        setting_key: settingKey,
        setting_value: settingValue,
      },
    });
  }

  function clearRecentRoots() {
    Streamlit.setComponentValue({
      event: {
        id: eventId("clear_recent_roots"),
        type: "clear_recent_roots",
      },
    });
  }

  function refreshIndex() {
    Streamlit.setComponentValue({
      event: {
        id: eventId("refresh_index"),
        type: "refresh_index",
      },
    });
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

  function startFolderPaneResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = layout.folderPaneWidth;
    const maxWidth = Math.max(layoutBounds.folderPaneMin, Math.min(layoutBounds.folderPaneMax, layout.treeWidth - 130));
    const handlePointerMove = (moveEvent: PointerEvent) => {
      const nextWidth = clampNumber(
        startWidth + moveEvent.clientX - startX,
        layoutBounds.folderPaneMin,
        maxWidth,
      );
      setLayout((current) => ({ ...current, folderPaneWidth: nextWidth }));
    };
    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove);
      document.body.classList.remove("mg-is-resizing");
    };

    document.body.classList.add("mg-is-resizing");
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp, { once: true });
  }

  function resizeFolderPaneWithKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 12 : -12;
    const maxWidth = Math.max(layoutBounds.folderPaneMin, Math.min(layoutBounds.folderPaneMax, layout.treeWidth - 130));
    setLayout((current) => ({
      ...current,
      folderPaneWidth: clampNumber(current.folderPaneWidth + delta, layoutBounds.folderPaneMin, maxWidth),
    }));
  }

  const shellStyle = {
    "--tree-width": sidebarsAutoCollapsed ? "82px" : `${layout.treeWidth}px`,
    "--folder-pane-width": `${layout.folderPaneWidth}px`,
  } as CSSProperties;

  return (
    <div
      className={`mg-shell ${sidebarsAutoCollapsed ? "is-sidebars-auto-collapsed" : ""} ${hasActiveRoot ? "" : "is-no-project"}`}
      style={shellStyle}
    >
      <header className="mg-appbar" aria-label="MPLGallery app controls">
        <div className="mg-brand">
          <img className="mg-brand-icon" src="./favicon.png" alt="" aria-hidden="true" />
          <span>MPLGallery</span>
        </div>
        <div className="mg-project-control">
          <button
            type="button"
            className="mg-project-button"
            aria-expanded={rootMenuOpen}
            aria-label={`Project root ${activeRootLabel}`}
            onClick={() => setRootMenuOpen((current) => !current)}
          >
            <Folder aria-hidden="true" size={16} />
            <span>{activeRootLabel}</span>
            <ChevronDown aria-hidden="true" size={14} />
          </button>
          {rootMenuOpen ? (
            <div className="mg-root-popover" role="dialog" aria-label="Project root menu">
              <label>
                Project path
                <input value={rootDraft} onChange={(event) => setRootDraft(event.target.value)} />
              </label>
              {rootContext.error ? <div className="mg-root-error">{rootContext.error}</div> : null}
              <div className="mg-root-actions">
                <button type="button" onClick={() => changeProjectRoot(rootDraft)}>
                  Open root
                </button>
                <button type="button" onClick={browseProjectRoot}>
                  Open Project...
                </button>
                <button type="button" onClick={resetProjectRoot}>
                  Launch root
                </button>
              </div>
              {rootContext.recentRoots.length ? (
                <div className="mg-root-recents" aria-label="Recent roots">
                  <div className="mg-root-recents-title">Recent</div>
                  {rootContext.recentRoots
                    .filter((root) => root !== rootContext.activeRoot)
                    .slice(0, 5)
                    .map((root) => (
                      <div className="mg-root-recent" key={root}>
                        <button type="button" title={root} onClick={() => changeProjectRoot(root)}>
                          {shortRootPath(root)}
                        </button>
                        <button type="button" aria-label={`Forget ${root}`} onClick={() => forgetRecentRoot(root)}>
                          ×
                        </button>
                      </div>
                    ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
        <button type="button" className="mg-appbar-button" onClick={browseProjectRoot}>
          <FolderOpen aria-hidden="true" size={16} />
          Open Project...
        </button>
        <div className="mg-mode-switch" role="group" aria-label="Browse mode">
          <button
            type="button"
            className={!imageLibraryMode ? "is-active" : ""}
            aria-pressed={!imageLibraryMode}
            onClick={() => setBrowseMode("plot-set-manager")}
          >
            Plot sets
          </button>
          <button
            type="button"
            className={imageLibraryMode ? "is-active" : ""}
            aria-pressed={imageLibraryMode}
            onClick={() => setBrowseMode("image-library")}
          >
            Pictures
          </button>
        </div>
        <button
          type="button"
          className="mg-appbar-button"
          onClick={draftCheckedDatasets}
          disabled={!checkedDatasetIds.size}
        >
          <BarChart3 aria-hidden="true" size={16} />
          Generate plots
          <ChevronDown aria-hidden="true" size={13} />
        </button>
        <button type="button" className="mg-appbar-button" onClick={refreshIndex}>
          <RefreshCw aria-hidden="true" size={16} />
          Refresh
        </button>
        {updateInfo?.available ? (
          <button
            type="button"
            className="mg-appbar-button is-update"
            aria-label={`${canInstallUpdate ? "Install" : "Download"} ${appInfo?.name ?? "MPLGallery"} ${updateInfo.latestVersion ?? "update"}`}
            onClick={openUpdate}
            disabled={updateInstallPending}
          >
            <CheckCircle2 aria-hidden="true" size={16} />
            {updateInstallPending ? "Downloading update..." : `Update ${updateInfo.latestVersion}`}
          </button>
        ) : null}
        <div className="mg-appbar-spacer" />
        <details className="mg-status-menu">
          <summary>
            <Info aria-hidden="true" size={16} />
            Status
            <ChevronDown aria-hidden="true" size={13} />
          </summary>
            <div className="mg-status-popover" aria-label="Project status">
              {appInfo?.version ? <span>App {appInfo.version}</span> : null}
              {updateInfo?.checked && !updateInfo.available ? <span>Up to date</span> : null}
              {updateInfo?.error ? <span className="is-warning">Update check failed</span> : null}
              {updateInstallPending ? <span>Downloading update...</span> : null}
              {updateInstallInfo?.started ? <span>Update installer started</span> : null}
              {updateInstallInfo?.error ? <span className="is-warning">Update install failed: {updateInstallInfo.error}</span> : null}
              <span>{status.totalPlots} plots</span>
            <span>{status.matchedCsvs} CSV matched</span>
            <span className={status.missingCsvs ? "is-warning" : ""}>{status.missingCsvs} missing CSV</span>
            <span className={status.renderErrors ? "is-warning" : ""}>{status.renderErrors} render errors</span>
          </div>
        </details>
        <div className="mg-settings-control">
          <button
            type="button"
            className="mg-appbar-button is-iconish"
            aria-expanded={settingsOpen}
            onClick={() => setSettingsOpen((current) => !current)}
          >
            <Settings aria-hidden="true" size={16} />
            Settings
          </button>
          {settingsOpen ? (
            <div className="mg-settings-popover" role="dialog" aria-label="Settings">
              <label className="mg-setting-row">
                <input
                  type="checkbox"
                  checked={userSettings?.rememberRecentProjects ?? true}
                  onChange={(event) => setUserSetting("remember_recent_projects", event.target.checked)}
                />
                <span>Remember recent projects</span>
              </label>
              <label className="mg-setting-row">
                <input
                  type="checkbox"
                  checked={userSettings?.restoreLastProjectOnStartup ?? false}
                  onChange={(event) => setUserSetting("restore_last_project_on_startup", event.target.checked)}
                />
                <span>Restore last project on startup</span>
              </label>
              <button type="button" className="mg-settings-action" onClick={clearRecentRoots}>
                Clear recent projects
              </button>
            </div>
          ) : null}
        </div>
        <div className="mg-help-control">
          <button
            type="button"
            className="mg-appbar-button is-iconish"
            aria-expanded={helpOpen}
            onClick={() => setHelpOpen((current) => !current)}
          >
            <HelpCircle aria-hidden="true" size={16} />
            Help
          </button>
          {helpOpen ? (
            <div className="mg-help-popover" role="dialog" aria-label="Help">
              <strong>Quick help</strong>
              <ul>
                <li>Open Project loads a repository or analysis folder.</li>
                <li>Use folder rows to scope the Files pane.</li>
                <li>Click a file row to select it and add its card.</li>
                <li>Use file-type chips to narrow the Files pane.</li>
                <li>Drag checked cards to reorder them, or drag the lower-right corner to resize them.</li>
                <li>Use card tabs for CSV, SVG, PNG, and YAML views.</li>
              </ul>
            </div>
          ) : null}
        </div>
      </header>
      {!hasActiveRoot ? (
        <main className="mg-workspace mg-empty-workspace" aria-label="Project workspace">
          <section className="mg-empty-project" aria-label="No project selected">
            <h1>No project open</h1>
            <p>Open a project folder to start browsing plots and images.</p>
            {rootContext.error ? <div className="mg-root-error">{rootContext.error}</div> : null}
            <button type="button" className="mg-appbar-button" onClick={browseProjectRoot}>
              <FolderOpen aria-hidden="true" size={16} />
              Open Project...
            </button>
            {rootContext.recentRoots.length ? (
              <div className="mg-empty-recents" aria-label="Recent projects">
                <div className="mg-root-recents-title">Recent projects</div>
                {rootContext.recentRoots.slice(0, 5).map((root) => (
                  <button type="button" key={root} title={root} onClick={() => changeProjectRoot(root)}>
                    {projectRootName(root)}
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        </main>
      ) : (
        <>
          <aside className="mg-tree-panel mg-left-workspace" aria-label="Plot set workspace">
            <div
              className={`mg-left-panes ${foldersCollapsed ? "is-folders-collapsed" : ""} ${filesCollapsed ? "is-files-collapsed" : ""}`}
            >
            <FoldersPane
              nodes={folderNodes}
              selectedFolder={selectedFolder}
              collapsed={foldersCollapsed}
              onToggleCollapsed={toggleFoldersCollapsed}
              onSelectFolder={selectFolder}
            />
            <div
              className="mg-pane-resizer"
              role="separator"
              aria-label="Resize folders and files panes"
              aria-orientation="vertical"
              aria-valuemin={layoutBounds.folderPaneMin}
              aria-valuemax={Math.max(layoutBounds.folderPaneMin, Math.min(layoutBounds.folderPaneMax, layout.treeWidth - 130))}
              aria-valuenow={layout.folderPaneWidth}
              tabIndex={foldersCollapsed || filesCollapsed ? -1 : 0}
              onKeyDown={resizeFolderPaneWithKeyboard}
              onPointerDown={foldersCollapsed || filesCollapsed ? undefined : startFolderPaneResize}
            />
            <FilesPane
              key={selectedFolder}
              plotSets={filteredPlotSets}
              itemNoun={itemNoun}
              activeFilters={fileFilters}
              checkedPlotSetIds={checkedPlotSetIds}
              selectedPlotSetId={selectedPlotSetId}
              collapsed={filesCollapsed}
              showUngrouped={showUngrouped}
              onToggleCollapsed={toggleFilesCollapsed}
              onToggleFilter={toggleFileFilter}
              onClearFilters={() => setFileFilters(new Set())}
              onToggleShowUngrouped={(show) => {
                setShowUngrouped(show);
              }}
              onFocus={focusPlotSet}
              onToggleChecked={togglePlotSet}
              onToggleAllChecked={(checked) => toggleVisiblePlotSets(filteredPlotSets, checked)}
            />
            </div>
          </aside>

          <div
            className="mg-resizer"
            role="separator"
            aria-label="Resize output tree"
            aria-orientation="vertical"
            aria-valuemin={layoutBounds.treeMin}
            aria-valuemax={layoutBounds.treeMax}
            aria-valuenow={layout.treeWidth}
            tabIndex={sidebarsAutoCollapsed ? -1 : 0}
            onKeyDown={resizeTreeWithKeyboard}
            onPointerDown={sidebarsAutoCollapsed ? undefined : startTreeResize}
          />

          <main className="mg-workspace" aria-label="Plot workspace">
        <div className="mg-workspace-header">
          <div className="mg-workspace-heading">
            <div className="mg-workspace-title">{workspaceTitle}</div>
            <div className="mg-eyebrow">{filteredPlotSets.length} in folder</div>
          </div>
          <div className="mg-header-actions">
            <span>{checkedPlotSetIds.size} selected</span>
            <strong>{`${visibleItems.length} item${visibleItems.length === 1 ? "" : "s"}`}</strong>
            <div className="mg-layout-mode" role="group" aria-label="Gallery layout">
              <button
                type="button"
                className={galleryLayout === "grid" ? "is-active" : ""}
                onClick={() => setGalleryLayout("grid")}
              >
                Grid
              </button>
              <button
                type="button"
                className={galleryLayout === "rows" ? "is-active" : ""}
                onClick={() => setGalleryLayout("rows")}
              >
                Rows
              </button>
              <button
                type="button"
                className={galleryLayout === "columns" ? "is-active" : ""}
                onClick={() => setGalleryLayout("columns")}
              >
                Columns
              </button>
            </div>
            <label className="mg-tile-control">
              <span>Tile size</span>
              <input
                type="range"
                min="160"
                max="1400"
                step="20"
                value={tileSize}
                onChange={(event) => updateTileSize(Number(event.target.value))}
                onPointerDown={startTileSizeDrag}
                onMouseDown={startTileSizeMouseDrag}
              />
            </label>
            <button className="mg-inspector-toggle" type="button" onClick={() => setLayout(defaultLayout)}>
              Reset layout
            </button>
          </div>
        </div>
        <div className="mg-workspace-body">
          <section className="mg-gallery" aria-label="Plot gallery">
            <div
              className={`mg-card-grid is-${galleryLayout} ${draggingPlotSetId ? "is-dragging-card" : ""}`}
              style={{ ["--tile-size" as string]: `${tileSize}px` }}
            >
              {visibleItems.length ? (
                visibleItems.map((item) => (
                  <DataPlotCard
                    key={item.id}
                    item={item}
                    activeTab={activeCardTabs[item.id] ?? defaultCardTab(item)}
                    selected={
                      item.plotSet?.plotSetId === selectedPlotSetId
                      ||
                      (item.dataset?.id != null && item.dataset.id === selectedDatasetId)
                      || item.records.some((record) => record.id === selectedRecord?.id)
                    }
                    tileSize={tileSize}
                    cardSize={cardSizes[item.id] ?? tileSize}
                    onActivateTab={(tab) => {
                      setActiveCardTabs((current) => ({ ...current, [item.id]: tab }));
                    }}
                    onGenerate={() => {
                      if (item.dataset) draftDataset(item.dataset.id);
                    }}
                    onMaximize={(plotId) => maximizePlot(plotId)}
                    onSaveRedraw={(plotId, redraw) => {
                      Streamlit.setComponentValue({
                        event: {
                          id: eventId("save_redraw_metadata"),
                          type: "save_redraw_metadata",
                          plot_id: plotId,
                          redraw,
                        },
                      });
                    }}
                    onSaveYaml={(plotId, attachmentPath, yamlText) => {
                      Streamlit.setComponentValue({
                        event: {
                          id: eventId("save_yaml_attachment"),
                          type: "save_yaml_attachment",
                          plot_id: plotId,
                          attachment_path: attachmentPath,
                          yaml_text: yamlText,
                        },
                      });
                    }}
                    onResize={(size) => resizeCard(item.id, size)}
                    checked={Boolean(item.plotSet && checkedPlotSetIds.has(item.plotSet.plotSetId))}
                    dragging={Boolean(item.plotSet && draggingPlotSetId === item.plotSet.plotSetId)}
                    dropTarget={Boolean(item.plotSet && dropTargetPlotSetId === item.plotSet.plotSetId)}
                    onDragStart={() => {
                      if (item.plotSet && checkedPlotSetIds.has(item.plotSet.plotSetId)) {
                        setDraggingPlotSetId(item.plotSet.plotSetId);
                      }
                    }}
                    onDragOver={() => {
                      if (
                        item.plotSet
                        && draggingPlotSetId
                        && checkedPlotSetIds.has(item.plotSet.plotSetId)
                        && draggingPlotSetId !== item.plotSet.plotSetId
                        && dropTargetPlotSetId !== item.plotSet.plotSetId
                      ) {
                        setDropTargetPlotSetId(item.plotSet.plotSetId);
                        reorderCheckedPlotSet(draggingPlotSetId, item.plotSet.plotSetId);
                      }
                    }}
                    onDrop={() => {
                      if (item.plotSet && draggingPlotSetId) {
                        reorderCheckedPlotSet(draggingPlotSetId, item.plotSet.plotSetId);
                      }
                      setDraggingPlotSetId(null);
                      setDropTargetPlotSetId(null);
                    }}
                    onDragEnd={() => {
                      setDraggingPlotSetId(null);
                      setDropTargetPlotSetId(null);
                    }}
                    onPointerDragOver={reorderDraggingPlotSet}
                  />
                ))
              ) : (
                <EmptyGallery message={noVisiblePlotsMessage} />
              )}
            </div>
          </section>
        </div>
      </main>
        </>
      )}

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

function buildVisibleItems({
  plotSets,
  datasetsById,
  recordsById,
  recordsByDatasetId,
  checkedPlotSetIds,
  checkedPlotSetOrder,
  fileFilters,
}: {
  plotSets: PlotSetEntity[];
  datasetsById: Map<string, DatasetRecord>;
  recordsById: Map<string, PlotRecord>;
  recordsByDatasetId: Map<string, PlotRecord[]>;
  checkedPlotSetIds: Set<string>;
  checkedPlotSetOrder: string[];
  fileFilters: Set<FileFilter>;
}): DataPlotItem[] {
  const items = new Map<string, DataPlotItem>();

  function includeItem(item: DataPlotItem) {
    if (!itemMatchesFilters(item, fileFilters)) return;
    items.set(item.id, item);
  }

  plotSets.forEach((plotSet) => {
    if (!checkedPlotSetIds.has(plotSet.plotSetId)) return;
    const datasetId = datasetIdForPlotSet(plotSet);
    const dataset = datasetId ? datasetsById.get(datasetId) ?? null : null;
    const records = recordsForPlotSet(plotSet, recordsById, recordsByDatasetId, datasetId);
    includeItem({ id: plotSet.plotSetId, plotSet, dataset, records });
  });

  const orderIndex = new Map(checkedPlotSetOrder.map((plotSetId, index) => [plotSetId, index]));
  return [...items.values()].sort((left, right) => {
    const leftOrder = left.plotSet ? orderIndex.get(left.plotSet.plotSetId) : undefined;
    const rightOrder = right.plotSet ? orderIndex.get(right.plotSet.plotSetId) : undefined;
    if (leftOrder != null && rightOrder != null && leftOrder !== rightOrder) return leftOrder - rightOrder;
    if (leftOrder != null && rightOrder == null) return -1;
    if (leftOrder == null && rightOrder != null) return 1;
    return cardTitle(left).localeCompare(cardTitle(right));
  });
}

function itemMatchesFilters(item: DataPlotItem, fileFilters: Set<FileFilter>): boolean {
  if (!fileFilters.size) return true;
  if (item.plotSet) return plotSetMatchesFilters(item.plotSet, fileFilters);
  return [...fileFilters].some((fileFilter) => {
    if (fileFilter === "csv") return Boolean(item.dataset);
    if (fileFilter === "svg") return item.records.some((record) => record.kind.toLowerCase() === "svg");
    if (fileFilter === "png") return item.records.some((record) => record.kind.toLowerCase() === "png");
    if (fileFilter === "yaml") return false;
    if (fileFilter === "missing") return Boolean(item.dataset && item.records.length === 0);
    return false;
  });
}

function datasetIdForPlotSet(plotSet: PlotSetEntity): string | null {
  return plotSet.attachments.find((attachment) => attachment.type === "csv" && attachment.datasetId)?.datasetId ?? null;
}

function recordsForPlotSet(
  plotSet: PlotSetEntity,
  recordsById: Map<string, PlotRecord>,
  recordsByDatasetId: Map<string, PlotRecord[]>,
  datasetId: string | null,
): PlotRecord[] {
  const records = new Map<string, PlotRecord>();
  if (datasetId) {
    (recordsByDatasetId.get(datasetId) ?? []).forEach((record) => records.set(record.id, record));
  }
  plotSet.attachments.forEach((attachment) => {
    if (!attachment.plotId) return;
    const record = recordsById.get(attachment.plotId);
    if (record) records.set(record.id, record);
  });
  return [...records.values()].sort((left, right) => preferredRecordSortKey(left).localeCompare(preferredRecordSortKey(right)));
}

function preferredRecordSortKey(record: PlotRecord): string {
  const suffixRank = record.kind.toLowerCase() === "svg" ? "0" : record.kind.toLowerCase() === "png" ? "1" : "2";
  return `${suffixRank}:${record.name.toLowerCase()}`;
}

function plotSetMatchesFolder(plotSet: PlotSetEntity, folderPath: string): boolean {
  if (folderPath === ".") return true;
  return plotSet.folderPath === folderPath || plotSet.folderPath.startsWith(`${folderPath}/`);
}

function plotSetMatchesFilters(plotSet: PlotSetEntity, fileFilters: Set<FileFilter>): boolean {
  if (!fileFilters.size) return true;
  const types = new Set(plotSet.attachments.map((attachment) => attachment.type));
  return [...fileFilters].some((fileFilter) => {
    if (fileFilter === "csv") return types.has("csv");
    if (fileFilter === "svg") return types.has("svg");
    if (fileFilter === "png") return types.has("png");
    if (fileFilter === "yaml") return types.has("mpl_yaml");
    if (fileFilter === "missing") return types.has("csv") && !types.has("svg") && !types.has("png");
    return false;
  });
}

function fileMatchesFilter(
  file: FileItem,
  fileFilters: Set<FileFilter>,
  recordsByDatasetId: Map<string, PlotRecord[]>,
): boolean {
  if (!fileFilters.size) return true;
  const suffix = (file.suffix ?? file.path.split(".").pop() ?? "").toLowerCase().replace(/^\./, "");
  return [...fileFilters].some((fileFilter) => {
    if (fileFilter === "csv") return file.kind === "csv";
    if (fileFilter === "svg") return file.kind === "image" && suffix === "svg";
    if (fileFilter === "png") return file.kind === "image" && suffix === "png";
    if (fileFilter === "yaml") return suffix === "yaml" || suffix === "yml";
    if (fileFilter === "missing") {
      return file.kind === "csv" && Boolean(file.datasetId && !(recordsByDatasetId.get(file.datasetId)?.length));
    }
    return false;
  });
}

function shortRootPath(rootPath: string): string {
  const normalized = rootPath.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length <= 2) return rootPath;
  return `.../${parts.slice(-2).join("/")}`;
}

function cardIdForDataset(datasetId: string): string {
  return `dataset:${datasetId}`;
}

function cardIdForPlot(plotId: string): string {
  return `plot:${plotId}`;
}

function defaultCardTab(item: DataPlotItem): string {
  const preferredPlotId = item.plotSet?.preferredFigure?.plotId;
  if (preferredPlotId && item.records.some((record) => record.id === preferredPlotId)) return preferredPlotId;
  const svgRecord = item.records.find((record) => record.kind.toLowerCase() === "svg");
  if (svgRecord) return svgRecord.id;
  return item.records[0]?.id ?? "csv";
}

function cardTitle(item: DataPlotItem): string {
  return item.plotSet?.title ?? item.dataset?.displayName ?? item.records[0]?.name ?? "Untitled";
}

function shouldIgnoreCardDrag(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return true;
  return Boolean(
    target.closest(
      ".mg-card-tabs, .mg-edit-button, .mg-card-resize, .mg-card-actions, input, select, textarea, label",
    ),
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

function FoldersPane({
  nodes,
  selectedFolder,
  collapsed,
  onToggleCollapsed,
  onSelectFolder,
}: {
  nodes: FolderViewNode[];
  selectedFolder: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onSelectFolder: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const childNodes = useMemo(() => {
    const children = new Map<string, FolderViewNode[]>();
    nodes.forEach((node) => {
      const parent = node.parentId ?? "";
      children.set(parent, [...(children.get(parent) ?? []), node]);
    });
    children.forEach((items) => items.sort((left, right) => left.label.localeCompare(right.label)));
    return children;
  }, [nodes]);
  const root = nodes.find((node) => node.id === ".") ?? nodes[0];

  useEffect(() => {
    setExpanded(new Set());
  }, [nodes]);

  function toggle(path: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function renderFolder(node: FolderViewNode, visualDepth = node.depth) {
    const children = childNodes.get(node.id) ?? [];
    const hasChildren = children.length > 0;
    const isExpanded = expanded.has(node.id) || Boolean(node.autoFlatten);
    const isSelected = selectedFolder === node.path;
    const shouldFlatten = Boolean(node.autoFlatten && node.depth > 1);
    if (shouldFlatten) {
      return (
        <div key={node.id} className="mg-folder-flattened">
          {children.map((child) => renderFolder(child, visualDepth))}
        </div>
      );
    }
    return (
      <div key={node.id} className="mg-folder-node">
        <div
          className={`mg-tree-row mg-folder-row ${isSelected ? "is-selected" : ""}`}
          style={{ paddingLeft: `${visualDepth * 12 + 3}px` }}
          role="treeitem"
          aria-selected={isSelected}
          aria-expanded={hasChildren ? isExpanded : undefined}
          onDoubleClick={() => {
            if (hasChildren && !node.autoFlatten) toggle(node.id);
          }}
        >
          <button
            type="button"
            className="mg-tree-twisty"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} ${node.label}`}
            disabled={!hasChildren || node.autoFlatten}
            onClick={() => toggle(node.id)}
          >
            {hasChildren ? (
              isExpanded ? <ChevronDown aria-hidden="true" size={13} /> : <ChevronRight aria-hidden="true" size={13} />
            ) : ""}
          </button>
          <button
            type="button"
            className="mg-tree-label"
            title={node.path}
            onClick={() => onSelectFolder(node.path)}
          >
            <FileIcon kind={isExpanded ? "folder-open" : "folder"} />
            <span className="mg-tree-name">{node.label}</span>
            {node.plotSetCount ? <span className="mg-count">{node.plotSetCount}</span> : null}
          </button>
        </div>
        {isExpanded ? children.map((child) => renderFolder(child, visualDepth + 1)) : null}
      </div>
    );
  }

  if (collapsed) {
    return (
      <section className="mg-sidebar-pane mg-folders-pane is-collapsed" aria-label="Folders">
        <button type="button" className="mg-pane-rail-button" aria-expanded={false} onClick={onToggleCollapsed}>
          <FileIcon kind="folder" />
          <span>Folders</span>
        </button>
      </section>
    );
  }

  return (
    <section className="mg-sidebar-pane mg-folders-pane" aria-label="Folders">
      <div className="mg-pane-title">
        <span>Folders</span>
        <button
          type="button"
          className="mg-pane-toggle is-icon-only"
          aria-expanded={!collapsed}
          aria-label="Hide folders"
          title="Hide folders"
          onClick={onToggleCollapsed}
        >
          <ChevronLeft aria-hidden="true" size={14} />
        </button>
      </div>
      <div role="tree" className="mg-folder-tree">
        {root ? renderFolder(root) : <div className="mg-empty is-small">No result folders.</div>}
      </div>
    </section>
  );
}

function FilesPane({
  plotSets,
  itemNoun,
  activeFilters,
  checkedPlotSetIds,
  selectedPlotSetId,
  collapsed,
  showUngrouped,
  onToggleCollapsed,
  onToggleFilter,
  onClearFilters,
  onToggleShowUngrouped,
  onFocus,
  onToggleChecked,
  onToggleAllChecked,
}: {
  plotSets: PlotSetEntity[];
  itemNoun: string;
  activeFilters: Set<FileFilter>;
  checkedPlotSetIds: Set<string>;
  selectedPlotSetId: string | null;
  collapsed: boolean;
  showUngrouped: boolean;
  onToggleCollapsed: () => void;
  onToggleFilter: (filter: FileFilter) => void;
  onClearFilters: () => void;
  onToggleShowUngrouped: (show: boolean) => void;
  onFocus: (plotSetId: string, attachmentId?: string) => void;
  onToggleChecked: (plotSetId: string, checked: boolean) => void;
  onToggleAllChecked: (checked: boolean) => void;
}) {
  const selectedRowRef = useRef<HTMLDivElement | null>(null);
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  const imageMode = itemNoun === "images";
  const visibleFilters = imageMode
    ? FILE_FILTERS.filter((filter) => filter.value === "svg" || filter.value === "png")
    : FILE_FILTERS;
  const allChecked = plotSets.length > 0 && plotSets.every((plotSet) => checkedPlotSetIds.has(plotSet.plotSetId));
  const checkedCount = plotSets.filter((plotSet) => checkedPlotSetIds.has(plotSet.plotSetId)).length;

  useEffect(() => {
    selectedRowRef.current?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [selectedPlotSetId, plotSets]);

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = checkedCount > 0 && !allChecked;
    }
  }, [allChecked, checkedCount]);

  if (collapsed) {
    return (
      <section className="mg-sidebar-pane mg-files-pane is-collapsed" aria-label="Files">
        <button type="button" className="mg-pane-rail-button" aria-expanded={false} onClick={onToggleCollapsed}>
          <Table2 aria-hidden="true" size={16} />
          <span>Files</span>
        </button>
      </section>
    );
  }

  return (
    <section className="mg-sidebar-pane mg-files-pane" aria-label="Files">
      <div className="mg-pane-title">
        <span>Files</span>
        <div className="mg-pane-title-actions">
          <span>{plotSets.length}</span>
          <input
            ref={selectAllRef}
            type="checkbox"
            className="mg-master-check"
            disabled={!plotSets.length}
            checked={allChecked}
            aria-label={allChecked ? `Clear all ${itemNoun} in folder` : `Select all ${itemNoun} in folder`}
            title={allChecked ? `Clear all ${itemNoun} in folder` : `Select all ${itemNoun} in folder`}
            onChange={(event) => onToggleAllChecked(event.target.checked)}
          />
          <button
            type="button"
            className="mg-pane-toggle is-icon-only"
            aria-expanded={!collapsed}
            aria-label="Hide files"
            title="Hide files"
            onClick={onToggleCollapsed}
          >
            <ChevronLeft aria-hidden="true" size={14} />
          </button>
        </div>
      </div>
      {checkedCount ? <div className="mg-file-selection-summary">{checkedCount} selected in folder</div> : null}
      <div className="mg-file-filter-chips" role="toolbar" aria-label="File type filters">
        <button
          type="button"
          className={activeFilters.size === 0 ? "is-active" : ""}
          aria-pressed={activeFilters.size === 0}
          onClick={onClearFilters}
        >
          All
        </button>
        {visibleFilters.map((filter) => (
          <button
            type="button"
            key={filter.value}
            title={filter.title}
            className={activeFilters.has(filter.value) ? "is-active" : ""}
            aria-pressed={activeFilters.has(filter.value)}
            onClick={() => onToggleFilter(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      <div className="mg-files-list" role="listbox" aria-label={itemNoun === "images" ? "Images" : "Plot sets"}>
        {plotSets.length ? (
          plotSets.map((plotSet, index) => {
            const checked = checkedPlotSetIds.has(plotSet.plotSetId);
            const figure = plotSet.preferredFigure;
            return (
              <div
                key={plotSet.plotSetId}
                ref={selectedPlotSetId === plotSet.plotSetId ? selectedRowRef : null}
                className={`mg-file-row is-shade-${index % 4} ${selectedPlotSetId === plotSet.plotSetId ? "is-selected" : ""}`}
                role="option"
                aria-selected={selectedPlotSetId === plotSet.plotSetId}
              >
                <button
                  type="button"
                  className="mg-file-main"
                  title={plotSet.title}
                  onClick={() => {
                    if (checked) {
                      onToggleChecked(plotSet.plotSetId, false);
                      return;
                    }
                    onFocus(plotSet.plotSetId, figure?.id);
                    onToggleChecked(plotSet.plotSetId, true);
                  }}
                >
                  <AttachmentIcon type={figure?.type ?? "csv"} />
                  <span className="mg-file-title">{plotSet.title}</span>
                  {imageMode ? null : (
                    <span className="mg-attachment-strip" aria-label={`Attachments for ${plotSet.title}`}>
                      {attachmentTypeSummary(plotSet).map((type) => (
                        <span key={`${plotSet.plotSetId}-${type}`} className={`mg-attachment-chip is-${type}`}>
                          {attachmentLabel(type)}
                        </span>
                      ))}
                    </span>
                  )}
                </button>
                <input
                  type="checkbox"
                  className="mg-tree-check"
                  aria-label={`Show ${plotSet.title}`}
                  checked={checked}
                  onChange={(event) => onToggleChecked(plotSet.plotSetId, event.target.checked)}
                />
              </div>
            );
          })
        ) : (
          <div className="mg-empty is-small">No {itemNoun} in this folder.</div>
        )}
      </div>
      <label className="mg-debug-toggle">
        <input
          type="checkbox"
          checked={showUngrouped}
          onChange={(event) => onToggleShowUngrouped(event.target.checked)}
        />
        <span>Debug ungrouped</span>
      </label>
    </section>
  );
}

function DataPlotCard({
  item,
  activeTab,
  selected,
  tileSize,
  cardSize,
  onActivateTab,
  onGenerate,
  onMaximize,
  onSaveRedraw,
  onSaveYaml,
  onResize,
  checked,
  dragging,
  dropTarget,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  onPointerDragOver,
}: {
  item: DataPlotItem;
  activeTab: string;
  selected: boolean;
  tileSize: number;
  cardSize: number;
  onActivateTab: (tab: string) => void;
  onGenerate: () => void;
  onMaximize: (plotId: string) => void;
  onSaveRedraw: (plotId: string, redraw: RedrawMetadata) => void;
  onSaveYaml: (plotId: string, attachmentPath: string, yamlText: string) => void;
  onResize: (size: number) => void;
  checked: boolean;
  dragging: boolean;
  dropTarget: boolean;
  onDragStart: () => void;
  onDragOver: () => void;
  onDrop: () => void;
  onDragEnd: () => void;
  onPointerDragOver: (draggedPlotSetId: string, targetPlotSetId: string) => void;
}) {
  const activeRecord = item.records.find((record) => record.id === activeTab) ?? item.records[0] ?? null;
  const csvPreview = csvPreviewData(item, activeRecord);
  const hasCsvTab = csvPreview !== null;
  const yamlAttachments = item.plotSet?.attachments.filter((attachment) => attachment.type === "mpl_yaml") ?? [];
  const activeYaml = yamlAttachments.find((attachment) => attachment.id === activeTab) ?? null;
  const figureCount = item.records.length;
  const canGenerate = Boolean(item.dataset && figureCount === 0);
  const cardStyle = {
    ["--card-size" as string]: `${cardSize}px`,
  } satisfies CSSProperties;

  function startResize(event: ReactPointerEvent<HTMLElement>) {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const startSize = cardSize;
    const pointerId = event.pointerId;
    event.currentTarget.setPointerCapture?.(pointerId);
    const onPointerMove = (moveEvent: PointerEvent) => {
      const delta = Math.max(moveEvent.clientX - startX, moveEvent.clientY - startY);
      onResize(startSize + delta);
    };
    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
  }

  function startCardPointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const plotSetId = item.plotSet?.plotSetId;
    if (!checked || !plotSetId || event.button !== 0 || shouldIgnoreCardDrag(event.target)) return;

    event.preventDefault();
    const card = event.currentTarget;
    const pointerId = event.pointerId;
    const startX = event.clientX;
    const startY = event.clientY;
    card.setPointerCapture?.(pointerId);
    card.style.transition = "none";
    card.style.zIndex = "20";
    card.style.opacity = "0.92";
    card.style.pointerEvents = "none";
    onDragStart();

    const onPointerMove = (moveEvent: PointerEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const deltaY = moveEvent.clientY - startY;
      card.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
      const targetCard = document
        .elementFromPoint(moveEvent.clientX, moveEvent.clientY)
        ?.closest<HTMLElement>("article.mg-data-plot-card[data-plot-set-id]");
      const targetPlotSetId = targetCard?.dataset.plotSetId;
      if (targetPlotSetId && targetPlotSetId !== plotSetId) {
        onPointerDragOver(plotSetId, targetPlotSetId);
      }
    };

    const onPointerUp = () => {
      card.style.transition = "";
      card.style.transform = "";
      card.style.zIndex = "";
      card.style.opacity = "";
      card.style.pointerEvents = "";
      card.releasePointerCapture?.(pointerId);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      onDragEnd();
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
  }

  return (
    <article
      className={`mg-card mg-data-plot-card ${selected ? "is-selected" : ""} ${checked ? "is-draggable" : ""} ${dragging ? "is-dragging" : ""} ${dropTarget ? "is-drop-target" : ""}`}
      style={cardStyle}
      data-plot-set-id={item.plotSet?.plotSetId}
      draggable={checked}
      aria-label={`${cardTitle(item)} card`}
      aria-grabbed={checked ? dragging : undefined}
      onPointerDown={startCardPointerDrag}
      onDragStart={(event: ReactDragEvent<HTMLElement>) => {
        if (!checked) return;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.plotSet?.plotSetId ?? item.id);
        event.dataTransfer.setDragImage?.(event.currentTarget, Math.min(180, event.currentTarget.clientWidth / 2), 24);
        onDragStart();
      }}
      onDragOver={(event: ReactDragEvent<HTMLElement>) => {
        if (!checked) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        onDragOver();
      }}
      onDrop={(event: ReactDragEvent<HTMLElement>) => {
        if (!checked) return;
        event.preventDefault();
        onDrop();
      }}
      onDragEnd={onDragEnd}
    >
      <div className="mg-card-header">
        <div className="mg-card-header-actions">
          <div className="mg-card-tabs" role="tablist" aria-label={`Views for ${cardTitle(item)}`}>
            {hasCsvTab ? (
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === "csv"}
                className={activeTab === "csv" ? "is-active" : ""}
                onClick={() => onActivateTab("csv")}
              >
                CSV
              </button>
            ) : null}
            {item.records.map((record) => (
              <button
                type="button"
                role="tab"
                key={record.id}
                aria-selected={activeTab === record.id}
                className={activeTab === record.id ? "is-active" : ""}
                onClick={() => onActivateTab(record.id)}
              >
                {record.kind}
              </button>
            ))}
            {yamlAttachments.map((attachment) => (
              <button
                type="button"
                role="tab"
                key={attachment.id}
                aria-selected={activeTab === attachment.id}
                className={activeTab === attachment.id ? "is-active" : ""}
                onClick={() => onActivateTab(attachment.id)}
              >
                YAML
              </button>
            ))}
          </div>
          {activeRecord ? (
            <button type="button" className="mg-edit-button" onClick={() => onMaximize(activeRecord.id)}>
              Edit
            </button>
          ) : null}
        </div>
      </div>
      <div className="mg-card-viewport">
        {activeYaml ? (
          <MetadataAttachmentView
            attachment={activeYaml}
            record={item.records.find((record) => record.id === activeYaml.plotId) ?? activeRecord}
            editable={Boolean(item.plotSet?.editable)}
            onOpenEditor={(plotId) => onMaximize(plotId)}
            onSaveRedraw={onSaveRedraw}
            onSaveYaml={onSaveYaml}
          />
        ) : activeTab === "csv" && csvPreview ? (
          <CsvPreviewTable preview={csvPreview} />
        ) : activeRecord && activeRecord.imageSrc ? (
          <button type="button" className="mg-card-image" onClick={() => onMaximize(activeRecord.id)}>
            <img src={activeRecord.imageSrc} alt={activeRecord.name} />
          </button>
        ) : activeRecord ? (
          <div className="mg-card-image mg-card-image-placeholder" aria-label={`Preview loading for ${activeRecord.name}`}>
            <FileImage aria-hidden="true" size={22} />
            <span>Preview loads after selecting this plot set.</span>
          </div>
        ) : csvPreview ? (
          <CsvPreviewTable preview={csvPreview} />
        ) : (
          <div className="mg-empty">No linked CSV or plot found.</div>
        )}
      </div>
      {canGenerate ? (
        <div className="mg-card-body">
          <div className="mg-card-actions">
            <button type="button" className="mg-primary" onClick={onGenerate}>
              Generate plot
            </button>
          </div>
        </div>
      ) : null}
      <div
        className="mg-card-resize"
        aria-hidden="true"
        onPointerDown={startResize}
      />
    </article>
  );
}

function csvPreviewData(item: DataPlotItem, activeRecord: PlotRecord | null): CsvPreviewData | null {
  if (item.dataset) {
    return {
      id: item.dataset.id,
      label: item.dataset.displayName,
      previewColumns: item.dataset.previewColumns,
      previewRows: item.dataset.previewRows,
      previewTruncated: item.dataset.previewTruncated,
      previewError: item.dataset.previewError,
    };
  }
  const record = activeRecord ?? item.records.find((candidate) => Boolean(candidate.csvPath)) ?? item.records[0] ?? null;
  if (!record || !record.csvPath) return null;
  return {
    id: record.id,
    label: record.name,
    previewColumns: record.previewColumns ?? [],
    previewRows: record.previewRows ?? [],
    previewTruncated: Boolean(record.previewTruncated),
    previewError: record.previewError,
  };
}

function CsvPreviewTable({ preview }: { preview: CsvPreviewData }) {
  const columns = preview.previewColumns.slice(0, 8);
  const rows = preview.previewRows.slice(0, 12);
  if (preview.previewError) {
    return (
      <div className="mg-csv-mini">
        <div className="mg-error" role="alert">Preview failed: {preview.previewError}</div>
      </div>
    );
  }
  if (columns.length === 0) {
    return <div className="mg-empty">No table preview available.</div>;
  }
  return (
    <div className="mg-csv-mini" aria-label={`CSV table preview for ${preview.label}`}>
      <table className="mg-csv-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${preview.id}-mini-row-${index}`}>
              {columns.map((column) => (
                <td key={`${preview.id}-mini-${index}-${column}`}>{row[column] == null ? "" : String(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetadataAttachmentView({
  attachment,
  record,
  editable,
  onOpenEditor,
  onSaveRedraw,
  onSaveYaml,
}: {
  attachment: PlotSetAttachment;
  record: PlotRecord | null;
  editable: boolean;
  onOpenEditor: (plotId: string) => void;
  onSaveRedraw: (plotId: string, redraw: RedrawMetadata) => void;
  onSaveYaml: (plotId: string, attachmentPath: string, yamlText: string) => void;
}) {
  const redraw = record?.redraw;
  const series = redraw?.series ?? [];
  const [draft, setDraft] = useState<RedrawMetadata>(() => redraw ?? {});
  const initialYamlText = attachment.textPreview?.trimEnd() ?? "";
  const [yamlText, setYamlText] = useState(initialYamlText);
  const canSaveYaml = Boolean(record && editable && !attachment.textPreviewTruncated);

  useEffect(() => {
    setDraft(redraw ?? {});
  }, [redraw, record?.id]);

  useEffect(() => {
    setYamlText(attachment.textPreview?.trimEnd() ?? "");
  }, [attachment.id, attachment.textPreview]);

  function patchDraft(patch: Partial<RedrawMetadata>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function saveMetadata() {
    if (!record) return;
    onSaveRedraw(record.id, normalizeRedraw(draft, draft.series ?? series));
  }

  function saveYamlText() {
    if (!record || !canSaveYaml) return;
    onSaveYaml(record.id, attachment.sourcePath, yamlText.endsWith("\n") ? yamlText : `${yamlText}\n`);
  }

  const fields = [
    ["Title", redraw?.title],
    ["Type", redraw?.kind],
    ["X", redraw?.x],
    ["Y", series.length ? series.map((item) => item.y).join(", ") : null],
    ["X label", redraw?.xlabel],
    ["Y label", redraw?.ylabel],
    ["X scale", redraw?.xscale],
    ["Y scale", redraw?.yscale],
    ["Grid", redraw?.grid == null ? null : redraw.grid ? "on" : "off"],
    ["Legend", redraw?.legend_location],
  ].filter((field): field is [string, string] => Boolean(field[1]));
  const rawYamlChanged = yamlText !== initialYamlText;
  return (
    <div className="mg-metadata-view">
      <div className="mg-metadata-head">
        <FileCode2 aria-hidden="true" size={19} />
        <div>
          <strong>{attachment.displayName}</strong>
          <span>{editable ? "Editable style sidecar" : "View-only sidecar"}</span>
        </div>
        <div className="mg-yaml-actions">
          {record ? (
            <button type="button" className="mg-edit-button" onClick={() => onOpenEditor(record.id)}>
              Full editor
            </button>
          ) : null}
          {record && editable ? (
            <button type="button" className="mg-primary is-compact" onClick={saveMetadata}>
              Save fields
            </button>
          ) : null}
        </div>
      </div>
      <div className="mg-yaml-field-grid" aria-label={`Editable YAML metadata for ${attachment.displayName}`}>
        <label>
          Title
          <input
            value={draft.title ?? ""}
            disabled={!editable}
            onChange={(event) => patchDraft({ title: event.target.value })}
          />
        </label>
        <label>
          Kind
          <input
            value={draft.kind ?? ""}
            disabled={!editable}
            onChange={(event) => patchDraft({ kind: event.target.value })}
          />
        </label>
        <label>
          X
          <input value={draft.x ?? ""} disabled={!editable} onChange={(event) => patchDraft({ x: event.target.value })} />
        </label>
        <label>
          X label
          <input
            value={draft.xlabel ?? ""}
            disabled={!editable}
            onChange={(event) => patchDraft({ xlabel: event.target.value })}
          />
        </label>
        <label>
          Y label
          <input
            value={draft.ylabel ?? ""}
            disabled={!editable}
            onChange={(event) => patchDraft({ ylabel: event.target.value })}
          />
        </label>
        <label className="mg-mini-toggle">
          <input
            type="checkbox"
            checked={draft.grid ?? true}
            disabled={!editable}
            onChange={(event) => patchDraft({ grid: event.target.checked })}
          />
          Grid
        </label>
      </div>
      <div className="mg-metadata-summary">
        {fields.length ? fields.map(([label, value]) => <span key={label}><strong>{label}</strong>{value}</span>) : <span>No plot metadata summary available.</span>}
      </div>
      {series.length ? (
        <div className="mg-yaml-series">
          {series.slice(0, 4).map((style) => (
            <span key={style.y}>
              {style.y}
              {style.color ? <i style={{ background: style.color }} /> : null}
              {style.linestyle ? ` ${style.linestyle}` : ""}
              {style.marker ? ` ${style.marker}` : ""}
            </span>
          ))}
        </div>
      ) : null}
      <label className="mg-yaml-editor">
        YAML
        <textarea
          value={yamlText}
          disabled={!canSaveYaml}
          spellCheck={false}
          onChange={(event) => setYamlText(event.target.value)}
          aria-label={`YAML text for ${attachment.displayName}`}
          placeholder="YAML preview is not available for this sidecar."
        />
      </label>
      <div className="mg-yaml-editor-actions">
        {attachment.textPreviewTruncated ? <span>Preview is truncated; raw save is disabled.</span> : <span>{attachment.sourcePath}</span>}
        <button type="button" className="mg-edit-button" disabled={!canSaveYaml || !rawYamlChanged} onClick={saveYamlText}>
          Save YAML
        </button>
      </div>
    </div>
  );
}

function AttachmentIcon({ type }: { type: string }) {
  if (type === "csv") return <Table2 className="mg-file-icon" aria-label="CSV plot-set attachment" size={14} />;
  if (type === "mpl_yaml") return <FileCode2 className="mg-file-icon" aria-label="Matplotlib YAML attachment" size={14} />;
  return <FileImage className="mg-file-icon" aria-label="Figure attachment" size={14} />;
}

function attachmentTypeSummary(plotSet: PlotSetEntity): string[] {
  const order = ["csv", "svg", "png", "mpl_yaml"];
  const available = new Set(plotSet.attachments.map((attachment) => attachment.type));
  return order.filter((type) => available.has(type));
}

function attachmentLabel(type: string): string {
  if (type === "mpl_yaml") return "YAML";
  return type.toUpperCase();
}

function syncLegacyDatasetChecks(current: Set<string>, plotSet: PlotSetEntity | undefined, checked: boolean): Set<string> {
  const next = new Set(current);
  plotSet?.attachments.forEach((attachment) => {
    if (!attachment.datasetId) return;
    if (checked) next.add(attachment.datasetId);
    else next.delete(attachment.datasetId);
  });
  return next;
}

function syncLegacyPlotChecks(current: Set<string>, plotSet: PlotSetEntity | undefined, checked: boolean): Set<string> {
  const next = new Set(current);
  plotSet?.attachments.forEach((attachment) => {
    if (!attachment.plotId) return;
    if (checked) next.add(attachment.plotId);
    else next.delete(attachment.plotId);
  });
  return next;
}

function folderNodesFromPlotSets(plotSets: PlotSetEntity[], rootLabel: string): FolderViewNode[] {
  const paths = new Set<string>(["."]);
  const figureRoots = new Set<string>();
  plotSets.forEach((plotSet) => {
    const parts = plotSet.folderPath.split("/").filter((part) => part && part !== ".");
    if (parts.length && plotSet.attachments.some((attachment) => attachment.type === "png" || attachment.type === "svg")) {
      figureRoots.add(parts[0]);
    }
  });
  plotSets.forEach((plotSet) => {
    const parts = plotSet.folderPath.split("/").filter((part) => part && part !== ".");
    if (!parts.length || !figureRoots.has(parts[0])) return;
    let current = "";
    parts.forEach((part) => {
      current = current ? `${current}/${part}` : part;
      paths.add(current);
    });
  });
  return [...paths].sort((left, right) => left.localeCompare(right)).map((path) => {
    const parentId = path === "." ? null : path.includes("/") ? path.split("/").slice(0, -1).join("/") : ".";
    const childCount = [...paths].filter((candidate) => {
      if (candidate === path || candidate === ".") return false;
      return (candidate.includes("/") ? candidate.split("/").slice(0, -1).join("/") : ".") === path;
    }).length;
    const plotSetCount = plotSets.filter((plotSet) => plotSet.folderPath === path).length;
    return {
      id: path,
      path,
      label: path === "." ? rootLabel : path.split("/").at(-1) ?? path,
      parentId,
      depth: path === "." ? 0 : path.split("/").length,
      childCount,
      plotSetCount,
      autoFlatten: false,
    };
  });
}

function legacyPlotSets(
  datasets: DatasetRecord[],
  records: PlotRecord[],
  recordsByDatasetId: Map<string, PlotRecord[]>,
): PlotSetEntity[] {
  const plotSets: PlotSetEntity[] = datasets.map((dataset) => {
    const linkedRecords = recordsByDatasetId.get(dataset.id) ?? [];
    const attachments: PlotSetAttachment[] = [
      {
        id: `${dataset.id}:csv`,
        type: "csv",
        displayName: dataset.displayName,
        sourcePath: dataset.path,
        datasetId: dataset.id,
        plotId: linkedRecords[0]?.id ?? null,
      },
      ...linkedRecords.map((record) => ({
        id: record.id,
        type: record.kind.toLowerCase(),
        displayName: record.name,
        sourcePath: record.imagePath,
        datasetId: dataset.id,
        plotId: record.id,
      })),
    ];
    const preferredFigure = attachments.find((attachment) => attachment.type === "svg")
      ?? attachments.find((attachment) => attachment.type === "png")
      ?? null;
    return {
      plotSetId: dataset.id,
      title: dataset.displayName,
      folderPath: dataset.path.includes("/") ? dataset.path.split("/").slice(0, -1).join("/") : ".",
      attachments,
      preferredFigure,
      editable: linkedRecords.some((record) => record.editable),
      checked: false,
      renderStatus: preferredFigure ? "ready" : "missing_figure",
    };
  });
  const datasetRecordIds = new Set(datasets.flatMap((dataset) => (recordsByDatasetId.get(dataset.id) ?? []).map((record) => record.id)));
  records.filter((record) => !datasetRecordIds.has(record.id)).forEach((record) => {
    plotSets.push({
      plotSetId: `plot:${record.id}`,
      title: record.name,
      folderPath: record.imagePath.includes("/") ? record.imagePath.split("/").slice(0, -1).join("/") : ".",
      attachments: [{
        id: record.id,
        type: record.kind.toLowerCase(),
        displayName: record.name,
        sourcePath: record.imagePath,
        plotId: record.id,
      }],
      preferredFigure: {
        id: record.id,
        type: record.kind.toLowerCase(),
        displayName: record.name,
        sourcePath: record.imagePath,
        plotId: record.id,
      },
      editable: record.editable,
      checked: false,
      renderStatus: record.renderError ? "error" : "ready",
    });
  });
  return plotSets;
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
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setExpanded(new Set());
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
    const isAutoExpanded = Boolean(current.autoExpand);
    const isExpanded = isAutoExpanded || expanded.has(current.path);
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
            disabled={!hasExpandableChildren || isAutoExpanded}
            onClick={() => toggle(current.path)}
          >
            {hasExpandableChildren ? (
              isExpanded ? <ChevronDown aria-hidden="true" size={14} /> : <ChevronRight aria-hidden="true" size={14} />
            ) : ""}
          </button>
          <button
            type="button"
            className="mg-tree-label"
            title={current.path === "." ? current.label : current.path}
            onClick={() => onSelectFolder(current.path)}
            onDoubleClick={() => {
              if (!isAutoExpanded && hasExpandableChildren) toggle(current.path);
            }}
          >
            <FileIcon kind={isExpanded ? "folder-open" : "folder"} />
            <span className="mg-tree-name">{current.label}</span>
            <span className={`mg-count ${checkedCount ? "has-checked" : ""}`}>
              {checkedCount ? `${checkedCount}/` : ""}
              {current.count}
            </span>
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
                  if (file.kind === "image" && file.plotId) onTogglePlot(file.plotId, checked);
                  if (file.kind === "csv" && file.datasetId) onToggleDataset(file.datasetId, checked);
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
      <button
        type="button"
        className="mg-tree-label"
        title={file.path}
        onClick={() => {
          if (file.kind === "image" || file.kind === "csv") onToggle(!checked);
          onSelect();
        }}
      >
        <FileIcon kind={file.iconKind} />
        <span className="mg-tree-name">{file.name}</span>
        {file.iconKind === "csv-drafted" ? (
          <span className="mg-file-status" title="Companion plot generated">
            <CheckCircle2 aria-hidden="true" size={12} />
          </span>
        ) : null}
      </button>
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
      {record.imageSrc ? (
        <img src={record.imageSrc} alt={record.name} />
      ) : (
        <div className="mg-card-image mg-card-image-placeholder" aria-label={`Preview loading for ${record.name}`}>
          <FileImage aria-hidden="true" size={22} />
          <span>Preview loads after selecting this plot set.</span>
        </div>
      )}
    </section>
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
            <div className="mg-eyebrow">Edit plot</div>
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
