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
.wheel-smoke-venv\Scripts\python -m mplgallery scan examples/install_smoke_project
```

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```
