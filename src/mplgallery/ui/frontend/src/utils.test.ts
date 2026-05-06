import { describe, expect, it } from "vitest";
import {
  buildTree,
  clampNumber,
  emptyGalleryMessage,
  filterRecords,
  galleryStatus,
  normalizeRedraw,
  parseLimits,
  plotIdSet,
  reconcileCheckedPlotIds,
} from "./utils";
import type { PlotRecord } from "./types";

const records: PlotRecord[] = [
  {
    id: "plots__alpha",
    name: "alpha.png",
    kind: "PNG",
    imagePath: "plots/alpha.png",
    csvPath: "data/plot_ready/alpha.csv",
    confidence: "exact",
    imageSrc: "data:image/png;base64,AA==",
    csvColumns: ["x", "y"],
    editable: true,
    redraw: { x: "x", series: [{ y: "y" }] },
    series: [{ y: "y" }],
  },
  {
    id: "nested__beta",
    name: "beta.svg",
    kind: "SVG",
    imagePath: "nested/plots/beta.svg",
    csvPath: "nested/data/beta.csv",
    confidence: "high",
    imageSrc: "data:image/svg+xml;base64,AA==",
    csvColumns: ["time", "temp"],
    editable: true,
    redraw: { x: "time", series: [{ y: "temp" }] },
    series: [{ y: "temp" }],
  },
];

describe("component utilities", () => {
  it("builds a folder tree from plot paths", () => {
    const tree = buildTree(records);
    expect(tree.count).toBe(2);
    expect(tree.children.map((child) => child.path)).toEqual(["nested", "plots"]);
  });

  it("filters by checked plot ids and search text", () => {
    expect(filterRecords(records, "alpha", new Set(["plots__alpha", "nested__beta"])).map((record) => record.id)).toEqual([
      "plots__alpha",
    ]);
    expect(filterRecords(records, "", new Set(["nested__beta"])).map((record) => record.id)).toEqual([
      "nested__beta",
    ]);
    expect(filterRecords(records, "", new Set()).map((record) => record.id)).toEqual([]);
  });

  it("defaults checkbox state to all plots before the user filters", () => {
    expect([...plotIdSet(records)].sort()).toEqual(["nested__beta", "plots__alpha"]);
    expect([...reconcileCheckedPlotIds(records, new Set(), false)].sort()).toEqual([
      "nested__beta",
      "plots__alpha",
    ]);
    expect([...reconcileCheckedPlotIds(records, new Set(), true)]).toEqual([]);
  });

  it("summarizes gallery status and empty state causes", () => {
    expect(galleryStatus(records)).toEqual({
      totalPlots: 2,
      matchedCsvs: 2,
      missingCsvs: 0,
      renderErrors: 0,
    });
    expect(emptyGalleryMessage([], "", new Set(), false)).toMatch(/No plot image files/);
    expect(emptyGalleryMessage(records, "missing", plotIdSet(records), false)).toBe(
      "No plots match this search.",
    );
    expect(emptyGalleryMessage(records, "", new Set(), true)).toBe(
      "No plots selected. Check a folder or plot in the output tree.",
    );
  });

  it("normalizes metadata while preserving style choices", () => {
    const redraw = normalizeRedraw(
      { title: " Alpha ", xscale: "linear", figure: { width_inches: 7 } },
      [{ y: "y", color: "#123456", linestyle: "--", marker: "s", alpha: 0.8 }],
    );
    expect(redraw.title).toBe("Alpha");
    expect(redraw.figure?.width_inches).toBe(7);
    expect(redraw.series?.[0].linestyle).toBe("--");
  });

  it("parses limits and rejects invalid bounds", () => {
    expect(parseLimits("0", "1")).toEqual([0, 1]);
    expect(parseLimits("", "")).toBeNull();
    expect(() => parseLimits("2", "1")).toThrow(/min less than max/);
  });

  it("clamps layout widths", () => {
    expect(clampNumber(120, 180, 400)).toBe(180);
    expect(clampNumber(520, 180, 400)).toBe(400);
    expect(clampNumber(260, 180, 400)).toBe(260);
  });
});
