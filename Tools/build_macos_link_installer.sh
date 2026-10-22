#!/bin/bash
set -euo pipefail
export COPYFILE_DISABLE=1

workspace_root="$(cd "$(dirname "$0")/.." && pwd)"
version="${STUDIOFORGE_VERSION:-1.0.0}"
architecture="${STUDIOFORGE_ARCHITECTURE:-arm64}"
build_dir="${STUDIOFORGE_BUILD_DIR:-$workspace_root/build-live-release}"
release_root="${STUDIOFORGE_RELEASE_DIR:-$workspace_root/release}"
application_identity="${MACOS_SIGN_IDENTITY:--}"
installer_identity="${MACOS_INSTALLER_IDENTITY:-}"
release_channel="${STUDIOFORGE_RELEASE_CHANNEL:-qa}"
bundle="$build_dir/router-link/StudioForgeLinkHAL.driver"
package="$release_root/StudioForge-Link-$version-macOS-$architecture.pkg"

[[ "$(uname -s)" == "Darwin" ]] || { echo "This installer must be built on macOS" >&2; exit 2; }
[[ "$architecture" == "arm64" || "$architecture" == "x86_64" ]] || {
    echo "HAL installer currently requires one explicit architecture" >&2; exit 2;
}
[[ "$release_channel" == "qa" || "$release_channel" == "public" ]] || {
    echo "STUDIOFORGE_RELEASE_CHANNEL must be qa or public" >&2; exit 2;
}
if [[ "$release_channel" == "public" ]]; then
    [[ "$application_identity" != "-" ]] || {
        echo "Public HAL release requires MACOS_SIGN_IDENTITY (Developer ID Application)" >&2; exit 4;
    }
    [[ -n "$installer_identity" ]] || {
        echo "Public HAL release requires MACOS_INSTALLER_IDENTITY (Developer ID Installer)" >&2; exit 4;
    }
    [[ -n "${MACOS_NOTARY_PROFILE:-}" ]] || {
        echo "Public HAL release requires MACOS_NOTARY_PROFILE" >&2; exit 4;
    }
fi

cmake --build "$build_dir" --target StudioForgeLinkHAL -j "${STUDIOFORGE_BUILD_JOBS:-4}"
if cmake --build "$build_dir" --target help 2>/dev/null | grep -q 'StudioForgeLinkHalFoundationTests'; then
    cmake --build "$build_dir" --target StudioForgeLinkHalFoundationTests -j "${STUDIOFORGE_BUILD_JOBS:-4}"
    "$build_dir/router-link/StudioForgeLinkHalFoundationTests"
fi
[[ -d "$bundle" ]] || { echo "Missing HAL bundle: $bundle" >&2; exit 3; }

if [[ "$application_identity" != "-" ]]; then
    codesign --force --timestamp --options runtime --sign "$application_identity" "$bundle"
fi
audit_args=("$bundle" --architecture "$architecture")
[[ "$application_identity" == "-" ]] || audit_args+=(--require-developer-id)
python3 "$workspace_root/Tools/audit_macos_link_driver.py" "${audit_args[@]}"

payload="$(mktemp -d "${TMPDIR:-/tmp}/studioforge-link-payload.XXXXXX")"
trap 'cmake -E remove_directory "$payload"' EXIT
install_dir="$payload/Library/Audio/Plug-Ins/HAL"
mkdir -p "$install_dir" "$release_root"
COPYFILE_DISABLE=1 ditto --norsrc --noextattr "$bundle" "$install_dir/StudioForgeLinkHAL.driver"
xattr -cr "$payload"

pkg_args=(--root "$payload" --identifier com.studioforge.link.hal.pkg
          --version "$version" --install-location /
          --scripts "$workspace_root/Packaging/macOS/link-driver-scripts"
          --component-plist "$workspace_root/Packaging/macOS/StudioForgeLinkHAL-component.plist")
if [[ -n "$installer_identity" ]]; then
    pkg_args+=(--sign "$installer_identity")
fi
pkgbuild "${pkg_args[@]}" "$package"
pkgutil --payload-files "$package" | grep -q 'Library/Audio/Plug-Ins/HAL/StudioForgeLinkHAL.driver'

if [[ -n "${MACOS_NOTARY_PROFILE:-}" ]]; then
    [[ -n "$installer_identity" && "$application_identity" != "-" ]] || {
        echo "Notarization requires Developer ID Application and Installer identities" >&2; exit 4;
    }
    xcrun notarytool submit "$package" --keychain-profile "$MACOS_NOTARY_PROFILE" --wait
    xcrun stapler staple "$package"
fi

echo "Built HAL installer: $package"
echo "Release channel: $release_channel"
echo "Installation requires administrator approval and a reboot; this script does neither."
