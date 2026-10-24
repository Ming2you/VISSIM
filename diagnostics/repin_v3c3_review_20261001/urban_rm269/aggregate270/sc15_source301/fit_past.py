"""Past-only SC15 queue-platoon service estimate and downstream-route support.

Use the stopped single-lane platoon present before GREEN, discard its first
three vehicles, then bound the interdeparture span of the remaining platoon.
The selected midpoint estimate and its timing bounds are not population CIs.
"""
from collections import Counter,defaultdict
from pathlib import Path
import gzip,hashlib,importlib.util,json,math,sys

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.validate_native_signal_record import read_ldp_frames


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())


def queued_platoon_blocks(frames,events,clock,source,head,sg,start=900,end=2100):
    by_vehicle={e['veh']:e for e in events};blocks=[];excluded=[]
    for green_start in range(start+1,end):
        if clock[green_start][sg]!='GREEN' or clock[green_start-1][sg]=='GREEN':continue
        green_end=green_start
        while clock[green_end][sg]=='GREEN':green_end+=1
        if green_end>end:continue
        before=max((f for f in frames if f['sec']<green_start),key=lambda f:f['sec'])
        q=sorted([r for r in before['rows'] if r[1]==source and r[3]<=head and r[4]<=5],key=lambda r:-r[3])
        assert green_start-before['sec']<=5
        tail=q[3:]
        if len(tail)<2:
            excluded.append(dict(green_start=green_start,reason='fewer_than_two_after_first_three'));continue
        if any(r[0] not in by_vehicle for r in tail):
            excluded.append(dict(green_start=green_start,reason='unobserved_tail_head_crossing'));continue
        e=[by_vehicle[r[0]] for r in tail]
        if any(x['lower_sec']<green_start or x['upper_sec']>green_end for x in e):
            excluded.append(dict(green_start=green_start,reason='tail_not_confirmed_inside_same_green'));continue
        assert all(e[i]['lower_sec']<=e[i+1]['upper_sec'] for i in range(len(e)-1))
        first,last=e[0],e[-1]
        lower=last['lower_sec']-first['upper_sec'];upper=last['upper_sec']-first['lower_sec']
        midpoint=(lower+upper)/2
        if midpoint<=0 or upper<=0:
            excluded.append(dict(green_start=green_start,reason='unresolved_platoon_duration'));continue
        blocks.append(dict(green_start=green_start,green_end=green_end,snapshot_sec=before['sec'],
            initial_stopped_ids=[r[0] for r in q],fitted_vehicle_ids=[r[0] for r in tail],
            gap_count=len(tail)-1,first=first,last=last,duration_lower_sec=max(0.,lower),
            duration_upper_sec=upper,duration_midpoint_sec=midpoint))
    return blocks,excluded


def main():
    assert not (HERE/'calibration.json').exists()
    done=read('E:/VISSIM_analysis/20261010_sc15_source301_past/completion.json')
    assert done['status']=='complete_past_only_source_cache' and not done['validation_future_used']
    path=Path(done['cache']);assert sha(path)==done['cache_sha256']
    cache=json.loads(gzip.decompress(path.read_bytes()))
    assert cache['fit_head_end']==2100 and cache['followup_end']<2400
    loader=importlib.util.spec_from_file_location('source300',A/'source_service300/source_audit.py')
    src=importlib.util.module_from_spec(loader);loader.loader.exec_module(src)
    ldp_path=Path(cache['source']).parent/'sdmpc31_g_2400_hold_s29_15_001.ldp'
    ldp=read_ldp_frames({15:ldp_path},{15:list(range(1,9))},900,2396)
    tracks=defaultdict(list)
    for f in cache['frames']:
        for r in f['rows']:tracks[r[0]].append((f['sec'],r))
    old=read(ROOT/'diagnostics/native_sc15_service_calibration.json')
    inputs={}
    branches={'straight':{10538,1220016101},'right':{10528,336},'left':{10539,1220012402}}
    for inp,decision,source,head,sg in [('1086','1099',343,66.44431013017493,'5'),('1087','1100',341,61.06358954207084,'1')]:
        events,unknown=src.crossing_witnesses(cache['frames'],source,head)
        blocks,excluded=queued_platoon_blocks(cache['frames'],events,ldp['frames'],source,head,'15:'+sg)
        assert len(blocks)>=4
        gaps=sum(b['gap_count'] for b in blocks)
        durations={k:sum(b['duration_'+k+'_sec'] for b in blocks) for k in ('lower','upper','midpoint')}
        rates={k:gaps/durations[k]*3600 if durations[k]>0 else None for k in durations}
        route=[]
        for e in events:
            if e['direction']!='north' or e['lower_sec']<900 or e['upper_sec']>2100:continue
            track=[(t,r) for t,r in tracks[e['veh']] if t>=e['upper_sec']]
            witnessed=[(t,name,r[1]) for t,r in track for name,links in branches.items() if r[1] in links]
            label=min(witnessed)[1] if witnessed else 'unresolved'
            route.append(dict(veh=e['veh'],source_interval=[e['lower_sec'],e['upper_sec']],
                downstream=label,first_witness=None if not witnessed else min(witnessed),
                final_seen_sec=track[-1][0]))
        counts=Counter(r['downstream'] for r in route)
        assert len(route)>30
        shares={name:dict(lower=counts[name]/len(route),upper=(counts[name]+counts['unresolved'])/len(route)) for name in branches}
        inputs[inp]=dict(decision=decision,source_link=source,sg=sg,head_position_m=head,
            old_rate_veh_h=old['inputs'][inp]['selected_service_veh_h'],selected_service_veh_h=rates['midpoint'],
            measurement_lower_veh_h=rates['upper'],measurement_upper_veh_h=rates['lower'],
            gaps=gaps,durations=durations,platoon_blocks=blocks,excluded_platoons=excluded,
            route_counts=dict(counts),route_share_identification_bounds=shares,route_witnesses=route,
            source_crossing_unresolved=len(unknown))
    pins={str(p):sha(p) for p in (path,Path(__file__),HERE/'plan.json',A/'source_service300/source_audit.py',
        A/'source_service300/completion.json',A/'source_service300/routing_audit.json',ldp_path,
        ROOT/'diagnostics/native_sc15_service_review.md',ROOT/'diagnostics/native_sc15_service_calibration.json')}
    report=dict(status='complete_past_queue_platoon_and_source_turn_support',seed=29,training_head_window=[900,2100],
        route_followup_end=2395.1,validation_start=2400,inputs=inputs,source_pins=pins,
        selected_estimator='pooled_known_queued_platoon_after_first_three_gaps / pooled_midpoint_crossing_span *3600',
        limitations=['5s crossing brackets give broad timing bounds, not statistical confidence intervals.',
            'The complete stopped platoon at GREEN start supplies the queue witness; a stopped tail at every later snapshot is not required.',
            'No complete-GREEN mean or future-validation count is fitted as saturation.',
            'Incomplete/censored platoons are explicitly excluded, which can introduce selection bias.',
            'Unresolved downstream outcomes stay unresolved and are not normalized away.',
            'Only one source-service parameter set is prepared; no whole-network gain qualification.'])
    (HERE/'calibration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for inp,r in inputs.items():print(inp,r['selected_service_veh_h'],r['measurement_lower_veh_h'],r['measurement_upper_veh_h'],r['route_counts'],r['route_share_identification_bounds'])


if __name__=='__main__':main()
