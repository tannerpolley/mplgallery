# mplgallery

`mplgallery` is a local-first plot-set manager for Python analysis projects. It
discovers project-owned plot sets under `results/<plot_set>/`, groups the CSV
snapshots, PNG/SVG/PDF figures, and `.mpl.yaml` sidecars that belong together,
and provides a Streamlit UI for browsing and lightly editing Matplotlib
appearance metadata.

The package is for plot appearance only. It does not tune, fit, optimize, or
alter scientific/model computations.

## Install from GitHub

```bash
pip install git+https://github.com/<owner>/mplgallery.git
```

## Download Release Wheels

Tagged releases publish wheel and source archives on GitHub Releases. Download
the `.whl` file from the release page, then install it with:

```bash
pip install mplgallery-*.whl
```

## Install locally with `uv`

```bash
uv sync --dev
uv run mplgallery run examples/sample_project
```

Optional DVC and MLflow integrations are not installed by default:

```bash
pip install "mplgallery[dvc,mlflow]"
```

Windows desktop mode is optional and keeps the browser workflow separate:

```bash
uv sync --extra desktop
```

## Run against a project

```bash
cd /path/to/project
mplgallery run
```

`run` is an alias for `serve` and is intended as the simple installed-package
entrypoint: run it from the analysis/project root and MPLGallery starts the
local Streamlit plot-set manager. Results folders, CSV snapshots, and figures
are shown together in one project file explorer.

You can also start from any folder and switch roots inside the app:

```bash
mplgallery run --choose-root
mplgallery run C:\path\to\starting\project --choose-root
```

The root chooser stores only convenience settings, such as recent project
folders, under the user config directory. Use recent roots, paste a folder path,
or use the local Browse action where the desktop folder picker is available.
Plot sets and `.mpl.yaml` sidecars stay inside the selected project or analysis
folder. User-level settings only store launcher convenience state such as recent
roots.

## Windows desktop app

On Windows, MPLGallery has two desktop paths:

- installed Python package mode, useful for development;
- release app mode, a single-file `mplgallery-desktop.exe` with Windows app
  metadata, an icon, Start Menu shortcuts, and update prompts.

For development, install the optional desktop extra and launch the native
window:

```bash
mplgallery desktop .
```

That starts the same local MPLGallery backend but hosts it in its own desktop
window instead of a normal browser tab.

The package also declares a Windows GUI launcher:

```text
mplgallery-desktop.exe
```

That entry point is intended for shortcuts and taskbar pinning because it opens
without a console window. You can point a shortcut at it and pass a project
folder path if needed.

Browser mode remains available for automation, browser tooling, or normal web
use:

```bash
mplgallery run .
mplgallery serve .
mplgallery desktop . --browser
```

### Install the released Windows app

Download the latest `mplgallery-desktop-<version>-windows-<arch>.zip` from
GitHub Releases, extract it, then install the app shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows_app.ps1 -ExePath .\mplgallery-desktop.exe -DesktopShortcut
```

The installer copies the executable to
`%LOCALAPPDATA%\Programs\MPLGallery\mplgallery-desktop.exe` and creates a Start
Menu shortcut. The Start Menu shortcut can be pinned to the taskbar like a
normal Windows app.

When the desktop UI starts, it checks GitHub Releases for a newer version. If a
newer Windows release asset exists, the app bar shows an update button that
opens the release download.

## Build a Windows single-file desktop executable

The repo now includes a PyInstaller-based Windows distribution path around the
desktop launcher. From this repo on Windows:

```bash
uv sync --extra desktop --group windows-dist
uv run python scripts/build_windows_dist.py
```

That produces:

- `dist/windows/mplgallery-desktop.exe`
- `dist/windows/mplgallery-desktop-<version>-windows-<arch>.zip`
- `dist/windows/mplgallery-desktop-build.json`

Tagged GitHub releases also build and publish the Windows app asset from the
`windows-latest` runner.

The build script also verifies the produced EXE by:

- running a non-interactive self-test mode;
- launching its bundled Streamlit backend in smoke-test mode;
- writing verification receipts into `build/windows-dist/`.

## Scan a project

```bash
mplgallery scan /path/to/project
mplgallery scan /path/to/project --json
mplgallery validate /path/to/project
```

`scan` reports discovered plot sets under `results/**` and compatibility
CSV/draft state. It ignores `.mplgallery`, docs/build/test noise, and arbitrary
non-result image assets. `validate` reports manifest references to missing
generated plot images or CSV files so ignored/generated artifact workflows fail
with a clear diagnostic instead of an empty gallery.

## Plot-Set Manager Workflow

```text
analysis_project/
  scripts/
    generate_results.py
    render_figures.py
  data/
    input/
    raw/
    processed/
  results/
    response_curve/
      response_curve.csv
      response_curve.svg
      response_curve.png
      response_curve.mpl.yaml
    regression_fit/
      model_curve.csv
      literature_points.csv
      regression_fit.svg
      regression_fit.mpl.yaml
  .mplgallery/
    manifest.yaml
    cache/
    indexes/
  config/
```

Project scripts own data generation and final figure rendering. MPLGallery does
not tune, fit, optimize, or alter scientific/model computations. It discovers
the plot sets those scripts produce and can edit `.mpl.yaml` sidecars that the
render scripts choose to consume.

The expected personal project layout is:

```text
analysis_name/
  scripts/           # your data-generation and analysis scripts; MPLGallery does not run them
  data/input/        # optional upstream inputs
  data/raw/          # raw outputs from scripts/models/functions
  data/processed/    # cleaned or analysis-ready tables
  results/runs/      # disposable diagnostics; ignored by MPLGallery defaults
  results/<plot_set>/ # curated plot snapshots, figures, and .mpl.yaml
  config/            # optional project configuration
```

By default, MPLGallery focuses on `results/**` plot sets and hides
`.mplgallery`, `results/runs`, docs builds, tests, and caches. Legacy CSV-first
drafting and broad artifact import remain compatibility workflows, not the
preferred new layout.

Initialize a CSV folder without rendering:

```bash
mplgallery init /path/to/project/data
```

Create compatibility draft recipes and generated previews for a CSV folder:

```bash
mplgallery draft /path/to/project/data
mplgallery draft /path/to/project/data --json
```

Drafting infers numeric columns and chooses a simple initial plot type. For new
work, prefer project render scripts that create `results/<plot_set>/` folders
with a `.mpl.yaml` sidecar.

## `.mpl.yaml` Sidecar Contract

Matplotlib does not natively read `.mpl.yaml`. Project render scripts, or
helpers imported by those scripts, should load the YAML and apply the declared
Matplotlib attributes before saving figures.

```yaml
version: 1
plot_id: response_curve
title: Response curve
files:
  figures:
    - response_curve.svg
    - response_curve.png
  data:
    - response_curve.csv
render:
  command: uv run python scripts/render_figures.py --plot response_curve
matplotlib:
  kind: line
  x: time_s
  title: Response curve
  xlabel: Time
  xlabel_unit: "$\\mathrm{s}$"
  ylabel: Response
  grid: true
  legend_location: best
  figure:
    width_inches: 6
    height_inches: 4
    dpi: 150
  series:
    - y: response
      label: Model
      color: "#1f77b4"
      linestyle: "-"
      marker: "o"
```

## pandas And Matplotlib Responsibilities

MPLGallery uses pandas for safe table handling:

- load and sample CSV files;
- preview plot-set CSV snapshots;
- validate column availability for editable sidecars;
- support compatibility draft plots from standalone CSV files when explicitly requested.

Matplotlib remains the editable figure contract:

- UI metadata edits for plot sets persist into `<plot_set>.mpl.yaml`;
- project render scripts or imported helper utilities apply that YAML to Matplotlib figures;
- labels, units, scales, limits, legends, grid, figure size, colors, markers,
  line styles, bar hatches, and opacity stay editable.

Source CSVs and plot-set CSV snapshots are never mutated by default.

## Import Existing Images As References

Existing PNG/SVG browsing is part of the default unified explorer. Explicit
reference import remains useful when you want to persist metadata for a specific
legacy artifact folder:

```bash
mplgallery import-artifacts /path/to/project/legacy/plots
mplgallery scan /path/to/project
mplgallery run /path/to/project
```

Curated images and nearby CSV companions are shown by default. Imported images
remain reference-only unless a CSV-backed recipe is added.

## Import Existing Plot Manifests

Projects with an existing ePC-SAFT-style `docs/plots/manifest.json` can seed an
MPLGallery manifest directly:

```bash
mplgallery import-manifest docs/plots/manifest.json --format epcsaft --project-root .
mplgallery import-manifest docs/plots/manifest.json --format epcsaft --project-root . --dry-run
```

The importer reads `output_path`, `svg_path`, `data_path`, `source_path`, and
`title`, writes `.mplgallery/manifest.yaml`, and reports missing plot/CSV
references separately.

## Modes

- Static Gallery Mode: browse PNG/SVG/CSV files without modifying the project.
- Plot-Set Metadata Mode: edit Matplotlib metadata in `<plot_set>.mpl.yaml`.
  Existing figures without sidecar YAML remain view-only. MPLGallery may run
  only explicit render commands declared in that sidecar.

## Plot Formats

SVG and PNG are both supported. Prefer SVG for clean Matplotlib line plots that
need crisp scaling or publication-friendly output. Keep PNG support for dense
scatter plots, heatmaps, raster/image plots, fast cached previews, and cases
where SVG files become too large or render inconsistently across tools.

## Supported Editing Surface

The browser editor supports common Matplotlib plot kinds including line,
scatter, bar, barh, area, hist, and step-style plots. It edits plot appearance
only:

- title, axis labels, axis units, legend title, limits, and scales;
- series labels, color, line width, line style, marker, and opacity;
- figure size, DPI, and grid state.

Axis units can use plain text or latex/mathtext strings such as
`$\mathrm{s}$`, `$\mu\mathrm{m}$`, or `$^\circ\mathrm{C}$`.

## Example Projects

- `examples/architecture_project`: compatibility fixture for older generated
  layout behavior.
- `examples/plot_set_project`: canonical `results/<plot_set>/` fixture with a
  CSV snapshot, SVG figure, `.mpl.yaml` sidecar, and split generate/render scripts.
- `examples/plot_types_project`: main mixed explorer fixture with PNG/SVG
  references and draftable CSV companions for line, scatter, bar, barh, area,
  hist, and step plots.
- `examples/sample_project`: original browser-first sample with PNG and SVG.
- `examples/generic_plots_project`: line and scatter examples.
- `examples/distribution_plots_project`: bar and histogram examples.
- `examples/install_smoke_project`: minimal project used to test installed wheels.

To browse every included example project in one app:

```bash
uv run mplgallery run examples
```

Regenerate an example project with its local scripts if you want to refresh the
assets:

```bash
uv run --no-sync python examples/generic_plots_project/scripts/generate_data.py
uv run --no-sync python examples/generic_plots_project/scripts/render_plots.py
uv run --no-sync python examples/plot_types_project/scripts/generate_plot_types.py
```

## Wheel Smoke Test

To verify the package works in a separate environment:

```bash
uv run --no-sync python -m build
python -m venv .wheel-smoke-venv
.wheel-smoke-venv\Scripts\pip install dist\*.whl
cd examples\install_smoke_project
..\..\.wheel-smoke-venv\Scripts\mplgallery.exe run --help
..\..\.wheel-smoke-venv\Scripts\mplgallery.exe scan . --json
```

The wheel must include `mplgallery/ui/frontend/dist/index.html`; source
`node_modules` are intentionally not packaged. CI also installs the built wheel
into a clean environment, creates a CSV-only external project, runs the
installed `mplgallery` console command, and briefly starts `mplgallery run`.

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

For repo-local PowerShell actions and VS Code tasks, see
[`docs/development_environment.md`](docs/development_environment.md).
