param(
    [string]$Version = "1.0.0",
    [string]$BuildDir = "build-windows-x64",
    [string]$DriverPackage = $env:STUDIOFORGE_WINDOWS_DRIVER_PACKAGE,
    [string]$SigningSubject = $env:STUDIOFORGE_WINDOWS_SIGNING_SUBJECT
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $IsWindows) { throw "Windows packaging must run on Windows." }
if ([string]::IsNullOrWhiteSpace($DriverPackage) -or -not (Test-Path $DriverPackage)) {
    throw "Missing Microsoft-signed StudioForge Link driver package. Packaging is blocked."
}
if ([string]::IsNullOrWhiteSpace($env:STUDIOFORGE_ASIO_SDK_DIR) -or
    -not (Test-Path $env:STUDIOFORGE_ASIO_SDK_DIR)) {
    throw "STUDIOFORGE_ASIO_SDK_DIR must point to the licensed ASIO SDK."
}
if ([string]::IsNullOrWhiteSpace($SigningSubject)) {
    throw "STUDIOFORGE_WINDOWS_SIGNING_SUBJECT is required for a release build."
}

$signtool = Get-Command signtool.exe -ErrorAction Stop
$driverFiles = Get-ChildItem -Path $DriverPackage -Recurse -Include *.sys,*.cat
if (-not $driverFiles) { throw "Driver package contains no SYS/CAT files." }
foreach ($file in $driverFiles) {
    & $signtool.Source verify /pa /v $file.FullName
    if ($LASTEXITCODE -ne 0) { throw "Driver signature verification failed: $($file.FullName)" }
}

cmake -S $Root -B (Join-Path $Root $BuildDir) -G "Visual Studio 17 2022" -A x64 `
    -DSTUDIOFORGE_ASIO_SDK_DIR="$env:STUDIOFORGE_ASIO_SDK_DIR" -DBUILD_TESTING=ON
cmake --build (Join-Path $Root $BuildDir) --config Release --target StudioForgeDAW StudioForgeCoreTests
ctest --test-dir (Join-Path $Root $BuildDir) -C Release --output-on-failure

Push-Location (Join-Path $Root "tune-AI")
try {
    pyinstaller --noconfirm "THM Vocal Panel.spec"
} finally {
    Pop-Location
}

# Installer authoring is deliberately not guessed here. This gate becomes the
# input to WiX/MSIX only after the Microsoft-signed driver and its supported
# install/uninstall commands are delivered by the Windows driver project.
throw "Build inputs verified. Final Windows installer awaits the signed driver install contract."
