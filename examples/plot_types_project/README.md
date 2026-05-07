# Plot Types Project

This example is the main mixed file-explorer fixture for MPLGallery. The
`results/<plot_set>/` folders contain the plotted CSV snapshot, PNG/SVG
figure, and `.mpl.yaml` sidecar for each supported plot type:

- line
- scatter
- bar
- barh
- area
- hist
- step

Regenerate the fixture with:

```powershell
uv run --no-sync python examples/plot_types_project/scripts/generate_plot_types.py
```
