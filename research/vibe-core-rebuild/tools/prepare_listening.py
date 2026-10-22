"""Export aligned, RMS-matched FLOAT WAVs without clipping or modifying inputs.

Identical shared headroom is applied after matching. These are listening
materials, not independent validation of alignment or perceived quality.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile

p=argparse.ArgumentParser()
p.add_argument('audit',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
m=json.loads((a.audit/'metrics.json').read_text())
def read(path):
    rate,x=wavfile.read(path)
    dtype=x.dtype
    x=x.astype(np.float64)
    if np.issubdtype(dtype,np.integer):x/=max(abs(np.iinfo(dtype).min),np.iinfo(dtype).max)
    if x.ndim==2:x=x.mean(axis=1)
    return rate,x
rate,artist=read(m['provenance']['artist']['path'])
cr,vibe=read(m['provenance']['candidate']['path'])
assert cr==rate
ad=m['artist_lag_samples'];vd=m['candidate_lag_samples']
start=max(0,-ad,-vd);end=min(len(artist)-ad,len(vibe)-vd)
artist=artist[start+ad:end+ad];vibe=vibe[start+vd:end+vd]
gain=np.sqrt(np.mean(artist**2)/np.mean(vibe**2))
vibe*=gain
headroom=min(1.,.95/max(np.max(abs(artist)),np.max(abs(vibe))))
a.output.mkdir(parents=True,exist_ok=True)
for name,x in [('Artist',artist),('Vibe-new-core',vibe)]:
    wavfile.write(a.output/(name+'.wav'),rate,(x*headroom).astype(np.float32))
(a.output/'levels.json').write_text(json.dumps(dict(sample_rate=rate,
    vibe_gain_db=20*np.log10(gain),shared_gain_db=20*np.log10(headroom),
    alignment='Estimated RMS envelope delay, not temporal warping',
    listening_verdict='NOT REVIEWED'),indent=2)+'\n')
