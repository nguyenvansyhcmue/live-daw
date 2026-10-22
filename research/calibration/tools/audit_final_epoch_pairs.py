#!/usr/bin/env python3
"""Compare finalized renderer tickets by source-decision identity, not output time."""
import argparse
import csv
import json
from pathlib import Path


def read(path):
    with path.open() as f:
        return {int(r['pendingCandidateId']): r for r in csv.DictReader(f)
                if r['finalized'] == '1'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('parent',type=Path); p.add_argument('candidate',type=Path)
    p.add_argument('output',type=Path); a=p.parse_args()
    parent=read(a.parent/'renderer_epoch_trace.csv')
    candidate=read(a.candidate/'renderer_epoch_trace.csv')
    rows=[]
    for key, old in parent.items():
        if key not in candidate:
            continue
        new=candidate[key]
        if old['decisionSourceSample'] != new['decisionSourceSample']:
            raise ValueError('Candidate identity differs: cannot join by ID')
        t=int(old['decisionSourceSample'])/48
        if not any(lo <= t <= hi for lo,hi in [(3820,3940),(7500,7630),(8320,8440)]):
            continue
        row=dict(id=key,decision_ms=t)
        for name in ['selectedMark','synthesisMark','firstAudible','controlTimestamp',
                     'controlPublicationSample','targetEventId','sealSample',
                     'sourcePeriod','ratio','retimeSamples']:
            row['parent_'+name]=float(old[name])
            row['candidate_'+name]=float(new[name])
        row['center_shift_ms']=(int(new['synthesisMark'])-int(old['synthesisMark']))/48
        row['source_same']=old['selectedMark']==new['selectedMark']
        rows.append(row)
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/'epoch-pairs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    summary=[]
    for label,lo,hi in [('down1',3820,3940),('up',7500,7630),('down2',8320,8440)]:
        rr=[r for r in rows if lo<=r['decision_ms']<=hi]
        summary.append(dict(window=label,count=len(rr),same_sources=sum(r['source_same'] for r in rr),
                            min_shift_ms=min(r['center_shift_ms'] for r in rr),
                            max_shift_ms=max(r['center_shift_ms'] for r in rr)))
    print(json.dumps(summary,indent=2))
    (a.output/'epoch-pair-summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':
    main()
