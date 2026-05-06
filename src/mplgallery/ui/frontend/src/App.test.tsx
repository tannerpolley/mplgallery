import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
    datasets: [],
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

describe("App root chooser", () => {
  beforeEach(() => {
    streamlitMock.setComponentValue.mockClear();
  });

  it("renders the active root and compact invalid-root errors", () => {
    render(
      <App
        payload={payload({
          rootContext: {
            activeRoot: "C:/Users/Tanner/Documents/git/mplgallery",
            launchRoot: "C:/Users/Tanner/Documents/git/mplgallery",
            recentRoots: [],
            error: "Project root does not exist: C:/missing",
            showRootChooser: true,
          },
        })}
      />,
    );

    expect(screen.getByText("Root")).toBeInTheDocument();
    expect(screen.getByText("…/git/mplgallery")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Project root does not exist");
  });

  it("emits root-selection and forget events for recent roots", () => {
    render(<App payload={payload()} />);

    fireEvent.click(screen.getByText("…/git/other-analysis"));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "change_project_root",
        root_path: "C:/Users/Tanner/Documents/git/other-analysis",
      }),
    });

    fireEvent.click(screen.getByLabelText("Forget C:/Users/Tanner/Documents/git/other-analysis"));
    expect(streamlitMock.setComponentValue).toHaveBeenLastCalledWith({
      event: expect.objectContaining({
        type: "forget_recent_root",
        root_path: "C:/Users/Tanner/Documents/git/other-analysis",
      }),
    });
  });

  it("keeps gallery filtering empty until a CSV or plot is selected", () => {
    render(<App payload={payload({ rootContext: { ...payload().rootContext!, showRootChooser: false } })} />);

    expect(screen.getAllByText("Select a CSV or check plots to build a gallery.").length).toBeGreaterThan(0);
  });
});
