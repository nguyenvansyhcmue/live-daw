"""Audio acceptance evidence; no DSP parameters or reference audio enter the core.

Timing alignment is an envelope estimate, not proof of algorithmic latency.
Pitch comparison never bridges an unvoiced gap. Envelope/formant metrics are
proxies, not a claim that listening has passed.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from scipy.signal import stft
from scipy.ndimage import median_filter

parser=argparse.ArgumentParser()
parser.add_argument('raw',type=Path)
parser.add_argument('artist',type=Path)
parser.add_argument('candidate',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--diagnostic',type=Path)
args=parser.parse_args()
tools=Path('/Users/hiimdrdey/autotune/artifacts/crossing24-bounded-preview-20261017-113218/source/tools')
sys.path.insert(0,str(tools))
from compare_pitch_correction_bounces import pitch_track,read_mono
from measure_artist_vibe_latency_aligned import envelope_delay
args.output.mkdir(parents=True,exist_ok=True)
rate,raw=read_mono(args.raw)
ar,artist=read_mono(args.artist)
cr,candidate=read_mono(args.candidate)
assert rate==ar==cr
ad=envelope_delay(raw,artist,rate);cd=envelope_delay(raw,candidate,rate)
a=pitch_track(artist,rate);c=pitch_track(candidate,rate)
at=a[:,0]/rate-ad/rate;ct=c[:,0]/rate-cd/rate
left=np.searchsorted(ct,at,side='right')-1
right=left+1
inrange=(left>=0)&(right<len(ct))
left=np.clip(left,0,len(ct)-1);right=np.clip(right,0,len(ct)-1)
valid=inrange & np.isfinite(a[:,1]) & (a[:,2]>=.55) & np.isfinite(c[left,1]) & np.isfinite(c[right,1]) & (c[left,2]>=.55)&(c[right,2]>=.55)
fraction=np.clip((at-ct[left])/np.maximum(ct[right]-ct[left],1e-9),0,1)
interpolated=c[left,1]+fraction*(c[right,1]-c[left,1])
error=1200*np.log2(np.maximum(interpolated,1e-12)/np.maximum(a[:,1],1e-12))
an=69+12*np.log2(np.maximum(a[:,1],1e-12)/440)
cn=69+12*np.log2(np.maximum(interpolated,1e-12)/440)
def stats(mask):
    v=valid&mask
    if not np.any(v):return {'frames':0}
    return {'frames':int(v.sum()),'median_abs_cents':float(np.median(abs(error[v]))),'p90_abs_cents':float(np.quantile(abs(error[v]),.9)),
            'note_match':float(np.mean(np.rint(an[v])==np.rint(cn[v]))),'coverage_of_artist_voiced':float(v.sum()/max(1,np.sum(mask&np.isfinite(a[:,1])&(a[:,2]>=.55))))}
results={'alignment_method':'RMS envelope estimate; no gap interpolation','artist_lag_samples':ad,'candidate_lag_samples':cd,'whole':stats(np.ones(len(at),bool)),
         'regions':{f'{lo}-{hi}':stats((at>=lo)&(at<hi)) for lo,hi in [(0,2),(4,4.6),(4.7,5.1),(7,8),(8.25,8.5)]}}
np.savetxt(args.output/'pitch-frames.csv',np.c_[at,an,cn,error,valid],delimiter=',',header='time,artist_midi,candidate_midi,error_cents,usable',comments='')
# Conservative transition landmarks: preserve uniform time-grid and mark
# missing endpoint/coverage as failure instead of deleting the event.
notes=median_filter(np.nan_to_num(np.rint(an),nan=-1).astype(int),size=3)
voiced=np.isfinite(a[:,1])&(a[:,2]>=.55)
notes[~voiced | (abs(an-notes)>.20)]=-1
boundaries=np.r_[0,np.flatnonzero(np.diff(notes)!=0)+1,len(notes)]
runs=[]
for l,r in zip(boundaries[:-1],boundaries[1:]):
    note=int(notes[l])
    if note<0:continue
    if runs and runs[-1][2]==note and l-runs[-1][1]<=8:
        runs[-1]=(runs[-1][0],int(r),note)
    else:runs.append((int(l),int(r),note))
runs=[run for run in runs if run[1]-run[0]>=8]
events=[]
for previous,current in zip(runs[:-1],runs[1:]):
    l,r,note=previous;nl,nr,newnote=current
    if note==newnote or abs(newnote-note)>5 or at[nl]-at[r-1]>.25:continue
    lo=max(l,r-24);hi=min(nr,nl+24)
    old=float(np.median(an[max(l,r-8):r]));new=float(np.median(an[nl:min(nr,nl+8)]))
    row={'time':float((at[r-1]+at[nl])*.5),'old_midi':note,'new_midi':newnote}
    for label,track,ok in [('artist',an,voiced),('candidate',cn,valid)]:
        step=new-old
        progress=(track[lo:hi]-old)/step
        row[label+'_coverage']=float(np.mean(ok[lo:hi]))
        candidates=np.flatnonzero((progress[1:]>=.5)&(progress[:-1]<.5)&ok[lo+1:hi]&ok[lo:hi-1])+1
        middle=min(candidates,key=lambda i:abs(at[lo+i]-row['time'])) if len(candidates) else None
        for fraction in [.1,.5,.9]:
            index=None
            if middle is not None:
                if fraction==.5:index=middle
                elif fraction<.5:
                    cross=np.flatnonzero((progress[:middle]<fraction)&ok[lo:lo+middle])
                    if len(cross):index=int(cross[-1])+1
                else:
                    cross=np.flatnonzero((progress[middle:]>=fraction)&ok[lo+middle:hi])
                    if len(cross):index=middle+int(cross[0])
            row[label+f'_t{int(fraction*100)}_ms']=float(at[lo+index]*1000) if index is not None else None
        t10=row[label+'_t10_ms'];t90=row[label+'_t90_ms']
        row[label+'_duration_ms']=t90-t10 if t10 is not None and t90 is not None else None
        row[label+'_slope_cents_per_ms']=abs(step)*80/(t90-t10) if t10 is not None and t90 is not None and t90>t10 else None
    events.append(row)
if events:
    with (args.output/'transitions.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=events[0].keys());writer.writeheader();writer.writerows(events)
results['transition_landmarks_count']=len(events)
# Align on the common raw time support for level and envelope measurements.
start=max(0,-ad,-cd);end=min(len(raw),len(artist)-ad,len(candidate)-cd)
aa=artist[start+ad:end+ad];cc=candidate[start+cd:end+cd]
rms=lambda x:float(np.sqrt(np.mean(x*x)+1e-24))
gain=rms(aa)/rms(cc)
results['level']={'candidate_minus_artist_rms_db':20*np.log10(1/gain),'peak_candidate':float(np.max(abs(cc))),
                 'sample_step_p999_artist':float(np.quantile(abs(np.diff(aa)),.999)),
                 'sample_step_p999_candidate_level_matched':float(np.quantile(abs(np.diff(cc*gain)),.999))}
_,_,sa=stft(aa,fs=rate,nperseg=2048,noverlap=1536,boundary=None)
_,_,sc=stft(cc*gain,fs=rate,nperseg=2048,noverlap=1536,boundary=None)
pa=abs(sa)**2+1e-20;pc=abs(sc)**2+1e-20
freq=np.fft.rfftfreq(2048,1/rate)
results['bands_level_matched_db']={f'{lo}-{hi}':float(10*np.log10(pc[(freq>=lo)&(freq<hi)].sum()/pa[(freq>=lo)&(freq<hi)].sum())) for lo,hi in [(100,500),(500,2000),(2000,6000),(6000,10000)]}
def envelope(s):
    cep=np.fft.irfft(np.log(abs(s)+1e-10),n=2048,axis=0)
    cutoff=int(rate*.0015);cep[cutoff:-cutoff]=0
    return np.fft.rfft(cep,n=2048,axis=0).real
envelope_delta=(envelope(sc)-envelope(sa))*20/np.log(10)
results['spectral_envelope_proxy_median_abs_db']=float(np.median(abs(envelope_delta[(freq>=200)&(freq<=5000)])))
if args.diagnostic:
    dr,diagnostic=read_mono(args.diagnostic);assert dr==rate
    size=min(len(diagnostic),len(candidate));d=diagnostic[:size];h=candidate[:size]
    g=float(np.dot(d,h)/max(np.dot(d,d),1e-20))
    results['host_vs_diagnostic']={'gain':g,'max_abs_difference_after_gain':float(np.max(abs(h-d*g))),'rms_difference_after_gain':rms(h-d*g)}
results['provenance']={label:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for label,path in [('raw',args.raw),('artist',args.artist),('candidate',args.candidate)]}
results['listening_verdict']='NOT VERIFIED'
(args.output/'metrics.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
