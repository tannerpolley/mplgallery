# mplgallery

`mplgallery` is a local-first CSV Plot Studio for Python analysis projects. It
expects an opinionated analysis layout, discovers CSV tables under
`analyses/<id>/data/` and `analyses/<id>/results/final/tables/`, drafts editable
Matplotlib plots, and stores
MPLGallery-owned recipes, scripts, plot-ready CSVs, and cached previews inside a
colocated `.mplgallery/` folder.

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

## Run against a project

```bash
cd /path/to/project
mplgallery run
```

`run` is an alias for `serve` and is intended as the simple installed-package
entrypoint: run it from the analysis/project root and MPLGallery starts the
local Streamlit CSV Plot Studio. PNG/SVG references and draftable CSV files are
shown together in one project file explorer.

You can also start from any folder and switch roots inside the app:

```bash
mplgallery run --choose-root
mplgallery run C:\path\to\starting\project --choose-root
```

The root chooser stores only convenience settings, such as recent project
folders, under the user config directory. Use recent roots, paste a folder path,
or use the local Browse action where the desktop folder picker is available.
Plot recipes, generated scripts, plot-ready CSVs, cached previews, and generated
figures stay inside the selected project or analysis folder.

## Scan a project

```bash
mplgallery scan /path/to/project
mplgallery scan /path/to/project --json
mplgallery validate /path/to/project
```

`scan` reports discovered architecture-standard CSV roots and draft status. It
also surfaces curated PNG/SVG references from `results/final/figures/`, but it
does not import arbitrary docs/build/test images. `validate` reports manifest
references to missing generated plot images or CSV files so ignored/generated
artifact workflows fail with a clear diagnostic instead of an empty gallery.

## CSV Plot Studio Workflow

```text
analysis_project/
  scripts/
  data/
    input/
    raw/
    processed/
    .mplgallery/
      manifest.yaml
      recipes/
      scripts/
      plot_ready/
      cache/
  analyses/
    study_id/
      data/
        input/
        raw/
        processed/
      results/
        runs/
        final/
          figures/
          tables/
          reports/
  config/
```

Source CSVs are immutable inputs. MPLGallery may sample/copy data into
`.mplgallery/plot_ready/` and render cached previews into `.mplgallery/cache/`,
but it does not edit source CSVs and does not run or manage whatever code
created them.

The expected personal project layout is:

```text
analysis_name/
  scripts/           # your data-generation and analysis scripts; MPLGallery does not run them
  data/input/        # optional upstream inputs
  data/raw/          # raw outputs from scripts/models/functions
  data/processed/    # cleaned or analysis-ready tables
  results/runs/      # disposable diagnostics; ignored by MPLGallery defaults
  results/final/figures/ # curated PNG/SVG references surfaced by default
  results/final/tables/  # curated result CSVs drafted by default
  results/final/reports/ # optional generated reports
  config/            # optional project configuration
```

By default, `serve` uses draftable CSV tables under `data/`, `plots/`, and
`results/final/tables/` roots, and it shows PNG/SVG references in the same file
explorer. Disposable `data/raw/`, `results/runs/`, docs builds, and other
scratch outputs are ignored by default. Legacy or non-standard figure folders
can still be imported explicitly with `import-artifacts`.

Initialize a CSV folder without rendering:

```bash
mplgallery init /path/to/project/data
```

Create draft recipes, generated render scripts, plot-ready CSVs, and cached SVG
previews:

```bash
mplgallery draft /path/to/project/data
mplgallery draft /path/to/project/data --json
```

Drafting infers numeric columns, chooses a simple initial plot type, writes YAML
recipes, and keeps generated artifacts under that folder's `.mplgallery/`
workspace.

## pandas And Matplotlib Responsibilities

MPLGallery uses pandas where table-shaped CSV workflows are strongest:

- load and sample CSV files;
- infer quick draft plots from column types;
- write plot-ready CSV copies under `.mplgallery/plot_ready/`;
- generate reproducible render scripts that start from `DataFrame.plot(...)`.

Matplotlib remains the editable figure contract:

- UI metadata edits persist into `.mplgallery/manifest.yaml`;
- cached rerenders apply the recipe metadata to a Matplotlib figure;
- labels, units, scales, limits, legends, grid, figure size, colors, markers,
  line styles, bar hatches, and opacity stay editable.

Source CSVs are never mutated. Any light table prep is recipe metadata and may
write derived CSVs only under `.mplgallery/plot_ready/`.

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
- Metadata Preview Mode: edit Matplotlib metadata in `.mplgallery/manifest.yaml`
  and render cached previews from plot-ready CSVs without modifying raw CSVs or
  generated plot artifacts.

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

- `examples/architecture_project`: standard `analyses/<id>/data` and
  `results/final/{figures,tables}` layout.
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
