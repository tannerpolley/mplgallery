# mplgallery

`mplgallery` is a local-first Matplotlib plot gallery for projects that generate
PNG/SVG plots from CSV data.

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
- Recipe Mode: edit and regenerate Matplotlib plots using `.mplg.yaml` recipe
  metadata.

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```
