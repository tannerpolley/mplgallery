"""CSV-to-plot association logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mplgallery.core.manifest import ProjectManifest
from mplgallery.core.models import (
    AssociationConfidence,
    DiscoveredFile,
    FileKind,
    PlotRecord,
    ScanResult,
)

NORMALIZED_SUFFIXES = (
    "_plot",
    "_figure",
    "_fig",
    "_fit",
    "_results",
    "_data",
    "-plot",
    "-fit",
)


@dataclass(frozen=True)
class CandidateScore:
    csv: DiscoveredFile
    score: int
    confidence: AssociationConfidence
    reason: str


def build_plot_records(
    scan: ScanResult,
    *,
    manifest: ProjectManifest | None = None,
) -> list[PlotRecord]:
    csvs = [file for file in scan.files if file.kind is FileKind.CSV]
    images = [file for file in scan.files if file.kind is FileKind.IMAGE]
    records = [
        _record_for_image(image, csvs, manifest or ProjectManifest())
        for image in sorted(images, key=lambda file: file.relative_path.as_posix().lower())
    ]
    return records


def _record_for_image(
    image: DiscoveredFile,
    csvs: list[DiscoveredFile],
    manifest: ProjectManifest,
) -> PlotRecord:
    manifest_record = manifest.record_for_plot(image.relative_path)
    if manifest_record:
        source_path = manifest_record.plot_csv_path or manifest_record.csv_path
        manifest_csv = _find_csv(csvs, source_path) if source_path is not None else None
        raw_csv = (
            _find_csv(csvs, manifest_record.raw_csv_path)
            if manifest_record.raw_csv_path is not None
            else None
        )
        if manifest_csv is not None:
            return PlotRecord(
                plot_id=_plot_id(image.relative_path),
                image=image,
                csv=manifest_csv,
                raw_csv=raw_csv,
                plot_csv=manifest_csv,
                association_confidence=AssociationConfidence.EXACT,
                association_reason="manifest override",
                redraw=manifest_record.redraw,
            )

    if not csvs:
        return PlotRecord(
            plot_id=_plot_id(image.relative_path),
            image=image,
            association_reason="no csv candidates",
        )

    candidates = [_score_candidate(image, csv) for csv in csvs]
    candidates = [candidate for candidate in candidates if candidate.score > 0]
    if not candidates:
        return PlotRecord(
            plot_id=_plot_id(image.relative_path),
            image=image,
            association_reason="no confident match",
        )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and candidates[1].score == best.score:
        return PlotRecord(
            plot_id=_plot_id(image.relative_path),
            image=image,
            association_reason="ambiguous candidates",
        )

    return PlotRecord(
        plot_id=_plot_id(image.relative_path),
        image=image,
        csv=best.csv,
        plot_csv=best.csv,
        association_confidence=best.confidence,
        association_reason=best.reason,
    )


def _score_candidate(image: DiscoveredFile, csv: DiscoveredFile) -> CandidateScore:
    if image.parent_dir == csv.parent_dir and image.stem == csv.stem:
        return CandidateScore(csv, 100, AssociationConfidence.HIGH, "same directory and same stem")

    if image.stem == csv.stem:
        if image.parent_dir.name == "plots" and csv.parent_dir.name == "data":
            reason = "sibling data/plots directories and same stem"
        else:
            reason = "nearby directory and same stem"
        return CandidateScore(csv, 90, AssociationConfidence.HIGH, reason)

    if _normalized_stem(image.stem) == _normalized_stem(csv.stem):
        return CandidateScore(csv, 70, AssociationConfidence.MEDIUM, "normalized stem match")

    if _nearby_csvs(image, [csv]):
        return CandidateScore(csv, 20, AssociationConfidence.LOW, "only csv nearby")

    return CandidateScore(csv, 0, AssociationConfidence.NONE, "no match")


def _find_csv(csvs: list[DiscoveredFile], relative_path: Path) -> DiscoveredFile | None:
    normalized = relative_path.as_posix()
    return next((csv for csv in csvs if csv.relative_path.as_posix() == normalized), None)


def _normalized_stem(stem: str) -> str:
    normalized = stem.lower()
    changed = True
    while changed:
        changed = False
        for suffix in NORMALIZED_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                changed = True
    return normalized


def _nearby_csvs(image: DiscoveredFile, csvs: list[DiscoveredFile]) -> list[DiscoveredFile]:
    parent = image.parent_dir
    experiment_dir = parent.parent if parent != Path(".") else parent
    return [
        csv
        for csv in csvs
        if csv.parent_dir == parent or csv.parent_dir == experiment_dir / "data"
    ]


def _plot_id(relative_path: Path) -> str:
    return relative_path.with_suffix("").as_posix().replace("/", "__")
