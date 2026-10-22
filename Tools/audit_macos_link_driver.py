#!/usr/bin/env python3
"""Fail-closed audit for the StudioForge Link HAL release candidate."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
from pathlib import Path


EXPECTED_BUNDLE_ID = "com.studioforge.link.hal"
EXPECTED_EXECUTABLE = "StudioForgeLinkHAL"


def run(*args: str) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return (result.stdout + result.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--architecture", choices=("arm64", "x86_64"), required=True)
    parser.add_argument("--require-developer-id", action="store_true")
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    info_path = bundle / "Contents" / "Info.plist"
    executable = bundle / "Contents" / "MacOS" / EXPECTED_EXECUTABLE
    if bundle.suffix != ".driver" or not info_path.is_file() or not executable.is_file():
        raise SystemExit(f"Invalid HAL bundle shape: {bundle}")

    with info_path.open("rb") as stream:
        info = plistlib.load(stream)
    if info.get("CFBundleIdentifier") != EXPECTED_BUNDLE_ID:
        raise SystemExit("Unexpected HAL bundle identifier")
    if info.get("CFBundleExecutable") != EXPECTED_EXECUTABLE:
        raise SystemExit("Unexpected HAL executable name")
    if info.get("CFPlugInDynamicRegistration") is not False:
        raise SystemExit("HAL factory must use static CFPlugIn registration")

    run("codesign", "--verify", "--strict", "--verbose=2", str(bundle))
    signature = run("codesign", "-dvvv", str(bundle))
    if args.require_developer_id and "Authority=Developer ID Application:" not in signature:
        raise SystemExit("HAL bundle is not signed with Developer ID Application")

    file_description = run("file", str(executable))
    if args.architecture not in file_description:
        raise SystemExit(
            f"HAL executable does not contain required {args.architecture} slice: {file_description}")
    print(f"StudioForge Link HAL audit passed: {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
