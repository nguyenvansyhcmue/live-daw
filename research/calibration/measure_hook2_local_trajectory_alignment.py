#!/usr/bin/env python3
"""Estimate Artist/Vibe local trajectory offset after raw-latency alignment.

Input is the existing transfer-frame-debug CSV, whose Artist and Vibe tracks
have already been independently aligned to the same raw vocal.  This avoids
mixing plugin latency with transition shape.  Offset is selected by robust
median absolute movement residual, not waveform phase.
"""
import argparse, csv, math
from pathlib import Path
import numpy as np

ROOT=Path('/Users/hiimdrdey/autotune')
INPUT=ROOT/'artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-20261017-113341/crossing_24ms/transfer/transfer-frame-debug.csv'
EVENTS=ROOT/'artifacts/hook2-tdpsola-renderer-crossing-preview-sweep-20261017-113341/crossing_24ms/transitions/transition-events.csv'
OUT=ROOT/'artifacts/hook2-local-trajectory-alignment-20261017.csv'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--transfer', type=Path, default=INPUT)
    parser.add_argument('--events', type=Path, default=EVENTS)
    parser.add_argument('--output', type=Path, default=OUT)
    args=parser.parse_args()
    rows=list(csv.DictReader(args.transfer.open()))
    time=np.array([float(r['raw_time_seconds']) for r in rows])
    artist=np.array([float(r['artist_movement_cents']) for r in rows])
    vibe=np.array([float(r['vibe_movement_cents']) for r in rows])
    increments=np.diff(time)
    dt=float(np.median(increments[increments > 0]))
    events=[r for r in csv.DictReader(args.events.open())
            if r.get('retune_ms')=='0' and r.get('flex_tune')=='0'
            and r.get('humanize')=='0' and r.get('natural_vibrato')=='0']
    result=[]
    for e in events:
        center=float(e['time_seconds']); mask=(time>=center-.100)&(time<=center+.100)
        a=artist[mask]; v=vibe[mask]
        best=None
        # Only compare when Artist has meaningful correction movement; this
        # makes held/noise frames unable to decide a timing offset.
        for lag_ms in range(-80,81):
            shift=round((lag_ms/1000)/dt)
            if abs(shift) >= len(a)-20:
                continue
            if shift>=0: x,y=a[shift:],v[:len(v)-shift] if shift else v
            else: x,y=a[:len(a)+shift],v[-shift:]
            active=np.abs(x)>=8.0
            if active.sum()<20: continue
            error=float(np.median(np.abs(y[active]-x[active])))
            corr=float(np.corrcoef(x[active],y[active])[0,1]) if active.sum()>2 else float('nan')
            candidate=(error, -corr if math.isfinite(corr) else 1e9, lag_ms, corr, int(active.sum()))
            if best is None or candidate<best: best=candidate
        if best is None: continue
        err,_,lag,corr,count=best
        result.append([center,e['direction'],round(lag,3),round(err,3),round(corr,4),count,
                       e['vibe_minus_artist_t10_ms'],e['vibe_minus_artist_t50_ms'],e['vibe_minus_artist_t90_ms']])
    with args.output.open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['event_s','direction','best_vibe_lead_ms','median_residual_cents','correlation','active_frames','t10_delta_ms','t50_delta_ms','t90_delta_ms']);w.writerows(result)
    print(args.output)
    for r in sorted(result,key=lambda x:x[3],reverse=True)[:12]:print(','.join(map(str,r)))
if __name__=='__main__':main()
