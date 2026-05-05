# AGENTS.md

## Project Goal

Build `mplgallery`, an installable Python package that provides a local
Streamlit UI for browsing, inspecting, editing, regenerating, and tracking
Matplotlib-generated PNG/SVG plots associated with CSV data files.

## Product Assumptions

- The package is local-first.
- Future team/shared-server support should remain possible.
- Streamlit is the UI layer.
- pandas is used for CSV loading, previewing, validation, and summary statistics.
- Matplotlib is the canonical rendering engine.
- MPLGallery is only for plot appearance and artifact browsing; it must not
  tune, fit, optimize, or alter scientific/model computations.
- DVC is the regeneration/dependency-tracking layer.
- MLflow is the run/artifact/history layer.
- Full-feature v1 expects a plot-ready CSV per plot, with an optional raw/model
  CSV tracked as provenance only.
- Legacy `csv_path` may remain as a compatibility alias for `plot_csv_path`.
- Live browsing and cached redraws must not overwrite generated plot artifacts.
- Live metadata edits persist to `.mplgallery/manifest.yaml`, not to CSV files.
- Any explicit future overwrite action must create a backup first.
- `.mplgallery/cache` is the default target-project cache for redraw images and
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
- Do not mutate raw CSVs; use `data/plot_ready` CSVs as render sources.
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
uv run mplgallery serve examples/sample_project
```

## First Milestone Scope

The first implementation should only include:

1. package scaffold;
2. CLI skeleton;
3. file scanner;
4. file/plot Pydantic models;
5. PNG/SVG/CSV association heuristics;
6. tests for scanner and association logic.

Do not implement recipe editing, DVC, MLflow, or full Streamlit UI until the
scanner/indexer is stable.
