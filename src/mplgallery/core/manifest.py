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


def load_manifests(project_root: Path | str) -> ProjectManifest:
    """Load the root manifest plus nested project manifests under a scan root."""
    root = Path(project_root).expanduser().resolve()
    combined = ProjectManifest()
    manifest_paths = sorted(root.glob("**/.mplgallery/manifest.yaml"))
    for manifest_path in manifest_paths:
        manifest_root = manifest_path.parent.parent
        try:
            prefix = manifest_root.relative_to(root)
        except ValueError:
            continue
        manifest = load_manifest(manifest_root)
        for record in manifest.records:
            combined.upsert_record(_prefix_record(record, prefix))
    return combined


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
    root = Path(project_root).expanduser().resolve()
    manifest_root, local_plot_path = _manifest_root_for_plot(root, plot_path)
    manifest = load_manifest(manifest_root)
    existing = manifest.record_for_plot(local_plot_path)
    if existing is None:
        updated = ManifestRecord(plot_path=local_plot_path, redraw=validated_redraw)
    else:
        updated = existing.model_copy(update={"redraw": validated_redraw})
    manifest.upsert_record(updated)
    save_manifest(manifest_root, manifest)
    prefix = manifest_root.relative_to(root) if manifest_root != root else Path(".")
    return _prefix_record(updated, prefix)


def _prefix_record(record: ManifestRecord, prefix: Path) -> ManifestRecord:
    if prefix == Path("."):
        return record
    return record.model_copy(
        update={
            "plot_path": prefix / record.plot_path,
            "raw_csv_path": prefix / record.raw_csv_path if record.raw_csv_path else None,
            "plot_csv_path": prefix / record.plot_csv_path if record.plot_csv_path else None,
            "csv_path": prefix / record.csv_path if record.csv_path else None,
        }
    )


def _manifest_root_for_plot(root: Path, plot_path: Path) -> tuple[Path, Path]:
    full_plot_path = root / plot_path
    candidates = [full_plot_path.parent, *full_plot_path.parents]
    for candidate in candidates:
        if candidate == root.parent:
            break
        if (candidate / ".mplgallery" / "manifest.yaml").exists():
            return candidate, full_plot_path.relative_to(candidate)
    for parent in full_plot_path.parents:
        if parent.parent == root and (parent / ".mplgallery" / "manifest.yaml").exists():
            return parent, full_plot_path.relative_to(parent)
    return root, plot_path


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
