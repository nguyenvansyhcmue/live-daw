#!/usr/bin/env python3
"""Bounded offline LLDB smoke test; stop at the first Artist DSP call."""

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path("/Users/hiimdrdey/autotune")
RUNNER = Path("/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner")
INPUT = Path("/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav")
COMMANDS = ROOT / "autotune_hook2_short_probe.lldb"
TIMEOUT_SECONDS = 60


def main() -> int:
    for path in (RUNNER, INPUT, COMMANDS):
        if not path.exists():
            print(f"Missing: {path}", file=sys.stderr)
            return 1
    directory = Path(tempfile.mkdtemp(prefix="artist-hook2-short-probe.", dir=ROOT / "artifacts"))
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
    print(f"Short probe: {directory}", flush=True)
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
    events = events_path.read_text().splitlines() if events_path.exists() else []
    print(f"Events: {events_path} ({max(0, len(events) - 1)} rows)")
    print(f"LLDB log: {log_path}")
    if not any("_DSPObject" in row for row in events[1:]):
        print("FAIL: no DSP breakpoint hit; do not infer Artist internal state.", file=sys.stderr)
        for line in log_path.read_text(errors="replace").splitlines()[-12:]:
            print(line, file=sys.stderr)
        return 2
    print("PASS: first Artist DSP call captured; full trace can be attempted next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
