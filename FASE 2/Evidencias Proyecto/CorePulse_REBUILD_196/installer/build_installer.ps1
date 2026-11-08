param(
    [string]$Python = 'python',
    [string]$Iscc = 'ISCC',
    [string]$Zig = 'zig',
    [switch]$SkipNative
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $SkipNative) {
    & (Join-Path $projectRoot 'native/build_overlay.ps1') -ZigPath $Zig
    if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación nativa' }
}
Push-Location $projectRoot
try {
    & (Join-Path $PSScriptRoot 'render_assets.ps1') -Python $Python
    # No resolver DLL desde herramientas de otras aplicaciones.
    $buildPath = $env:PATH
    $env:PATH = (($env:PATH -split ';') | Where-Object {$_ -notmatch '(?i)poppler|conda'}) -join ';'
    & $Python -m PyInstaller --noconfirm --clean installer/CorePulse.spec
    if ($LASTEXITCODE -ne 0) { throw 'Falló el empaquetado de CorePulse' }
    & $Iscc ('/DPayloadDir=' + (Join-Path $projectRoot 'dist/CorePulse')) ('/DReleaseDir=' + (Join-Path $projectRoot 'release')) installer/CorePulse.iss
    if ($LASTEXITCODE -ne 0) { throw 'Falló la creación del instalador' }
    Get-FileHash -LiteralPath (Join-Path $projectRoot 'release/CorePulse_Setup_179_x64.exe') -Algorithm SHA256
} finally { $env:PATH = $buildPath; Pop-Location }
