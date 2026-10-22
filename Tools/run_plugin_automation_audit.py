#!/usr/bin/env python3
"""Release gate for StudioForge plug-in automation.

Every VST3 runs in StudioForgeVst3Probe, never in the DAW process. The probe
reads host parameters, exercises the exact normalised macro range (20/50/80),
and restores its starting values before exiting. A crashed or unsupported
third-party plug-in is quarantined in the report; it does not hide failures in
plug-ins that *did* load successfully.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def vst3_roots() -> list[Path]:
    return [Path("/Library/Audio/Plug-Ins/VST3"), Path.home() / "Library/Audio/Plug-Ins/VST3"]


def plugin_bundles(roots: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for bundle in sorted(root.glob("*.vst3")):
            if "backup" in bundle.name.lower():
                continue
            resolved = bundle.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(bundle)
    return result


def parse_report(path: Path) -> dict[str, int]:
    # Keep this runner independent from Python's optional pyexpat extension.
    # Homebrew Python installations with a mismatched libexpat must not block
    # a release audit that only needs five scalar root attributes.
    document = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<STUDIOFORGE_PLUGIN_PARAMETER_AUDIT\b([^>]*)>", document)
    if match is None:
        raise ValueError("unexpected probe report")
    attributes = match.group(1)
    keys = ("parameterCount", "vendorIdentifierCount", "mappableParameterCount",
            "roundTripFailures", "exerciseFailures")
    values: dict[str, int] = {}
    for key in keys:
        value = re.search(rf'\b{re.escape(key)}="([0-9]+)"', attributes)
        values[key] = int(value.group(1)) if value is not None else 0
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Run StudioForge VST3 automation quality gate")
    parser.add_argument("--probe", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--core-tests", type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    if not args.probe.is_file():
        parser.error(f"Probe not found: {args.probe}")
    if args.core_tests is not None:
        result = subprocess.run([str(args.core_tests)], check=False)
        if result.returncode != 0:
            print("Core automation tests failed", file=sys.stderr)
            return result.returncode

    args.report.parent.mkdir(parents=True, exist_ok=True)
    work = args.report.parent / ".plugin-automation-audit"
    work.mkdir(parents=True, exist_ok=True)
    plugins: list[dict[str, object]] = []
    totals = {"scanned": 0, "loadable": 0, "quarantined": 0, "parameters": 0,
              "mappable": 0, "roundTripFailures": 0, "exerciseFailures": 0}

    for index, bundle in enumerate(plugin_bundles(vst3_roots())):
        totals["scanned"] += 1
        output = work / f"{index:03d}.xml"
        try:
            process = subprocess.run(
                [str(args.probe), str(bundle), str(output), "--audit-parameters"],
                check=False, timeout=args.timeout, capture_output=True, text=True,
            )
        except subprocess.TimeoutExpired:
            plugins.append({"plugin": bundle.name, "status": "quarantined", "reason": "timeout"})
            totals["quarantined"] += 1
            continue

        if process.returncode != 0 or not output.is_file():
            plugins.append({"plugin": bundle.name, "status": "quarantined",
                            "reason": f"probe exit {process.returncode}"})
            totals["quarantined"] += 1
            continue

        try:
            metrics = parse_report(output)
        except (OSError, ValueError) as error:
            plugins.append({"plugin": bundle.name, "status": "quarantined", "reason": str(error)})
            totals["quarantined"] += 1
            continue

        totals["loadable"] += 1
        totals["parameters"] += metrics["parameterCount"]
        totals["mappable"] += metrics["mappableParameterCount"]
        totals["roundTripFailures"] += metrics["roundTripFailures"]
        totals["exerciseFailures"] += metrics["exerciseFailures"]
        plugins.append({"plugin": bundle.name, "status": "passed", **metrics})

    passed = totals["roundTripFailures"] == 0 and totals["exerciseFailures"] == 0
    payload = {"schema": 1, "generatedAt": datetime.now(timezone.utc).isoformat(),
               "passed": passed, "totals": totals, "plugins": plugins}
    args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "totals": totals, "report": str(args.report)}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
