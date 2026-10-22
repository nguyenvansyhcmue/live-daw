#!/usr/bin/env python3
"""Compare two fixed-origin Vibe renders against one external vocal reference."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('raw',type=Path);p.add_argument('reference',type=Path)
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--pitch-tools',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();sys.path.insert(0,str(a.pitch_tools))
from compare_pitch_correction_bounces import pitch_track
from measure_artist_vibe_latency_aligned import envelope_delay,read_mono
sr,raw=read_mono(a.raw)
rr,ref=read_mono(a.reference)
pr,par=read_mono(a.parent)
cr,can=read_mono(a.candidate)
if len({sr,rr,pr,cr})!=1:raise ValueError('Sample-rate mismatch')
ref_delay=envelope_delay(raw,ref,sr)
parent_delay=envelope_delay(raw,par,sr)
tracks={}
for name,x,delay in [('reference',ref,ref_delay),('parent',par,parent_delay),('candidate',can,parent_delay)]:
 tr=pitch_track(x,sr)
 t=tr[:,0]/sr-delay/sr
 good=np.isfinite(tr[:,1])&(tr[:,1]>0)&(tr[:,2]>=.55)
 tracks[name]=(t[good],tr[good,1])
t,rf=tracks['reference']
result={'sample_rate':sr,'source_samples_scored':min(len(raw),len(par),len(can)),
        'reference_alignment_samples':ref_delay,'frozen_vibe_alignment_samples':parent_delay}
for name in ('parent','candidate'):
 tt,v=tracks[name]
 output=np.interp(t,tt,v,left=np.nan,right=np.nan)
 good=np.isfinite(output)
 cents=np.abs(1200*np.log2(output[good]/rf[good]))
 same=np.rint(69+12*np.log2(output[good]/440))==np.rint(69+12*np.log2(rf[good]/440))
 result[name]={'median_abs_pitch_cents':float(np.median(cents)),
               'p90_abs_pitch_cents':float(np.quantile(cents,.9)),
               'same_note_fraction':float(np.mean(same)),
               'voiced_comparison_frames':int(np.sum(good))}
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
