# Freeze YTSDownloader (PyQt6 Suite) with PyInstaller onedir on Windows.
# Run on Windows — PyInstaller does not cross-compile.
# Invoke from repo root:  .\scripts\build_pyinstaller.ps1
# No Activate.ps1 required; uses .venv\Scripts\python.exe directly.
# Optional: $env:BUNDLE_NATIVES = "auto"|"1"|"0" — copy native\bin next to the freeze
#   (auto=default: copy if repo native\bin is non-empty; 1=require; 0=skip).
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

# Optional: $env:YTS_PYTHON = "C:\path\to\python.exe"
if ($env:YTS_PYTHON) {
    $Py = $env:YTS_PYTHON
} else {
    $Py = Join-Path $Root ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Py)) {
    Write-Error "missing $Py — create the venv and install requirements.txt first (or set YTS_PYTHON)"
}

foreach ($req in @("main.py", "config.ini")) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $req))) {
        Write-Error "run from a complete checkout (main.py, config.ini, themes/)"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $Root "themes") -PathType Container)) {
    Write-Error "run from a complete checkout (main.py, config.ini, themes/)"
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffmpeg -or -not $ffprobe) {
    Write-Warning "ffmpeg/ffprobe not on PATH — freeze may succeed, but download/mux needs them at runtime"
}

& $Py -m pip install -U "pyinstaller>=6.11"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Themes = Join-Path $Root "themes"
$Assets = Join-Path $Root "assets"
$IconPng = Join-Path $Root "assets\icons\256x256\ytsdownloader.png"
$Config = Join-Path $Root "config.ini"
$Main = Join-Path $Root "main.py"
$SpecPath = Join-Path $Root "build"
$WorkPath = Join-Path $Root "build\pyi"
$DistPath = Join-Path $Root "dist"

# ';' remains the Windows --add-data separator; absolute sources avoid specpath resolution bugs.
& $Py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name YTSDownloader `
    --onedir `
    --paths $Root `
    --collect-all yt_dlp `
    --collect-all imageio_ffmpeg `
    --collect-all moviepy `
    --collect-submodules ytscore `
    --collect-submodules ytsgui `
    --hidden-import PIL `
    --add-data "$Themes;themes" `
    --add-data "$Assets;assets" `
    --add-data "$Config;." `
    --icon $IconPng `
    --specpath $SpecPath `
    --workpath $WorkPath `
    --distpath $DistPath `
    $Main
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Out = Join-Path $Root "dist\YTSDownloader"
# Suite reads config.ini / themes/ / assets from process cwd (not only from _internal datas).
Copy-Item -LiteralPath $Config -Destination (Join-Path $Out "config.ini") -Force
$OutThemes = Join-Path $Out "themes"
if (Test-Path -LiteralPath $OutThemes) {
    Remove-Item -LiteralPath $OutThemes -Recurse -Force
}
Copy-Item -LiteralPath $Themes -Destination $OutThemes -Recurse -Force
$OutAssets = Join-Path $Out "assets"
if (Test-Path -LiteralPath $OutAssets) {
    Remove-Item -LiteralPath $OutAssets -Recurse -Force
}
Copy-Item -LiteralPath $Assets -Destination $OutAssets -Recurse -Force

# Optional native sidecars: ship as <onedir>\native\bin\ (Suite discovers via native_bridge).
$SrcNative = Join-Path $Root "native\bin"
$BundleMode = if ($env:BUNDLE_NATIVES) { $env:BUNDLE_NATIVES } else { "auto" }
if ($BundleMode -ne "0") {
    $HasNatives = $false
    if (Test-Path -LiteralPath $SrcNative -PathType Container) {
        $HasNatives = @(Get-ChildItem -LiteralPath $SrcNative -Force -ErrorAction SilentlyContinue).Count -gt 0
    }
    if ($HasNatives) {
        $OutNativeRoot = Join-Path $Out "native"
        if (Test-Path -LiteralPath $OutNativeRoot) {
            Remove-Item -LiteralPath $OutNativeRoot -Recurse -Force
        }
        $OutNativeBin = Join-Path $OutNativeRoot "bin"
        New-Item -ItemType Directory -Path $OutNativeBin -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $SrcNative "*") -Destination $OutNativeBin -Recurse -Force
        Write-Host "Bundled native\bin\ → $OutNativeBin\"
    } elseif ($BundleMode -eq "1") {
        Write-Warning "BUNDLE_NATIVES=1 but $SrcNative is empty — run .\scripts\build_natives.sh (or WSL) first"
    } else {
        Write-Host "Note: no native\bin\ to bundle (Python fallbacks). Build natives then re-freeze, or set BUNDLE_NATIVES=0 to silence."
    }
}

Write-Host ""
Write-Host "Built: $Out\"
Write-Host "Ship the entire folder. Runtime still needs ffmpeg and ffprobe on PATH."
Write-Host "Optional natives live under native\bin\ next to the binary when bundled."
Write-Host "Try:  cd dist\YTSDownloader; .\YTSDownloader.exe"
