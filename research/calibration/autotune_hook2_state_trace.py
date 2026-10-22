"""Bounded LLDB callbacks for an OFFLINE Auto-Tune Artist AU render.

The callback runs in LLDB while the target thread is stopped. It is never
real-time safe, even though returning False automatically resumes the target.
"""

import hashlib
import os
import struct
from pathlib import Path

import lldb


AU_BINARY = Path(
    "/Library/Audio/Plug-Ins/Components/Auto-Tune Artist.component/Contents/MacOS/Auto-Tune Artist"
)
EXPECTED_SHA256 = "2f2b7a5b4e52e4fd63b7b683ac49277d95c775a00ac98eded83fa0c6b826f33b"
STATE = {"directory": None, "event": 0, "retune": None, "retune_wrapper": 0,
         "generic_count": 0, "au_count": 0, "max_events": 600}


def initialize(debugger):
    directory = Path(os.environ["ARTIST_TRACE_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(AU_BINARY.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"AU binary changed: {digest}; refusing stale offsets")
    STATE.update(directory=directory, event=0, retune=None, retune_wrapper=0,
                 generic_count=0, au_count=0)
    (directory / "events.tsv").write_text(
        "event\tkind\tparameter_id\ts0_raw\tobject_address\tnote\n", encoding="utf-8"
    )
    print(f"Artist offline trace ready: {directory} (AU SHA-256 {digest})")


def _read(process, address, count):
    error = lldb.SBError()
    data = process.ReadMemory(address, count, error)
    return data if error.Success() and len(data) == count else None


def _register(frame, name):
    reg = frame.FindRegister(name)
    return reg.GetValue() if reg.IsValid() else None


def _address(frame, name):
    reg = frame.FindRegister(name)
    return reg.GetValueAsUnsigned() if reg.IsValid() else 0


def _parameter_id(process, string_object_address):
    # In this binary, parameterChanged starts with `ldr x0, [x1]` and passes
    # that pointer to a UTF-8 compare. This is binary-specific, not JUCE ABI.
    pointer_bytes = _read(process, string_object_address, 8)
    if pointer_bytes is None:
        return "<unreadable-String>"
    pointer = int.from_bytes(pointer_bytes, "little")
    error = lldb.SBError()
    value = process.ReadCStringFromMemory(pointer, 128, error)
    return value if error.Success() and value else "<unreadable-id>"


def _record(kind, parameter_id, raw_value, address, note=""):
    if STATE["directory"] is None or STATE["event"] >= STATE["max_events"]:
        return None
    STATE["event"] += 1
    number = STATE["event"]
    clean = lambda value: str(value).replace("\t", " ").replace("\n", " ")
    with (STATE["directory"] / "events.tsv").open("a", encoding="utf-8") as output:
        output.write(
            f"{number}\t{clean(kind)}\t{clean(parameter_id)}\t{clean(raw_value)}"
            f"\t0x{address:x}\t{clean(note)}\n"
        )
    return number


def parameter_changed(frame, bp_loc, internal_dict):
    """Capture the parameter ID and float register at the wrapper callback."""
    process = frame.GetThread().GetProcess()
    parameter_id = _parameter_id(process, _address(frame, "x1"))
    lower_id = parameter_id.lower()
    is_retune = lower_id == "retk" or "retune" in lower_id
    is_humanize = lower_id == "humk" or "humanize" in lower_id
    focused = is_retune or is_humanize
    if not focused:
        if STATE["generic_count"] >= 40:
            return False
        STATE["generic_count"] += 1
    s0_raw = _register(frame, "s0")
    number = _record("parameterChanged", parameter_id, s0_raw, _address(frame, "x0"))
    if number is not None and (focused or STATE["generic_count"] <= 8):
        print(f"ARTIST PARAM #{number}: {parameter_id} s0={s0_raw}")
    if number is not None and is_retune:
        STATE["retune"] = (number, s0_raw)
        STATE["retune_wrapper"] = _address(frame, "x0")
        target = frame.GetThread().GetProcess().GetTarget()
        for breakpoint_id in (2, 3):
            breakpoint = target.FindBreakpointByID(breakpoint_id)
            if breakpoint.IsValid():
                breakpoint.SetEnabled(True)
    return False


def au_set_parameter(frame, bp_loc, internal_dict):
    """Confirm that the AU wrapper receives host parameter changes."""
    if STATE["au_count"] >= 12:
        return False
    STATE["au_count"] += 1
    parameter_id = f"AU numeric ID {_address(frame, 'x1')}"
    _record("JuceAU::SetParameter", parameter_id, _register(frame, "s0"),
            _address(frame, "x0"))
    if STATE["au_count"] == 12:
        breakpoint = frame.GetThread().GetProcess().GetTarget().FindBreakpointByID(4)
        if breakpoint.IsValid():
            breakpoint.SetEnabled(False)
    return False


def _dsp_snapshot(frame, kind, breakpoint_id):
    # First process call following a Retune event only. Different AU instances
    # may have different pointers/counters; snapshots are candidates, not proof.
    target = frame.GetThread().GetProcess().GetTarget()
    breakpoint = target.FindBreakpointByID(breakpoint_id)
    if breakpoint.IsValid():
        breakpoint.SetEnabled(False)
    event = STATE["retune"] or (0, "unknown")
    if STATE["directory"] is None:
        return False
    address = _address(frame, "x0")
    data = _read(frame.GetThread().GetProcess(), address, 0x500)
    if data is None:
        _record(kind, "Retune", event[1], address, "0x500-byte object read failed")
        return False
    filename = f"event_{event[0]:04d}_{kind}.bin"
    (STATE["directory"] / filename).write_bytes(data)
    _record(kind, "Retune", event[1], address,
            f"first process after Retune or initial process; {filename}")
    print(f"ARTIST DSP: {kind} after Retune s0={event[1]} -> {filename}")
    return False


def at_process(frame, bp_loc, internal_dict):
    return _dsp_snapshot(frame, "AT_DSPObject", 2)


def dt_process(frame, bp_loc, internal_dict):
    return _dsp_snapshot(frame, "DT_DSPObject", 3)


def probe_at_process(frame, bp_loc, internal_dict):
    """Record one AT process call, then stop the short LLDB probe."""
    _dsp_snapshot(frame, "AT_DSPObject", 2)
    return True


def probe_dt_process(frame, bp_loc, internal_dict):
    """Record one DT process call, then stop the short LLDB probe."""
    _dsp_snapshot(frame, "DT_DSPObject", 3)
    return True


def retune_coefficient_probe(frame, bp_loc, internal_dict):
    """Follow the statically verified RetK pointer chain at process entry.

    For this exact AU, the RetK writer in parameterChanged loads wrapper+0x298,
    then its +0x18 pointer, and writes a double at the resulting object's +0x90.
    This is not an arbitrary scan of the DT_DSPObject prefix.
    """
    target = frame.GetThread().GetProcess().GetTarget()
    breakpoint = target.FindBreakpointByID(2)
    if breakpoint.IsValid():
        breakpoint.SetEnabled(False)
    process = frame.GetThread().GetProcess()
    wrapper = STATE["retune_wrapper"]
    event = STATE["retune"]
    if not wrapper or event is None:
        _record("RetuneCoeff", "RetK", "unavailable", 0, "no RetK event yet")
        return False

    first = _read(process, wrapper + 0x298, 8)
    intermediate = struct.unpack("<Q", first)[0] if first else 0
    second = _read(process, intermediate + 0x18, 8) if intermediate else None
    nested = struct.unpack("<Q", second)[0] if second else 0
    value_bytes = _read(process, nested + 0x90, 8) if nested else None
    if value_bytes is None:
        _record("RetuneCoeff", "RetK", "unreadable", nested + 0x90,
                f"requested={event[1]} wrapper=0x{wrapper:x} middle=0x{intermediate:x}")
        return False
    coefficient = struct.unpack("<d", value_bytes)[0]
    _record("RetuneCoeff", "RetK", f"{coefficient:.17g}", nested + 0x90,
            f"requested={event[1]} wrapper=0x{wrapper:x} middle=0x{intermediate:x}")
    print(f"ARTIST RETUNE: requested={event[1]} coefficient={coefficient:.17g}"
          f" at nested+0x90 (0x{nested + 0x90:x})")
    try:
        return float(event[1]) >= 49.5  # Stop at first 50 ms case, before the remaining matrix.
    except (TypeError, ValueError):
        return False
