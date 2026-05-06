from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from mplgallery.core.studio import (
    CSV_ROOT_NAMES,
    build_csv_studio_index,
    draft_csv_root,
    find_csv_roots,
    import_artifact_references,
    init_csv_root,
)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_csv_root_discovery_prefers_named_output_folders_and_ignores_noise(tmp_path: Path) -> None:
    write(tmp_path / "data" / "model_results.csv", "time,value\n0,1\n1,2\n")
    write(tmp_path / "data" / "plot_ready" / "derived.csv", "time,value\n0,1\n1,2\n")
    write(tmp_path / "data" / "input" / "feed.csv", "time,value\n0,3\n")
    write(tmp_path / "data" / "raw" / "raw_results.csv", "time,value\n0,4\n")
    write(tmp_path / "data" / "processed" / "processed_results.csv", "time,value\n0,5\n")
    write(tmp_path / "results" / "summary.csv", "category,count\na,3\n")
    write(tmp_path / "out" / "plots" / "legacy.svg", "<svg></svg>")
    write(tmp_path / "out" / "reports" / "table.csv", "x,y\n1,2\n")
    write(tmp_path / "docs" / "_build" / "html" / "_static" / "icon.csv", "x,y\n1,2\n")
    write(tmp_path / "tests" / "plots" / "out" / "test_fixture.csv", "x,y\n1,2\n")
    write(tmp_path / "build" / "out" / "generated_noise.csv", "x,y\n1,2\n")

    roots = find_csv_roots(tmp_path)

    assert CSV_ROOT_NAMES >= {"data", "out", "outputs", "result", "results"}
    assert [root.relative_path.as_posix() for root in roots] == ["data", "out", "results"]
    assert [dataset.relative_path.as_posix() for dataset in roots[0].datasets] == [
        "data/input/feed.csv",
        "data/model_results.csv",
        "data/plot_ready/derived.csv",
        "data/processed/processed_results.csv",
        "data/raw/raw_results.csv",
    ]
    assert [dataset.relative_path.as_posix() for dataset in roots[1].datasets] == [
        "out/reports/table.csv"
    ]


def test_init_csv_root_creates_portable_mplgallery_workspace(tmp_path: Path) -> None:
    csv_root = tmp_path / "out"
    write(csv_root / "table.csv", "x,y\n0,1\n")

    workspace = init_csv_root(csv_root)

    assert workspace.root == csv_root.resolve()
    assert (csv_root / ".mplgallery" / "manifest.yaml").exists()
    for folder in ("recipes", "scripts", "plot_ready", "cache"):
        assert (csv_root / ".mplgallery" / folder).is_dir()


def test_draft_generation_writes_recipe_script_plot_ready_and_cache_without_touching_source(
    tmp_path: Path,
) -> None:
    csv_root = tmp_path / "data"
    source = write(csv_root / "experiment.csv", "time,signal,fit\n0,1.0,0.8\n1,2.0,1.9\n")
    before_hash = sha256(source)
    before_mtime = source.stat().st_mtime_ns

    result = draft_csv_root(csv_root, project_root=tmp_path)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.plot_csv is not None
    assert record.raw_csv is not None
    assert record.redraw is not None
    assert record.mode.value == "recipe"
    assert record.image.relative_path.as_posix().startswith("data/.mplgallery/cache/")
    assert record.cache and record.cache.cache_path and record.cache.cache_path.exists()
    assert record.cache.cache_path.suffix == ".svg"
    assert record.plot_csv.path.exists()
    assert record.recipe_path and record.recipe_path.exists()
    assert record.metadata_files
    assert any(path.name.startswith("render_") and path.suffix == ".py" for path in record.metadata_files)
    assert source.stat().st_mtime_ns == before_mtime
    assert sha256(source) == before_hash

    recipe = yaml.safe_load(record.recipe_path.read_text(encoding="utf-8"))
    assert recipe["source_csv_path"] == "experiment.csv"
    assert recipe["plot_ready_path"].startswith(".mplgallery/plot_ready/")
    assert recipe["redraw"]["x"] == "time"
    assert recipe["redraw"]["y"] == ["signal", "fit"]


def test_draft_generation_handles_categorical_numeric_and_no_numeric_csvs(tmp_path: Path) -> None:
    csv_root = tmp_path / "results"
    write(csv_root / "counts.csv", "category,count\na,4\nb,8\n")
    write(csv_root / "labels.csv", "name,group\na,left\nb,right\n")

    result = draft_csv_root(csv_root, project_root=tmp_path)

    assert len(result.datasets) == 2
    assert len(result.records) == 1
    assert result.records[0].redraw is not None
    assert result.records[0].redraw.kind == "bar"
    assert result.records[0].redraw.x == "category"
    statuses = {dataset.path.name: dataset.draft_status for dataset in result.datasets}
    assert statuses["labels.csv"] == "no_numeric_columns"


def test_large_csv_draft_samples_plot_ready_output(tmp_path: Path) -> None:
    csv_root = tmp_path / "out"
    rows = "\n".join(f"{index},{index * 2}" for index in range(6005))
    write(csv_root / "large.csv", f"x,y\n{rows}\n")

    result = draft_csv_root(csv_root, project_root=tmp_path, sample_rows=5000)

    assert len(result.records) == 1
    plot_ready = result.records[0].plot_csv
    assert plot_ready is not None
    assert len(plot_ready.path.read_text(encoding="utf-8").splitlines()) == 5001


def test_default_csv_studio_index_does_not_import_png_or_svg(tmp_path: Path) -> None:
    write(tmp_path / "data" / "table.csv", "x,y\n0,1\n")
    write(tmp_path / "data" / "legacy.png", "not-real-image")
    write(tmp_path / "data" / "legacy.svg", "<svg></svg>")

    index = build_csv_studio_index(tmp_path, ensure_drafts=False)

    assert len(index.csv_roots) == 1
    assert index.imported_artifacts == []
    assert all(record.image.suffix == ".svg" for record in index.records)


def test_artifact_import_is_opt_in_and_reference_only(tmp_path: Path) -> None:
    write(tmp_path / "data" / "table.csv", "x,y\n0,1\n")
    png = write(tmp_path / "data" / "legacy.png", "not-real-image")
    svg = write(tmp_path / "data" / "legacy.svg", "<svg></svg>")

    result = import_artifact_references(tmp_path / "data")

    assert result.imported_count == 2
    assert sorted(path.name for path in result.imported_paths) == [png.name, svg.name]
    manifest = yaml.safe_load((tmp_path / "data" / ".mplgallery" / "manifest.yaml").read_text())
    assert {record["plot_path"] for record in manifest["records"]} == {"legacy.png", "legacy.svg"}
    assert all(record["notes"] == "Imported reference artifact" for record in manifest["records"])
    assert all("redraw" not in record for record in manifest["records"])


def test_analysis_layout_imports_out_plots_references_explicitly(tmp_path: Path) -> None:
    write(tmp_path / "scripts" / "generate.py", "print('not executed')\n")
    write(tmp_path / "data" / "processed" / "table.csv", "x,y\n0,1\n")
    write(tmp_path / "out" / "plots" / "figure.svg", "<svg></svg>")
    write(tmp_path / "out" / "reports" / "summary.md", "# report\n")

    default_index = build_csv_studio_index(tmp_path, ensure_drafts=False)
    assert [root.relative_path.as_posix() for root in default_index.csv_roots] == ["data"]
    assert default_index.imported_artifacts == []

    import_result = import_artifact_references(tmp_path / "out" / "plots")
    assert import_result.imported_count == 1

    artifact_index = build_csv_studio_index(tmp_path, include_artifacts=True)
    assert any(
        record.image.relative_path.as_posix() == "out/plots/figure.svg"
        for record in artifact_index.imported_artifacts
    )


def test_scan_cli_json_reports_csv_studio_roots_without_default_artifact_records(tmp_path: Path) -> None:
    write(tmp_path / "data" / "table.csv", "x,y\n0,1\n")
    write(tmp_path / "data" / "legacy.svg", "<svg></svg>")

    completed = subprocess.run(
        ["uv", "run", "mplgallery", "scan", str(tmp_path), "--json"],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["mode"] == "csv-studio"
    assert [root["relative_path"] for root in payload["csv_roots"]] == ["data"]
    assert payload["plots_discovered"] == 0
    assert payload["artifact_records"] == 0
