#!/usr/bin/env python3
"""Offline stage-span audit; no DSP edits, no fitted internal-clock offsets."""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np


def midi(hz):
    return 69 + 12 * np.log2(np.maximum(hz, 1e-20) / 440)


def crossing(t, notes, old, new, lo, hi):
    mask = (t >= lo) & (t <= hi) & np.isfinite(notes)
    t, notes = t[mask], notes[mask]
    progress = (notes - old) / (new - old)
    times = []
    for threshold in (0.1, 0.5, 0.9):
        hits = np.flatnonzero(progress >= threshold)
        times.append(float(t[hits[0]]) if len(hits) else None)
    return dict(t10_ms=times[0], t50_ms=times[1], t90_ms=times[2],
                span_ms=times[2]-times[0] if all(v is not None for v in times) else None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run', type=Path)
    p.add_argument('--pitch-tools', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    sys.path.insert(0, str(a.pitch_tools))
    from compare_pitch_correction_bounces import pitch_track
    from measure_artist_vibe_latency_aligned import read_mono
    with (a.run/'full_default_intervals.csv').open() as f:
        rows = list(csv.DictReader(f))
    def col(name):
        return np.array([float(r[name]) for r in rows])
    sr, audio = read_mono(a.run/'full_default_render.wav')
    t = col('sampleIndex')*1000/sr
    command = midi(col('sourceControlF0Hz')*col('sourceControlPitchRatio'))
    target = col('committedTargetMidi')
    # Interval spawn telemetry describes provisional scheduling. After retiming
    # it is NOT the final emitted lattice. Use finalized epoch tickets instead.
    with (a.run/'renderer_epoch_trace.csv').open() as f:
        epochs = [r for r in csv.DictReader(f) if r['finalized'] == '1']
    marks = np.array(sorted(set(float(r['synthesisMark']) for r in epochs)))
    et = marks[1:]*1000/sr
    cadence = midi(sr/np.diff(marks))
    track = pitch_track(audio, sr)
    wt = track[:, 0]*1000/sr
    wn = midi(track[:, 1])
    wn[track[:, 2] < .55] = np.nan
    results, details = [], []
    # Explicit evaluation windows; never passed into the renderer.
    for anchor, old, new, near in [(3.855604,59,57,3884.67),
                                  (7.542271,57,59,7572.67),
                                  (8.356937,59,57,8386.0)]:
        changes = np.flatnonzero((np.r_[False,np.diff(target)!=0]) & (target == new)
                                & (np.abs(t-near)<15))
        if len(changes) != 1:
            raise ValueError(f'Ambiguous commit for {anchor}: {changes}')
        commit=t[changes[0]]
        stages={}
        for label, times, notes in [('command_observed',t,command),
                                    ('finalized_cadence',et,cadence),
                                    ('wav_pitch',wt,wn)]:
            stages[label]=crossing(times, notes,old,new,commit-8,commit+65)
            for x,y in zip(times,notes):
                if commit-12 <= x <= commit+70:
                    details.append(dict(anchor_seconds=anchor,stage=label,
                                        engine_time_ms=float(x),midi=float(y)))
        results.append(dict(anchor_seconds=anchor,old_midi=old,new_midi=new,
                            commit_observed_ms=float(commit),stages=stages))
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/'stage-curves.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=details[0].keys());w.writeheader();w.writerows(details)
    payload=dict(run=str(a.run),sample_rate=sr,events=results,
                 limitations=['Fixed MIDI endpoints, first crossings, no monotonicity assumption.',
                 'Command timestamp is observation/availability, not acoustic onset.',
                 'Cadence is scheduled grain-center spacing, not measured waveform F0.',
                 'WAV estimator uses a centered 1024-sample window and 64-sample hop; spans can be blurred.',
                 'Stage spans are diagnostic evidence, not additive causal latency components.'])
    (a.output/'stage-spans.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))


if __name__ == '__main__':
    main()
