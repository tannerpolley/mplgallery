from __future__ import annotations

from pathlib import Path

from mplgallery.core.associations import build_plot_records
from mplgallery.core.manifest import ProjectManifest
from mplgallery.core.models import AssociationConfidence
from mplgallery.core.scanner import scan_project


def touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def records_for(root: Path):
    return build_plot_records(scan_project(root))


def test_same_directory_same_stem_matches_with_high_confidence(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "alpha.png")
    touch(tmp_path / "plots" / "alpha.csv", "x,y\n0,1\n")

    [record] = records_for(tmp_path)

    assert record.csv is not None
    assert record.csv.relative_path.as_posix() == "plots/alpha.csv"
    assert record.association_confidence is AssociationConfidence.HIGH
    assert record.association_reason == "same directory and same stem"


def test_sibling_data_and_plots_same_stem_matches_with_high_confidence(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "alpha.png")
    touch(tmp_path / "data" / "alpha.csv", "x,y\n0,1\n")

    [record] = records_for(tmp_path)

    assert record.csv is not None
    assert record.csv.relative_path.as_posix() == "data/alpha.csv"
    assert record.association_confidence is AssociationConfidence.HIGH
    assert record.association_reason == "sibling data/plots directories and same stem"


def test_manifest_override_matches_with_exact_confidence(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "alpha.png")
    touch(tmp_path / "data" / "manual.csv", "x,y\n0,1\n")
    touch(tmp_path / "data" / "alpha.csv", "x,y\n1,2\n")
    scan = scan_project(tmp_path)
    manifest = ProjectManifest.from_mapping(
        {
            "records": [
                {
                    "plot_path": "plots/alpha.png",
                    "csv_path": "data/manual.csv",
                    "redraw": {
                        "kind": "line",
                        "x": "x",
                        "y": ["y"],
                    },
                }
            ]
        }
    )

    [record] = build_plot_records(scan, manifest=manifest)

    assert record.csv is not None
    assert record.csv.relative_path.as_posix() == "data/manual.csv"
    assert record.association_confidence is AssociationConfidence.EXACT
    assert record.association_reason == "manifest override"
    assert record.redraw is not None
    assert record.redraw.kind == "line"


def test_ambiguous_same_score_candidates_are_left_unmatched(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "alpha.png")
    touch(tmp_path / "data" / "alpha.csv", "x,y\n0,1\n")
    touch(tmp_path / "results" / "alpha.csv", "x,y\n1,2\n")

    [record] = records_for(tmp_path)

    assert record.csv is None
    assert record.association_confidence is AssociationConfidence.NONE
    assert record.association_reason == "ambiguous candidates"


def test_missing_csv_is_left_unmatched(tmp_path: Path) -> None:
    touch(tmp_path / "plots" / "alpha.svg")

    [record] = records_for(tmp_path)

    assert record.csv is None
    assert record.association_confidence is AssociationConfidence.NONE
    assert record.association_reason == "no csv candidates"
