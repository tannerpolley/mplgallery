# AGENTS.md

## Project Goal

Build `mplgallery`, an installable Python package that provides a local
Streamlit UI for discovering CSV analysis tables, drafting editable Matplotlib
plots, browsing cached previews, and managing plot recipes under colocated
`.mplgallery/` folders.

The primary personal project layout is:

```text
analysis_name/
  scripts/
  data/
    input/
    raw/
    processed/
  out/
    plots/
    reports/
  config/
```

## Product Assumptions

- The package is local-first.
- Future team/shared-server support should remain possible.
- Streamlit is the UI layer.
- pandas is used for CSV loading, previewing, validation, and summary statistics.
- Matplotlib is the canonical rendering engine.
- MPLGallery is only for CSV plotting, plot appearance, and reference artifact browsing; it must not
  tune, fit, optimize, or alter scientific/model computations.
- DVC is the regeneration/dependency-tracking layer.
- MLflow is the run/artifact/history layer.
- Full-feature v1 expects a plot-ready CSV per plot, with an optional raw/model
  CSV tracked as provenance only.
- Default v1 behavior is CSV-first. PNG/SVG artifact discovery is opt-in
  reference/import mode.
- Default CSV roots are folders named `data`, `out`, `outputs`, `result`, or
  `results`, plus explicitly targeted folders.
- MPLGallery-owned files for a CSV root live under that root's `.mplgallery/`
  folder: `manifest.yaml`, `recipes/`, `scripts/`, `plot_ready/`, and `cache/`.
- `out/plots` is the expected location for generated PNG/SVG reference artifacts,
  but those artifacts remain opt-in imports rather than default scan results.
- Legacy `csv_path` may remain as a compatibility alias for `plot_csv_path`.
- Live browsing and cached redraws must not overwrite generated plot artifacts.
- Live metadata edits persist to `.mplgallery/manifest.yaml`, not to CSV files.
- Any explicit future overwrite action must create a backup first.
- `.mplgallery/cache` is the default per-CSV-root cache for redraw images and
  fingerprints.
- Static gallery mode must be read-only.
- True Matplotlib-level editing requires recipe metadata.

## Engineering Rules

- Use `uv` as the primary Python package and environment manager for local
  development.
- Use a `src/` package layout.
- Keep business logic separate from Streamlit UI code.
- Prefer small modules with unit tests.
- Do not place project-scanning logic directly inside Streamlit callbacks.
- Do not make Streamlit responsible for DVC dependency logic.
- Do not make MLflow required for static gallery browsing of a target project.
- Do not modify target analysis projects except through explicit overwrite or
  regeneration actions.
- Do not overwrite any plot without first creating a backup.
- Do not mutate source CSVs; use `.mplgallery/plot_ready` CSVs as render
  sources when MPLGallery needs a sampled or derived table.
- Do not add model tuning, fitting, parameter optimization, or data-generation
  controls to the UI.
- Keep the first user-facing UI closer to a file explorer than an analytics
  dashboard.
- Avoid implementing all milestones in one pass.

## Commands

Run these before considering a task complete:

```bash
uv run pytest
uv run ruff check .
```

Use this for local development:

```bash
uv sync --dev
uv run mplgallery serve examples
```
