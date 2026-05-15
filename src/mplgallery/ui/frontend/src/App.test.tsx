import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AppHost } from "./appHost";
import type { BrowserPayload } from "./types";

const emitEventMock = vi.hoisted(() => vi.fn());
const openMock = vi.hoisted(() => vi.fn());

function payload(overrides: Partial<BrowserPayload> = {}): BrowserPayload {
  return {
    projectRoot: "C:/Users/Tanner/Documents/git/mplgallery",
    rootContext: {
      activeRoot: "C:/Users/Tanner/Documents/git/mplgallery",
      launchRoot: "C:/Users/Tanner/Documents/git/mplgallery",
      recentRoots: ["C:/Users/Tanner/Documents/git/other-analysis"],
      error: null,
      showRootChooser: false,
    },
    userSettings: {
      rememberRecentProjects: true,
      restoreLastProjectOnStartup: false,
    },
    selectedPlotId: null,
    datasets: [
      {
        id: "data__processed__alpha",
        displayName: "alpha.csv",
        path: "data/processed/alpha.csv",
        csvRootId: "data",
        csvRootPath: "data",
        draftStatus: "not_initialized",
        associatedPlotId: "plots__alpha",
        associatedPlotIds: ["plots__alpha"],
        rowCountSampled: 2,
        columns: ["time", "signal"],
        numericColumns: ["time", "signal"],
        categoricalColumns: [],
        previewColumns: ["time", "signal"],
        previewRows: [
          { time: 0, signal: 1 },
          { time: 1, signal: 2 },
        ],
        previewTruncated: false,
        previewError: null,
      },
    ],
    records: [
      {
        id: "plots__alpha",
        name: "alpha.svg",
        kind: "SVG",
        imagePath: "results/final/figures/alpha.svg",
        sourceDatasetId: "data__processed__alpha",
        csvPath: "data/processed/alpha.csv",
        confidence: "exact",
        imageSrc: "data:image/svg+xml;base64,AA==",
        csvColumns: ["time", "signal"],
        editable: true,
        redraw: { x: "time", series: [{ y: "signal" }] },
        series: [{ y: "signal" }],
      },
    ],
    files: [
      {
        id: "csv:data__processed__alpha",
        kind: "csv",
        path: "data/processed/alpha.csv",
        name: "alpha.csv",
        parentPath: "data/processed",
        iconKind: "csv-drafted",
        datasetId: "data__processed__alpha",
        plotId: "plots__alpha",
        draftStatus: "drafted",
      },
      {
        id: "plot:plots__alpha",
        kind: "image",
        path: "results/final/figures/alpha.svg",
        name: "alpha.svg",
        parentPath: "results/final/figures",
        iconKind: "image",
        plotId: "plots__alpha",
        datasetId: "data__processed__alpha",
      },
    ],
    plotSets: [
      {
        plotSetId: "data__processed__alpha",
        title: "alpha.csv",
        folderPath: "data/processed",
        attachments: [
          {
            id: "data__processed__alpha:csv",
            type: "csv",
            displayName: "alpha.csv",
            sourcePath: "data/processed/alpha.csv",
            datasetId: "data__processed__alpha",
            plotId: "plots__alpha",
          },
          {
            id: "plots__alpha",
            type: "svg",
            displayName: "alpha.svg",
            sourcePath: "results/final/figures/alpha.svg",
            datasetId: "data__processed__alpha",
            plotId: "plots__alpha",
          },
          {
            id: "plots__alpha_png",
            type: "png",
            displayName: "alpha.png",
            sourcePath: "results/final/figures/alpha.png",
            datasetId: "data__processed__alpha",
            plotId: "plots__alpha",
          },
          {
            id: "plots__alpha:alpha.mpl.yaml",
            type: "mpl_yaml",
            displayName: "alpha.mpl.yaml",
            sourcePath: "results/final/figures/alpha.mpl.yaml",
            datasetId: "data__processed__alpha",
            plotId: "plots__alpha",
            textPreview: "kind: line\nx: time\nseries:\n  - y: signal\n",
            textPreviewTruncated: false,
          },
        ],
        preferredFigure: {
          id: "plots__alpha",
          type: "svg",
          displayName: "alpha.svg",
          sourcePath: "results/final/figures/alpha.svg",
          datasetId: "data__processed__alpha",
          plotId: "plots__alpha",
        },
        editable: true,
        checked: false,
        renderStatus: "ready",
      },
    ],
    options: {
      plotKinds: ["line"],
      lineStyles: [{ value: "-", label: "Solid" }],
      markers: [{ value: "o", label: "Circle" }],
      colors: [{ value: "#1f77b4", label: "Blue" }],
      units: [],
      scales: ["linear"],
      gridAxes: ["both"],
      legendLocations: ["best"],
      hatches: [{ value: "", label: "None" }],
    },
    errors: {},
    ...overrides,
  };
}

const host: AppHost = {
  emitEvent: emitEventMock,
  openExternal: openMock,
};

function renderApp(nextPayload: BrowserPayload) {
  return render(<App payload={nextPayload} host={host} />);
}

function expandTreeFolder(label: string) {
  fireEvent.click(screen.getByRole("button", { name: `Expand ${label}` }));
}

function filesPane() {
  return screen.getByRole("region", { name: "Files" });
}

function foldersPane() {
  return screen.getByRole("region", { name: "Folders" });
}

describe("App explorer", () => {
  beforeEach(() => {
    emitEventMock.mockClear();
    openMock.mockClear();
    vi.stubGlobal("open", openMock);
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps gallery empty until a CSV or image is selected", () => {
    render(<App payload={payload()} />);

    expect(screen.getAllByText("Select plot sets from Files to build a gallery.").length).toBeGreaterThan(0);
    expect(screen.queryByRole("img", { name: "alpha.svg" })).not.toBeInTheDocument();
  });

  it("starts in a blank project state without preloaded files", () => {
    render(
      <App
        payload={payload({
          projectRoot: "",
          rootContext: {
            activeRoot: "",
            launchRoot: "C:/Users/Tanner/AppData/Local/Programs/MPLGallery",
            recentRoots: ["C:/Users/Tanner/Documents/git/other-analysis"],
            error: null,
            showRootChooser: true,
          },
          datasets: [],
          records: [],
          files: [],
          plotSets: [],
          folderView: { nodes: [], rootId: ".", defaultSelectedPath: "." },
          filesView: { rows: [] },
        })}
      />,
    );

    expect(screen.getByText("No project open")).toBeInTheDocument();
    expect(screen.getByText("Open a project folder to start browsing plots and images.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Files" })).not.toBeInTheDocument();
    expect(screen.queryByText("alpha.csv")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open Project..." }).length).toBeGreaterThan(0);
    expect(screen.getByText("other-analysis")).toBeInTheDocument();
  });

  it("renders compact folder-only navigation and keeps files in the files pane", () => {
    render(<App payload={payload()} />);

    expect(screen.getAllByText("mplgallery").length).toBeGreaterThan(0);
    expect(within(foldersPane()).queryByText("data")).not.toBeInTheDocument();
    fireEvent.click(within(foldersPane()).getByRole("button", { name: "Expand mplgallery" }));
    expect(within(foldersPane()).getByText("data")).toBeInTheDocument();
    expect(within(foldersPane()).queryByText("processed")).not.toBeInTheDocument();
    fireEvent.click(within(foldersPane()).getByRole("button", { name: "Expand data" }));
    expect(within(foldersPane()).getByText("processed")).toBeInTheDocument();
    expect(screen.queryByText("data/processed")).not.toBeInTheDocument();
    expect(within(foldersPane()).queryByText("alpha.csv")).not.toBeInTheDocument();
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(screen.getByLabelText("Show alpha.csv")).toBeInTheDocument();
  });

  it("toggles folders when double-clicking the folder row label", () => {
    render(<App payload={payload()} />);
    const rootFolder = within(foldersPane()).getByText("mplgallery").closest("button");
    expect(rootFolder).not.toBeNull();
    fireEvent.doubleClick(rootFolder as HTMLElement);
    const dataFolder = within(foldersPane()).getByText("data").closest("button");
    expect(dataFolder).not.toBeNull();

    expect(within(foldersPane()).queryByText("processed")).not.toBeInTheDocument();
    fireEvent.doubleClick(dataFolder as HTMLElement);
    expect(within(foldersPane()).getByText("processed")).toBeInTheDocument();
    fireEvent.doubleClick(dataFolder as HTMLElement);
    expect(within(foldersPane()).queryByText("processed")).not.toBeInTheDocument();
    fireEvent.doubleClick(dataFolder as HTMLElement);
    expect(within(foldersPane()).getByText("processed")).toBeInTheDocument();
  });

  it("uses an IDE-style root control and emits root/refresh actions", () => {
    renderApp(payload());

    fireEvent.click(screen.getByRole("button", { name: "Project root mplgallery" }));
    expect(screen.getByRole("dialog", { name: "Project root menu" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open root" }));
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "change_project_root",
      root_path: "C:/Users/Tanner/Documents/git/mplgallery",
    }));

    fireEvent.click(screen.getByRole("button", { name: /Refresh/ }));
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "refresh_index",
    }));
  });

  it("prompts for available desktop app updates", () => {
    const updateHost: AppHost = {
      ...host,
      capabilities: {
        supportsDrafting: false,
        supportsEditing: false,
        supportsBrowseDialog: true,
        supportsRootReset: true,
        supportsInlineUpdateInstall: true,
      },
    };
    render(
      <App
        host={updateHost}
        payload={payload({
          appInfo: {
            name: "MPLGallery",
            version: "0.1.0",
            appId: "Tanner.MPLGallery",
            update: {
              checked: true,
              available: true,
              currentVersion: "0.1.0",
              latestVersion: "0.2.0",
              releaseUrl: "https://github.com/tannerpolley/mplgallery/releases/tag/v0.2.0",
              downloadUrl: "https://github.com/tannerpolley/mplgallery/releases/download/v0.2.0/mplgallery.zip",
              error: null,
            },
            canInstallUpdates: true,
          },
        })}
      />,
    );

    expect(screen.getByText("Update 0.2.0")).toBeInTheDocument();
    const updateButton = screen.getByRole("button", { name: "Install MPLGallery 0.2.0" });
    fireEvent.click(updateButton);
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "install_update",
      download_url: "https://github.com/tannerpolley/mplgallery/releases/download/v0.2.0/mplgallery.zip",
    }));
    expect(updateButton).toBeDisabled();
    expect(screen.getAllByText("Downloading update...").length).toBeGreaterThan(0);
    expect(openMock).not.toHaveBeenCalled();
  });

  it("opens settings and emits project memory setting events", () => {
    renderApp(payload());

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByLabelText("Remember recent projects")).toBeChecked();
    expect(screen.getByLabelText("Restore last project on startup")).not.toBeChecked();

    fireEvent.click(screen.getByLabelText("Restore last project on startup"));
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_user_setting",
      setting_key: "restore_last_project_on_startup",
      setting_value: true,
    }));

    fireEvent.click(screen.getByRole("button", { name: "Clear recent projects" }));
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "clear_recent_roots",
    }));
  });

  it("switches between plot set and picture browsing modes", () => {
    renderApp(payload());

    const modeSwitch = screen.getByRole("group", { name: "Browse mode" });
    expect(within(modeSwitch).getByRole("button", { name: "Plot sets" })).toHaveAttribute("aria-pressed", "true");
    expect(within(modeSwitch).getByRole("button", { name: "Pictures" })).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(within(modeSwitch).getByRole("button", { name: "Pictures" }));
    expect(within(modeSwitch).getByRole("button", { name: "Pictures" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Images")).toBeInTheDocument();
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_browse_mode",
      browse_mode: "image-library",
    }));
  });

  it("creates and reapplies remembered custom sets", () => {
    renderApp(payload());

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByRole("button", { name: "Create set" }));
    fireEvent.change(screen.getByLabelText("Custom set name"), { target: { value: "My set" } });
    fireEvent.click(screen.getByRole("button", { name: "Save set" }));

    expect(screen.getByText("My set").closest('[role="button"]')).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Clear gallery" }));
    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();

    fireEvent.click(screen.getByText("My set").closest('[role="button"]') as HTMLElement);
    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();

    cleanup();
    renderApp(payload());
    expect(screen.getByText("My set").closest('[role="button"]')).not.toBeNull();
  });

  it("removes remembered custom sets", () => {
    renderApp(payload());

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByRole("button", { name: "Create set" }));
    fireEvent.change(screen.getByLabelText("Custom set name"), { target: { value: "Throwaway set" } });
    fireEvent.click(screen.getByRole("button", { name: "Save set" }));

    expect(screen.getByText("Throwaway set").closest('[role="button"]')).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Remove custom set Throwaway set" }));
    expect(screen.queryByText("Throwaway set")).not.toBeInTheDocument();
    expect(screen.getByText("No custom sets yet.")).toBeInTheDocument();

    cleanup();
    renderApp(payload());
    expect(screen.queryByText("Throwaway set")).not.toBeInTheDocument();
  });

  it("surfaces update installer failures in status", () => {
    render(
      <App
        payload={payload({
          appInfo: {
            name: "MPLGallery",
            version: "0.1.0",
            appId: "Tanner.MPLGallery",
            update: {
              checked: true,
              available: true,
              currentVersion: "0.1.0",
              latestVersion: "0.2.0",
              releaseUrl: "https://github.com/tannerpolley/mplgallery/releases/tag/v0.2.0",
              downloadUrl: "https://github.com/tannerpolley/mplgallery/releases/download/v0.2.0/mplgallery.zip",
              error: null,
            },
            updateInstall: {
              started: false,
              error: "download failed",
            },
            canInstallUpdates: true,
          },
        })}
      />,
    );

    expect(screen.getByText("Update install failed: download failed")).toBeInTheDocument();
  });

  it("filters the explorer to CSV files or figure files from the workspace controls", () => {
    renderApp(payload());

    const filterToolbar = screen.getByRole("toolbar", { name: "File type filters" });
    fireEvent.click(within(filterToolbar).getByRole("button", { name: "SVG" }));
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(within(filesPane()).getAllByText("SVG").length).toBeGreaterThan(0);

    fireEvent.click(within(filterToolbar).getByRole("button", { name: "CSV" }));
    fireEvent.click(within(filterToolbar).getByRole("button", { name: "SVG" }));
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(within(filesPane()).getAllByText("CSV").length).toBeGreaterThan(0);
    expect(within(filterToolbar).getByRole("button", { name: "CSV" })).toHaveAttribute("aria-pressed", "true");
  });

  it("clicking a plot-set row checks it and adds the card", () => {
    renderApp(payload());

    const alphaRow = within(filesPane()).getByText("alpha.csv");
    fireEvent.click(alphaRow);

    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_checked_plot_sets",
      plot_set_ids: ["data__processed__alpha"],
    }));
    expect(screen.queryByRole("complementary", { name: /CSV preview for alpha.csv/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "SVG" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();

    fireEvent.click(alphaRow);

    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_checked_plot_sets",
      plot_set_ids: [],
    }));
    expect(screen.queryByRole("img", { name: "alpha.svg" })).not.toBeInTheDocument();
  });

  it("plot-set cards expose CSV and image attachment tabs", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(screen.getByRole("tab", { name: "SVG" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "CSV" }));
    expect(screen.getByRole("tab", { name: "CSV" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("signal")).toBeInTheDocument();
  });

  it("opens help content from the app bar", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByRole("button", { name: "Help" }));

    expect(screen.getByRole("dialog", { name: "Help" })).toBeInTheDocument();
    expect(screen.getByText("Drag checked cards to reorder them, or drag the lower-right corner to resize the whole gallery.")).toBeInTheDocument();
  });

  it("lets the plot card resize the whole gallery from the corner handle", () => {
    const base = payload();
    render(
      <App
        payload={payload({
          plotSets: [
            base.plotSets![0],
            {
              ...base.plotSets![0],
              plotSetId: "data__processed__beta",
              title: "beta.csv",
              preferredFigure: {
                ...base.plotSets![0].preferredFigure!,
                id: "data__processed__beta:svg",
                displayName: "beta.svg",
                plotId: "data__processed__beta:svg",
              },
              attachments: base.plotSets![0].attachments.map((attachment) => {
                if (attachment.type === "svg") {
                  return {
                    ...attachment,
                    id: "data__processed__beta:svg",
                    displayName: "beta.svg",
                    plotId: "data__processed__beta:svg",
                  };
                }
                if (attachment.type === "png") {
                  return {
                    ...attachment,
                    id: "data__processed__beta:png",
                    displayName: "beta.png",
                    plotId: "data__processed__beta:png",
                  };
                }
                if (attachment.type === "csv") {
                  return {
                    ...attachment,
                    id: "data__processed__beta:csv",
                    datasetId: "data__processed__beta",
                  };
                }
                return attachment;
              }),
            },
          ],
          records: [
            ...base.records,
            {
              ...base.records[0],
              id: "data__processed__beta:svg",
              name: "beta.svg",
              sourceDatasetId: "data__processed__beta",
            },
            {
              ...base.records[1],
              id: "data__processed__beta:png",
              name: "beta.png",
              kind: "PNG",
              sourceDatasetId: "data__processed__beta",
            },
          ],
          datasets: [
            ...base.datasets,
            {
              ...base.datasets[0],
              id: "data__processed__beta",
              displayName: "beta.csv",
              path: "data/processed/beta.csv",
              associatedPlotId: "data__processed__beta:svg",
              associatedPlotIds: ["data__processed__beta:svg", "data__processed__beta:png"],
            },
          ],
        })}
      />,
    );
    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByLabelText("Show beta.csv"));

    const alphaCard = screen.getByRole("img", { name: "alpha.svg" }).closest("article");
    const betaCard = screen.getByRole("img", { name: "beta.svg" }).closest("article");
    expect(alphaCard).not.toBeNull();
    expect(betaCard).not.toBeNull();
    const resizeHandle = (alphaCard as HTMLElement).querySelector(".mg-card-resize") as HTMLElement;
    expect(resizeHandle).not.toBeNull();

    fireEvent.pointerDown(resizeHandle, { clientX: 100, clientY: 100, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 320, clientY: 320 });
    fireEvent.pointerUp(window);

    expect(alphaCard as HTMLElement).toHaveStyle("--card-size: 450px");
    expect(betaCard as HTMLElement).toHaveStyle("--card-size: 450px");

    fireEvent.change(screen.getByLabelText("Tile size"), { target: { value: "460" } });
    expect(alphaCard as HTMLElement).toHaveStyle("--card-size: 460px");
    expect(betaCard as HTMLElement).toHaveStyle("--card-size: 460px");
  });

  it("shows YAML metadata and content in the YAML tab", () => {
    renderApp(payload());

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    expect(screen.queryByRole("tab", { name: "YAML" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByText("alpha.mpl.yaml")).not.toBeInTheDocument();
  });

  it("keeps plot generation actions hidden in the read-only host", () => {
    const noPlotPayload = payload({
      datasets: [
        {
          ...payload().datasets[0],
          associatedPlotId: null,
          associatedPlotIds: [],
          draftStatus: "not_initialized",
        },
      ],
      records: [],
      files: [
        {
          ...payload().files[0],
          iconKind: "csv",
          plotId: null,
          draftStatus: "not_initialized",
        },
      ],
      plotSets: undefined,
    });
    renderApp(noPlotPayload);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    expect(screen.queryByRole("button", { name: "Generate plot" })).not.toBeInTheDocument();
  });

  it("can switch the same unified card between image and CSV tabs", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    const card = screen.getByRole("img", { name: "alpha.svg" }).closest("article");
    expect(card).not.toBeNull();
    fireEvent.click(within(card as HTMLElement).getByRole("tab", { name: "CSV" }));

    expect(within(card as HTMLElement).getByRole("tab", { name: "CSV" })).toHaveAttribute("aria-selected", "true");
    expect(within(card as HTMLElement).getByRole("table")).toBeInTheDocument();
  });

  it("shows CSV tab for record-only cards when a matched csvPath exists", () => {
    const base = payload();
    const recordOnlyPayload = payload({
      datasets: [],
      records: [
        {
          ...base.records[0],
          sourceDatasetId: null,
          previewColumns: ["time", "signal"],
          previewRows: [
            { time: 0, signal: 1 },
            { time: 1, signal: 2 },
          ],
          previewTruncated: false,
          previewError: null,
        },
      ],
      files: [
        {
          ...base.files[1],
          datasetId: null,
        },
      ],
      plotSets: undefined,
    });

    render(<App payload={recordOnlyPayload} />);
    fireEvent.click(screen.getByLabelText("Show alpha.svg"));

    const card = screen.getByRole("img", { name: "alpha.svg" }).closest("article");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("tab", { name: "CSV" })).toBeInTheDocument();
    fireEvent.click(within(card as HTMLElement).getByRole("tab", { name: "CSV" }));
    expect(within(card as HTMLElement).getByRole("table")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("signal")).toBeInTheDocument();
  });

  it("labels loose image-only projects as an image library without file metadata tags", () => {
    const base = payload();
    render(
      <App
        payload={payload({
          browseMode: "image-library",
          datasets: [],
          records: [
            {
              ...base.records[0],
              id: "exports__overview",
              name: "overview.png",
              kind: "PNG",
              imagePath: "exports/overview.png",
              csvPath: null,
              sourceDatasetId: null,
              editable: false,
              widthPx: 1200,
              heightPx: 800,
              sizeBytes: 153600,
              imageFormat: "PNG",
            },
          ],
          files: [],
          plotSets: [
            {
              plotSetId: "plotset::exports::overview",
              title: "overview",
              folderPath: "exports",
              attachments: [
                {
                  id: "exports__overview",
                  type: "png",
                  displayName: "overview.png",
                  sourcePath: "exports/overview.png",
                  datasetId: null,
                  plotId: "exports__overview",
                },
              ],
              preferredFigure: {
                id: "exports__overview",
                type: "png",
                displayName: "overview.png",
                sourcePath: "exports/overview.png",
                datasetId: null,
                plotId: "exports__overview",
              },
              editable: false,
              checked: false,
              renderStatus: "ready",
            },
          ],
        })}
      />,
    );

    expect(screen.getByText("Images")).toBeInTheDocument();
    expect(screen.getByText("Select images from Files to build a gallery.")).toBeInTheDocument();
    expect(within(filesPane()).queryByLabelText("Attachments for overview")).not.toBeInTheDocument();
    expect(within(filesPane()).queryByRole("button", { name: "CSV" })).not.toBeInTheDocument();
    expect(within(filesPane()).queryByRole("button", { name: "YAML" })).not.toBeInTheDocument();
    expect(within(filesPane()).getByText("overview.png")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Show overview.png"));
    expect(screen.getByRole("img", { name: "overview.png" })).toBeInTheDocument();
    expect(screen.queryByText("1200 x 800px")).not.toBeInTheDocument();
    expect(screen.queryByText("150 KiB")).not.toBeInTheDocument();
    expect(screen.queryByText("view only")).not.toBeInTheDocument();
  });

  it("shows only image-backed files in picture mode", () => {
    const base = payload();
    render(
      <App
        payload={payload({
          browseMode: "image-library",
          plotSets: [
            {
              ...base.plotSets![0],
              plotSetId: "csv-only",
              title: "table.csv",
              attachments: [
                {
                  id: "csv-only:csv",
                  type: "csv",
                  displayName: "table.csv",
                  sourcePath: "data/table.csv",
                  datasetId: "data__processed__alpha",
                  plotId: null,
                },
              ],
              preferredFigure: null,
            },
            {
              plotSetId: "plotset::exports::overview",
              title: "overview",
              folderPath: "exports",
              attachments: [
                {
                  id: "exports__overview",
                  type: "png",
                  displayName: "overview.png",
                  sourcePath: "exports/overview.png",
                  datasetId: null,
                  plotId: "exports__overview",
                },
              ],
              preferredFigure: {
                id: "exports__overview",
                type: "png",
                displayName: "overview.png",
                sourcePath: "exports/overview.png",
                datasetId: null,
                plotId: "exports__overview",
              },
              editable: false,
              checked: false,
              renderStatus: "ready",
            },
          ],
        })}
      />,
    );

    expect(within(filesPane()).getByText("overview.png")).toBeInTheDocument();
    expect(within(filesPane()).queryByText("table.csv")).not.toBeInTheDocument();
  });

  it("does not surface plot editing actions in the read-only host", () => {
    render(<App payload={payload()} />);
    fireEvent.click(screen.getByLabelText("Show alpha.csv"));

    expect(screen.queryByRole("button", { name: "Details" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: /Plot look for alpha.svg/ })).not.toBeInTheDocument();
  });

  it("uses the right-side checkbox to keep a plot set in the gallery", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
  });

  it("selects and clears all visible plot sets from the files pane", () => {
    render(
      <App
        host={host}
        payload={payload({
          plotSets: [
            payload().plotSets![0],
            {
              ...payload().plotSets![0],
              plotSetId: "data__processed__beta",
              title: "beta.csv",
            },
          ],
        })}
      />,
    );

    fireEvent.click(screen.getByRole("checkbox", { name: "Select all plot sets in folder" }));
    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(screen.getByLabelText("Show beta.csv")).toBeChecked();
    expect(screen.getByText("2 selected in folder")).toBeInTheDocument();
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_checked_plot_sets",
      plot_set_ids: ["data__processed__alpha", "data__processed__beta"],
    }));

    fireEvent.click(screen.getByRole("checkbox", { name: "Clear all plot sets in folder" }));
    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(screen.getByLabelText("Show beta.csv")).not.toBeChecked();
  });

  it("clears the gallery from the workspace toolbar", () => {
    renderApp(payload());

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear gallery" }));

    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(screen.queryByRole("img", { name: "alpha.svg" })).not.toBeInTheDocument();
    expect(emitEventMock).toHaveBeenLastCalledWith(expect.objectContaining({
      id: expect.any(String),
      type: "set_checked_plot_sets",
      plot_set_ids: [],
    }));
  });

  it("alternates file-row shade classes for easier scanning", () => {
    render(
      <App
        payload={payload({
          plotSets: [
            payload().plotSets![0],
            {
              ...payload().plotSets![0],
              plotSetId: "data__processed__beta",
              title: "beta.csv",
            },
          ],
        })}
      />,
    );

    const rows = within(filesPane()).getAllByRole("option");
    expect(rows[0]).toHaveClass("is-shade-0");
    expect(rows[1]).toHaveClass("is-shade-1");
  });

  it("shows only top-level roots with PNG/SVG plot sets and preserves nested folders below them", () => {
    const base = payload();
    render(
      <App
        payload={payload({
          plotSets: [
            {
              ...base.plotSets![0],
              plotSetId: "analyses__case_a__alpha",
              folderPath: "analyses/case_a/results/final",
            },
            {
              ...base.plotSets![0],
              plotSetId: "analyses__case_b__beta",
              title: "beta.csv",
              folderPath: "analyses/case_b/results",
              attachments: base.plotSets![0].attachments.filter((attachment) => attachment.type !== "png"),
            },
            {
              ...base.plotSets![0],
              plotSetId: "docs__gamma",
              title: "gamma.csv",
              folderPath: "docs/plots",
              attachments: base.plotSets![0].attachments.filter((attachment) => attachment.type !== "png"),
            },
          ],
        })}
      />,
    );

    fireEvent.click(within(foldersPane()).getByRole("button", { name: "Expand mplgallery" }));
    expect(within(foldersPane()).getByText("analyses")).toBeInTheDocument();
    expect(within(foldersPane()).getByText("docs")).toBeInTheDocument();
    fireEvent.click(within(foldersPane()).getByRole("button", { name: "Expand analyses" }));
    expect(within(foldersPane()).getByText("case_a")).toBeInTheDocument();
    expect(within(foldersPane()).getByText("case_b")).toBeInTheDocument();
  });

  it("collapses folder and file panes to narrow rails", () => {
    render(<App payload={payload()} />);

    const hideFolders = screen.getByRole("button", { name: "Hide folders" });
    expect(hideFolders).toHaveTextContent("");
    expect(screen.queryByText("Workspace")).not.toBeInTheDocument();

    fireEvent.click(hideFolders);
    expect(foldersPane()).toHaveClass("is-collapsed");
    expect(screen.getByRole("button", { name: /Folders/ })).toHaveAttribute("aria-expanded", "false");

    const hideFiles = screen.getByRole("button", { name: "Hide files" });
    expect(hideFiles).toHaveTextContent("");
    fireEvent.click(hideFiles);
    expect(screen.getByRole("button", { name: /Folders/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("button", { name: /Files/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByLabelText("MPLGallery app controls").closest(".mg-shell")).toHaveClass(
      "is-sidebars-auto-collapsed",
    );

    fireEvent.click(screen.getByRole("button", { name: /Folders/ }));
    expect(foldersPane()).not.toHaveClass("is-collapsed");
    expect(screen.getByLabelText("MPLGallery app controls").closest(".mg-shell")).not.toHaveClass(
      "is-sidebars-auto-collapsed",
    );
  });

  it("reorders checked plot cards by dragging the whole card onto another card", () => {
    const base = payload();
    const betaRecord = {
      ...base.records[0],
      id: "plots__beta",
      name: "beta.svg",
      imagePath: "results/final/figures/beta.svg",
      imageSrc: "data:image/svg+xml;base64,BB==",
    };
    const betaDataset = {
      ...base.datasets[0],
      id: "data__processed__beta",
      displayName: "beta.csv",
      path: "data/processed/beta.csv",
      associatedPlotId: "plots__beta",
      associatedPlotIds: ["plots__beta"],
    };
    const betaPlotSet = {
      ...base.plotSets![0],
      plotSetId: "data__processed__beta",
      title: "beta.csv",
      attachments: base.plotSets![0].attachments.map((attachment) => ({
        ...attachment,
        id: attachment.id.replace("alpha", "beta"),
        displayName: attachment.displayName.replace("alpha", "beta"),
        sourcePath: attachment.sourcePath.replace("alpha", "beta"),
        datasetId: attachment.datasetId ? "data__processed__beta" : attachment.datasetId,
        plotId: attachment.plotId ? "plots__beta" : attachment.plotId,
      })),
      preferredFigure: {
        ...base.plotSets![0].preferredFigure!,
        id: "plots__beta",
        displayName: "beta.svg",
        sourcePath: "results/final/figures/beta.svg",
        datasetId: "data__processed__beta",
        plotId: "plots__beta",
      },
    };
    const dataTransfer = {
      effectAllowed: "move",
      dropEffect: "move",
      setData: vi.fn(),
      getData: vi.fn(),
      setDragImage: vi.fn(),
    };

    render(
      <App
        payload={payload({
          datasets: [base.datasets[0], betaDataset],
          records: [base.records[0], betaRecord],
          plotSets: [base.plotSets![0], betaPlotSet],
        })}
      />,
    );

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByLabelText("Show beta.csv"));
    const alphaCard = screen.getByRole("article", { name: "alpha.csv card" });
    const betaCard = screen.getByRole("article", { name: "beta.csv card" });

    fireEvent.dragStart(alphaCard, { dataTransfer });
    fireEvent.dragOver(betaCard, { dataTransfer });

    const cards = screen.getAllByRole("article");
    expect(cards[0]).toHaveAccessibleName("beta.csv card");
    expect(cards[1]).toHaveAccessibleName("alpha.csv card");
  });
});
