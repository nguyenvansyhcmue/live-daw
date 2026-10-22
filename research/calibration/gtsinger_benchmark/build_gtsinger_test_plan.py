#!/usr/bin/env python3
"""Build a key-aware, immutable Vibe/Artist test plan from a GTSinger manifest."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


MAJOR = {-7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F", 0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#"}
MINOR = {-7: "Ab", -6: "Eb", -5: "Bb", -4: "F", -3: "C", -2: "G", -1: "D", 0: "A", 1: "E", 2: "B", 3: "F#", 4: "C#", 5: "G#", 6: "D#", 7: "A#"}
# Vibe's public Key menu uses a single sharp-spelled chromatic domain. Keep
# the score spelling for provenance, but never ask the host to set unsupported
# flat labels such as Bb.
PLUGIN_KEY = {"Cb": "B", "Gb": "F#", "Db": "C#", "Ab": "G#", "Eb": "D#", "Bb": "A#"}


def score_key(musicxml: Path) -> tuple[str, str, int]:
    root = ET.parse(musicxml).getroot()
    fifths = root.findtext(".//key/fifths")
    mode = (root.findtext(".//key/mode") or "major").strip().lower()
    if fifths is None or mode not in {"major", "minor"}:
        raise ValueError(f"No supported score key in {musicxml}")
    value = int(fifths)
    mapping = MAJOR if mode == "major" else MINOR
    if value not in mapping:
        raise ValueError(f"Unsupported fifths={value} in {musicxml}")
    return mapping[value], ("Major" if mode == "major" else "Natural Minor"), value


def plugin_key(score_spelling: str) -> str:
    return PLUGIN_KEY.get(score_spelling, score_spelling)


def voice_stats(annotation: Path) -> dict:
    words = json.loads(annotation.read_text(encoding="utf-8"))
    notes = [note for word in words for note in word.get("note", []) if isinstance(note, int) and note > 0]
    if not notes:
        raise ValueError(f"No voiced score notes in {annotation}")
    return {
        "duration_seconds": round(float(words[-1]["end_time"]), 4),
        "score_note_min": min(notes),
        "score_note_max": max(notes),
        "score_note_count": len(notes),
        "style": {key: words[0].get(key) for key in ("singing_method", "pace", "range", "emotion")},
    }


def technique_seconds(annotation: Path, technique: str) -> float:
    """Return manually annotated phoneme duration for this group technique."""
    words = json.loads(annotation.read_text(encoding="utf-8"))
    intervals = []
    field = technique.lower()
    for word in words:
        starts, ends, labels = word.get("ph_start", []), word.get("ph_end", []), word.get(field, [])
        for start, end, label in zip(starts, ends, labels):
            if str(label) == "1" and float(end) > float(start):
                intervals.append((float(start), float(end)))
    if not intervals:
        return 0.0
    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return round(sum(end - start for start, end in merged), 6)


def plugin_voice(dataset_voice: str) -> str:
    """Map an explicit dataset singer folder to Vibe's public Voice control."""
    if "Alto" in dataset_voice:
        return "Alto"
    if "Tenor" in dataset_voice:
        return "Tenor"
    raise ValueError(f"No Vibe Voice mapping for dataset singer {dataset_voice}")


def artist_voice(vibe_voice: str) -> str:
    """Artist labels its shared middle vocal range differently from Vibe."""
    return {"Alto": "Alto", "Tenor": "Alto-Tenor"}[vibe_voice]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.manifest.parent
    entries = []
    paired = defaultdict(dict)
    for item in manifest["selection"]["items"]:
        paths = {Path(path).suffix: root / path for path in item["files"]}
        # TextGrid has no suffix in this dataset. JSON and MusicXML are enough
        # to make key-safe rendering decisions; TextGrid remains a later metric.
        score_spelling, scale, fifths = score_key(paths[".musicxml"])
        key = plugin_key(score_spelling)
        stats = voice_stats(paths[".json"])
        annotated_seconds = technique_seconds(paths[".json"], item["technique"]) if item["group"] != "Control_Group" else 0.0
        dataset_voice = item.get("dataset_voice") or manifest.get("selection", {}).get("voice", "EN-Alto-1").replace("English ", "")
        vibe_voice = plugin_voice(dataset_voice)
        entry = {**item, "dataset_voice": dataset_voice, "input_wav": str(root / item["files"][0]), "voice": vibe_voice, "artist_voice": artist_voice(vibe_voice), "score_key": score_spelling, "key": key, "scale": scale, "fifths": fifths, "technique_annotation_seconds": annotated_seconds, **stats,
                 "controls": {"retune_ms": 0.0, "flex_percent": 0.0, "humanize_percent": 0.0, "natural_vibrato": 0.0}}
        entries.append(entry)
        paired[(dataset_voice, item["technique"], item["song"], item["clip"])][item["group"]] = entry

    pairs = []
    for identity, groups in sorted(paired.items()):
        dataset_voice, technique, song, clip = identity
        target_group = f"{technique}_Group"
        if "Control_Group" not in groups or target_group not in groups:
            raise ValueError(f"Incomplete controlled pair: {identity}")
        control, technique_entry = groups["Control_Group"], groups[target_group]
        if (control["key"], control["scale"]) != (technique_entry["key"], technique_entry["scale"]):
            raise ValueError(f"Pair has mismatched scores: {identity}")
        pairs.append({"dataset_voice": dataset_voice, "voice": control["voice"], "artist_voice": control["artist_voice"], "technique": technique, "song": song, "clip": clip, "key": control["key"], "score_key": control["score_key"], "scale": control["scale"], "control": control["input_wav"], "technique_wav": technique_entry["input_wav"], "technique_annotation_seconds": technique_entry["technique_annotation_seconds"]})

    plan = {
        "schema": 1,
        "source_manifest": str(args.manifest),
        "source_revision": manifest["source"]["revision"],
        "purpose": "Internal non-commercial Artist/Vibe behaviour benchmark. Do not redistribute source audio.",
        "invariants": ["Render each input through both plugins with identical host block size, sample rate and controls.", "Set Voice, Key and Scale from this plan for every clip; never apply the legacy fixed F# Natural Minor profile.", "Evaluate Control/technique pairs separately; no DSP promotion without a per-technique gate.", "Keep Hook-2 baseline as a separate regression fixture."],
        "entries": entries,
        "controlled_pairs": pairs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"entries={len(entries)} controlled_pairs={len(pairs)}")
    print(f"plan={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
