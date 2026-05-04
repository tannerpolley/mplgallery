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
- DVC is the regeneration/dependency-tracking layer.
- MLflow is the run/artifact/history layer.
- v1 assumes one CSV per plot.
- Edited recipe-enabled plots overwrite originals by default.
- Before overwriting, always create a backup.
- Static gallery mode must be read-only.
- True Matplotlib-level editing requires recipe metadata.

## Engineering Rules

- Use a `src/` package layout.
- Keep business logic separate from Streamlit UI code.
- Prefer small modules with unit tests.
- Do not place project-scanning logic directly inside Streamlit callbacks.
- Do not make Streamlit responsible for DVC dependency logic.
- Do not make MLflow required for static gallery browsing of a target project.
- Do not modify target analysis projects except through explicit overwrite or
  regeneration actions.
- Do not overwrite any plot without first creating a backup.
- Avoid implementing all milestones in one pass.

## Commands

Run these before considering a task complete:

```bash
python -m pytest
python -m ruff check .
```

Use this for local development:

```bash
python -m pip install -e ".[dev]"
mplgallery serve examples/sample_project
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
