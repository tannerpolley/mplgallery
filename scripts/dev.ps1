param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "help",
        "sync",
        "serve",
        "serve-examples",
        "preview-url",
        "preview-url-examples",
        "desktop",
        "desktop-examples",
        "scan",
        "test",
        "lint",
        "check",
        "frontend-install",
        "frontend-test",
        "frontend-build",
        "build",
        "windows-dist",
        "wheel-smoke"
    )]
    [string] $Action = "help",

    [Parameter(Position = 1)]
    [string] $Project = "examples",

    [int] $Port = 8507
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendRoot = Join-Path $RepoRoot "src\mplgallery\ui\frontend"
$SmokeVenv = Join-Path $RepoRoot ".wheel-smoke-venv"

function Invoke-Repo {
    param([string[]] $Command)
    Push-Location $RepoRoot
    try {
        $Executable = $Command[0]
        $Arguments = if ($Command.Length -gt 1) { $Command[1..($Command.Length - 1)] } else { @() }
        & $Executable @Arguments
    }
    finally {
        Pop-Location
    }
}

function Invoke-Frontend {
    param([string[]] $Command)
    Push-Location $FrontendRoot
    try {
        $Executable = $Command[0]
        $Arguments = if ($Command.Length -gt 1) { $Command[1..($Command.Length - 1)] } else { @() }
        & $Executable @Arguments
    }
    finally {
        Pop-Location
    }
}

function Show-Help {
    @"
mplgallery dev actions

Usage:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 <action> [project] [-Port 8507]

Core actions:
  sync             uv sync --dev
  serve            uv run mplgallery serve <project> (static browser preview)
  serve-examples   uv run mplgallery serve examples (static browser preview)
  preview-url      uv run mplgallery preview-url <project> (prints localhost preview URL)
  preview-url-examples
                   uv run mplgallery preview-url examples (prints localhost preview URL)
  desktop          uv run mplgallery desktop <project>
  desktop-examples uv run mplgallery desktop examples
  scan             uv run mplgallery scan <project>
  test             uv run pytest
  lint             uv run ruff check .
  check            test + lint

Frontend actions:
  frontend-install npm install in the React frontend folder
  frontend-test    npm run test
  frontend-build   npm run build

Packaging actions:
  build            uv run --no-sync python -m build
  windows-dist     build frontend, Tauri executable, setup EXE, Windows ZIP, and build report
  wheel-smoke      build wheel, install it in .wheel-smoke-venv, scan install_smoke_project

Examples:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 sync
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 desktop examples
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 scan examples\sample_project
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1 check
"@
}

switch ($Action) {
    "help" {
        Show-Help
    }
    "sync" {
        Invoke-Repo @("uv", "sync", "--dev")
    }
    "serve" {
        Invoke-Repo @("uv", "run", "mplgallery", "serve", $Project)
    }
    "serve-examples" {
        Invoke-Repo @("uv", "run", "mplgallery", "serve", "examples")
    }
    "preview-url" {
        Invoke-Repo @("uv", "run", "mplgallery", "preview-url", $Project)
    }
    "preview-url-examples" {
        Invoke-Repo @("uv", "run", "mplgallery", "preview-url", "examples")
    }
    "desktop" {
        Invoke-Repo @("uv", "run", "mplgallery", "desktop", $Project)
    }
    "desktop-examples" {
        Invoke-Repo @("uv", "run", "mplgallery", "desktop", "examples")
    }
    "scan" {
        Invoke-Repo @("uv", "run", "mplgallery", "scan", $Project)
    }
    "test" {
        Invoke-Repo @("uv", "run", "pytest")
    }
    "lint" {
        Invoke-Repo @("uv", "run", "ruff", "check", ".")
    }
    "check" {
        Invoke-Repo @("uv", "run", "pytest")
        Invoke-Repo @("uv", "run", "ruff", "check", ".")
    }
    "frontend-install" {
        Invoke-Frontend @("npm", "install")
    }
    "frontend-test" {
        Invoke-Frontend @("npm", "run", "test")
    }
    "frontend-build" {
        Invoke-Frontend @("npm", "run", "build")
    }
    "build" {
        Invoke-Repo @("uv", "run", "--no-sync", "python", "-m", "build")
    }
    "windows-dist" {
        Invoke-Repo @("uv", "run", "--no-sync", "python", "scripts\build_windows_dist.py")
    }
    "wheel-smoke" {
        Invoke-Repo @("uv", "run", "--no-sync", "python", "-m", "build")
        if (!(Test-Path $SmokeVenv)) {
            Invoke-Repo @("python", "-m", "venv", ".wheel-smoke-venv")
        }
        $Wheel = Get-ChildItem -LiteralPath (Join-Path $RepoRoot "dist") -Filter "*.whl" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($null -eq $Wheel) {
            throw "No wheel found in dist after build."
        }
        Invoke-Repo @((Join-Path $SmokeVenv "Scripts\python.exe"), "-m", "pip", "install", "--force-reinstall", $Wheel.FullName)
        $InstalledDist = & (Join-Path $SmokeVenv "Scripts\python.exe") -c "from pathlib import Path; import mplgallery.ui.component as c; print(c._FRONTEND_BUILD_DIR / 'index.html')"
        if (!(Test-Path -LiteralPath $InstalledDist)) {
            throw "Installed wheel is missing frontend dist/index.html: $InstalledDist"
        }
        Invoke-Repo @((Join-Path $SmokeVenv "Scripts\mplgallery.exe"), "scan", "examples\install_smoke_project")
    }
}
