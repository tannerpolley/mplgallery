"""Pydantic models for discovered files, manifests, and plot records."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FileKind(str, Enum):
    IMAGE = "image"
    CSV = "csv"


class AssociationConfidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class PlotMode(str, Enum):
    STATIC = "static"
    RECIPE = "recipe"


class MatplotlibFigureAttributes(BaseModel):
    width_inches: float = 6.0
    height_inches: float = 4.0
    dpi: int = 150
    facecolor: str | None = None
    constrained_layout: bool | None = None


class AxisMetadata(BaseModel):
    label: str | None = None
    unit: str | None = None
    scale: str = "linear"
    limits: tuple[float, float] | None = None


class SeriesStyle(BaseModel):
    y: str
    label: str | None = None
    color: str | None = None
    edgecolor: str | None = None
    linewidth: float | None = None
    linestyle: str | None = None
    marker: str | None = None
    markersize: float | None = None
    hatch: str | None = None
    bar_width: float | None = None
    alpha: float | None = None
    zorder: float | None = None


class SubplotMetadata(BaseModel):
    subplot_id: str
    title: str | None = None
    kind: str = "line"
    x: str | None = None
    y: list[str] = Field(default_factory=list)
    xlabel: str | None = None
    xlabel_unit: str | None = None
    ylabel: str | None = None
    ylabel_unit: str | None = None
    xscale: str = "linear"
    yscale: str = "linear"
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    grid: bool = True
    grid_axis: str | None = None
    grid_alpha: float | None = None
    legend_title: str | None = None
    legend_location: str | None = None
    bins: int | None = None
    series: list[SeriesStyle] = Field(default_factory=list)


class RedrawMetadata(BaseModel):
    kind: str = "line"
    x: str | None = None
    y: list[str] = Field(default_factory=list)
    title: str | None = None
    xlabel: str | None = None
    xlabel_unit: str | None = None
    ylabel: str | None = None
    ylabel_unit: str | None = None
    xscale: str = "linear"
    yscale: str = "linear"
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    grid: bool = True
    grid_axis: str | None = None
    grid_alpha: float | None = None
    legend_title: str | None = None
    legend_location: str | None = None
    bins: int | None = None
    figure: MatplotlibFigureAttributes = Field(default_factory=MatplotlibFigureAttributes)
    series: list[SeriesStyle] = Field(default_factory=list)
    subplots: list[SubplotMetadata] = Field(default_factory=list)
    subplot_rows: int | None = None
    subplot_cols: int | None = None
    sharex: bool = False
    sharey: bool = False


class CacheMetadata(BaseModel):
    cache_path: Path | None = None
    source_size_bytes: int | None = None
    source_modified_at: datetime | None = None
    redraw_fingerprint: str | None = None
    render_error: str | None = None


class DiscoveredFile(BaseModel):
    path: Path
    relative_path: Path
    kind: FileKind
    suffix: str
    stem: str
    parent_dir: Path
    size_bytes: int
    modified_at: datetime
    created_at: datetime | None = None
    width_px: int | None = None
    height_px: int | None = None
    image_format: str | None = None


class ScanResult(BaseModel):
    project_root: Path
    files: list[DiscoveredFile]
    ignored_dir_count: int = 0

    @property
    def images(self) -> list[DiscoveredFile]:
        return [file for file in self.files if file.kind is FileKind.IMAGE]

    @property
    def csvs(self) -> list[DiscoveredFile]:
        return [file for file in self.files if file.kind is FileKind.CSV]


class DatasetRecord(BaseModel):
    path: Path
    relative_path: Path
    csv_root: Path
    csv_root_relative_path: Path
    row_count_sampled: int = 0
    columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    draft_status: str = "not_initialized"
    recipe_path: Path | None = None
    plot_ready_path: Path | None = None
    cache_path: Path | None = None


class CSVRootRecord(BaseModel):
    path: Path
    relative_path: Path
    datasets: list[DatasetRecord] = Field(default_factory=list)


class PlotRecipeRecord(BaseModel):
    version: int = 1
    source_csv_path: Path
    plot_ready_path: Path
    cache_path: Path
    script_path: Path
    redraw: RedrawMetadata
    status: str = "draft"
    sample_rows: int | None = None


class CSVStudioIndex(BaseModel):
    project_root: Path
    csv_roots: list[CSVRootRecord] = Field(default_factory=list)
    datasets: list[DatasetRecord] = Field(default_factory=list)
    records: list["PlotRecord"] = Field(default_factory=list)
    ignored_dir_count: int = 0
    imported_artifacts: list["PlotRecord"] = Field(default_factory=list)


class ManifestRecord(BaseModel):
    plot_path: Path
    raw_csv_path: Path | None = None
    plot_csv_path: Path | None = None
    csv_path: Path | None = None
    redraw: RedrawMetadata | None = None
    notes: str | None = None


class PlotRecord(BaseModel):
    plot_id: str
    image: DiscoveredFile
    csv: DiscoveredFile | None = None
    raw_csv: DiscoveredFile | None = None
    plot_csv: DiscoveredFile | None = None
    association_confidence: AssociationConfidence = AssociationConfidence.NONE
    association_reason: str | None = None
    redraw: RedrawMetadata | None = None
    cache: CacheMetadata | None = None
    recipe_path: Path | None = None
    mode: PlotMode = PlotMode.STATIC
    metadata_files: list[Path] = Field(default_factory=list)
    dvc_stage: str | None = None
    mlflow_run_ids: list[str] = Field(default_factory=list)
