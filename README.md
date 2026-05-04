# mplgallery

`mplgallery` is a local-first Matplotlib plot gallery for projects that generate
PNG/SVG plots from CSV data.

The package is for plot appearance only. It does not tune, fit, optimize, or
alter scientific/model computations.

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
- Metadata Preview Mode: edit Matplotlib metadata in `.mplgallery/manifest.yaml`
  and render cached previews from plot-ready CSVs without modifying raw CSVs or
  generated plot artifacts.

## Plot Formats

SVG and PNG are both supported. Prefer SVG for clean Matplotlib line plots that
need crisp scaling or publication-friendly output. Keep PNG support for dense
scatter plots, heatmaps, raster/image plots, fast cached previews, and cases
where SVG files become too large or render inconsistently across tools.

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

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```
