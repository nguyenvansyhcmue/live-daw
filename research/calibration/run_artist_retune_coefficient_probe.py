#!/usr/bin/env python3
"""Bounded 0/50 ms Artist AU Retune-state probe on the offline Hook 2 host."""

import csv
import math
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path("/Users/hiimdrdey/autotune")
RUNNER = Path("/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner")
INPUT = Path("/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav")
COMMANDS = ROOT / "autotune_retune_coefficient_probe.lldb"
TIMEOUT_SECONDS = 180


def main() -> int:
    for path in (RUNNER, INPUT, COMMANDS):
        if not path.exists():
            print(f"Missing: {path}", file=sys.stderr)
            return 1
    directory = Path(tempfile.mkdtemp(prefix="artist-retune-coeff.", dir=ROOT / "artifacts"))
    env = os.environ.copy()
    env.update(
        ARTIST_TRACE_DIR=str(directory),
        STUDIOFORGE_CALIBRATION_VOICE="Alto-Tenor",
        STUDIOFORGE_CALIBRATION_KEY="F#",
        STUDIOFORGE_CALIBRATION_SCALE="Natural Minor",
    )
    command = ["lldb", "-b", "-s", str(COMMANDS), "--", str(RUNNER), str(INPUT),
               str(directory), "Auto-Tune Artist"]
    log_path = directory / "lldb.log"
    print(f"Retune coefficient probe: {directory}", flush=True)
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env=env, start_new_session=True)
        try:
            process.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            print(f"FAIL: LLDB exceeded {TIMEOUT_SECONDS}s; see {log_path}", file=sys.stderr)
            return 2
    events_path = directory / "events.tsv"
    if events_path.exists():
        with events_path.open() as source:
            rows = list(csv.DictReader(source, delimiter="\t"))
    else:
        rows = []
    captured = [(row["note"].split("requested=")[-1].split()[0], row["s0_raw"])
                for row in rows if row["kind"] == "RetuneCoeff"]
    print(f"Retune coefficients: {captured}")
    print(f"Events: {events_path}")
    print(f"LLDB log: {log_path}")
    values = {}
    for requested, coefficient in captured:
        try:
            key, value = round(float(requested)), float(coefficient)
        except ValueError:
            continue
        if math.isfinite(value):
            values[key] = value
    if not {0, 50}.issubset(values) or abs(values[0]) > 1e-12 or values[50] <= 0:
        for line in log_path.read_text(errors="replace").splitlines()[-12:]:
            print(line, file=sys.stderr)
        print("FAIL: both 0 and 50 ms coefficient states were not captured.", file=sys.stderr)
        return 2
    print("PASS: nested Retune coefficient captured at 0 and 50 ms; no Vibe code changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
