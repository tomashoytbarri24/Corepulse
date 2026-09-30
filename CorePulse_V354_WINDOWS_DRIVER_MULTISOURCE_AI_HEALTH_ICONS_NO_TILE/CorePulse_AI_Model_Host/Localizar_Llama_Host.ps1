param(
    [switch]$Quiet
)

$ErrorActionPreference = 'SilentlyContinue'

function Emit-Path([string]$Path) {
    if ($Path -and (Test-Path -LiteralPath $Path -PathType Leaf)) {
        try {
            $resolved = (Resolve-Path -LiteralPath $Path).Path
        } catch {
            $resolved = $Path
        }
        Write-Output $resolved
        exit 0
    }
}

# 1) PATH actual. Se aceptan las dos formas que llama.cpp ha distribuido en Windows:
#    - llama.exe (frontend unificado: `llama serve`)
#    - llama-server.exe (binario de servidor portable)
foreach ($name in @('llama.exe', 'llama-server.exe')) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) { Emit-Path $cmd.Source }
}

# 2) Enlaces portables creados por WinGet. Esto funciona en la MISMA consola donde
#    acabamos de instalar el paquete, sin exigir cerrar y abrir el BAT.
$linkRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'
foreach ($name in @('llama.exe', 'llama-server.exe')) {
    Emit-Path (Join-Path $linkRoot $name)
}

# 3) Fallback: buscar el binario real dentro de los directorios de paquetes WinGet.
$roots = @()
if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages') }
if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles 'WinGet\Packages') }

foreach ($root in $roots) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    foreach ($name in @('llama.exe', 'llama-server.exe')) {
        $hit = Get-ChildItem -LiteralPath $root -Filter $name -File -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { Emit-Path $hit.FullName }
    }
}

if (-not $Quiet) {
    Write-Error 'No se encontro llama.exe ni llama-server.exe.'
}
exit 1
