#!/usr/bin/env python3
"""Fail closed when a StudioForge macOS distribution is not self-contained."""

from __future__ import annotations

import argparse
import json
import plistlib
import subprocess
import sys
from pathlib import Path


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, text=True, capture_output=True)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def executable_for(app: Path) -> Path | None:
    try:
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        return app / "Contents/MacOS" / str(info["CFBundleExecutable"])
    except (OSError, KeyError, plistlib.InvalidFileException):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution", type=Path)
    parser.add_argument("--architecture", choices=("arm64", "x86_64", "universal2"), default="arm64")
    parser.add_argument("--require-developer-id", action="store_true")
    args = parser.parse_args()

    root = args.distribution.resolve()
    daw = root / "StudioForge Live DAW.app"
    panel = root / "Tune-AI.app"
    helper = daw / "Contents/Resources/Helpers/StudioForgeVst3Probe"
    errors: list[str] = []

    for app in (daw, panel):
        if not app.is_dir():
            fail(errors, f"missing application: {app}")
            continue
        executable = executable_for(app)
        if executable is None or not executable.is_file():
            fail(errors, f"invalid CFBundleExecutable: {app}")

    if not helper.is_file():
        fail(errors, f"missing protected plug-in scanner: {helper}")

    panel_executable = executable_for(panel)
    if panel_executable is not None and panel_executable.is_file():
        try:
            bridge = subprocess.run(
                [str(panel_executable), "--studioforge-analyse-url", ""],
                check=False,
                text=True,
                capture_output=True,
                timeout=20,
            )
            payload = json.loads(bridge.stdout.strip())
            if bridge.returncode != 1 or payload.get("ok") is not False:
                fail(errors, "packaged Tune-AI headless bridge returned an invalid contract")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as error:
            fail(errors, f"packaged Tune-AI headless bridge is unavailable: {error}")

    binaries = [candidate for candidate in (executable_for(daw), executable_for(panel), helper)
                if candidate is not None and candidate.is_file()]
    required = {"arm64", "x86_64"} if args.architecture == "universal2" else {args.architecture}
    for binary in binaries:
        result = run("lipo", "-archs", str(binary))
        architectures = set(result.stdout.strip().split()) if result.returncode == 0 else set()
        if not required.issubset(architectures):
            fail(errors, f"{binary} has {sorted(architectures)}, requires {sorted(required)}")

        strings = run("strings", str(binary)).stdout
        forbidden = ("/Users/hiimdrdey/code/daw", "build-live-release", "build-macos-tests")
        for marker in forbidden:
            if marker in strings:
                fail(errors, f"development path leaked into {binary}: {marker}")

    for app in (daw, panel):
        if not app.is_dir():
            continue
        verification = run("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app))
        if verification.returncode != 0:
            fail(errors, f"invalid code signature: {app}: {verification.stderr.strip()}")
        details = run("codesign", "-dv", "--verbose=4", str(app)).stderr
        if args.require_developer_id and ("Authority=Developer ID Application:" not in details
                                          or "flags=0x10000(runtime)" not in details):
            fail(errors, f"Developer ID hardened-runtime signature missing: {app}")

    if errors:
        print("StudioForge macOS release audit FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"StudioForge macOS release audit passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
