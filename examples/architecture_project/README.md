# Architecture Project Example

This fixture follows the user-level Python modeling repository architecture:

```text
analyses/response_study/
  results/
    response_curve/
      response_curve.csv
      response_curve.svg
      response_curve.mpl.yaml
    processed_response_plot/
      processed_response_plot.csv
      processed_response_plot.svg
      processed_response_plot.mpl.yaml
```

MPLGallery should discover the plot-set folders under `results/` and treat each
folder as one grouped data/figure/style unit.
