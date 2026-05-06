# MPLGallery: Bootstrap + Master Plan + Codex Handoff

**Document date:** 2026-05-04  
**Active pivot note:** As of 2026-05-05, the active v1 direction is CSV Plot
Studio first, not artifact browser first. The package should discover CSV
tables in analysis output folders such as `data`, `out`, `outputs`, `result`,
and `results`; create editable draft Matplotlib recipes, generated scripts,
plot-ready CSVs, and cached previews under the CSV root's `.mplgallery/`
folder; and treat existing PNG/SVG files as explicit reference imports only.
The assumed personal project layout is `analysis_name/scripts`,
`analysis_name/data/input`, `analysis_name/data/raw`,
`analysis_name/data/processed`, `analysis_name/out/plots`,
`analysis_name/out/reports`, and optional `analysis_name/config`.
**Working GitHub repository name:** `mplgallery`  
**Python distribution name:** `mplgallery`  
**Python import name:** `mplgallery`  
**CLI command:** `mplgallery`  
**Primary implementation agent:** Codex working from a local empty folder, cloning the GitHub repository into that folder, then scaffolding and building the package.

---

## 0. Purpose of This Document

This document is intended to be handed to a Codex coding agent. The agent should use it to create a new installable Python package named `mplgallery`.

The package should provide a local frontend for browsing and managing Matplotlib-generated plot files across many unrelated analysis projects.

The user will create the GitHub repository and an empty local folder. Codex should handle the rest:

1. clone the GitHub repository into the empty local folder;
2. create the initial Python package scaffold;
3. create project instructions and documentation;
4. implement the package in milestone-sized vertical slices;
5. run tests and linting at each milestone;
6. commit changes incrementally.

This document should be treated as the product spec and engineering handoff.

---

## 1. User Decisions Already Made

These are fixed requirements for v1 unless explicitly changed later.

| Decision | Requirement |
|---|---|
| Product shape | v1 is a fast local plot artifact browser first, not an editing workbench first. |
| Package workflow | `uv` is the primary package and environment manager for development. |
| Plot overwrite behavior | Live browsing and cached redraws must not overwrite generated plot artifacts by default. Overwrite is a later explicit recipe/render action. |
| Backup behavior | Any future overwrite action must create a backup copy first. |
| Recipe metadata | Lightweight recipe metadata is acceptable and expected for reliable redraw/edit flows. |
| Live update behavior | Changed CSV-backed plots should redraw into `.mplgallery/cache` and display the cached image. |
| Future collaboration | v1 is local-first, but the architecture should allow future team/shared-server mode. |
| DVC/MLflow | DVC and MLflow remain first-class dependencies for provenance/reproducibility, but static browsing and cached redraws must work without an initialized DVC/MLflow target project. |
| CSV/plot relation | Full-feature v1 expects one plot-ready CSV per plot, with an optional raw/model CSV tracked as provenance. Legacy `csv_path` remains a temporary compatibility alias for `plot_csv_path`. |
| Plot backend | Matplotlib is the canonical plotting engine. |
| UI backend | Streamlit is the Python host layer; a custom HTML/JS component is preferred for the polished tree/grid browser UI. |
| Data handling | pandas should be used for CSV loading, previewing, validation, and summary statistics. |
| Model scope | MPLGallery is for plot appearance only. It must not tune, fit, optimize, or alter scientific/model computations. |
| Plot formats | Support both SVG and PNG. Prefer SVG for clean vector line plots; keep PNG for dense/raster plots, fast previews, compatibility, and cases where SVG becomes too large or inconsistent. |

---

## 2. Product Vision

Build an installable Python package that can be installed from GitHub and used inside any analysis project:

```bash
pip install git+https://github.com/<owner>/mplgallery.git
mplgallery serve /path/to/analysis/project
```

The package should launch a local plot artifact browser backed by Streamlit/Python services. It should scan the selected project root, find plots and CSV files, and present them through a dense file-explorer-style UI with a folder tree and responsive image grid.

The intended user produces analysis plots from Python scripts, usually with Matplotlib, where source data is stored as CSV and output plots are saved as PNG or SVG. The goal is to avoid manually hunting through folders for plots and data files.

The software should first feel like a fast local file browser for Matplotlib artifacts. Recipe editing, overwrite flows, DVC controls, and MLflow history should build on that foundation without making the default browsing experience feel like a heavy analytics dashboard.

### 2.1 Analysis Group Workflow Convention

Full-feature MPLGallery projects should keep raw model outputs, plot-ready data, plotting metadata, and rendering scripts separated:

```text
analysis_group/
  data/raw/                 # model/function outputs, immutable by MPLGallery
  data/plot_ready/          # plotting/prep outputs consumed by MPLGallery
  plots/                    # generated PNG/SVG artifacts
  scripts/generate_data.py  # computes raw CSVs only
  scripts/render_plots.py   # reads raw CSVs, writes plot-ready CSVs, reads YAML, renders figures
  .mplgallery/manifest.yaml # associations and Matplotlib metadata
  .mplgallery/cache/        # untracked cached previews
```

MPLGallery reads `plot_csv_path` with pandas for live cached previews and metadata editing. `raw_csv_path` is provenance-only and must not be mutated by MPLGallery. Live editing writes `.mplgallery/manifest.yaml` plus cached preview images under `.mplgallery/cache`; it must not overwrite generated plot artifacts unless a later explicit overwrite/build action is added.

The UI should expose only plot-look controls: titles, labels, limits, scales, grid, figure size, DPI, colors, markers, line styles, and similar Matplotlib presentation metadata. It should not expose controls for model parameters, fitting, optimization, data generation, or scientific computation.

### 2.2 UI Baseline From Prior Handoff

The prior `plot_gallery_package_ui_handoff.md` is the browsing baseline for v1. Preserve these behaviors:

- file-explorer-style left sidebar;
- expandable/collapsible folder rows;
- separate disclosure controls from folder selection checkboxes;
- folder checkboxes select every plot in that folder and all descendants;
- multiple folders can be selected at once;
- search filters visible plots without destroying selected folder state;
- output-tree browsing by default, with source-tree mode later;
- responsive image grid as the main content;
- compact, scannable cards where plot images dominate;
- tile-size control;
- light theme, dense layout, simple borders, and minimal decoration.

Avoid UI regressions:

- do not make users browse one plot at a time;
- do not use a dropdown as the primary plot selector;
- do not show long paths or raw metadata on every card by default;
- do not let controls consume more vertical space than the plot images;
- do not make the sidebar feel like a form instead of a file explorer.

---

## 3. Bootstrap Workflow for Codex

### 3.1 Human Setup

The human user will do only this:

1. Create a GitHub repository, preferably named `mplgallery`.
2. Copy the repository clone URL.
3. Create an empty local folder where the repo should live.
4. Open that empty folder in the Codex app.
5. Attach this Markdown document to the Codex conversation if the app supports attachments, or paste the document contents into the first message after the bootstrap prompt.
6. Give Codex the bootstrap prompt below.

Recommended local folder:

```text
~/code/mplgallery
```

or on Windows:

```text
C:\Users\<name>\code\mplgallery
```

The bootstrap prompt assumes Codex can see this document. Codex should save this document into the cloned repository at:

```text
docs/mplgallery_codex_bootstrap_master_plan.md
```

The local folder should be empty so Codex can run:

```bash
git clone <REPO_URL> .
```

This ensures the currently opened Codex project folder becomes the Git repository root after cloning.

### 3.2 Fallback Rules for Codex

If `git clone <REPO_URL> .` fails because the folder is not empty:

1. inspect the folder with `ls -la` or the platform equivalent;
2. if the folder already contains a clone of the target repo, continue;
3. if the folder contains unrelated files, create a subfolder named `mplgallery`, clone into that subfolder, and state clearly that the user should reopen the cloned repo folder in Codex after bootstrap;
4. do not delete user files.

If Git authentication fails:

1. report the exact Git command that failed;
2. explain whether the URL appears to be SSH or HTTPS;
3. do not invent credentials;
4. stop before scaffolding outside a cloned repository.

---

## 4. First Prompt for Codex

Copy this prompt into Codex after opening the empty local folder.

````md
You are bootstrapping a new Python package project from an empty local folder.

GitHub repo URL:

<PASTE_GITHUB_REPO_URL_HERE>

Goal:
Create the initial `mplgallery` package repository according to the product spec in `docs/mplgallery_codex_bootstrap_master_plan.md` once the file exists.

First, clone the GitHub repo into the current empty folder using:

```bash
git clone <PASTE_GITHUB_REPO_URL_HERE> .
```

Then create the initial scaffold and documentation for the package.

Required initial files:

- `README.md`
- `AGENTS.md`
- `pyproject.toml`
- `.gitignore`
- `docs/mplgallery_codex_bootstrap_master_plan.md`
- `src/mplgallery/__init__.py`
- `src/mplgallery/cli.py`
- `src/mplgallery/core/__init__.py`
- `src/mplgallery/core/models.py`
- `src/mplgallery/core/scanner.py`
- `src/mplgallery/core/associations.py`
- `src/mplgallery/ui/__init__.py`
- `src/mplgallery/ui/app.py`
- `src/mplgallery/integrations/__init__.py`
- `src/mplgallery/integrations/dvc.py`
- `src/mplgallery/integrations/mlflow.py`
- `tests/test_scanner.py`
- `tests/test_associations.py`
- `examples/sample_project/`

For this first pass, implement only Milestone 0 and Milestone 1:

Milestone 0:
- Clone repo into current folder.
- Create package scaffold.
- Create `pyproject.toml` with package metadata, dependencies, dev dependencies, and `mplgallery` CLI entry point.
- Create `AGENTS.md` with durable coding-agent instructions.
- Create README with minimal usage examples.
- Copy this master plan into `docs/mplgallery_codex_bootstrap_master_plan.md`.

Milestone 1:
- Implement recursive project scanning for `.png`, `.svg`, and `.csv` files.
- Implement Pydantic models for discovered files and plot records.
- Implement basic one-CSV-per-plot association heuristics.
- Add unit tests for scanner and association behavior.

Do not implement the full Streamlit UI, DVC integration, MLflow integration, recipe rendering, or plot editing yet. Create placeholders where useful, but keep the first implementation small and testable.

After implementing, use `uv` as the primary Python package and environment
manager. Run:

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

If a command fails, fix the cause when it is reasonable. If a dependency or environment issue prevents completion, document the exact failure.

Finally:
- summarize changed files;
- summarize tests run;
- commit the initial scaffold and Milestone 1 implementation.
````
---

## 5. Repository Shape to Create

Codex should create this structure first:

```text
mplgallery/
  README.md
  AGENTS.md
  pyproject.toml
  .gitignore

  docs/
    mplgallery_codex_bootstrap_master_plan.md

  src/
    mplgallery/
      __init__.py
      cli.py

      core/
        __init__.py
        models.py
        scanner.py
        associations.py
        manifest.py
        recipes.py
        renderer.py
        backups.py
        config.py
        paths.py

      ui/
        __init__.py
        app.py
        pages.py
        state.py
        components.py

      integrations/
        __init__.py
        dvc.py
        mlflow.py

  tests/
    test_scanner.py
    test_associations.py
    test_manifest.py
    test_recipes.py
    test_backups.py

  examples/
    sample_project/
      data/
        experiment_001.csv
        experiment_002.csv
      plots/
        experiment_001.png
        experiment_002.svg
      scripts/
        generate_plots.py
```

Not every file needs full implementation in the first commit. Empty or minimal placeholders are acceptable for future modules.

---

## 6. Initial `pyproject.toml`

Use a modern `src/` layout. The package should expose a CLI command named `mplgallery`.

Recommended first `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "mplgallery"
version = "0.1.0"
description = "Local-first Matplotlib plot gallery for CSV-generated PNG/SVG plots."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
  { name = "Tanner" }
]
dependencies = [
  "streamlit>=1.35",
  "pandas>=2.0",
  "matplotlib>=3.8",
  "pydantic>=2.0",
  "pyyaml>=6.0",
  "typer>=0.12",
  "rich>=13.0",
  "pillow>=10.0",
  "mlflow>=2.0",
  "dvc>=3.0"
]

[dependency-groups]
dev = [
  "pytest>=8.0",
  "ruff>=0.5",
  "mypy>=1.8"
]

[project.scripts]
mplgallery = "mplgallery.cli:main"

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Notes:

- DVC and MLflow are included in the standard install for v1 because the product design treats them as first-class.
- The code should still run in static browse mode when a target project has not initialized DVC or MLflow.
- Later, the package can split heavy dependencies into extras such as `mplgallery[full]` if installation weight becomes a problem.

---

## 7. Initial `AGENTS.md`

Codex should create this file at repo root:

````md
# AGENTS.md

## Project Goal

Build `mplgallery`, an installable Python package that provides a local Streamlit UI for browsing, inspecting, editing, regenerating, and tracking Matplotlib-generated PNG/SVG plots associated with CSV data files.

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
- Do not modify target analysis projects except through explicit overwrite/regeneration actions.
- Do not overwrite any plot without first creating a backup.
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

Do not implement recipe editing, DVC, MLflow, or full Streamlit UI until the scanner/indexer is stable.
````
---

## 8. Initial CLI Design

The CLI should support these commands eventually:

```bash
mplgallery serve <project_root>
mplgallery scan <project_root>
mplgallery init <project_root>
mplgallery render <project_root> --plot-id <plot_id>
mplgallery dvc init-stages <project_root>
mplgallery mlflow ui <project_root>
```

### v0.1 CLI Minimum

For Milestone 1, implement at least:

```bash
mplgallery scan <project_root>
```

and optionally:

```bash
mplgallery serve <project_root>
```

`serve` can initially launch a placeholder Streamlit app.

### CLI Responsibilities

`mplgallery serve <project_root>` should:

1. validate the path;
2. resolve it to an absolute path;
3. set environment variable `MPLGALLERY_PROJECT_ROOT`;
4. launch the packaged Streamlit app using `python -m streamlit run`.

`mplgallery scan <project_root>` should:

1. scan for `.png`, `.svg`, and `.csv` files;
2. associate likely CSV files to plots;
3. print a human-readable summary;
4. optionally support `--json` later.

`mplgallery render <project_root> --plot-id <plot_id>` should later:

1. load `.mplgallery` config and recipe metadata;
2. load the associated CSV;
3. render the Matplotlib figure;
4. create a backup;
5. overwrite the original output;
6. log to MLflow;
7. return a nonzero exit code if rendering fails.

---

## 9. Core Product Modes

The package must explicitly distinguish two modes.

### 9.1 Static Gallery Mode

Works on any project containing images and CSV files.

Capabilities:

- recursively scan for `.png`, `.svg`, `.csv`;
- create plot records;
- associate likely CSV files;
- display image gallery;
- preview CSV;
- compare multiple image files side-by-side;
- show metadata such as file size, modified time, image dimensions, extension, and association confidence;
- allow manual association overrides later.

Limitations:

- cannot safely edit Matplotlib-level properties of arbitrary PNG/SVG files;
- cannot infer original Python plotting logic;
- cannot know exact axis labels, line colors, legends, fits, or transforms unless metadata exists.

The UI must label static plots as **View-only**.

### 9.2 Recipe Mode

Works when a plot has recipe metadata.

Capabilities:

- load CSV;
- load plot recipe;
- expose editable Matplotlib settings;
- render preview;
- overwrite original plot after confirmation/action;
- create backup before overwrite;
- log changes to MLflow;
- optionally run through DVC stages.

Recipe Mode is how the package supports editing axes, labels, colors, figure size, DPI, grid, legends, tick styles, markers, and other Matplotlib features.

---

## 10. Critical Technical Caveat

A PNG file is pixels. An SVG file is vector markup. Neither is equivalent to a recoverable Matplotlib `Figure` object.

Therefore, do not attempt to reverse-engineer arbitrary plots into editable Matplotlib code.

Instead:

1. always support browsing arbitrary PNG/SVG files;
2. support true editing only when a recipe exists;
3. provide a path to create a new generic recipe from CSV data;
4. optionally parse image metadata when useful, but do not rely on it as the sole source of truth.

---

## 11. Project Root Selection

### v1 Source of Truth

The primary project root should come from the CLI:

```bash
mplgallery serve /path/to/project
```

If no path is provided, default to the current working directory:

```bash
mplgallery serve .
```

The Streamlit UI can include a sidebar text input for changing the project root, but the CLI argument should be the normal path.

### Browser Folder Picker Caveat

Do not depend on a true native browser folder picker for arbitrary local filesystem access. For a local Streamlit app, the reliable mechanisms are:

- CLI path argument;
- text input path in the sidebar;
- recent project history stored under user config;
- future desktop wrapper if needed.

---

## 12. Scanner and Indexer Specification

### 12.1 Files to Discover

The scanner should recursively discover:

```text
*.png
*.svg
*.csv
```

SVG and PNG should remain first-class. SVG is usually better for clean line plots because it scales without blur and can be publication-friendly. PNG remains necessary for dense scatter plots, heatmaps, raster image plots, browser thumbnails, performance-sensitive pages, and workflows where SVG output is too large or renders differently across applications.

Later extensions:

```text
*.jpg
*.jpeg
*.pdf
*.json
*.yaml
*.yml
*.parquet
```

For v1, prioritize PNG, SVG, and CSV.

### 12.2 Default Ignore Rules

Do not scan these directories unless the user explicitly disables ignores:

```text
.git/
.dvc/
.mlruns/
mlruns/
.venv/
venv/
env/
__pycache__/
.ipynb_checkpoints/
node_modules/
.dist/
dist/
build/
.site/
```

Also skip hidden directories by default except:

```text
.mplgallery/
```

### 12.3 File Metadata

For each discovered file, capture:

```text
absolute_path
relative_path
suffix
stem
parent_dir
file_size_bytes
modified_time
created_time if available
sha256 optional/later
```

For images, additionally capture:

```text
width_px
height_px
format
```

Use Pillow for PNG dimensions. For SVG, parse width/height/viewBox where feasible.

### 12.4 Plot Record

Each plot record should contain:

```text
plot_id
image_path
image_type
associated_csv_path optional
association_confidence
association_reason
recipe_path optional
mode static|recipe
metadata_files
possible_script_files optional/later
dvc_stage optional
mlflow_run_ids optional/later
```

Use Pydantic models for validation and serialization.

---

## 13. CSV Association Algorithm

v1 assumes one CSV per plot. The association engine should score candidate CSV files.

### 13.1 Signals

Use these signals, in this order:

1. **Recipe metadata override**  
   If `.mplg.yaml` specifies `csv_path`, use it.

2. **Manifest override**  
   If `.mplgallery/manifest.yaml` maps plot path to CSV path, use it.

3. **Same directory and same stem**  
   `plots/foo.png` ↔ `plots/foo.csv`

4. **Nearby directory and same stem**  
   `plots/foo.png` ↔ `data/foo.csv`

5. **Stem normalization**  
   Treat common suffixes as removable:

   ```text
   _plot
   _figure
   _fig
   _fit
   _results
   _data
   -plot
   -fit
   ```

6. **Directory sibling relationship**  
   `project/experiment_001/plots/foo.png` ↔ `project/experiment_001/data/foo.csv`

7. **Only CSV nearby**  
   If the image directory or parent experiment directory contains exactly one CSV, associate with low confidence.

8. **No confident match**  
   Leave unassociated and display as orphan/unmatched.

### 13.2 Confidence Levels

Use explicit confidence categories:

```text
exact
high
medium
low
none
```

Example mapping:

| Reason | Confidence |
|---|---|
| recipe metadata | exact |
| manifest override | exact |
| same dir + same stem | high |
| sibling data/plots + same stem | high |
| normalized stem | medium |
| only CSV nearby | low |
| ambiguous multiple candidates | none |

The UI should display confidence and allow later manual correction.

---

## 14. `.mplgallery` Project Metadata Directory

When initialized, target projects should contain:

```text
<project_root>/
  .mplgallery/
    config.yaml
    manifest.yaml
    recipes/
    backups/
    cache/
    logs/
```

### 14.1 `config.yaml`

Example:

```yaml
version: 1
project_name: null
scan:
  include_extensions: [".png", ".svg", ".csv"]
  ignore_dirs:
    - ".git"
    - ".dvc"
    - "mlruns"
    - ".venv"
    - "__pycache__"
association:
  assume_one_csv_per_plot: true
  allow_low_confidence_matches: true
rendering:
  overwrite_originals: false
  backup_before_overwrite: true
  backup_dir: ".mplgallery/backups"
cache:
  enabled: true
  image_cache_dir: ".mplgallery/cache"
  fingerprint_strategy: "size_mtime"
mlflow:
  enabled: true
  tracking_uri: "file:./mlruns"
dvc:
  enabled: true
  create_stages: true
ui:
  default_page: "gallery"
  thumbnail_width: 320
  max_csv_preview_rows: 1000
```

`.mplgallery/cache` is the default target-project location for untracked cached redraw images and CSV fingerprints. It should be ignored in target projects and must not be treated as the source of truth for generated artifacts.

### 14.2 `manifest.yaml`

Example:

```yaml
version: 1
records:
  - plot_id: experiment_001_fit
    plot_path: plots/experiment_001_fit.png
    raw_csv_path: data/raw/experiment_001_raw.csv
    plot_csv_path: data/plot_ready/experiment_001_fit.csv
    redraw:
      kind: line
      x: time_s
      title: "Experiment 001 Fit"
      xlabel: "Time [s]"
      ylabel: "Conversion"
      xscale: linear
      yscale: linear
      xlim: [0.0, 10.0]
      ylim: [0.0, 1.0]
      grid: true
      figure:
        width_inches: 6.0
        height_inches: 4.0
        dpi: 150
      series:
        - y: conversion
          label: "Model conversion"
          color: "#2a6f97"
          linewidth: 1.8
          linestyle: "-"
          marker: "o"
          alpha: 0.9
    dvc_stage: render_experiment_001_fit
    mode: recipe
    notes: "Manual association confirmed."
```

The manifest should support manual association overrides and Matplotlib metadata edits without modifying discovered files. `plot_csv_path` is the render source for cached previews; `raw_csv_path` is displayed as provenance only. `csv_path` may be accepted temporarily for older manifests, but new records should use `plot_csv_path`.

---

## 15. Recipe Metadata Schema

Recipe metadata enables true plot editing and regeneration.

### 15.1 Preferred Location

Default central location:

```text
.mplgallery/recipes/<plot_id>.mplg.yaml
```

Optional sidecar location:

```text
plots/example.png.mplg.yaml
```

The scanner should support both. If both exist, central `.mplgallery/recipes/` should take precedence unless config says otherwise.

### 15.2 Minimal Recipe Example

```yaml
version: 1
plot_id: experiment_001_fit
kind: line_scatter
csv_path: data/experiment_001.csv
output_path: plots/experiment_001_fit.png
format: png
columns:
  x: time_s
  y: conversion
style:
  title: "Experiment 001 Fit"
  xlabel: "Time [s]"
  ylabel: "Conversion"
  xscale: linear
  yscale: linear
  xlim: null
  ylim: null
  figsize: [8, 5]
  dpi: 150
  grid: true
  legend: true
  legend_loc: best
  line:
    color: null
    linewidth: 2.0
    linestyle: "-"
    marker: "o"
    markersize: 4
    alpha: 1.0
savefig:
  bbox_inches: tight
  transparent: false
  facecolor: white
  metadata:
    Creator: "mplgallery"
```

### 15.3 Recipe Kinds for v1

Implement a small set:

```text
line
scatter
line_scatter
multi_line_from_columns
```

Defer complex fits and user-defined Python callbacks until the core is stable.

### 15.4 Advanced Style Escape Hatch

Because the user eventually wants broad Matplotlib feature control, include an advanced section:

```yaml
advanced:
  rcParams:
    axes.titlesize: 14
    axes.labelsize: 12
    lines.linewidth: 2
```

The UI should initially support curated common fields, then allow advanced YAML editing for `rcParams` with validation.

---

## 16. Matplotlib Editing Scope

### 16.1 v1 Editable Fields

The Streamlit UI should support editing these fields for recipe-enabled plots:

| Category | Fields |
|---|---|
| Title/labels | title, xlabel, ylabel |
| Axis limits | xlim min/max, ylim min/max |
| Axis scale | linear/log for x and y |
| Figure | width, height, dpi |
| Grid | enabled, style later |
| Legend | enabled, location |
| Line | color, linewidth, linestyle, alpha |
| Marker | marker type, marker size |
| Ticks | tick label size, x tick rotation |
| Save | output format, bbox_inches, transparent |

### 16.2 Explicit Non-Goals for v1

Do not attempt full arbitrary Matplotlib artist editing in v1.

Defer:

- editing arbitrary annotations;
- editing multiple axes/subplots;
- editing twin axes;
- editing colorbars;
- editing fitted model internals;
- reverse-engineering static SVGs into recipes;
- visually dragging labels/legends in the browser.

### 16.3 Overwrite Flow

When user applies edits:

1. validate recipe;
2. load CSV;
3. render preview to temporary file;
4. show preview in UI;
5. user clicks overwrite/apply;
6. create timestamped backup of original output;
7. save new figure to original output path;
8. update recipe metadata;
9. log artifacts/params to MLflow;
10. refresh gallery cache;
11. if DVC stage exists, optionally run or recommend `dvc repro` depending on current workflow setting.

Because overwrite is the chosen default, the UI must make backup status visible.

---

## 17. Backup Specification

Backups are mandatory before overwrite.

Backup path pattern:

```text
<project_root>/.mplgallery/backups/<timestamp>/<relative_original_path>
```

Example:

```text
.mplgallery/backups/2026-05-04T14-30-12/plots/experiment_001_fit.png
```

Also write a small backup manifest:

```yaml
version: 1
created_at: "2026-05-04T14:30:12"
plot_id: experiment_001_fit
original_path: plots/experiment_001_fit.png
backup_path: .mplgallery/backups/2026-05-04T14-30-12/plots/experiment_001_fit.png
reason: recipe_overwrite
```

Do not rely only on Git/DVC for backup. Create a local copy first.

---

## 18. DVC Integration Plan

DVC should be the reproducibility and dependency-tracking layer.

### 18.1 Target Role

DVC should handle:

- dependency graph from CSV + recipe → PNG/SVG;
- stale output detection;
- reproducible plot regeneration;
- command-line rebuild through `dvc repro`;
- future remote storage of large outputs.

### 18.2 DVC Stage Pattern

For each recipe-enabled plot, generate or support a stage like:

```yaml
stages:
  render_experiment_001_fit:
    cmd: mplgallery render . --plot-id experiment_001_fit
    deps:
      - data/experiment_001.csv
      - .mplgallery/recipes/experiment_001_fit.mplg.yaml
    outs:
      - plots/experiment_001_fit.png
```

This makes `mplgallery render` the deterministic headless rendering command. DVC should call the CLI, not Streamlit.

### 18.3 DVC Commands to Support Later

```bash
mplgallery dvc init-stages <project_root>
mplgallery dvc status <project_root>
mplgallery dvc repro <project_root> --plot-id <plot_id>
```

Internally these can call:

```bash
dvc status
dvc repro <stage-name>
```

### 18.4 v1 Behavior if Project Has No DVC

If a target project does not have DVC initialized:

- static gallery mode should still work;
- recipe preview should still work;
- direct overwrite through internal renderer should work;
- UI should display "DVC not initialized";
- `mplgallery init` can optionally create DVC scaffolding later.

DVC is first-class, but existing projects should not be unusable without a DVC repo.

---

## 19. MLflow Integration Plan

MLflow should be the artifact, parameter, metric, and history layer.

### 19.1 Target Role

MLflow should log:

- plot ID;
- CSV artifact;
- output PNG/SVG artifact;
- recipe YAML artifact;
- style parameters;
- fit metrics when available;
- row/column counts;
- render timestamp;
- package version;
- DVC stage name if available;
- Git commit hash if available.

### 19.2 Default Tracking URI

For local-first v1:

```text
file:<project_root>/mlruns
```

or equivalently use local `mlruns/` under the target project.

### 19.3 Experiment Naming

Recommended experiment name:

```text
mplgallery/<project_name>
```

If project name is unknown, use the project root folder name.

### 19.4 MLflow UI

Later CLI helper:

```bash
mplgallery mlflow ui <project_root>
```

can run:

```bash
mlflow ui --backend-store-uri <project_root>/mlruns
```

### 19.5 Future Team Mode

For team/shared-server mode, allow config:

```yaml
mlflow:
  enabled: true
  tracking_uri: "http://mlflow.company.local:5000"
```

Do not hard-code local file tracking only.

---

## 20. Browser-First UI Plan

Streamlit should host the local app, provide Python data access, and coordinate scanning, pandas previews, fingerprints, cached redraws, and errors. The polished browser surface should come from custom HTML/JS components where Streamlit-native widgets are too bulky for a file-explorer UI.

The default view should be a local artifact browser, not an analytics dashboard.

### 20.1 Pages

Use a multipage layout or internal navigation with these pages:

```text
Gallery
Plot Detail
Compare
Recipes
Project Health
Settings
History
```

### 20.2 Gallery Page

Features:

- compact sidebar with search;
- output-tree folder browser by default;
- expand all, collapse all, clear selection controls;
- folder checkboxes that preserve selection state while search filters;
- responsive image grid;
- tile-size control;
- minimal refresh/cache status;
- filters by extension, association confidence, recipe status, directory, modified date;
- badges:
  - Static
  - Recipe
  - CSV matched
  - CSV missing
  - DVC stage
  - MLflow history
- multi-select checkboxes for comparison.

Paths, cache paths, raw CSV tables, and debug metadata should be available on demand, not visible on every card by default.

### 20.3 Plot Detail Page

Show:

- full-size PNG/SVG;
- path and metadata;
- associated CSV preview;
- CSV summary:
  - rows;
  - columns;
  - numeric column list;
  - missing values;
  - min/max for numeric columns;
- recipe metadata if available;
- DVC stage if available;
- MLflow runs if available;
- edit controls if recipe-enabled.

### 20.4 Compare Page

v1 comparison:

- side-by-side image grid;
- synced metadata cards;
- associated CSV summaries;
- download selected image list as a CSV manifest.

Later comparison:

- overlay curves if selected plots share the same CSV schema;
- compare MLflow parameters/metrics;
- compare image dimensions and modification times.

### 20.5 Recipes Page

Show:

- all recipe-enabled plots;
- invalid recipes;
- missing CSV paths;
- missing output paths;
- render buttons;
- create generic recipe from CSV workflow.

### 20.6 Project Health Page

Show:

- orphan images;
- orphan CSVs;
- ambiguous associations;
- low-confidence associations;
- missing recipes;
- stale DVC status where detectable;
- large files;
- ignored directories count.

### 20.7 Settings Page

Allow editing project-level `.mplgallery/config.yaml` fields:

- ignore dirs;
- extensions;
- thumbnail width;
- max CSV preview rows;
- backup behavior;
- MLflow tracking URI;
- DVC enabled flag.

---

## 21. pandas Usage

Use pandas for:

- `read_csv` previews;
- column detection;
- numeric/non-numeric classification;
- basic summary statistics;
- missing-value counts;
- detecting possible x/y columns for generic recipes.

Avoid loading extremely large CSVs fully in the UI by default. Use:

```python
pd.read_csv(path, nrows=max_preview_rows)
```

For summary stats, make size-aware decisions. If CSV is very large, show a warning and preview only.

---

## 22. Sample Project for Tests and Demo

Codex should create a small sample project:

```text
examples/sample_project/
  data/
    raw/
      experiment_001_raw.csv
      experiment_002_raw.csv
    plot_ready/
      experiment_001_plot.csv
      experiment_002_plot.csv
  plots/
    experiment_001.png
    experiment_002.svg
  scripts/
    generate_data.py
    render_plots.py
    generate_plots.py  # compatibility wrapper that runs both scripts
```

`generate_data.py` should generate deterministic raw/model CSVs only. `render_plots.py` should read raw CSVs, write plot-ready CSVs, read `.mplgallery/manifest.yaml`, and render PNG/SVG artifacts with Matplotlib.

Example CSV columns:

```text
time_s,conversion,fit
0,0.00,0.02
1,0.10,0.11
2,0.21,0.20
```

The sample project is important for manual testing:

```bash
mplgallery serve examples/sample_project
```

---

## 23. Implementation Milestones

Build in vertical slices. Do not implement everything at once.

### Milestone 0 — Bootstrap and Scaffold

Deliverables:

- clone repo;
- create package structure;
- create `pyproject.toml`;
- create `README.md`;
- create `AGENTS.md`;
- create this plan under `docs/`;
- create placeholder modules;
- initial commit.

Acceptance:

```bash
uv sync --dev
uv run python -c "import mplgallery; print(mplgallery.__version__)"
```

### Milestone 1 — Scanner, Manifest, and Association Core

Deliverables:

- recursive scanner;
- ignore rules;
- Pydantic file models;
- plot record model;
- manifest record model;
- cache metadata hooks for `.mplgallery/cache`;
- association scoring;
- optional manifest association overrides;
- scanner, manifest, and association tests;
- `mplgallery scan <project_root>` summary output.

Acceptance:

```bash
uv run pytest tests/test_scanner.py tests/test_associations.py
uv run mplgallery scan examples/sample_project
```

### Milestone 2 — Live Browser Shell

Deliverables:

- `mplgallery serve <project_root>` launches Streamlit;
- Streamlit passes scan/index data to a browser-first gallery surface;
- gallery page displays discovered PNG/SVG files in a dense responsive grid;
- compact output-tree sidebar;
- selected plot detail panel;
- associated CSV preview with pandas;
- basic filters/search;
- tile-size control.

Acceptance:

```bash
uv run mplgallery serve examples/sample_project
```

Manual validation:

- sample PNG appears;
- sample SVG appears;
- CSV preview appears for matched plot;
- unmatched files are visible and labeled.

### Milestone 3 — Custom Tree/Grid Component

Deliverables:

- custom HTML/JS component for the file-explorer tree and image grid;
- separate expand/collapse controls from folder checkboxes;
- multiple folder selection;
- search that preserves tree selection state;
- card layout where images dominate and metadata is on demand.

Acceptance:

- Browser validation shows output-tree selection and grid filtering work without replacing the UI with dropdown-based browsing.

### Milestone 4 — Cached CSV Redraws

Deliverables:

- CSV fingerprinting by size and modification time;
- metadata-driven CSV-to-Matplotlib redraw path using pandas-loaded CSV data;
- cached redraw outputs under `.mplgallery/cache`;
- per-plot render error reporting;
- original PNG/SVG artifacts remain unchanged by default.

Acceptance:

- changing a CSV regenerates only the affected cached image;
- gallery displays the cached redraw;
- tracked/generated plot artifacts are not overwritten.

### Milestone 5 — Static Build

Deliverables:

- `mplgallery build <project_root>`;
- static `index.html` output that preserves the tree/grid browsing model;
- documented generated output location.

Acceptance:

```bash
uv run mplgallery build examples/sample_project
```

### Milestone 6 — Project Metadata and Recipe Parsing

Deliverables:

- `mplgallery init <project_root>`;
- `.mplgallery/config.yaml`;
- `.mplgallery/manifest.yaml`;
- manual association override support;
- manifest fields for `raw_csv_path`, `plot_csv_path`, legacy `csv_path`, and `redraw`;
- project health page initial version;
- recipe schema;
- recipe parser/validator;
- basic recipe renderer for `line`, `scatter`, and `line_scatter`;
- `mplgallery render <project_root> --plot-id <plot_id>`;
- tests for recipe parsing and rendering.

Acceptance:

```bash
uv run mplgallery init examples/sample_project
uv run mplgallery render examples/sample_project --plot-id experiment_001
```

### Milestone 7 — Metadata Editor and Cached Preview Flow

Deliverables:

- editable controls for title/labels/limits/scale/line/marker/size/DPI;
- per-series label/color/linewidth/linestyle/marker/alpha controls;
- YAML metadata persistence in `.mplgallery/manifest.yaml`;
- preview rendering into `.mplgallery/cache`;
- per-plot render errors instead of app-level crashes;
- tests proving raw CSVs and generated plot artifacts are not modified by live edits.

Acceptance:

- edit label in UI;
- preview updates;
- manifest changes persist after reload;
- cached preview uses `plot_csv_path`;
- raw CSV and original generated artifact remain unchanged.

### Milestone 7.5 — Explicit Overwrite Flow

Deliverables:

- backup-before-overwrite;
- explicit overwrite original output action;
- backup manifest;
- tests for backup behavior.

Acceptance:

- explicit overwrite creates backup;
- original PNG/SVG path is updated only after explicit overwrite;
- backup file exists.

### Milestone 8 — DVC Integration

Deliverables:

- detect DVC project;
- generate DVC stages for recipe plots;
- show DVC stage in UI;
- run `dvc repro <stage>` from CLI/UI with safe error handling.

Acceptance:

```bash
uv run mplgallery dvc init-stages examples/sample_project
dvc repro render_experiment_001
```

### Milestone 9 — MLflow Integration

Deliverables:

- configure local tracking URI;
- log render runs;
- log plot/CSV/recipe artifacts;
- log style params;
- show recent MLflow runs for a plot in UI.

Acceptance:

- rendering a recipe creates an MLflow run;
- output plot and recipe are logged as artifacts;
- params appear in run data.

### Milestone 10 — Hardening and GitHub Install Workflow

Deliverables:

- `pip install git+https://github.com/<owner>/mplgallery.git` works;
- docs for installing into target projects;
- smoke tests on at least one real analysis project;
- packaging cleanup.

Acceptance:

```bash
python -m venv /tmp/mplgallery-test-env
source /tmp/mplgallery-test-env/bin/activate
pip install git+https://github.com/<owner>/mplgallery.git
mplgallery --help
```

---

## 24. Minimal First Implementation Details

### 24.1 `models.py`

Create models similar to:

```python
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FileKind(str, Enum):
    IMAGE = "image"
    CSV = "csv"
    METADATA = "metadata"


class AssociationConfidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class DiscoveredFile(BaseModel):
    path: Path
    relative_path: Path
    kind: FileKind
    suffix: str
    stem: str
    size_bytes: int
    modified_at: datetime


class PlotRecord(BaseModel):
    plot_id: str
    image: DiscoveredFile
    csv: DiscoveredFile | None = None
    association_confidence: AssociationConfidence = AssociationConfidence.NONE
    association_reason: str | None = None
    recipe_path: Path | None = None
    mode: str = "static"
```

Adjust as needed, but keep models explicit and testable.

### 24.2 `scanner.py`

Responsibilities:

- validate project root;
- recursively walk files;
- apply ignore rules;
- classify file kind;
- return discovered files.

### 24.3 `associations.py`

Responsibilities:

- accept image files and CSV files;
- score candidate CSVs for each image;
- return `PlotRecord` objects;
- avoid false exact matches when multiple candidates tie.

### 24.4 Tests

Test cases:

1. same directory same stem;
2. sibling `data/` and `plots/` directories;
3. normalized suffix match;
4. ambiguous CSV candidates;
5. no CSV found;
6. ignored directories not scanned.

---

## 25. Static Gallery UI Implementation Guidance

When implementing the first UI:

- keep scanner logic outside Streamlit;
- cache scan results with `st.cache_data` where appropriate;
- use `st.image` for local PNG/SVG display;
- use `st.dataframe` for CSV previews;
- avoid `st.column_config.ImageColumn` for local thumbnails unless paths are converted to supported URLs or data URLs;
- prefer card/grid layout for thumbnails initially.

UI state should include:

```text
project_root
scan_results
selected_plot_id
selected_compare_plot_ids
filters
```

---

## 26. Team/Shared-Server Future Path

v1 is local-first. Do not overbuild team mode now, but avoid blocking it.

Future team architecture:

```text
Shared analysis filesystem or object store
  ↓
MPLGallery server process
  ↓
Streamlit or FastAPI frontend
  ↓
MLflow tracking server
  ↓
DVC remote storage
  ↓
Authentication/authorization layer
```

Design choices now that help later:

- do not hard-code local-only MLflow tracking;
- keep project root access behind a path abstraction;
- use config files for root settings;
- avoid global mutable state;
- keep rendering headless through CLI;
- make file modification actions explicit and auditable;
- log overwrite actions.

Do not implement authentication, permissions, or multi-user locks in v1.

---

## 27. Safety and Data Integrity Rules

The package will operate on user analysis projects, so data integrity matters.

Rules:

1. Static gallery mode is read-only.
2. Recipe mode may write only after explicit user action.
3. Overwrite always creates backup first.
4. Never delete original CSV files.
5. Never silently modify user scripts.
6. Never rewrite `dvc.yaml` without user command/action.
7. Never run arbitrary discovered Python scripts automatically.
8. `mplgallery render` should execute package-controlled renderers first, not arbitrary user code.
9. User-defined plotting functions can be supported later through a safer plugin/entry-point design.
10. All write operations should be logged.

---

## 28. README Minimum

The initial README should include:

````md
# mplgallery

`mplgallery` is a local-first Matplotlib plot gallery for projects that generate PNG/SVG plots from CSV data.

## Install from GitHub

```bash
pip install git+https://github.com/<owner>/mplgallery.git
```

## Run against a project

```bash
mplgallery serve /path/to/project
```

## Scan a project

```bash
mplgallery scan /path/to/project
```

## Modes

- Static Gallery Mode: browse PNG/SVG/CSV files without modifying the project.
- Recipe Mode: edit and regenerate Matplotlib plots using `.mplg.yaml` recipe metadata.

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```
````
---

## 29. `.gitignore` Minimum

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Environments
.venv/
venv/
env/

# Build artifacts
build/
dist/

# Local app artifacts
.streamlit/secrets.toml

# MLflow / DVC local runtime artifacts for package repo examples
mlruns/
.dvc/cache/

# OS/editor
.DS_Store
.vscode/
.idea/
```

Do not globally ignore `.dvc/` if the package repo eventually uses DVC itself. For now, ignoring `.dvc/cache/` is safer than ignoring all `.dvc/`.

---

## 30. Codex Work Instructions After Bootstrap

After Milestone 0/1, future prompts should be narrow.

### Prompt for Milestone 2

````md
Implement Milestone 2 only from `docs/mplgallery_codex_bootstrap_master_plan.md`.

Goal:
`mplgallery serve examples/sample_project` launches a Streamlit UI showing discovered PNG/SVG plots and associated CSV previews.

Constraints:
- Do not implement recipe editing yet.
- Do not implement DVC or MLflow yet.
- Keep scanner logic outside Streamlit.
- Use existing scanner and association models.
- Add tests where feasible.

Run:

```bash
uv run pytest
uv run ruff check .
```

Summarize files changed and limitations.
````

### Prompt for Milestone 3

```md
Implement Milestone 3 only.

Add `.mplgallery/config.yaml`, `.mplgallery/manifest.yaml`, `mplgallery init`, and manifest-based association overrides.

Do not implement recipe rendering, DVC, or MLflow yet.

Run tests and linting.
```

### Prompt for Milestone 4

```md
Implement Milestone 4 only.

Add `.mplg.yaml` recipe parsing and headless Matplotlib rendering for line, scatter, and line_scatter recipes.

Add `mplgallery render <project_root> --plot-id <plot_id>`.

Do not add the full Streamlit editor yet.

Run tests and linting.
```

### Prompt for Milestone 5

```md
Implement Milestone 5 only.

Add Streamlit recipe editing controls, preview rendering, backup-before-overwrite, and overwrite original output.

Make sure static gallery mode remains read-only.

Run tests and linting.
```
---

## 31. Definition of Done for v1

v1 is complete when the following works from a clean environment:

```bash
pip install git+https://github.com/<owner>/mplgallery.git
mplgallery serve /path/to/project
```

and the app can:

1. scan arbitrary project folders;
2. show PNG/SVG plots;
3. show associated CSV data;
4. compare multiple plots;
5. distinguish static and recipe-enabled plots;
6. edit common Matplotlib fields for recipe-enabled plots;
7. preview regenerated plot;
8. overwrite original with backup;
9. run headless render from CLI;
10. log render artifacts to MLflow;
11. use or generate DVC stages for reproducible rendering.

---

## 32. Main Risks

| Risk | Mitigation |
|---|---|
| User expects arbitrary PNG editing | UI must clearly label static plots as view-only. |
| DVC/MLflow dependencies are heavy | Keep architecture modular; consider extras later. |
| Association heuristics create wrong matches | Use confidence scores and manual overrides. |
| Overwrite destroys valuable plot | Mandatory backup before overwrite. |
| Streamlit app becomes too large | Keep business logic in `core/`, not `ui/`. |
| Arbitrary script execution risk | v1 recipes should use built-in renderers only. |
| Large projects scan slowly | Add ignore rules, caching, and later SQLite index. |
| SVG dimensions inconsistent | Best-effort parse; do not block gallery display. |

---

## 33. Reference Notes for the Implementer

Use official documentation as needed for current APIs. Key facts to verify during implementation:

- `pyproject.toml` is the modern configuration file for Python packaging tools and can define project metadata/build configuration.
- `[project.scripts]` creates installable CLI entry points.
- Streamlit can display local image files with `st.image`.
- Streamlit can display pandas-like dataframes with `st.dataframe`.
- Matplotlib `savefig` writes figures to image/vector formats and supports metadata arguments.
- DVC `repro` regenerates pipeline results from stages defined in `dvc.yaml`.
- MLflow Tracking logs parameters, metrics, artifacts, plots, and run metadata.
- Codex app works against a selected local project folder; after cloning into `.` the selected folder should become the repo root.

---

## 34. Final Instruction to Codex

Do not build the full product in one pass.

The correct first deliverable is a small, tested foundation:

```text
clone → scaffold → scanner → association engine → CLI scan → tests → commit
```

Only after that should the UI, metadata, recipe system, DVC integration, and MLflow integration be added.
