#!/usr/bin/env python3
"""Verify a generated GTSinger plan is safe for a per-key calibration run."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("plan", type=Path)
args = parser.parse_args()
plan = json.loads(args.plan.read_text(encoding="utf-8"))
entries, pairs = plan["entries"], plan["controlled_pairs"]
assert entries and pairs, "plan has no entries or controlled pairs"
assert len(entries) == len(pairs) * 2, f"entries/pairs mismatch: {len(entries)} / {len(pairs)}"
plugin_keys = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}
dataset_voices = set()
plugin_voices = set()
for entry in entries:
    assert Path(entry["input_wav"]).is_file(), entry["input_wav"]
    assert entry["voice"] in {"Alto", "Tenor"}, entry["voice"]
    assert entry["artist_voice"] in {"Alto", "Alto-Tenor"}, entry["artist_voice"]
    assert entry["dataset_voice"].startswith("EN-"), entry["dataset_voice"]
    assert entry["key"] in plugin_keys, f"non-canonical plug-in key: {entry['key']}"
    assert entry["scale"] in {"Major", "Natural Minor"}
    assert entry["controls"] == {"retune_ms": 0.0, "flex_percent": 0.0, "humanize_percent": 0.0, "natural_vibrato": 0.0}
    dataset_voices.add(entry["dataset_voice"])
    plugin_voices.add(entry["voice"])
for pair in pairs:
    assert "technique_annotation_seconds" in pair
    assert pair["voice"] in plugin_voices
    assert pair["key"] in plugin_keys
    assert pair["score_key"]
    assert pair["artist_voice"] in {"Alto", "Alto-Tenor"}
print(f"gtsinger_plan | entries={len(entries)} pairs={len(pairs)} dataset_voices={','.join(sorted(dataset_voices))} plugin_voices={','.join(sorted(plugin_voices))} controls=hard_tune_zero status=PASS")
