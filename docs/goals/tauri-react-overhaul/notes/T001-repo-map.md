# T001 Repo Map

## Runtime boundary

- `pyproject.toml`
  - Current app runtime depends on `streamlit`, `matplotlib`, `pandas`, and Python packaging entrypoints.
  - Desktop packaging still layers `pywebview` and `pyinstaller` on top of the Python app instead of replacing it.
- `src/mplgallery/cli.py`
  - `serve`, `run`, and `desktop` all flow through Streamlit app launch behavior.
  - The current CLI surface is therefore operationally tied to Streamlit.
- `src/mplgallery/desktop.py`
  - The Windows desktop app starts a local Streamlit server and embeds its URL in a `pywebview` window.
  - The current installed app is a wrapper around a local web app, not a native frontend runtime.

## Packaging and update boundary

- `src/mplgallery/updater.py`
  - Update discovery is already release-based and Windows-oriented.
  - The install path expects a packaged asset bundle containing `mplgallery-desktop.exe` plus installer helpers.
  - The update concept is reusable, but the asset naming and install flow will need to be migrated for a Tauri package.
- `README.md`
  - User-facing docs still describe MPLGallery as a local Windows and Python app with plot editing, YAML editing, and Streamlit-based execution paths.
  - The README confirms which current behaviors are marketed product features versus implementation details that can be retired.

## Reusable product surfaces

- `src/mplgallery/core/scanner.py`
  - `scan_project()` already performs the core local-first recursive scan over `.csv`, `.png`, and `.svg`.
  - Ignore rules and file metadata extraction are strong candidates for the Tauri backend.
- `src/mplgallery/core/studio.py`
  - The studio index owns the current classification layer between CSV roots, plot sets, records, reference images, and image-library mode.
  - The classification logic is product-relevant even though parts of the file also support drafting and Matplotlib editing.
- `src/mplgallery/core/models.py`
  - `DiscoveredFile`, `ScanResult`, `DatasetRecord`, `PlotSetRecord`, `PlotRecord`, and `CSVStudioIndex` capture concepts the new app will still need.
  - Those types provide a concrete starting point for the later Tauri command/data model task.
- `src/mplgallery/ui/frontend/src/App.tsx`
  - The frontend already contains the gallery shell, folder/files pane behavior, selection model, pictures mode, layout controls, update affordances, and card rendering.
  - The React UI is reusable, but it is currently coupled to the Streamlit bridge.
- `src/mplgallery/ui/frontend/src/types.ts`
  - The existing payload and record types provide a direct inventory of the current frontend contract.

## Streamlit- or editing-specific systems to retire later

- `src/mplgallery/ui/component.py`
  - This file is the Streamlit bridge and event hub.
  - Product-neutral events like root changes, refresh, browse mode, and update install are reusable concepts.
  - Editing-specific events like `save_redraw_metadata`, `save_yaml_attachment`, `draft_dataset`, and rerender flows are specific to the old plot-editing product and should not survive the migration target.
- `src/mplgallery/ui/frontend/src/App.tsx`
  - The app imports `Streamlit` directly and drives the UI from a Python-sent payload.
  - Card tabs and state still carry YAML editing, redraw metadata, and draft-generation assumptions.
- `src/mplgallery/core/models.py`
  - `RedrawMetadata`, subplot metadata, recipe/cache metadata, and series styling are tied to Matplotlib redraw/editing rather than browsing.
- `src/mplgallery/core/studio.py`
  - Draft dataset generation and Matplotlib-backed redraw behaviors are outside the approved new scope.

## Current verification surfaces

- Goal board validation:
  - `node C:\Users\Tanner\.codex\skills\goalbuddy\scripts\check-goal-state.mjs docs\goals\tauri-react-overhaul\state.yaml`
- Existing repo validation paths referenced by the board:
  - `npm --prefix src/mplgallery/ui/frontend test`
  - `npm --prefix src/mplgallery/ui/frontend run build`
  - `uv run pytest`
  - `uv run ruff check .`

## Candidate migration slices and risks for Judge review

1. First safe slice should be side-by-side Tauri scaffolding with mock/static scan data, leaving the Streamlit app intact.
2. The Tauri backend should adopt local scanning/classification before any attempt to remove the Streamlit payload bridge.
3. Windows packaging and updater migration is a distinct late slice because the current update flow hardcodes Python-era asset assumptions.
4. The main scope risk is allowing YAML editing, Matplotlib redraw, or draft-generation behavior to leak into the new Tauri contract.
5. The main migration safety rule remains: do not remove Streamlit/pywebview until the Tauri app reaches verified browsing parity for CSV, PNG, and SVG workflows.
