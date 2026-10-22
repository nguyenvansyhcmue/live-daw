# StudioForge macOS release

The macOS distribution contains two sibling applications:

- `StudioForge Live DAW.app`
- `Tune-AI.app` (display name: THM Vocal Panel)

Keeping them together is part of the runtime contract. The DAW launches the
panel and its one-shot analysis service from that sibling bundle. The DAW also
contains its protected VST3/Audio Unit scanner and bundled VibeAutotune VST3;
no path into a developer checkout is allowed in a release.

System-wide audio routing is a separate privileged component:

- `StudioForgeLinkHAL.driver` is installed in `/Library/Audio/Plug-Ins/HAL`;
- `StudioForge-Link-<version>-macOS-<arch>.pkg` owns that installation;
- users must reboot after installing or upgrading it.

The app archive and HAL installer are deliberately separate artifacts. Copying
the `.driver` into either application does not register a Core Audio device.

## Local release candidate

```bash
cd /path/to/daw
STUDIOFORGE_VERSION=1.0.0 Tools/package_macos_release.sh
```

The script rebuilds THM Vocal Panel, builds the Release DAW, stages both apps,
signs them ad hoc, runs the clean-machine audit and creates a DMG. On a locked
CI runner without a disk-image device it creates a Finder-safe ZIP instead.
This local artifact is for QA; Gatekeeper distribution requires Developer ID.

## Public notarized release

Import a `Developer ID Application` certificate into the signing keychain and
create an `xcrun notarytool` keychain profile. Then run:

```bash
MACOS_SIGN_IDENTITY='Developer ID Application: Company Name (TEAMID)' \
MACOS_NOTARY_PROFILE='studioforge-notary' \
STUDIOFORGE_VERSION=1.0.0 \
Tools/package_macos_release.sh
```

The pipeline signs nested code first, enables hardened runtime, signs the two
outer apps with their entitlements, rejects developer-path leaks, creates and
signs the DMG, submits it to Apple, staples the ticket and asks Gatekeeper to
assess the final artifact. Any failure stops the release.

The Link installer additionally requires a `Developer ID Installer`
certificate. Build it only after the HAL tests pass:

```bash
MACOS_SIGN_IDENTITY='Developer ID Application: Company Name (TEAMID)' \
MACOS_INSTALLER_IDENTITY='Developer ID Installer: Company Name (TEAMID)' \
MACOS_NOTARY_PROFILE='studioforge-notary' \
STUDIOFORGE_RELEASE_CHANNEL=public \
STUDIOFORGE_VERSION=1.0.0 \
Tools/build_macos_link_installer.sh
```

These identities come from an active Apple Developer Program team. The notary
profile is created once with `xcrun notarytool store-credentials`; credentials
must stay in the login/CI keychain, never in this repository. A public release
is incomplete until both the application artifact and Link installer are
signed, notarized and stapled, then verified on a clean Mac after reboot.

## Architecture policy

The current PyInstaller runtime, DAW, probe and bundled plug-in are ARM64. Set
`STUDIOFORGE_ARCHITECTURE=universal2` only after every nested executable has
both `arm64` and `x86_64` slices; the release audit rejects mixed/thin bundles.

## Useful controls

- `STUDIOFORGE_BUILD_DIR`: configured CMake Release build directory.
- `STUDIOFORGE_RELEASE_DIR`: artifact output directory.
- `STUDIOFORGE_BUILD_JOBS`: parallel build job count.
- `TUNE_AI_APP_PATH`: prebuilt panel override.
- `STUDIOFORGE_REBUILD_TUNE_AI=0`: use that prebuilt override instead of
  rebuilding from source.

