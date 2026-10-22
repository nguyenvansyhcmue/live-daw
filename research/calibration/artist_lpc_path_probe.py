#!/usr/bin/env python3
"""Bounded offline Artist AU LPC-path probe on a Hook-2 excerpt.

Run as a program from a normal Terminal. LLDB imports this same file for
breakpoint callbacks. Never attach it to a live DAW/audio-monitoring process.
"""

import csv
import hashlib
import json
import os
import signal
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ARTIST = Path("/Library/Audio/Plug-Ins/Components/Auto-Tune Artist.component/Contents/MacOS/Auto-Tune Artist")
EXPECTED_SHA256 = "2f2b7a5b4e52e4fd63b7b683ac49277d95c775a00ac98eded83fa0c6b826f33b"
RUNNER = Path("/Users/hiimdrdey/code/daw/build-macos-arm64/StudioForgeCalibrationRunner")
INPUT = ROOT / "artifacts/artist-lpc-path-20261022/hook2_4p2_5p3.wav"
COMMANDS = ROOT / "artist_lpc_path_probe.lldb"
TARGET_SAMPLES = 43200  # 0.9 s of the 4.2–5.3 s excerpt at 48 kHz.
MAX_HITS_PER_LPC_FUNCTION = 8
FUNCTIONS = ("LPC_inv_fir", "LPC_fwd_iir", "LPC_design",
             "LPC_model_glottal", "LPC_remove_glottal")
STATE = {"directory": None, "object": 0, "samples": 0, "blocks": 0,
         "at_calls": 0, "counts": {name: 0 for name in FUNCTIONS},
         "first_events": [], "vtable_target": None, "virtual_slots": None,
         "retune": None,
         "invalid_frames": False}

# Observed indirect-call slots in the exact AU image: +0x78 at DT::process
# 0x80144; +0x68/+0x70/+0xa8/+0xa0 at AT::process 0x7e208/0x7e220/
# 0x7e2e8/0x7e41c. Resolve them against the live object's vtable; symbol
# names alone are not evidence that a particular slot ran on this preset.
VIRTUAL_SLOTS = (0x68, 0x70, 0x78, 0xa0, 0xa8)


def _reg(frame, name):
    register = frame.FindRegister(name)
    return register.GetValueAsUnsigned() if register.IsValid() else 0


def _read_u64(process, address):
    import lldb
    error = lldb.SBError()
    raw = process.ReadMemory(address, 8, error) if address else b""
    return struct.unpack("<Q", raw)[0] if error.Success() and len(raw) == 8 else None


def _symbol(target, address):
    resolved = target.ResolveLoadAddress(address)
    if not resolved.IsValid():
        return None
    symbol = resolved.GetSymbol()
    return symbol.GetName() if symbol.IsValid() else None


def _save():
    directory = STATE["directory"]
    summary = {key: value for key, value in STATE.items() if key != "directory"}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (directory / "first-events.csv").open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("function", "excerpt_sample_at_entry", "object", "caller"))
        writer.writerows(STATE["first_events"])


def initialize(debugger):
    digest = hashlib.sha256(ARTIST.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError("Artist binary changed; refusing stale symbol/offset probe")
    STATE["directory"] = Path(os.environ["ARTIST_LPC_PROBE_DIR"])
    print("Artist LPC probe initialized; binary SHA-256=" + digest)


def parameter_changed(frame, bp_loc, internal_dict):
    process = frame.GetThread().GetProcess()
    name_object = _reg(frame, "x1")
    pointer = _read_u64(process, name_object)
    if pointer:
        import lldb
        error = lldb.SBError()
        name = process.ReadCStringFromMemory(pointer, 64, error)
        if error.Success() and name == "RetK":
            try:
                STATE["retune"] = float(frame.FindRegister("s0").GetValue())
            except (TypeError, ValueError):
                pass
    return False


def dt_process(frame, bp_loc, internal_dict):
    process = frame.GetThread().GetProcess()
    object_address = _reg(frame, "x0")
    frames = _reg(frame, "x3")
    if frames == 0 or frames > 4096:
        STATE["invalid_frames"] = True
        _save()
        return True
    if not STATE["object"]:
        STATE["object"] = object_address
        vtable = _read_u64(process, object_address)
        STATE["virtual_slots"] = {}
        for offset in VIRTUAL_SLOTS:
            target = _read_u64(process, vtable + offset) if vtable else None
            STATE["virtual_slots"][hex(offset)] = {
                "address": hex(target) if target else None,
                "symbol": _symbol(process.GetTarget(), target) if target else None,
            }
        STATE["vtable_target"] = STATE["virtual_slots"]["0x78"]
        print("Selected DT object=" + hex(object_address)
              + " virtual slots=" + str(STATE["virtual_slots"]))
        _save()  # Preserve the object/virtual target even if a later callback fails.
    if object_address != STATE["object"]:
        return False
    STATE["samples"] += frames
    STATE["blocks"] += 1
    if STATE["samples"] >= TARGET_SAMPLES:
        _save()
        print("LPC_PROBE_DONE: " + str(STATE["directory"] / "summary.json"))
        return True
    return False


def at_process(frame, bp_loc, internal_dict):
    if STATE["object"] and _reg(frame, "x0") == STATE["object"]:
        STATE["at_calls"] += 1
    return False


def lpc_entry(frame, bp_loc, internal_dict):
    if not STATE["object"]:
        return False
    function = frame.GetFunctionName() or ""
    name = next((item for item in FUNCTIONS if item in function), None)
    if name is None:
        return False
    STATE["counts"][name] += 1
    if len(STATE["first_events"]) < 80:
        parent = frame.GetThread().GetFrameAtIndex(1)
        caller = parent.GetFunctionName() if parent.IsValid() else None
        STATE["first_events"].append((name, STATE["samples"], hex(_reg(frame, "x0")), caller))
    # One virtual LPC method may run once per sample. Its first few call sites
    # prove reachability; leaving a debugger breakpoint on every audio sample
    # would make even this bounded offline probe unreasonably slow.
    if STATE["counts"][name] >= MAX_HITS_PER_LPC_FUNCTION:
        bp_loc.GetBreakpoint().SetEnabled(False)
        _save()
    return False


def main():
    for path in (ARTIST, RUNNER, INPUT, COMMANDS):
        if not path.exists():
            print("Missing: " + str(path), file=sys.stderr)
            return 1
    if hashlib.sha256(ARTIST.read_bytes()).hexdigest() != EXPECTED_SHA256:
        print("Artist binary SHA-256 mismatch", file=sys.stderr)
        return 1
    directory = Path(tempfile.mkdtemp(prefix="artist-lpc-path.", dir=ROOT / "artifacts"))
    environment = os.environ.copy()
    environment.update(ARTIST_LPC_PROBE_DIR=str(directory),
                       STUDIOFORGE_CALIBRATION_VOICE="Alto-Tenor",
                       STUDIOFORGE_CALIBRATION_KEY="F#",
                       STUDIOFORGE_CALIBRATION_SCALE="Natural Minor")
    command = ["lldb", "-b", "-s", str(COMMANDS), "--", str(RUNNER),
               str(INPUT), str(directory), "Auto-Tune Artist"]
    log = directory / "lldb.log"
    print("Artist LPC path probe: " + str(directory), flush=True)
    with log.open("wb") as output:
        child = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                 env=environment, start_new_session=True)
        try:
            child.wait(timeout=240)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=10)
            print("TIMEOUT: see " + str(log), file=sys.stderr)
            return 2
    summary = directory / "summary.json"
    if not summary.exists():
        print("INCOMPLETE: no DSP summary; see " + str(log), file=sys.stderr)
        return 2
    data = json.loads(summary.read_text())
    if data["invalid_frames"] or data["samples"] < TARGET_SAMPLES:
        print("INCOMPLETE: invalid or insufficient process frames; see " + str(summary))
        return 2
    print("COMPLETE: " + str(summary))
    print("LPC first-hit counts (capped at 8/function): " + str(data["counts"]))
    print("Caller samples: " + str(directory / "first-events.csv"))
    print("LLDB log: " + str(log))
    print("No Vibe or installed Artist files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
