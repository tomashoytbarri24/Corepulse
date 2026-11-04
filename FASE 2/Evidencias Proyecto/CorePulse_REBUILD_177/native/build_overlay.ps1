param(
    [string]$ZigPath = "zig",
    [switch]$KeepDebugSymbols
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$binaryDir = Join-Path $projectRoot "bin"
$vendor = Join-Path $PSScriptRoot "vendor/kiero"
$imgui = Join-Path $vendor "examples/imgui/imgui"
$backends = Join-Path $imgui "examples"
$minhook = Join-Path $vendor "minhook/src"
$zig = (Get-Command -Name $ZigPath -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $binaryDir -Force | Out-Null

$imguiSources = @(
    (Join-Path $imgui "imgui.cpp"),
    (Join-Path $imgui "imgui_draw.cpp"),
    (Join-Path $imgui "imgui_widgets.cpp"),
    (Join-Path $backends "imgui_impl_win32.cpp")
)
$hookSources = @(
    (Join-Path $minhook "buffer.c"),
    (Join-Path $minhook "hook.c"),
    (Join-Path $minhook "trampoline.c")
)

function Invoke-ZigBuild([object[]]$Arguments) {
    $flat = foreach ($argument in $Arguments) {
        if ($argument -is [array]) {
            foreach ($item in $argument) { [string]$item }
        } else {
            [string]$argument
        }
    }
    & $zig c++ @flat
    if ($LASTEXITCODE -ne 0) {
        throw "Compilación nativa fallida: $($Arguments[-1])"
    }
}

Push-Location $projectRoot
try {
    Invoke-ZigBuild @(
        "native/capture_guard.cpp", "-target", "x86_64-windows-gnu", "-O2", "-municode",
        "-o", (Join-Path $binaryDir "CorePulseCaptureGuard.exe"), "-ladvapi32"
    )
    Invoke-ZigBuild @(
        "native/overlay_host.cpp", "-target", "x86_64-windows-gnu",
        "-O2", "-o", (Join-Path $binaryDir "CorePulseOverlayHost.exe"),
        "-luser32", "-lgdi32", "-ldwmapi", "-lshcore", "-lmsimg32"
    )
    foreach ($arch in @("x86_64", "x86")) {
        $suffix = if ($arch -eq "x86_64") { "x64" } else { "x86" }
        $target = "$arch-windows-gnu"
        $hde = if ($arch -eq "x86_64") { "hde64.c" } else { "hde32.c" }
        Invoke-ZigBuild @(
            "native/hook_loader.cpp", "-target", $target, "-O2", "-municode",
            "-o", (Join-Path $binaryDir "CorePulseHookLoader-$suffix.exe"),
            "-luser32", "-lkernel32"
        )
        foreach ($api in @("D3D9", "D3D10", "D3D11", "D3D12")) {
            $source = "native/gamehook_$($api.ToLowerInvariant()).cpp"
            $backend = "imgui_impl_$($api.ToLowerInvariant().Replace('d3d', 'dx')).cpp"
            $lib = $api.ToLowerInvariant()
            $extra = @()
            if ($api -in @("D3D10", "D3D11", "D3D12")) {
                $extra += "-ld3dcompiler_47"
            }
            if ($api -eq "D3D12") {
                if ($arch -eq "x86") { $extra += "-DImTextureID=uint64_t" }
            }
            Invoke-ZigBuild (@(
                $source, (Join-Path $vendor "kiero.cpp"),
                $hookSources, (Join-Path $minhook "hde/$hde"),
                $imguiSources, (Join-Path $backends $backend),
                "-target", $target,
                "-DKIERO_INCLUDE_$api=1", "-DKIERO_USE_MINHOOK=1",
                "-I", $imgui, "-shared", "-O2",
                "-o", (Join-Path $binaryDir "CorePulseGameHook$api-$suffix.dll"),
                "-luser32", "-lgdi32", "-limm32", "-lxinput1_4", "-ldxgi", "-l$lib"
            ) + $extra)
        }
        Invoke-ZigBuild @(
            "native/gamehook_opengl.cpp", $hookSources,
            (Join-Path $minhook "hde/$hde"), $imguiSources,
            (Join-Path $backends "imgui_impl_opengl2.cpp"),
            (Join-Path $backends "imgui_impl_opengl3.cpp"),
            (Join-Path $backends "libs/gl3w/GL/gl3w.c"),
            "-target", $target, "-I", (Join-Path $backends "libs/gl3w"),
            "-I", $imgui, "-shared", "-O2",
            "-o", (Join-Path $binaryDir "CorePulseGameHookOpenGL-$suffix.dll"),
            "-luser32", "-lgdi32", "-limm32", "-lxinput1_4", "-lopengl32"
        )
    }
    if (-not $KeepDebugSymbols) {
        Get-ChildItem -LiteralPath $binaryDir -Filter "CorePulse*.pdb" -File |
            Remove-Item -Force
        Get-ChildItem -LiteralPath $binaryDir -Filter "gamehook_*.lib" -File |
            Remove-Item -Force
    }
} finally {
    Pop-Location
}
