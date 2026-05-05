# Development Environment

This project uses `uv` as the primary Python package and environment manager.
Use Node only for the packaged Streamlit frontend component under
`src/mplgallery/ui/frontend`.

## First Setup

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 sync
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 frontend-install
```

The Python environment is created in `.venv`. VS Code is configured to use
`.venv\Scripts\python.exe`.

## Common Actions

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 serve-examples -Port 8507
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 serve examples\sample_project -Port 8507
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 scan examples
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 check
```

`mplgallery serve` runs Streamlit in headless mode, so it hosts the local URL
without opening an extra browser tab.

Open the running app at:

```text
http://localhost:8507/
```

## Frontend Component Actions

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 frontend-test
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 frontend-build
```

Run `frontend-build` after editing `src/mplgallery/ui/frontend/src` so the
packaged component assets under `src/mplgallery/ui/frontend/dist` are refreshed.

## Packaging Actions

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 build
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 wheel-smoke
```

`wheel-smoke` builds the package, installs the newest wheel into
`.wheel-smoke-venv`, and runs:

```powershell
python -m mplgallery scan examples\install_smoke_project
```

## VS Code Tasks

The repo includes `.vscode/tasks.json` for these actions:

- `mplgallery: sync dev env`
- `mplgallery: serve examples`
- `mplgallery: scan examples`
- `mplgallery: check`
- `mplgallery: frontend test`
- `mplgallery: frontend build`
- `mplgallery: build wheel`
- `mplgallery: wheel smoke`

Use `Terminal: Run Task` in VS Code to launch them.
