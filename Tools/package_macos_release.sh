#!/bin/bash
set -euo pipefail

workspace_root="$(cd "$(dirname "$0")/.." && pwd)"
version="${STUDIOFORGE_VERSION:-1.0.0}"
architecture="${STUDIOFORGE_ARCHITECTURE:-arm64}"
build_dir="${STUDIOFORGE_BUILD_DIR:-$workspace_root/build-live-release}"
release_root="${STUDIOFORGE_RELEASE_DIR:-$workspace_root/release}"
stage="$release_root/StudioForge-$version-macOS-$architecture"
dmg="$release_root/StudioForge-$version-macOS-$architecture.dmg"
zip="$release_root/StudioForge-$version-macOS-$architecture.zip"
identity="${MACOS_SIGN_IDENTITY:--}"
default_panel_source="$workspace_root/tune-AI/dist/THM Vocal Panel.app"
if [[ ! -d "$default_panel_source" ]]; then
    default_panel_source="$workspace_root/dist/THM Vocal Panel.app"
fi
panel_source="${TUNE_AI_APP_PATH:-$default_panel_source}"
daw_source="$build_dir/StudioForgeDAW_artefacts/Release/StudioForge DAW.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macOS packaging must run on macOS" >&2
    exit 2
fi
if [[ "$architecture" != "arm64" && "$architecture" != "x86_64" && "$architecture" != "universal2" ]]; then
    echo "Unsupported STUDIOFORGE_ARCHITECTURE=$architecture" >&2
    exit 2
fi

if [[ "${STUDIOFORGE_REBUILD_TUNE_AI:-1}" != "0" ]]; then
    "$workspace_root/Tools/build_tune_ai_macos.sh"
    panel_source="$workspace_root/tune-AI/dist/THM Vocal Panel.app"
fi

build_jobs="${STUDIOFORGE_BUILD_JOBS:-}"
if [[ -z "$build_jobs" ]]; then
    build_jobs="$(sysctl -n hw.logicalcpu 2>/dev/null || true)"
fi
if [[ -z "$build_jobs" ]]; then
    build_jobs=4
fi
cmake --build "$build_dir" --target StudioForgeDAW -j "$build_jobs"
[[ -d "$daw_source" ]] || { echo "Missing DAW artifact: $daw_source" >&2; exit 3; }
[[ -d "$panel_source" ]] || { echo "Missing AutoKey artifact: $panel_source" >&2; exit 3; }

cmake -E remove_directory "$stage"
mkdir -p "$stage"
ditto "$daw_source" "$stage/StudioForge Live DAW.app"
ditto "$panel_source" "$stage/Tune-AI.app"
for app in "$stage/StudioForge Live DAW.app" "$stage/Tune-AI.app"; do
    plutil -replace CFBundleShortVersionString -string "$version" "$app/Contents/Info.plist"
    plutil -replace CFBundleVersion -string "$version" "$app/Contents/Info.plist"
done

daw_entitlements="$workspace_root/Packaging/macOS/StudioForgeDAW.entitlements"
panel_entitlements="$workspace_root/Packaging/macOS/TuneAI.entitlements"
sign_code() {
    local target="$1"
    local entitlements="${2:-}"
    if [[ "$identity" == "-" ]]; then
        if [[ -n "$entitlements" ]]; then
            codesign --force --deep --sign - --entitlements "$entitlements" "$target"
        else
            codesign --force --deep --sign - "$target"
        fi
    elif [[ -n "$entitlements" ]]; then
        codesign --force --deep --timestamp --options runtime --sign "$identity" \
            --entitlements "$entitlements" "$target"
    else
        codesign --force --deep --timestamp --options runtime --sign "$identity" "$target"
    fi
}

# Sign nested code first. --deep is retained for the PyInstaller application
# because its collected framework topology is generated rather than declared
# by this build; the final strict verification and release audit fail closed.
sign_code "$stage/StudioForge Live DAW.app/Contents/Resources/Helpers/StudioForgeVst3Probe"
if [[ -d "$stage/StudioForge Live DAW.app/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3" ]]; then
    sign_code "$stage/StudioForge Live DAW.app/Contents/Resources/PlugIns/VST3/VibeAutotune.vst3"
fi
sign_code "$stage/Tune-AI.app" "$panel_entitlements"
sign_code "$stage/StudioForge Live DAW.app" "$daw_entitlements"

audit_args=("$stage" --architecture "$architecture")
if [[ "$identity" != "-" ]]; then
    audit_args+=(--require-developer-id)
fi
python3 "$workspace_root/Tools/audit_macos_release.py" "${audit_args[@]}"

cmake -E remove -f "$dmg"
cmake -E remove -f "$zip"
dmg_stage="$(mktemp -d "${TMPDIR:-/tmp}/studioforge-dmg.XXXXXX")"
trap 'cmake -E remove_directory "$dmg_stage"' EXIT
ditto "$stage/StudioForge Live DAW.app" "$dmg_stage/StudioForge Live DAW.app"
ditto "$stage/Tune-AI.app" "$dmg_stage/Tune-AI.app"
ln -s /Applications "$dmg_stage/Applications"
artifact="$dmg"
if ! hdiutil create -quiet -volname "StudioForge $version" -srcfolder "$dmg_stage" -format UDZO "$dmg"; then
    if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
        echo "DMG creation failed; refusing to continue a notarized release" >&2
        exit 5
    fi
    # CI/sandboxed macOS runners may not expose the disk-image device. Keep a
    # Finder-safe ZIP fallback so the exact audited apps are still testable.
    echo "DMG device unavailable; creating a Finder-safe ZIP instead" >&2
    ditto -c -k --sequesterRsrc "$dmg_stage" "$zip"
    artifact="$zip"
fi

if [[ "$identity" != "-" && "$artifact" == "$dmg" ]]; then
    codesign --force --timestamp --sign "$identity" "$dmg"
fi
if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
    [[ "$identity" != "-" ]] || { echo "Notarization requires MACOS_SIGN_IDENTITY" >&2; exit 4; }
    xcrun notarytool submit "$dmg" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
    xcrun stapler staple "$dmg"
    spctl --assess --type open --context context:primary-signature --verbose=2 "$dmg"
fi

echo "Packaged: $artifact"
