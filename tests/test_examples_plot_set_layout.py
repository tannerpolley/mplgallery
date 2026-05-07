from __future__ import annotations

from pathlib import Path

from mplgallery.core.plot_sets import discover_plot_sets, load_mpl_yaml


REPO_ROOT = Path(__file__).parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"


def _is_internal(path: Path) -> bool:
    parts = {part.lower() for part in path.relative_to(EXAMPLES_ROOT).parts}
    return ".mplgallery" in parts or "__pycache__" in parts


def test_examples_use_plot_set_result_folders() -> None:
    assert not [path for path in EXAMPLES_ROOT.rglob("plots") if path.is_dir()]
    assert not [path for path in EXAMPLES_ROOT.rglob("final") if path.is_dir()]

    public_csvs = [
        path
        for path in EXAMPLES_ROOT.rglob("*.csv")
        if path.is_file() and not _is_internal(path)
    ]
    public_figures = [
        path
        for suffix in ("*.png", "*.svg")
        for path in EXAMPLES_ROOT.rglob(suffix)
        if path.is_file() and not _is_internal(path)
    ]

    assert public_csvs
    assert public_figures
    for path in public_csvs + public_figures:
        relative_parts = path.relative_to(EXAMPLES_ROOT).parts
        assert "results" in relative_parts
        results_index = relative_parts.index("results")
        assert len(relative_parts) > results_index + 2
        plot_set_name = relative_parts[results_index + 1]
        assert path.parent.name == plot_set_name


def test_example_figures_have_sibling_data_and_mpl_yaml() -> None:
    public_figures = [
        path
        for suffix in ("*.png", "*.svg")
        for path in EXAMPLES_ROOT.rglob(suffix)
        if path.is_file() and not _is_internal(path)
    ]

    for figure in public_figures:
        sidecar = figure.with_suffix(".mpl.yaml")
        csv = figure.with_suffix(".csv")
        assert sidecar.exists(), figure
        assert csv.exists(), figure
        parsed = load_mpl_yaml(sidecar)
        assert parsed.redraw is not None
        assert figure.name in {path.name for path in parsed.figure_files}
        assert csv.name in {path.name for path in parsed.data_files}


def test_examples_are_discoverable_as_plot_sets() -> None:
    plot_sets = discover_plot_sets(EXAMPLES_ROOT)

    assert plot_sets
    assert all(plot_set.csv_files for plot_set in plot_sets)
    assert all(plot_set.figure_files for plot_set in plot_sets)
    assert all(plot_set.editable for plot_set in plot_sets)


def test_example_scripts_do_not_generate_legacy_plot_layouts() -> None:
    legacy_markers = ("data/processed", "data/plot_ready", "data/raw", "results/final", '"plots"', "'plots'")
    scripts = [path for path in EXAMPLES_ROOT.rglob("*.py") if not _is_internal(path)]

    for script in scripts:
        text = script.read_text(encoding="utf-8")
        assert not any(marker in text for marker in legacy_markers), script
