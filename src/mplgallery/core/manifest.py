"""Manifest loading and association override support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from mplgallery.core.models import ManifestRecord, RedrawMetadata


class ProjectManifest(BaseModel):
    version: int = 1
    records: list[ManifestRecord] = Field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "ProjectManifest":
        return cls.model_validate(data)

    def record_for_plot(self, plot_path: Path) -> ManifestRecord | None:
        normalized = plot_path.as_posix()
        for record in self.records:
            if record.plot_path.as_posix() == normalized:
                return record
        return None

    def upsert_record(self, updated_record: ManifestRecord) -> None:
        normalized = updated_record.plot_path.as_posix()
        for index, record in enumerate(self.records):
            if record.plot_path.as_posix() == normalized:
                self.records[index] = updated_record
                return
        self.records.append(updated_record)


def load_manifest(project_root: Path | str) -> ProjectManifest:
    root = Path(project_root)
    manifest_path = root / ".mplgallery" / "manifest.yaml"
    if not manifest_path.exists():
        return ProjectManifest()

    data = yaml.safe_load(manifest_path.read_text()) or {}
    return ProjectManifest.from_mapping(data)


def save_manifest(project_root: Path | str, manifest: ProjectManifest) -> Path:
    root = Path(project_root)
    manifest_path = root / ".mplgallery" / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _manifest_to_yaml_data(manifest)
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False))
    return manifest_path


def update_manifest_redraw(
    project_root: Path | str,
    plot_path: Path,
    redraw: Any,
) -> ManifestRecord:
    validated_redraw = (
        redraw if isinstance(redraw, RedrawMetadata) else RedrawMetadata.model_validate(redraw)
    )
    manifest = load_manifest(project_root)
    existing = manifest.record_for_plot(plot_path)
    if existing is None:
        updated = ManifestRecord(plot_path=plot_path, redraw=validated_redraw)
    else:
        updated = existing.model_copy(update={"redraw": validated_redraw})
    manifest.upsert_record(updated)
    save_manifest(project_root, manifest)
    return updated


def _manifest_to_yaml_data(manifest: ProjectManifest) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for record in manifest.records:
        item: dict[str, Any] = {"plot_path": record.plot_path.as_posix()}
        if record.raw_csv_path is not None:
            item["raw_csv_path"] = record.raw_csv_path.as_posix()
        if record.plot_csv_path is not None:
            item["plot_csv_path"] = record.plot_csv_path.as_posix()
        if record.csv_path is not None:
            item["csv_path"] = record.csv_path.as_posix()
        if record.redraw is not None:
            item["redraw"] = record.redraw.model_dump(mode="json", exclude_none=True)
        if record.notes is not None:
            item["notes"] = record.notes
        records.append(item)
    return {"version": manifest.version, "records": records}
