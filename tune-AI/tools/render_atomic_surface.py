#!/usr/bin/env python3
"""Render the real Auto-Key widget for visual regression review.

The default capture is the honest idle state. ``--fixture`` only supplies a
deterministic, test-process view snapshot; it is never imported by production.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ui.atomic_surface import AtomicSurface


def fixture_snapshot() -> dict:
    labels = ("Tightness", "Character", "Presence", "Air", "Space", "Blend")
    values = (.28, .46, .62, .38, .31, .78)
    return {
        "macros": [
            {
                "macroId": index,
                "state": 2,
                "value": value,
                "macroName": label,
                "busName": "Master",
                "pluginName": "Visual fixture",
                "targets": [{"valueText": str(round(value * 100))}],
            }
            for index, (label, value) in enumerate(zip(labels, values))
        ],
        "audioAnalysis": {"sourceName": "Master Post-FX"},
        "analysisSources": [{"kind": "master", "id": "master", "name": "Master Post-FX"}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    app = QApplication.instance() or QApplication([])
    view = AtomicSurface()
    view.resize(round(1448 * args.scale), round(1086 * args.scale))
    if args.fixture:
        view.set_snapshot(fixture_snapshot())
        view.set_active_mode("natural")
        view.set_preset_name("Default")
        view.set_tone("C# Minor", 0)
        view.set_waveform([.08 + .44 * abs(math.sin(i * .31)) *
                           math.exp(-((i - 44) / 31) ** 2) for i in range(96)])
        spectrum = [
            min(1.0, .10 + .52 * math.exp(-((i - 26) / 13) ** 2)
                + .28 * math.exp(-((i - 68) / 17) ** 2))
            for i in range(96)
        ]
        view.set_input_level(.72)
        view.set_spectrum(spectrum)
        view.set_eq_surface({
            "capability": "eq_interactive",
            "parameterModel": {"frequencyMinHz": 10, "frequencyMaxHz": 30000,
                               "gainMinDb": -30, "gainMaxDb": 30},
            "bands": [
                {"bandId": f"band:{i + 1}", "index": i + 1,
                 "used": {"parameterId": f"used{i}", "normalizedValue": 1},
                 "enabled": {"parameterId": f"enabled{i}", "normalizedValue": 1},
                 "frequency": {"parameterId": f"f{i}", "normalizedValue": f},
                 "gain": {"parameterId": f"g{i}", "normalizedValue": g},
                 "q": {"parameterId": f"q{i}", "normalizedValue": .3,
                       "displayValue": "1.00"}}
                for i, (f, g) in enumerate(((.17, .48), (.35, .60), (.53, .46),
                                             (.72, .55), (.86, .58)))
            ],
        })
        view.set_capture_status("SIGNAL")
    view.show()
    app.processEvents()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not view.grab().save(str(args.output)):
        raise RuntimeError(f"Could not save {args.output}")
    view.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
