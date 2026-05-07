import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
      recentRoots: [
        "C:/Users/Tanner/Documents/git/mplgallery",
        "C:/Users/Tanner/Documents/git/other-analysis",
      ],
      error: null,
      showRootChooser: true,
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
        csvPath: "data/processed/alpha.csv",
        confidence: "exact",
        imageSrc: "data:image/svg+xml;base64,AA==",
        csvColumns: ["x", "y"],
        editable: true,
        redraw: { x: "x", series: [{ y: "y" }] },
        series: [{ y: "y" }],
      },
    ],
    files: [
      {
        id: "folder:data",
        kind: "csv",
        path: "data/processed/alpha.csv",
        name: "alpha.csv",
        parentPath: "data/processed",
        iconKind: "csv",
        datasetId: "data__processed__alpha",
        draftStatus: "not_initialized",
      },
      {
        id: "plot:plots__alpha",
        kind: "image",
        path: "results/final/figures/alpha.svg",
        name: "alpha.svg",
        parentPath: "results/final/figures",
        iconKind: "image",
        plotId: "plots__alpha",
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

describe("App explorer", () => {
  beforeEach(() => {
    streamlitMock.setComponentValue.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("keeps gallery filtering empty until a CSV or plot is selected", () => {
    render(<App payload={payload({ rootContext: { ...payload().rootContext!, showRootChooser: false } })} />);

    expect(screen.getAllByText("Select a CSV or check plots to build a gallery.").length).toBeGreaterThan(0);
  });

  it("renders a unified file tree with project root label, compressed folders, and file icons", () => {
    render(<App payload={payload({ rootContext: { ...payload().rootContext!, showRootChooser: false } })} />);

    expect(screen.getByRole("button", { name: /mplgallery2/ })).toBeInTheDocument();
    expect(screen.getByText("data/processed")).toBeInTheDocument();
    expect(screen.getByLabelText("CSV file")).toBeInTheDocument();
    expect(screen.getByLabelText("Image file")).toBeInTheDocument();
    expect(screen.queryByText("CSV tables")).not.toBeInTheDocument();
    expect(screen.getByText("2 files")).toBeInTheDocument();
    expect(screen.getByText("Plot file explorer")).toBeInTheDocument();
  });

  it("opens CSV draft preferences before generating a companion plot", () => {
    render(
      <App
        payload={payload({
          rootContext: { ...payload().rootContext!, showRootChooser: false },
        })}
      />,
    );

    fireEvent.click(screen.getByText("alpha.csv"));
    expect(screen.getByRole("complementary", { name: /CSV preview for alpha.csv/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate companion plot" }));

    expect(screen.getByRole("dialog", { name: /Draft plot preferences/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate companion" }));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "draft_dataset_with_preferences",
        dataset_id: "data__processed__alpha",
        redraw: expect.objectContaining({
          x: "time",
          y: ["signal"],
        }),
        output_format: "svg",
      }),
    });
  });

  it("shows checked CSV cards in gallery and opens generation modal", () => {
    render(<App payload={payload({ rootContext: { ...payload().rootContext!, showRootChooser: false } })} />);

    fireEvent.click(screen.getByLabelText("Include CSV alpha.csv"));
    expect(screen.getByText("Generate plot")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate plot" }));
    expect(screen.getByRole("dialog", { name: /Draft plot preferences/ })).toBeInTheDocument();
  });

  it("keeps gallery cards visible when clicking CSV card and opens/close preview drawer", () => {
    render(<App payload={payload({ rootContext: { ...payload().rootContext!, showRootChooser: false } })} />);

    fireEvent.click(screen.getByLabelText("Include plot alpha.svg"));
    fireEvent.click(screen.getByLabelText("Include CSV alpha.csv"));
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV alpha.csv" }));

    expect(screen.getByRole("complementary", { name: /CSV preview for alpha.csv/ })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Back to gallery" }));
    expect(screen.queryByRole("complementary", { name: /CSV preview for alpha.csv/ })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "alpha.svg" })).toBeInTheDocument();
  });
});
