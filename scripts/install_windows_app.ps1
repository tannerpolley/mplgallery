param(
    [string]$ExePath = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\MPLGallery",
    [switch]$DesktopShortcut
)

$ErrorActionPreference = "Stop"

function Resolve-MplGalleryExe {
    param([string]$Candidate)
    if ($Candidate) {
        return (Resolve-Path -LiteralPath $Candidate).Path
    }
    $packaged = Join-Path $PSScriptRoot "mplgallery-desktop.exe"
    if (Test-Path -LiteralPath $packaged) {
        return (Resolve-Path -LiteralPath $packaged).Path
    }
    $local = Join-Path $PSScriptRoot "..\dist\windows\mplgallery-desktop.exe"
    if (Test-Path -LiteralPath $local) {
        return (Resolve-Path -LiteralPath $local).Path
    }
    throw "Pass -ExePath or build dist\windows\mplgallery-desktop.exe first."
}

function New-Shortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$WorkingDirectory
    )
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.Description = "MPLGallery desktop app"
    $shortcut.IconLocation = "$TargetPath,0"
    $shortcut.Save()
}

function Stop-MplGalleryProcesses {
    param([string]$InstalledExe)

    $targetPath = [System.IO.Path]::GetFullPath($InstalledExe)
    $processes = Get-CimInstance Win32_Process | Where-Object {
        ($_.ExecutablePath -and ([System.IO.Path]::GetFullPath($_.ExecutablePath) -ieq $targetPath)) -or
        ($_.CommandLine -and $_.CommandLine -like "*--webview-exe-name=mplgallery-desktop.exe*")
    }
    foreach ($process in $processes) {
        if ($process.ProcessId -ne $PID) {
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($process in $processes) {
        if ($process.ProcessId -ne $PID) {
            Wait-Process -Id $process.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
        }
    }
}

$sourceExe = Resolve-MplGalleryExe -Candidate $ExePath
$installRoot = [Environment]::ExpandEnvironmentVariables($InstallDir)
$installedExe = Join-Path $installRoot "mplgallery-desktop.exe"

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
Stop-MplGalleryProcesses -InstalledExe $installedExe
Copy-Item -LiteralPath $sourceExe -Destination $installedExe -Force

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\MPLGallery"
New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
New-Shortcut `
    -ShortcutPath (Join-Path $startMenuDir "MPLGallery.lnk") `
    -TargetPath $installedExe `
    -WorkingDirectory $installRoot

if ($DesktopShortcut) {
    $desktopDir = [Environment]::GetFolderPath("Desktop")
    New-Shortcut `
        -ShortcutPath (Join-Path $desktopDir "MPLGallery.lnk") `
        -TargetPath $installedExe `
        -WorkingDirectory $installRoot
}

$uninstallScript = Join-Path $installRoot "uninstall.ps1"
@"
`$ErrorActionPreference = "Stop"
Remove-Item -LiteralPath "$startMenuDir" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath "$installRoot" -Recurse -Force -ErrorAction SilentlyContinue
"@ | Set-Content -LiteralPath $uninstallScript -Encoding UTF8

Write-Host "Installed MPLGallery to $installedExe"
Write-Host "Start Menu shortcut: $startMenuDir\MPLGallery.lnk"
if ($DesktopShortcut) {
    Write-Host "Desktop shortcut created."
}
