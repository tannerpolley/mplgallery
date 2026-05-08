import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { BrowserPayload } from "./types";

const streamlitMock = vi.hoisted(() => ({
  setComponentValue: vi.fn(),
}));

vi.mock("streamlit-component-lib", () => ({
  Streamlit: streamlitMock,
}));

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
    streamlitMock.setComponentValue.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("keeps gallery empty until a CSV or image is selected", () => {
    render(<App payload={payload()} />);

    expect(screen.getAllByText("Select plot sets from Files to build a gallery.").length).toBeGreaterThan(0);
    expect(screen.queryByRole("img", { name: "alpha.svg" })).not.toBeInTheDocument();
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
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByRole("button", { name: "Project root mplgallery" }));
    expect(screen.getByRole("dialog", { name: "Project root menu" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open root" }));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "change_project_root",
        root_path: "C:/Users/Tanner/Documents/git/mplgallery",
      }),
    });

    fireEvent.click(screen.getByRole("button", { name: /Refresh/ }));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({ type: "refresh_index" }),
    });
  });

  it("filters the explorer to CSV files or figure files from the workspace controls", () => {
    render(<App payload={payload()} />);

    fireEvent.change(screen.getByLabelText("Filter"), { target: { value: "figures" } });
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(within(filesPane()).getByText("SVG")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filter"), { target: { value: "csv" } });
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(within(filesPane()).getByText("CSV")).toBeInTheDocument();
  });

  it("clicking a plot-set row checks it and adds the card", () => {
    render(<App payload={payload()} />);

    fireEvent.click(within(filesPane()).getByText("alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "set_checked_plot_sets",
        plot_set_ids: ["data__processed__alpha"],
      }),
    });
    expect(screen.queryByRole("complementary", { name: /CSV preview for alpha.csv/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "SVG" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
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

  it("shows YAML metadata and content in the YAML tab", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByRole("tab", { name: "YAML" }));

    expect(screen.getByText("alpha.mpl.yaml")).toBeInTheDocument();
    expect(screen.getByText("Open editor")).toBeInTheDocument();
    expect(screen.getByText(/kind: line/)).toBeInTheDocument();
    expect(screen.getByText("X")).toBeInTheDocument();
    expect(screen.getByText("time")).toBeInTheDocument();
  });

  it("opens draft preferences from the unified card only when no companion figure exists", () => {
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
    render(<App payload={noPlotPayload} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));
    fireEvent.click(screen.getByRole("button", { name: "Generate plot" }));

    expect(screen.getByRole("dialog", { name: /Draft plot preferences/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate companion" }));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "draft_dataset_with_preferences",
        dataset_id: "data__processed__alpha",
        output_format: "svg",
      }),
    });
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

  it("uses the right-side checkbox to keep a plot set in the gallery", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByLabelText("Show alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
  });

  it("selects and clears all visible plot sets from the files pane", () => {
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

    fireEvent.click(screen.getByRole("button", { name: "Select all plot sets in folder" }));
    expect(screen.getByLabelText("Show alpha.csv")).toBeChecked();
    expect(screen.getByLabelText("Show beta.csv")).toBeChecked();
    expect(screen.getByText("2 selected in folder")).toBeInTheDocument();
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "set_checked_plot_sets",
        plot_set_ids: ["data__processed__alpha", "data__processed__beta"],
      }),
    });

    fireEvent.click(screen.getByRole("button", { name: "Clear all plot sets in folder" }));
    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(screen.getByLabelText("Show beta.csv")).not.toBeChecked();
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

  it("shows only top-level roots with PNG plot sets and preserves nested folders below them", () => {
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
    fireEvent.click(within(foldersPane()).getByRole("button", { name: "Expand analyses" }));
    expect(within(foldersPane()).getByText("case_a")).toBeInTheDocument();
    expect(within(foldersPane()).getByText("case_b")).toBeInTheDocument();
    expect(within(foldersPane()).queryByText("docs")).not.toBeInTheDocument();
  });

  it("collapses folder and file panes to narrow rails", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByRole("button", { name: "Hide folders" }));
    expect(foldersPane()).toHaveClass("is-collapsed");
    expect(screen.getByRole("button", { name: /Folders/ })).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(screen.getByRole("button", { name: "Hide files" }));
    expect(filesPane()).toHaveClass("is-collapsed");
    expect(screen.getByRole("button", { name: /Files/ })).toHaveAttribute("aria-expanded", "false");
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
