# MPLGallery Browser-First Handoff Plan

**Document date:** 2026-05-04  
**Purpose:** handoff plan for revising the master plan and then implementing the first real build step after a Codex restart.

> Status update, 2026-05-05: this browser-first plan is retained for history,
> but the active product direction is now CSV-first. MPLGallery defaults to
> discovering CSV roots such as `data/`, `out/`, and `results/`, drafting
> Matplotlib recipes/previews under each root's `.mplgallery/` folder, and only
> importing existing PNG/SVG files through explicit reference-artifact commands.

## Summary

Revise `docs/mplgallery_codex_bootstrap_master_plan.md` so v1 is an artifact browser first, not an editing workbench first. The prior handoff in `plot_gallery_package_ui_handoff.md` should become product guidance: fast local file-browser feel, output-tree sidebar, compact image grid, cached redraws from CSV changes, and minimal visible metadata by default.

Chosen defaults:

- Primary product shape: artifact browser.
- UI stack: Streamlit host plus custom HTML/JS component for the tree/grid.
- Live updates: redraw changed CSV-backed plots into cache, never overwrite originals by default.
- Redraw contract: simple documented CSV schema plus lightweight metadata.
- Sidebar default: output artifact path tree.
- Project input: arbitrary scan first, optional manifest improves behavior.
- DVC/MLflow: remain core dependencies, but support provenance/reproducibility rather than driving the first UI.
- Static `build`: after live `serve`.
- First implementation slice: scanner plus manifest.

## Master Plan Revision

Before implementation, update `docs/mplgallery_codex_bootstrap_master_plan.md`:

- Add a new `UI Baseline From Prior Handoff` section summarizing `plot_gallery_package_ui_handoff.md`.
- Encode the UI baseline explicitly: file-explorer sidebar, separate expand/select controls, multi-folder selection, search preserving tree state, compact responsive image grid, tile-size control, light dense layout.
- Change product vision language from Streamlit dashboard/workbench to local plot artifact browser with Streamlit-backed Python services.
- Revise the decisions table so `uv` is the primary package manager, Streamlit is the host layer, and a custom component is preferred for polished tree/grid UI.
- Make cached redraw the default live-update behavior.
- Make overwrite an explicit later recipe/render action only.
- Reorder milestones so early work is: scanner/index, manifest/cache model, live browser shell, custom tree/grid component, cached redraw, static build, then recipe editing/overwrite, DVC, and MLflow UI surfaces.
- Keep DVC and MLflow in dependencies, but clarify that static browsing and cached redraw must work when a target project has not initialized either tool.
- Add `.mplgallery/cache` as the default target-project cache for fingerprints and cached redraw images, with guidance that it should be untracked/ignored in target projects.

The master plan revision should be committed separately before scanner implementation.

## First Implementation Step

After the master plan is revised and committed, implement only the scanner plus manifest slice:

- Build recursive discovery for `.png`, `.svg`, and `.csv` files.
- Apply default ignore rules for directories such as `.git`, `.dvc`, `mlruns`, `.venv`, `venv`, `env`, `__pycache__`, `.ipynb_checkpoints`, `node_modules`, `dist`, and `build`.
- Add explicit models for discovered files, plot records, associations, manifest records, and cache metadata hooks.
- Support arbitrary project scans first.
- Add optional manifest fields for association overrides and redraw metadata.
- Implement `uv run mplgallery scan examples/sample_project` as a smoke path.
- Do not build the UI yet.
- Do not implement overwrite behavior yet.
- Do not implement DVC/MLflow behavior yet beyond preserving model fields/placeholders.

## Test Plan

Use `uv` only:

```bash
uv run pytest
uv run ruff check .
uv run mplgallery scan examples/sample_project
```

Add scanner tests for:

- ignored directories;
- PNG/SVG/CSV discovery;
- relative paths;
- arbitrary project roots.

Add manifest and association tests for:

- same-stem matches;
- output/data sibling matches;
- manifest override;
- ambiguous matches;
- missing CSV.

## Assumptions

- `plot_gallery_package_ui_handoff.md` is source material for the master plan and should be referenced from the plan or moved under `docs/` during the plan update commit.
- Existing bootstrap commits should remain intact.
- The next implementation session should first update and commit the master plan, then start the scanner plus manifest implementation in a separate commit.
