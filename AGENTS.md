# AGENTS.md

## Project Goal

Build `mplgallery`, an installable Python package that provides a local
Streamlit UI for discovering, grouping, previewing, and lightly editing
project-owned Matplotlib plot sets.

The primary personal project layout is:

```text
analysis_name/
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

## Product Assumptions

- The package is local-first.
- Future team/shared-server support should remain possible.
- Streamlit is the UI layer.
- pandas is used for CSV loading, previewing, validation, and summary statistics.
- Matplotlib is the canonical rendering engine.
- MPLGallery is only for plot-set discovery, grouping, previewing, plot appearance, and reference artifact browsing; it must not
  tune, fit, optimize, or alter scientific/model computations.
- DVC is the regeneration/dependency-tracking layer.
- MLflow is the run/artifact/history layer.
- Full-feature v1 expects one plot-set folder per figure or figure family under
  `results/<plot_set>/`.
- Default v1 discovery focuses on `results/**` plot sets. Old CSV-first or
  project-wide discovery should remain explicit compatibility behavior.
- A plot set may contain CSV, SVG, PNG, PDF, `.mpl.yaml`, and provenance files.
- Every plotted series, including literature/reference points, should be
  snapshotted inside the plot set.
- Project scripts and coding agents own scientific computation and final figure
  generation. MPLGallery groups, previews, edits sidecar metadata, and may run
  only explicit render commands declared in `.mpl.yaml`.
- `.mplgallery/manifest.yaml` is project-local and hidden from normal browsing;
  it stores grouping overrides, app UI metadata, cache/index fingerprints, and
  scan state.
- Legacy `csv_path` may remain as a compatibility alias for `plot_csv_path`.
- Live browsing and cached redraws must not overwrite generated plot artifacts.
- Live metadata edits for editable plot sets persist to `<plot_set>.mpl.yaml`,
  not to CSV files.
- Any explicit future overwrite action must create a backup first.
- `.mplgallery/cache` is for app cache/index state and must not be surfaced as
  project plot output.
- Static gallery mode must be read-only.
- True Matplotlib-level editing requires `.mpl.yaml` sidecar metadata.

## Engineering Rules

- Use `uv` as the primary Python package and environment manager for local
  development.
- Use a `src/` package layout.
- Keep business logic separate from Streamlit UI code.
- Prefer small modules with unit tests.
- Do not place project-scanning logic directly inside Streamlit callbacks.
- Do not make Streamlit responsible for DVC dependency logic.
- Do not make MLflow required for static gallery browsing of a target project.
- Do not modify target analysis projects except through explicit overwrite or
  regeneration actions.
- Do not overwrite any plot without first creating a backup.
- Do not mutate source CSVs or plot-set CSV snapshots.
- Do not infer or run arbitrary Python render scripts. Only run commands
  explicitly declared in `.mpl.yaml`.
- Do not add model tuning, fitting, parameter optimization, or data-generation
  controls to the UI.
- Keep the first user-facing UI closer to a file explorer than an analytics
  dashboard.
- Avoid implementing all milestones in one pass.

## Release Rules

- When a user-facing app feature, installer behavior, update behavior, or
  desktop distribution change is committed to `main`, treat it as release-bound
  by default.
- For release-bound changes, bump the project version in both `pyproject.toml`
  and `src/mplgallery/__init__.py`, rebuild the Windows distribution, tag the
  version, and publish GitHub release assets so installed Windows apps can find
  the update automatically.
- Do not leave major feature work only on `main` at the same version as the
  currently published GitHub release unless the user explicitly asks to defer
  packaging or release publication.
- The update button only appears when GitHub Releases has a newer semantic
  version than the installed app. If a feature was pushed but not released, the
  installed app will correctly report no update.
- Validate update-button behavior from the frozen Windows executable, not only
  `uv run mplgallery serve`, because install actions depend on
  `sys.frozen == True` and use the packaged Windows update helper.
- For update-button QA, use a controlled fake latest-release endpoint when
  needed, click the button in Browser, and confirm the UI shows either
  `Downloading update...`, `Update installer started`, or a visible
  `Update install failed: ...` status instead of appearing inert.
- Build and release the Windows ZIP asset alongside the setup EXE. The app
  updater downloads the ZIP because it contains `mplgallery-desktop.exe`,
  `install_windows_app.ps1`, and wrapper files needed for in-app updates.

## Commands

Run these before considering a task complete:

```bash
uv run pytest
uv run ruff check .
```

Use this for local development:

```bash
uv sync --dev
uv run mplgallery serve examples
```
