"""Reuse194 caches to separate neighbor renewal from within-platoon errors.

Future geometry is used only to stratify evaluation, never as a model input.
No fit, forecast, FZP read, native run, or production dynamics modification.
"""
from collections import defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import math
import time

from diagnostics.repin_v3c3_review_20261001.neighbor_information194.check import normalize, physical_link

HERE=Path(__file__).resolve().parent
R=HERE.parent


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def main():
    started=time.perf_counter()
    output=HERE/'neighbor_renewal.json'
    assert not output.exists()
    source=R/'neighbor_information194'
    rows=read(source/'rows.json.gz')
    protocol=read(source/'protocol.json')
    paths={}
    for key in protocol['input_sha256']:
        p=Path(key)
        if not p.name.endswith('_frames.json.gz'):continue
        case=p.stem.removesuffix('_frames').removeprefix('s')
        if p.parent.name=='blocking176':case='67_'+p.name.removesuffix('_frames.json.gz')
        paths[case]=p
    scores=[]
    for case,path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==protocol['input_sha256'][str(path)]
        frames=normalize(read(path));future_leaders={}
        for t,frame in frames.items():
            by=defaultdict(list)
            for vid,z in frame.items():
                link=physical_link(z['x'])
                if link is not None:by[link,z['lane']].append((z['x'],vid))
            leaders={}
            for lane in by.values():
                lane.sort()
                for (_,vid),(_,lead) in zip(lane,lane[1:]):leaders[vid]=lead
            future_leaders[t]=leaders
        groups=defaultdict(list)
        selected=[r for r in rows if r['case']==case]
        for r in selected:
            leader=future_leaders[round(r['t']+5,6)].get(r['id'])
            category='same_leader' if leader==r['leader'] else 'no_future_leader' if leader is None else 'changed_leader'
            groups[category].append(r)
        assert sum(map(len,groups.values()))==len(selected)
        for category, rr in sorted(groups.items()):
            item=dict(case=case,category=category,n=len(rr),fraction=len(rr)/len(selected))
            for model in ('mean','ordered'):
                errors=[r[model]-r['y'] for r in rr]
                item[model+'_rmse_kmh']=math.sqrt(sum(e*e for e in errors)/len(rr))
                item[model+'_squared_error_share']=sum(e*e for e in errors)/sum((r[model]-r['y'])**2 for r in selected)
            scores.append(item)
    output.write_text(json.dumps(dict(status='complete_conditional_diagnostic',scores=scores,
        seconds=time.perf_counter()-started,rows=len(rows),fits=0,autonomous=0,native=0,
        definition='Same vehicle, same physical link and lane at five-second endpoints; classify by geometric immediate leader at the later endpoint.',
        limitations='Future categories are evaluation-only; intervening lane changes may be censored. Repeated vehicles are not independent runs; no causal RM/VSL attribution.',
        source_rows_sha256=hashlib.sha256((source/'rows.json.gz').read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print(str(output))


if __name__=='__main__':main()
