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
    expect(within(foldersPane()).getByText("data")).toBeInTheDocument();
    expect(within(foldersPane()).getByText("processed")).toBeInTheDocument();
    expect(screen.queryByText("data/processed")).not.toBeInTheDocument();
    expect(within(foldersPane()).queryByText("alpha.csv")).not.toBeInTheDocument();
    expect(within(filesPane()).getByText("alpha.csv")).toBeInTheDocument();
    expect(screen.getByLabelText("Show alpha.csv")).toBeInTheDocument();
  });

  it("toggles folders when double-clicking the folder row label", () => {
    render(<App payload={payload()} />);
    const rootFolder = within(foldersPane()).getByText("mplgallery").closest("button");
    const processedFolder = within(foldersPane()).getByText("processed").closest("button");
    expect(rootFolder).not.toBeNull();
    expect(processedFolder).not.toBeNull();

    expect(within(foldersPane()).getByText("processed")).toBeInTheDocument();
    fireEvent.doubleClick(rootFolder as HTMLElement);
    expect(within(foldersPane()).queryByText("processed")).not.toBeInTheDocument();
    fireEvent.doubleClick(rootFolder as HTMLElement);
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

  it("clicking a plot-set row opens one unified card without auto-checking it", () => {
    render(<App payload={payload()} />);

    fireEvent.click(within(filesPane()).getByText("alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(screen.queryByRole("complementary", { name: /CSV preview for alpha.csv/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "SVG" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
  });

  it("plot-set cards expose CSV and image attachment tabs", () => {
    render(<App payload={payload()} />);

    fireEvent.click(within(filesPane()).getByText("alpha.csv"));

    expect(screen.getByLabelText("Show alpha.csv")).not.toBeChecked();
    expect(screen.getByRole("tab", { name: "SVG" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "CSV" }));
    expect(screen.getByRole("tab", { name: "CSV" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("signal")).toBeInTheDocument();
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
    });
    render(<App payload={noPlotPayload} />);

    fireEvent.click(within(filesPane()).getByText("alpha.csv"));
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

    fireEvent.click(within(filesPane()).getByText("alpha.csv"));
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
    });

    render(<App payload={recordOnlyPayload} />);
    fireEvent.click(within(filesPane()).getByText("alpha.svg"));

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
});
