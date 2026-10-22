#!/usr/bin/env python3
"""Small, reproducible gate for the Hook-2 hard-tune experiments.

It only reads existing artifacts. A candidate is promotable only if it beats
the selected 24-ms baseline on the global error and does not create more than
Artist's 29 transitions. It deliberately does not install anything.
"""
import csv
from pathlib import Path

ROOT=Path('/Users/hiimdrdey/autotune/artifacts')
CASES={
 'baseline crossing-24': ROOT/'hook2-tdpsola-renderer-crossing-preview-sweep-20261017-113341/crossing_24ms',
 'boundary dwell 3': ROOT/'hook2-boundary-dwell3-current-20261017-121009',
 'rapid preview': ROOT/'hook2-rapid-legato-preview-current-20261017-121457',
 'rapid preview lead .50': ROOT/'hook2-rapid-legato-lead50-current-20261017-121855',
 'renderer crossing 48 ms': ROOT/'hook2-crossing48-current-20261017-122453',
}
def metrics(root):
    transfer=(root/'transfer/transfer-report.md').read_text()
    import re
    slope=float(re.search(r'slope: ([0-9.]+)',transfer).group(1))
    median=float(re.search(r'Global median absolute movement error: ([0-9.]+)',transfer).group(1))
    p90=float(re.search(r'\| 0 \| 0/0/0/0 \| [0-9.]+ \| [0-9.]+ \| ([0-9.]+) \|',transfer).group(1))
    row=next(csv.DictReader((root/'comparison/calibration-report.csv').open()))
    transitions=int(row['vibe_transition_count'])
    events=[]
    for e in csv.DictReader((root/'transitions/transition-events.csv').open()):
        if 4.42<float(e['time_seconds'])<4.85: events.append(float(e['vibe_minus_artist_t50_ms']))
    return slope,median,p90,transitions,events
def main():
    rows={name:metrics(path) for name,path in CASES.items()}
    base=rows['baseline crossing-24']
    out=['# Hook-2 candidate scorecard','',
         'Promotion: median and P90 may not worsen; Vibe transitions ≤ Artist 29; both 4.447/4.631 windows must improve.', '',
         '| Candidate | Slope | Median cents | P90 cents | Transitions | 4.447/4.631 t50 ms | Verdict |','|---|---:|---:|---:|---:|---|---|']
    for name,(s,m,p,t,ev) in rows.items():
        promoted=(m<=base[1] and p<=base[2] and t<=29 and len(ev)>=2 and abs(ev[0])<abs(base[4][0]) and abs(ev[1])<abs(base[4][1]))
        verdict='BASELINE' if name=='baseline crossing-24' else ('PROMOTE' if promoted else 'REJECT')
        out.append(f'| {name} | {s:.4f} | {m:.2f} | {p:.2f} | {t} | {", ".join(f"{x:+.1f}" for x in ev)} | {verdict} |')
    target=ROOT/'hook2-candidate-scorecard-20261017.md'; target.write_text('\n'.join(out)+'\n'); print(target); print('\n'.join(out))
if __name__=='__main__': main()
