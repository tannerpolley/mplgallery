# Plot Gallery Package UI Handoff

## Goal

Create a separate installable software package that can add a local plot gallery workflow to a Python project that produces Matplotlib PNG/SVG images and companion CSV files.

The package should make it easy to browse generated plots, inspect CSV-backed data, and see updated plot images when CSV files change without manually rerunning plotting scripts or rebuilding a static gallery.

## Core Product Idea

- A Python project writes plot artifacts into a predictable gallery folder.
- Each plot has a generated image, preferably PNG and optionally SVG.
- Each plot can have a companion CSV file with the data needed to redraw the plot.
- A local dashboard or static browser reads those artifacts and presents them as a clean plot gallery.
- If a CSV changes, only the affected plot should update.
- The package should work around standard Matplotlib output, not Plotly.

## Strong UI Preference From The Existing `index.html`

The static `docs/plots/index.html` gallery is the best reference for the browsing experience.

Keep these parts:

- A true file-explorer-style left sidebar.
- Expandable and collapsible folder rows.
- Separate disclosure controls from folder selection checkboxes.
- Folder checkboxes select every plot in that folder and all descendants.
- Multiple folders can be checked at once.
- Search filters plots without destroying the selected folder state.
- Source tree and output tree modes are useful.
- Main content should be a responsive image grid.
- Plot images should dominate each card.
- Cards should be compact and scannable.
- A tile-size control is useful.
- Light theme, dense layout, simple borders, minimal decoration.

Avoid these regressions:

- Do not make users browse one plot at a time.
- Do not use a dropdown as the primary plot selector.
- Do not show long file paths around every plot by default.
- Do not put metadata expanders on every card by default.
- Do not let controls consume more vertical space than the plot images.
- Do not make the sidebar feel like a form instead of a file explorer.

## Streamlit Lessons

Streamlit is useful for quick local serving, polling, Python integration, and cache-backed redraws, but it is clunky for a polished tree/file-explorer UI if using only native widgets.

Good Streamlit responsibilities:

- Launch a local dashboard quickly.
- Read project plot manifests and CSV files.
- Fingerprint CSV files by size and modification time.
- Regenerate cached PNGs from changed CSVs.
- Display a live image grid.
- Show errors without crashing the whole app.

Poor Streamlit fit:

- Building a clean, native-feeling file explorer with separate expand/collapse buttons and checkboxes.
- Fine-grained compact card layout if relying only on default Streamlit cards, captions, and expanders.
- Frequent full-page refreshes with many images.

If Streamlit remains the backend, consider using a custom HTML/JS component for the tree and grid, with Streamlit/Python handling manifests, CSV fingerprinting, and Matplotlib rendering.

## Preferred Gallery Behavior

- Default view should look like a local artifact browser, not an analytics dashboard.
- Sidebar should start compact:
  - search
  - source/output tree switch
  - expand all
  - collapse all
  - clear selection
  - folder tree
- Project paths, cache paths, and debug metadata should be under an optional settings/details area.
- Main panel should show only:
  - count of visible plots
  - optional refresh/cache status
  - image grid
- Each plot card should show:
  - image first
  - small title or filename
  - only minimal status if a cached redraw or render error occurred
- File paths, SVG links, CSV paths, and raw CSV tables should be available on demand, not visible by default.

## Live Update Model

The desired update model is hybrid:

- Use pregenerated PNG files immediately.
- Watch or poll companion CSV files.
- When a CSV changes, redraw only that plot into an untracked cache directory.
- Display the cached redraw instead of overwriting the tracked/generated PNG.
- Leave full static regeneration as an explicit command.

This keeps browsing fast and avoids modifying project artifacts while the gallery is open.

## Matplotlib And CSV Requirements

- Use Matplotlib for rendering and preserve the Matplotlib visual style.
- Do not use Plotly.
- Pandas is acceptable for CSV reading and data preview.
- The redraw path should accept a simple, documented CSV schema.
- The package should provide helpers for exporting plot data from Matplotlib where possible.
- Rendering failures should be visible per plot, not fatal to the whole gallery.

## Package Direction

A separate package could expose commands like:

```powershell
uvx matplotlib-gallery init
uvx matplotlib-gallery serve
uvx matplotlib-gallery build
```

Possible package pieces:

- `manifest`: scan a project for PNG/SVG/CSV bundles.
- `export`: helpers for plot scripts to write companion CSV data.
- `render`: CSV to Matplotlib PNG/SVG redraw logic.
- `serve`: local live dashboard.
- `build`: static `index.html` gallery output.
- `cache`: untracked image cache for changed CSV redraws.

## Design Priority

The user values speed, clarity, and low-friction local review.

The correct feel is closer to a fast local file browser for plots than a custom data app. The old static `index.html` browsing model is the UI baseline; Streamlit should only be used where it makes the live Python workflow easier.

