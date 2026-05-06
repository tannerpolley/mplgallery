"""Import helpers for existing scientific plot manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mplgallery.core.manifest import load_manifest, save_manifest
from mplgallery.core.models import ManifestRecord, RedrawMetadata


class ManifestImportResult(BaseModel):
    records_imported: int = 0
    manifest_path: Path | None = None
    missing_plot_paths: list[Path] = Field(default_factory=list)
    missing_csv_paths: list[Path] = Field(default_factory=list)
    dry_run: bool = False


def import_epcsaft_manifest(
    manifest_json_path: Path | str,
    *,
    project_root: Path | str,
    dry_run: bool = False,
) -> ManifestImportResult:
    """Import an ePC-SAFT docs/plots/manifest.json into .mplgallery/manifest.yaml."""
    json_path = Path(manifest_json_path).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    items = payload.get("items", payload if isinstance(payload, list) else [])
    if not isinstance(items, list):
        raise ValueError("Expected manifest JSON to contain an 'items' list or be a list.")

    imported_records: list[ManifestRecord] = []
    missing_plot_paths: set[Path] = set()
    missing_csv_paths: set[Path] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        plot_paths = _plot_paths_from_item(item)
        csv_path = _optional_relative_path(item.get("data_path"), root)
        raw_csv_path = _optional_relative_path(item.get("raw_data_path"), root)
        title = item.get("title")
        source_path = _optional_relative_path(item.get("source_path"), root)
        notes = _notes(title=title, source_path=source_path)
        redraw = RedrawMetadata(title=str(title)) if title else None

        if csv_path is not None and not (root / csv_path).exists():
            missing_csv_paths.add(csv_path)
        if raw_csv_path is not None and not (root / raw_csv_path).exists():
            missing_csv_paths.add(raw_csv_path)

        for plot_path in plot_paths:
            if not (root / plot_path).exists():
                missing_plot_paths.add(plot_path)
            imported_records.append(
                ManifestRecord(
                    plot_path=plot_path,
                    raw_csv_path=raw_csv_path,
                    plot_csv_path=csv_path,
                    redraw=redraw,
                    notes=notes,
                )
            )

    manifest_path = root / ".mplgallery" / "manifest.yaml"
    if not dry_run:
        manifest = load_manifest(root)
        for record in imported_records:
            manifest.upsert_record(record)
        manifest_path = save_manifest(root, manifest)

    return ManifestImportResult(
        records_imported=len(imported_records),
        manifest_path=manifest_path if not dry_run else None,
        missing_plot_paths=sorted(missing_plot_paths, key=lambda path: path.as_posix()),
        missing_csv_paths=sorted(missing_csv_paths, key=lambda path: path.as_posix()),
        dry_run=dry_run,
    )


def _plot_paths_from_item(item: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for key in ("output_path", "plot_path", "png_path", "svg_path"):
        value = item.get(key)
        if not value:
            continue
        path = _relative_path(value)
        if path not in paths:
            paths.append(path)
    return paths


def _optional_relative_path(value: Any, root: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value).replace("\\", "/"))
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root)
        except ValueError:
            return path
    return path


def _relative_path(value: Any) -> Path:
    return Path(str(value).replace("\\", "/"))


def _notes(*, title: Any, source_path: Path | None) -> str | None:
    lines: list[str] = []
    if title:
        lines.append(f"title: {title}")
    if source_path is not None:
        lines.append(f"source: {source_path.as_posix()}")
    return "\n".join(lines) if lines else None
