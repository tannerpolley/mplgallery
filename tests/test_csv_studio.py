from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from mplgallery.core.manifest import update_manifest_redraw
from mplgallery.core.models import SeriesStyle
from mplgallery.core.renderer import render_cached_plot
from mplgallery.core.studio import (
    CSV_ROOT_NAMES,
    build_csv_studio_index,
    draft_csv_root,
    find_csv_roots,
    import_artifact_references,
    init_csv_root,
)
from mplgallery.ui.app import _load_index
from mplgallery.ui.component import build_component_payload


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_csv_root_discovery_prefers_named_output_folders_and_ignores_noise(tmp_path: Path) -> None:
    write(tmp_path / "data" / "reference_like.csv", "time,value\n0,1\n1,2\n")
    write(tmp_path / "analyses" / "material_fit" / "data" / "input" / "feed.csv", "time,value\n0,3\n")
    write(tmp_path / "analyses" / "material_fit" / "data" / "raw" / "raw_results.csv", "time,value\n0,4\n")
    write(
        tmp_path / "analyses" / "material_fit" / "data" / "processed" / "processed_results.csv",
        "time,value\n0,5\n",
    )
    write(
        tmp_path / "analyses" / "material_fit" / "results" / "final" / "tables" / "summary.csv",
        "category,count\na,3\n",
    )
    write(
        tmp_path / "analyses" / "material_fit" / "results" / "runs" / "diagnostic.csv",
        "x,y\n1,2\n",
    )
    write(tmp_path / "out" / "plots" / "legacy.svg", "<svg></svg>")
    write(tmp_path / "out" / "reports" / "table.csv", "x,y\n1,2\n")
    write(tmp_path / "docs" / "_build" / "html" / "_static" / "icon.csv", "x,y\n1,2\n")
    write(tmp_path / "tests" / "plots" / "out" / "test_fixture.csv", "x,y\n1,2\n")
    write(tmp_path / "build" / "out" / "generated_noise.csv", "x,y\n1,2\n")

    roots = find_csv_roots(tmp_path)

    assert CSV_ROOT_NAMES == {"data"}
    assert [root.relative_path.as_posix() for root in roots] == [
        "analyses/material_fit/data",
        "analyses/material_fit/results/final/tables",
        "data",
    ]
    assert [dataset.relative_path.as_posix() for dataset in roots[0].datasets] == [
        "analyses/material_fit/data/input/feed.csv",
        "analyses/material_fit/data/processed/processed_results.csv",
        "analyses/material_fit/data/raw/raw_results.csv",
    ]
    assert [dataset.relative_path.as_posix() for dataset in roots[1].datasets] == [
        "analyses/material_fit/results/final/tables/summary.csv"
    ]


def test_architecture_result_figures_are_default_references_without_broad_artifact_scan(
    tmp_path: Path,
) -> None:
    write(tmp_path / "analyses" / "study" / "data" / "processed" / "table.csv", "x,y\n0,1\n")
    write(tmp_path / "analyses" / "study" / "results" / "final" / "figures" / "figure.svg", "<svg></svg>")
    write(tmp_path / "analyses" / "study" / "results" / "final" / "figures" / "figure.png", "not-real")
    write(tmp_path / "analyses" / "study" / "results" / "runs" / "scratch.svg", "<svg></svg>")
    write(tmp_path / "docs" / "_build" / "html" / "_static" / "icon.svg", "<svg></svg>")

    index = build_csv_studio_index(tmp_path, ensure_drafts=False)

    assert [record.image.relative_path.as_posix() for record in index.imported_artifacts] == [
        "analyses/study/results/final/figures/figure.png",
        "analyses/study/results/final/figures/figure.svg",
    ]
    assert all(record.association_reason == "Architecture result figure" for record in index.imported_artifacts)
    assert not any("results/runs" in record.image.relative_path.as_posix() for record in index.records)
    assert not any("docs/_build" in record.image.relative_path.as_posix() for record in index.records)


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
    assert record.image.relative_path.as_posix() == "results/final/figures/mplgallery/experiment.svg"
    assert record.owned_by_mplgallery is True
    assert record.visibility_role == "draft"
    assert record.source_dataset_id == "data__experiment"
    assert record.cache and record.cache.cache_path and record.cache.cache_path.exists()
    assert record.cache.cache_path.suffix == ".svg"
    assert ".mplgallery/cache" not in record.cache.cache_path.as_posix()
    assert record.plot_csv.path.exists()
    assert record.recipe_path and record.recipe_path.exists()
    assert record.metadata_files
    assert any(path.name.startswith("render_") and path.suffix == ".py" for path in record.metadata_files)
    assert source.stat().st_mtime_ns == before_mtime
    assert sha256(source) == before_hash

    recipe = yaml.safe_load(record.recipe_path.read_text(encoding="utf-8"))
    assert recipe["source_csv_path"] == "experiment.csv"
    assert recipe["plot_ready_path"].startswith(".mplgallery/plot_ready/")
    assert recipe["cache_path"] == "../results/final/figures/mplgallery/experiment.svg"
    assert recipe["draft_engine"] == "pandas"
    assert recipe["prep"]["selected_columns"] == ["time", "signal", "fit"]
    assert recipe["redraw"]["x"] == "time"
    assert recipe["redraw"]["y"] == ["signal", "fit"]
    script_path = next(path for path in record.metadata_files if path.suffix == ".py")
    script_text = script_path.read_text(encoding="utf-8")
    assert "frame.plot(" in script_text
    manifest = yaml.safe_load((csv_root / ".mplgallery" / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["records"][0]["plot_path"] == "../results/final/figures/mplgallery/experiment.svg"


def test_draft_generation_for_analysis_data_writes_to_analysis_result_figures(tmp_path: Path) -> None:
    csv_root = tmp_path / "analyses" / "study" / "data"
    write(csv_root / "processed" / "response.csv", "time,response\n0,1\n1,2\n")

    result = draft_csv_root(csv_root, project_root=tmp_path)

    assert [record.image.relative_path.as_posix() for record in result.records] == [
        "analyses/study/results/final/figures/mplgallery/processed_response.svg"
    ]
    assert not any(".mplgallery/cache" in record.image.relative_path.as_posix() for record in result.records)


def test_csv_studio_index_links_existing_drafts_without_exposing_cache(tmp_path: Path) -> None:
    csv_root = tmp_path / "analyses" / "study" / "data"
    write(csv_root / "processed" / "response.csv", "time,response\n0,1\n1,2\n")

    cold_index = build_csv_studio_index(tmp_path, ensure_drafts=False)
    assert cold_index.records == []
    assert cold_index.datasets[0].associated_plot_id is None

    draft_csv_root(csv_root, project_root=tmp_path)
    warm_index = build_csv_studio_index(tmp_path, ensure_drafts=False)

    assert [record.image.relative_path.as_posix() for record in warm_index.records] == [
        "analyses/study/results/final/figures/mplgallery/processed_response.svg"
    ]
    assert warm_index.records[0].owned_by_mplgallery is True
    assert warm_index.records[0].visibility_role == "draft"
    assert warm_index.datasets[0].associated_plot_id == warm_index.records[0].plot_id
    assert not any(".mplgallery/cache" in record.image.relative_path.as_posix() for record in warm_index.records)


def test_streamlit_index_load_does_not_auto_generate_drafts(tmp_path: Path) -> None:
    csv_root = tmp_path / "data"
    write(csv_root / "response.csv", "time,response\n0,1\n1,2\n")

    index = _load_index(tmp_path)

    assert index.records == []
    assert index.datasets[0].draft_status == "not_initialized"
    assert not (csv_root / ".mplgallery").exists()


def test_component_payload_includes_dataset_and_owned_plot_metadata(tmp_path: Path) -> None:
    csv_root = tmp_path / "data"
    write(csv_root / "response.csv", "time,response\n0,1\n1,2\n")
    index = draft_csv_root(csv_root, project_root=tmp_path)

    payload = build_component_payload(
        project_root=tmp_path,
        records=index.records,
        datasets=index.datasets,
        selected_plot_id=None,
        errors={},
    )

    assert payload["selectedPlotId"] is None
    assert payload["datasets"][0]["id"] == "data__response"
    assert payload["datasets"][0]["associatedPlotId"] == index.records[0].plot_id
    assert payload["records"][0]["sourceDatasetId"] == "data__response"
    assert payload["records"][0]["ownedByMplgallery"] is True
    assert payload["records"][0]["visibilityRole"] == "draft"


def test_generated_pandas_render_script_can_render_cache_from_plot_ready_csv(tmp_path: Path) -> None:
    csv_root = tmp_path / "data"
    write(csv_root / "experiment.csv", "time,signal,fit\n0,1.0,0.8\n1,2.0,1.9\n")

    result = draft_csv_root(csv_root, project_root=tmp_path)
    record = result.records[0]
    assert record.cache is not None
    assert record.cache.cache_path is not None
    script_path = next(path for path in record.metadata_files if path.suffix == ".py")
    record.cache.cache_path.unlink()

    subprocess.run([sys.executable, str(script_path)], cwd=csv_root, check=True)

    assert record.cache.cache_path.exists()


def test_pandas_draft_preserves_matplotlib_metadata_edits_without_changing_source_csv(
    tmp_path: Path,
) -> None:
    csv_root = tmp_path / "data"
    source = write(csv_root / "experiment.csv", "time,signal,fit\n0,1.0,0.8\n1,2.0,1.9\n2,3.0,2.8\n")
    before_hash = sha256(source)
    result = draft_csv_root(csv_root, project_root=tmp_path)
    record = result.records[0]
    assert record.redraw is not None
    assert record.plot_csv is not None

    edited_redraw = record.redraw.model_copy(
        update={
            "title": "Edited title",
            "xlabel": "Elapsed",
            "ylabel": "Response",
            "xlim": (0.0, 2.0),
            "ylim": (0.0, 3.5),
            "series": [
                SeriesStyle(
                    y="signal",
                    label="Edited signal",
                    color="#d62728",
                    linestyle="--",
                    marker="s",
                    linewidth=2.5,
                ),
                record.redraw.series[1],
            ],
        }
    )

    update_manifest_redraw(csv_root, Path(os.path.relpath(record.image.path, csv_root)), edited_redraw)
    rerendered = render_cached_plot(tmp_path, record.model_copy(update={"redraw": edited_redraw}))

    assert rerendered.cache is not None
    assert rerendered.cache.cache_path is not None
    assert rerendered.cache.cache_path.exists()
    assert sha256(source) == before_hash
    manifest = yaml.safe_load((csv_root / ".mplgallery" / "manifest.yaml").read_text(encoding="utf-8"))
    manifest_redraw = manifest["records"][0]["redraw"]
    assert manifest_redraw["title"] == "Edited title"
    assert manifest_redraw["series"][0]["color"] == "#d62728"


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
