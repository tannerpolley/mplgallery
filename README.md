# mplgallery

`mplgallery` is a local-first Matplotlib plot gallery for projects that generate
PNG/SVG plots from CSV data.

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
uv run mplgallery serve examples/sample_project
```

Optional DVC and MLflow integrations are not installed by default:

```bash
pip install "mplgallery[dvc,mlflow]"
```

## Run against a project

```bash
mplgallery serve /path/to/project
```

## Scan a project

```bash
mplgallery scan /path/to/project
mplgallery scan /path/to/project --json
mplgallery validate /path/to/project
```

`validate` reports manifest references to missing generated plot images or CSV
files so ignored/generated artifact workflows fail with a clear diagnostic
instead of an empty gallery.

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

## Recommended Analysis Group Layout

```text
analysis_group/
  data/raw/
  data/plot_ready/
  plots/
  scripts/generate_data.py
  scripts/render_plots.py
  .mplgallery/manifest.yaml
  .mplgallery/cache/
```

Use `raw_csv_path` for immutable model/function outputs and `plot_csv_path` for
the CSV that MPLGallery reads with pandas for previews and metadata editing.

## Example Projects

- `examples/sample_project`: original browser-first sample with PNG and SVG.
- `examples/generic_plots_project`: line and scatter examples.
- `examples/distribution_plots_project`: bar and histogram examples.
- `examples/install_smoke_project`: minimal project used to test installed wheels.

To browse every included example project in one app:

```bash
uv run mplgallery serve examples
```

Regenerate an example project with its local scripts if you want to refresh the
assets:

```bash
uv run --no-sync python examples/generic_plots_project/scripts/generate_data.py
uv run --no-sync python examples/generic_plots_project/scripts/render_plots.py
```

## Wheel Smoke Test

To verify the package works in a separate environment:

```bash
uv run --no-sync python -m build
python -m venv .wheel-smoke-venv
.wheel-smoke-venv\Scripts\pip install dist\*.whl
.wheel-smoke-venv\Scripts\mplgallery.exe scan examples/install_smoke_project
```

The wheel must include `mplgallery/ui/frontend/dist/index.html`; source
`node_modules` are intentionally not packaged.

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

For repo-local PowerShell actions and VS Code tasks, see
[`docs/development_environment.md`](docs/development_environment.md).
