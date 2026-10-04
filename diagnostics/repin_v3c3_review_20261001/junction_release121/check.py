"""Bounded cached interaction/flow audit. No FZP, COM, fit, or rollout."""
from collections import Counter, defaultdict
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parents[1]
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def dump(name, x):
    (HERE/name).write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    assert not (HERE/'assessment.json').exists(), 'Preserve completed results'
    data = read(R/'lane_interaction110/frames.json.gz')
    events = read(R/'boundary_time88/events.json')
    network = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    raw = network.read_bytes()
    PINS[str(network)] = hashlib.sha256(raw).hexdigest()
    net = ET.fromstring(raw)
    links = {int(x.get('no')): x for x in net.findall('./links/link')}
    branch = float(links[10483].find('fromLinkEndPt').get('pos'))
    merge = float(links[10490].find('toLinkEndPt').get('pos'))
    assert links[10483].find('fromLinkEndPt').get('lane') == '119 1'
    assert links[10490].find('toLinkEndPt').get('lane') == '119 1'
    start, end = 2700.1, 3145.1
    dump('protocol.json', dict(scope='seed67 common2700.1 RMrelease110/90, cached445s',
        hypothesis='Shared10483/10490 bottleneck interaction: localized front vs propagated stopped queue; relate to observed short discharge without a fitted VSL bonus.',
        budget=dict(native_runs=0, fzp_reads=0, forecasts=0, fits=0),
        source_pins=PINS, start_sec=start, end_sec=end,
        thresholds_kmh=[1,5], history_sec=10, blocks_sec=[150,150,145],
        limitations=['5s sampled interaction associations, not causal attribution or full event durations.',
            '5s observed mainline face crossings are lower bounds; exact off-entry counts use cached native MER.',
            'Front definition stops at first moving vehicle, not the ultimate cause of congestion.',
            'Only current and prior frames define current features; future events are response labels only.']))
    offsets = data['offsets_m']
    def x(r):
        return offsets.get(str(r['link']), math.nan)+r['pos']
    exit_x = offsets['119']+branch
    rows_out, block_rows, results = [], [], {}
    for arm in ('release', 'release_vsl90'):
        frames = data['cases'][arm]['frames']
        assert len(frames)==90 and frames[0]['t']==start and frames[-1]['t']==end
        es = [e for e in events if e['case']==f'67_release/{arm}' and e['ref']=='off_entry:10483']
        assert len({e['vehicle'] for e in es})==len(es)
        last_merge = {}
        previous = {}
        merged_ids = set()
        chain_counts = Counter()
        arm_rows = []
        for k, frame in enumerate(frames):
            t, rows = frame['t'], frame['rows']
            for vid, r in rows.items():
                old = previous.get(vid)
                if old and old['link']==10490 and r['link']==119:
                    last_merge[vid] = t
                    merged_ids.add(vid)
            rec = dict(case=arm, time_sec=t, stopped_total=0, stopped_upstream_branch=0,
                upstream_chain_reaches_downstream=0, upstream_chain_recent_merge=0,
                upstream_chain_offramp=0, upstream_chain_spans_exit=0,
                stopped_body_spans_exit=0, queued_exit_within50m=0,
                recent_merge_in_link119=0)
            for vid, r in rows.items():
                if r['link']==119 and r['lane']==1:
                    rec['stopped_body_spans_exit'] += int(r['speed']<5 and r['pos']-float(r['LENGTH'])<=branch<=r['pos'])
                    rec['queued_exit_within50m'] += int(r['NEXTLINK\\NO']=='10483' and 0<=branch-r['pos']<=50 and r['speed']<5)
                    rec['recent_merge_in_link119'] += int(t-last_merge.get(vid,-1e6)<=10)
                if r['cell'] is None or not 16<=r['cell']<=25 or r['speed']>=5:
                    continue
                rec['stopped_total'] += 1
                if x(r)>exit_x:
                    continue
                rec['stopped_upstream_branch'] += 1
                cur, seen, chain = vid, set(), []
                why='missing'
                while cur in rows and cur not in seen:
                    z=rows[cur];seen.add(cur);chain.append((cur,z))
                    if z['speed']>=5:
                        why='moving';break
                    if z['INTERACTTARGTYPE']!='Vehicle':
                        why='nonvehicle';break
                    cur=z['INTERACTTARGNO']
                else:
                    if cur in seen: why='cycle'
                leaders=chain[1:]
                rec['upstream_chain_reaches_downstream'] += int(any(x(z)>exit_x for _,z in leaders))
                rec['upstream_chain_recent_merge'] += int(any(t-last_merge.get(j,-1e6)<=10 for j,z in leaders))
                rec['upstream_chain_offramp'] += int(any(z['link']==10483 for _,z in leaders))
                rec['upstream_chain_spans_exit'] += int(any(z['link']==119 and z['lane']==1 and z['speed']<5 and z['pos']-float(z['LENGTH'])<=branch<=z['pos'] for _,z in leaders))
                front_id, front=chain[-1]
                if why!='moving': category=why
                elif front['link']==10483: category='moving_off10483'
                elif front['link']==10490 or t-last_merge.get(front_id,-1e6)<=10: category='moving_recent10490'
                elif front['cell'] is not None: category=f"moving_cell{front['cell']}"
                else: category='moving_other'
                chain_counts[category]+=1
            if k<len(frames)-1:
                nxt=frames[k+1]
                assert abs(nxt['t']-t-5)<1e-7
                for label, boundary in [('cell19_exit', data['bounds_m'][20]), ('after_merge_face',data['bounds_m'][21])]:
                    crossings=[vid for vid,z in rows.items() if z['cell'] is not None and x(z)<boundary
                        and vid in nxt['rows'] and nxt['rows'][vid]['cell'] is not None and x(nxt['rows'][vid])>=boundary]
                    rec[label+'_observed_crossings_next5s']=len(crossings)
                rec['exact10483_entry_next5s']=sum(t<e['time_sec']<=nxt['t'] for e in es)
                rec['interval_sec']=5
            else:
                rec['cell19_exit_observed_crossings_next5s']=None
                rec['after_merge_face_observed_crossings_next5s']=None
                rec['exact10483_entry_next5s']=None
                rec['interval_sec']=0
            arm_rows.append(rec)
            previous=rows
        assert sum(chain_counts.values())==sum(z['stopped_upstream_branch'] for z in arm_rows)
        assert sum(z['exact10483_entry_next5s'] or 0 for z in arm_rows)==sum(start<e['time_sec']<=end for e in es)
        # Disjoint chronological windows, no arbitrary best-lag selection.
        blocks=[]
        for left,right in [(start,start+150),(start+150,start+300),(start+300,end)]:
            rs=[z for z in arm_rows if left<=z['time_sec']<right]
            out=dict(case=arm,start_sec=left,end_sec=right,intervals=len(rs))
            for name in arm_rows[0]:
                if name not in ('case','time_sec','interval_sec'):
                    out[name]=sum(z[name] for z in rs)/(1 if 'next5s' in name else len(rs))
            blocks.append(out);block_rows.append(out)
        groups={}
        for feature in ('stopped_body_spans_exit','upstream_chain_recent_merge','upstream_chain_reaches_downstream'):
            groups[feature]={}
            for active in (False,True):
                rs=[z for z in arm_rows[:-1] if bool(z[feature])==active]
                groups[feature][str(active)]=dict(intervals=len(rs),
                    observed_exit10483_veh_per5s=sum(z['exact10483_entry_next5s'] for z in rs)/len(rs) if rs else None,
                    mean_upstream_stopped=sum(z['stopped_upstream_branch'] for z in rs)/len(rs) if rs else None)
        results[arm]=dict(blocks=blocks, chain_first_moving_category_samples=dict(chain_counts),
            conditional_groups=groups, observed_direct_10490_merges_unique=len(merged_ids),
            exact10483_entries=sum(start<e['time_sec']<=end for e in es))
        rows_out.extend(arm_rows)
    initial={a:{k:v for k,v in data['cases'][a]['frames'][0]['rows'].items() if v['cell'] is not None and 16<=v['cell']<=25} for a in results}
    assert initial['release']==initial['release_vsl90']
    for name,rs in [('frames.csv',rows_out),('blocks.csv',block_rows)]:
        with (HERE/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    for path,pin in PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin
    dump('assessment.json',dict(status='COMPLETE_CACHED_JUNCTION_AUDIT',
        branch_position_m=branch, merge_position_m=merge, separation_m=merge-branch,
        cases=results, initial_equal=True, source_pins=PINS,
        caution='Overlapping association counts are not an additive causal decomposition. No fitted capacity loss or gain forecast qualification.'))
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
