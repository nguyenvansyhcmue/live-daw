#!/usr/bin/env python3
"""Bounded, offline Artist AU parameter-state probe. Never attach to a live DAW.

Run this file normally to launch the existing StudioForge calibration runner under
LLDB. LLDB imports the same file for callbacks. No plug-in or Vibe source is
modified. File offsets/pointer paths apply only to EXPECTED_ARTIST_SHA256.
"""

import csv
import hashlib
import math
import os
import signal
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARTIST = Path("/Library/Audio/Plug-Ins/Components/Auto-Tune Artist.component/Contents/MacOS/Auto-Tune Artist")
EXPECTED_ARTIST_SHA256 = "2f2b7a5b4e52e4fd63b7b683ac49277d95c775a00ac98eded83fa0c6b826f33b"
RUNNER = Path("/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner")
INPUT = Path("/Users/hiimdrdey/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/hook2_raw_segment.wav")
COMMANDS = ROOT / "artist_knob_map_probe.lldb"
PARAMETERS = {"RetK", "HumK", "FlexTune_ID", "NaVK"}
STATE = {"directory": None, "values": {}, "wrapper": 0, "pending": False, "captures": 0}


def _read(process, address, size):
    import lldb
    if not address:
        return None
    error = lldb.SBError()
    data = process.ReadMemory(address, size, error)
    return data if error.Success() and len(data) == size else None


def _value(process, address, fmt):
    data = _read(process, address, struct.calcsize(fmt))
    return struct.unpack(fmt, data)[0] if data is not None else None


def _address(frame, register):
    value = frame.FindRegister(register)
    return value.GetValueAsUnsigned() if value.IsValid() else 0


def _parameter_id(process, string_object):
    ptr = _value(process, string_object, "<Q")
    if not ptr:
        return "<unreadable>"
    import lldb
    error = lldb.SBError()
    result = process.ReadCStringFromMemory(ptr, 128, error)
    return result if error.Success() and result else "<unreadable>"


def _write(row):
    with (STATE["directory"] / "knob-states.csv").open("a", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(row)


def initialize(debugger):
    digest = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
    if digest != EXPECTED_ARTIST_SHA256:
        raise RuntimeError(f"Artist AU changed ({digest}); refusing stale offsets")
    directory = Path(os.environ["ARTIST_KNOB_PROBE_DIR"])
    STATE.update(directory=directory, values={}, wrapper=0, pending=False, captures=0)
    with (directory / "knob-states.csv").open("w", newline="") as handle:
        csv.writer(handle).writerow([
            "capture", "retune_ms", "humanize", "flex_tune", "natural_vibrato",
            "sample_rate", "retune_coefficient", "combined_coefficient",
            "retune_raw", "humanize_raw", "flex_internal", "natural_internal",
            "retune_field", "flex_field", "natural_field",
        ])
    print(f"Artist knob probe initialized; binary SHA-256={digest}")


def parameter_changed(frame, bp_loc, internal_dict):
    process = frame.GetThread().GetProcess()
    name = _parameter_id(process, _address(frame, "x1"))
    if name not in PARAMETERS:
        return False
    raw = frame.FindRegister("s0").GetValue()
    try:
        numeric = float(raw)
    except (TypeError, ValueError):
        return False
    STATE["values"][name] = numeric
    STATE["wrapper"] = _address(frame, "x0")
    STATE["pending"] = True
    target = process.GetTarget()
    probe_breakpoint = target.FindBreakpointByID(2)
    if probe_breakpoint.IsValid():
        probe_breakpoint.SetEnabled(True)
    return False


def process_entry(frame, bp_loc, internal_dict):
    target = frame.GetThread().GetProcess().GetTarget()
    breakpoint = target.FindBreakpointByID(2)
    if breakpoint.IsValid():
        breakpoint.SetEnabled(False)
    if not STATE["pending"]:
        return False
    STATE["pending"] = False
    process = frame.GetThread().GetProcess()
    wrapper = STATE["wrapper"]
    middle = _value(process, wrapper + 0x298, "<Q")
    nested = _value(process, middle + 0x18, "<Q") if middle else None
    natural_object = _value(process, middle + 0x8, "<Q") if middle else None
    values = STATE["values"]
    STATE["captures"] += 1
    capture = STATE["captures"]
    _write([
        capture,
        values.get("RetK"), values.get("HumK"), values.get("FlexTune_ID"), values.get("NaVK"),
        _value(process, nested + 0x4, "<f") if nested else None,
        _value(process, nested + 0x90, "<d") if nested else None,
        _value(process, nested + 0x88, "<d") if nested else None,
        _value(process, nested + 0xc4, "<f") if nested else None,
        _value(process, nested + 0xc0, "<f") if nested else None,
        _value(process, nested + 0xc8, "<f") if nested else None,
        _value(process, natural_object + 0x8d8, "<d") if natural_object else None,
        hex(nested + 0x90) if nested else None,
        hex(nested + 0xc8) if nested else None,
        hex(natural_object + 0x8d8) if natural_object else None,
    ])
    print(f"KNOB CAPTURE #{capture}: {values}")
    # Case 16 is the first positive Natural Vibrato case. Stop there rather
    # than running the entire 24-case matrix under a debugger.
    return values.get("NaVK") == 3.0 and capture > 10


def main():
    for path in (ARTIST, RUNNER, INPUT, COMMANDS):
        if not path.exists():
            print(f"Missing: {path}", file=sys.stderr)
            return 1
    digest = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
    if digest != EXPECTED_ARTIST_SHA256:
        print(f"Artist AU changed: {digest}; refusing stale offsets", file=sys.stderr)
        return 1
    directory = Path(tempfile.mkdtemp(prefix="artist-knob-map.", dir=ROOT / "artifacts"))
    environment = os.environ.copy()
    environment.update(ARTIST_KNOB_PROBE_DIR=str(directory),
                       STUDIOFORGE_CALIBRATION_VOICE="Alto-Tenor",
                       STUDIOFORGE_CALIBRATION_KEY="F#",
                       STUDIOFORGE_CALIBRATION_SCALE="Natural Minor")
    command = ["lldb", "-b", "-s", str(COMMANDS), "--", str(RUNNER), str(INPUT),
               str(directory), "Auto-Tune Artist"]
    log = directory / "lldb.log"
    print(f"Artist knob-map probe: {directory}", flush=True)
    with log.open("wb") as output:
        child = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                 env=environment, start_new_session=True)
        try:
            child.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=10)
            print(f"FAIL: probe timed out; see {log}", file=sys.stderr)
            return 2
    result = directory / "knob-states.csv"
    if not result.exists():
        print(f"FAIL: no state file; see {log}", file=sys.stderr)
        return 2
    with result.open(newline="") as source:
        rows = list(csv.DictReader(source))
    def selected(name, requested):
        return [row for row in rows if row[name]
                and math.isclose(float(row[name]), requested, abs_tol=0.01)]
    required = [("retune_ms", 0), ("retune_ms", 50),
                ("humanize", 50), ("flex_tune", 50), ("natural_vibrato", 3)]
    if not all(selected(name, number) for name, number in required):
        print(f"INCOMPLETE: {len(rows)} snapshots; see {result} and {log}")
        return 2
    def field_matches(name, requested, field, expected, tolerance):
        return any(row[field] and math.isfinite(float(row[field]))
                   and math.isclose(float(row[field]), expected, abs_tol=tolerance)
                   for row in selected(name, requested))
    checks = [
        ("retune_ms", 0, "retune_coefficient", 0.0, 1e-9),
        ("retune_ms", 50, "retune_coefficient", 0.99855698552190264, 1e-6),
        ("humanize", 50, "humanize_raw", 50.0, 0.01),
        ("flex_tune", 50, "flex_internal", 0.5, 0.01),
        ("natural_vibrato", 3, "natural_internal", 0.25, 0.01),
    ]
    failed = [(name, value, field) for name, value, field, expected, tolerance in checks
              if not field_matches(name, value, field, expected, tolerance)]
    if failed:
        print(f"FAIL: static field map not verified at DSP entry: {failed}; see {result}")
        return 2
    print(f"PASS: {len(rows)} offline state snapshots; no Vibe code changed.")
    print(f"States: {result}")
    print(f"LLDB: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
