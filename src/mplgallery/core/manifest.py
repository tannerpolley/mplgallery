"""Manifest loading and association override support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from mplgallery.core.models import ManifestRecord


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


def load_manifest(project_root: Path | str) -> ProjectManifest:
    root = Path(project_root)
    manifest_path = root / ".mplgallery" / "manifest.yaml"
    if not manifest_path.exists():
        return ProjectManifest()

    data = yaml.safe_load(manifest_path.read_text()) or {}
    return ProjectManifest.from_mapping(data)
