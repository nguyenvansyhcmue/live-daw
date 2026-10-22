#!/usr/bin/env python3
"""Emit a balanced, bounded set of GTSinger controlled-pair render jobs."""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("plan", type=Path)
parser.add_argument("--pairs-per-technique", type=int, default=1)
args = parser.parse_args()
if args.pairs_per_technique < 1:
    raise SystemExit("pairs-per-technique must be positive")
plan = json.loads(args.plan.read_text(encoding="utf-8"))
by_voice_and_technique = defaultdict(list)
for pair in plan["controlled_pairs"]:
    by_voice_and_technique[(pair["dataset_voice"], pair["voice"], pair["technique"])].append(pair)
print("dataset_voice\tvibe_voice\tartist_voice\ttechnique\tsong\tclip\tgroup\tvibe_key\tartist_key\tscale\tinput_wav")
for dataset_voice, voice, technique in sorted(by_voice_and_technique):
    pairs = sorted((pair for pair in by_voice_and_technique[(dataset_voice, voice, technique)] if pair.get("technique_annotation_seconds", 0.0) > 0.0), key=lambda value: (value["song"], value["clip"]))
    if len(pairs) < args.pairs_per_technique:
        raise SystemExit(f"{dataset_voice} {technique}: requested {args.pairs_per_technique} annotation-positive pairs, found {len(pairs)}")
    for pair in pairs[:args.pairs_per_technique]:
        for group, wav_field in (("Control_Group", "control"), (f"{technique}_Group", "technique_wav")):
            print("\t".join((dataset_voice, voice, pair["artist_voice"], technique, pair["song"], pair["clip"], group, pair["key"], pair["score_key"], pair["scale"], pair[wav_field])))
