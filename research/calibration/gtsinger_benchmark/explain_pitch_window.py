#!/usr/bin/env python3
"""Tie an aligned audio-pitch window to selected/renderer target telemetry."""
import argparse, csv, math
from pathlib import Path
import numpy as np

def load_f0(path):
    return np.asarray([(float(x['time_seconds']), float(x['f0_hz'])) for x in csv.DictReader(open(path))
                       if float(x['f0_hz']) > 0 and math.isfinite(float(x['f0_hz']))])
def closest(a, t):
    i=np.searchsorted(a[:,0],t); i=min(max(i,1),len(a)-1)
    return a[i if abs(a[i,0]-t)<abs(a[i-1,0]-t) else i-1]
def main():
 p=argparse.ArgumentParser(); p.add_argument('artist');p.add_argument('vibe');p.add_argument('trace');p.add_argument('output');p.add_argument('--start',type=float,required=True);p.add_argument('--end',type=float,required=True);p.add_argument('--step-ms',type=float,default=8.0);a=p.parse_args()
 artist,vibe=load_f0(a.artist),load_f0(a.vibe); trace=list(csv.DictReader(open(a.trace))); sr=48000
 rows=[]
 for t in np.arange(a.start,a.end+1e-9,a.step_ms/1000):
  af=closest(artist,t);vf=closest(vibe,t);tr=min(trace,key=lambda x:abs(float(x['sampleIndex'])/sr-t))
  err=1200*math.log2(vf[1]/af[1])
  rows.append([f'{t:.6f}',f'{af[1]:.3f}',f'{vf[1]:.3f}',f'{err:.3f}',tr['committedTargetMidi'],tr['sourceControlTargetMidi'],tr['outputRendererControlTargetMidi'],tr['olaDominantGrainTargetMidi'],tr['rendererShouldRenderWet'],tr['rendererGrainStarved']])
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['time_s','artist_hz','vibe_hz','vibe_minus_artist_cents','selected_midi','source_target_midi','output_target_midi','audible_grain_target_midi','wet','starved']);w.writerows(rows)
 print(out)
if __name__=='__main__':main()
