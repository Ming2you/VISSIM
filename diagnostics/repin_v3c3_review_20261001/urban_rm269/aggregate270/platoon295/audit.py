"""Cached platoon/signal-overlap diagnostic, no future observations in plant."""
from collections import defaultdict,Counter
import gzip,hashlib,importlib.util,json,math,pickle,sys
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.validate_native_signal_record import read_ldp_frames
loader=importlib.util.spec_from_file_location('heads295',H/'sc12_source/audit.py')
head=importlib.util.module_from_spec(loader);loader.loader.exec_module(head)
head.LINKS={'SC6_S':1210018302}
PINS={}
def read(p):
    b=Path(p).read_bytes();PINS[str(Path(p).resolve())]=hashlib.sha256(b).hexdigest();return json.loads(b)
def pin(p):
    b=Path(p).read_bytes();PINS[str(Path(p).resolve())]=hashlib.sha256(b).hexdigest();return b
def runs(frames,key,start,end,state):
    a=None;out=[]
    for t in range(start,end+1):
        good=t<end and frames[t][key]==state
        if good and a is None:a=t
        if not good and a is not None:out.append([a,t]);a=None
    return out
def main():
    assert not (HERE/'assessment.json').exists()
    parent=read(A/'cohort294/completion.json')
    assert parent['status']=='complete_diagnostic_not_adopted'
    assert hashlib.sha256(pin(A/'cohort294/assessment.json')).hexdigest()==parent['assessment_sha256']
    cached=Path('E:/VISSIM_analysis/20261010_gatearrival291')
    done=read(cached/'completion.json')
    assert done['status']=='complete_thin_closed_corridor_cache'
    net=ET.fromstring(pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    positions={int(x.get('lane').split()[1]):float(x.get('pos')) for x in net.findall('./signalHeads/signalHead')
        if x.get('lane').split()[0]=='1210018302'}
    allrows={};native={};traces={}
    roots={'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold'),
           'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected')}
    for arm,root in roots.items():
        label='hold' if arm=='hold' else 'selected';stem=f'sdmpc31_g_2400_{label}_s29'
        folder=root/f'decisions_{stem}'
        ldppaths={s:root/'vissim_eval'/f'{stem}_{s}_001.ldp' for s in (6,10)}
        ldp=read_ldp_frames(ldppaths,{s:list(range(1,9)) for s in (6,10)},2395,2850)
        for p,d in ldp['pins'].items():PINS[p]=d['sha256']
        signal=ldp['frames']
        assert len(signal)==456
        blob=pin(done['arms'][arm]['cache']);assert hashlib.sha256(blob).hexdigest()==done['arms'][arm]['cache_sha256']
        cache=json.loads(gzip.decompress(blob));assert cache['sample_sec']==5
        frames=cache['frames'];allrows[arm]=frames
        records={};seen_terminal=set();entries=[];history=defaultdict(list);snapshots=[]
        for frame in frames:
            t=frame['sec'];now={r[0]:r for r in frame['rows']}
            for v,r in now.items():history[v].append((t,r))
            terminal=[r for r in now.values() if r[1]==1210018302 and r[3]<=positions[r[2]]]
            # Current FZP next-link/route is diagnostic target evidence, not forecast input.
            p1=[r for r in terminal if r[7] in ('10205','10207')]
            lane_p1=[r for r in terminal if r[2] in (1,2,3)]
            for r in terminal:
                if r[0] not in seen_terminal:
                    prior=records.get(r[0]);known_bracket=prior is not None and prior[1]!=1210018302
                    entries.append(dict(veh=r[0],time_upper=t,bracket_5s=known_bracket,
                        initial=t<2400,phase='p1' if r[7] in ('10205','10207') else 'p2',
                        incoming_link=prior[1] if prior else None))
                    seen_terminal.add(r[0])
            if t>=2400:
                sec=int(math.floor(t));green=signal[sec]['6:8']=='GREEN'
                near=[r for r in p1 if positions[r[2]]-r[3]<=30]
                snapshots.append(dict(sec=t,p1_inventory=len(p1),p1_lane_inventory=len(lane_p1),
                    p1_stopped=sum(r[4]<5 for r in p1),near_head=len(near),near_head_stopped=sum(r[4]<5 for r in near),
                    sc6_green=green,sc10_green=signal[sec]['10:8']=='GREEN'))
            records=now
        blocks=[]
        mer_all=[]
        for start in (2400,2550,2700):
            counts,ev=head.heads_and_entries(folder,start+150)
            events=[dict(lane=l,veh=v,sec=t) for l,v,t in ev['SC6_S'] if l in (1,2,3)]
            mer_all+=events
            n=sum(x['crossings'] for x in counts['SC6_S']['rows'] if x['lane'] in (1,2,3))
            ss=[s for s in snapshots if start<=s['sec']<start+150];assert len(ss)==30
            ent=[r for r in entries if start<=r['time_upper']<start+150 and r['phase']=='p1']
            # Nearby late observations only identify demand available around a
            # sampled instant; they do not reconstruct exact service capacity.
            green=[s for s in ss if s['sc6_green']]
            matched_sources=Counter();all_before=0;lags=[]
            for event in events:
                earlier=[(t,r) for t,r in history[event['veh']] if t<event['sec']]
                terminal_before=[t for t,r in earlier if r[1]==1210018302 and r[3]<=positions[r[2]]]
                if terminal_before:
                    all_before+=1;lags.append(event['sec']-min(terminal_before))
                src=[(t,r[1]) for t,r in earlier if r[1] in (1220015100,138)]
                if src:matched_sources[str(max(src)[1])]+=1
                else:matched_sources['no_retained_source_witness']+=1
            blocks.append(dict(start_sec=start,head_count=n,known_head_events=len(events),unresolved=n-len(events),
                native_green_sec=sum(signal[t]['6:8']=='GREEN' for t in range(start,start+150)),
                green_intervals=runs(signal,'6:8',start,start+150,'GREEN'),
                arrival_witness_p1_count=len(ent),arrival_adjacent5_witnesses=sum(r['bracket_5s'] for r in ent),
                mean_p1_inventory=sum(s['p1_inventory'] for s in ss)/30,
                mean_p1_stopped=sum(s['p1_stopped'] for s in ss)/30,
                green_snapshots=len(green),green_with_near_head_count=sum(s['near_head']>0 for s in green),
                green_with_near_head_stopped_count=sum(s['near_head_stopped']>0 for s in green),
                mean_p1_stock_during_green=sum(s['p1_inventory'] for s in green)/len(green) if green else None,
                mean_near_head_during_green=sum(s['near_head'] for s in green)/len(green) if green else None,
                head_events_with_terminal_before=all_before,
                source_witness_for_head_events=dict(matched_sources),
                terminal_first_seen_to_head=dict(n=len(lags),median=sorted(lags)[len(lags)//2],maximum=max(lags)) if lags else None))
        native[arm]=dict(blocks=blocks,snapshots=snapshots,arrival_witnesses=entries,mer_p1_events=mer_all)
        traces[arm]=history
    assert allrows['hold'][:2]==allrows['city'][:2],'Common cached2395.1/2400.1 prefix changed'
    PINS.update(head.PINS)
    # Joint time table over SC6's short internal-red window.
    table=[]
    for start in range(2550,2700,10):
        row=dict(start_sec=start)
        for arm,d in native.items():
            snaps=[s for s in d['snapshots'] if start<=s['sec']<start+10];assert len(snaps)==2
            row[arm]=dict(green_samples=sum(s['sc6_green'] for s in snaps),
                stock_mean=sum(s['p1_inventory'] for s in snaps)/2,
                stopped_mean=sum(s['p1_stopped'] for s in snaps)/2,
                near_mean=sum(s['near_head'] for s in snaps)/2,
                head_known=sum(start<=r['sec']<start+10 for r in d['mer_p1_events']))
        table.append(row)
    model={}
    for arm in ('hold','city'):
        response=json.loads(gzip.decompress(pin(A/'sourcepath292/forecast2400_r3'/f'{arm}.response.json.gz')))
        rows=[]
        for start in (2400,2550,2700):
            rr=[r for r in response['transfers'] if start<=r['start_sec']<start+150 and r['source']!=r['target']]
            incoming=Counter()
            for r in rr:
                if r['target']=='storage:SC12_to_SC6':incoming[r['source'] or r['route_key']]+=r['vehicles']
            rows.append(dict(start_sec=start,accepted_approach_sources=dict(incoming)))
        model[arm]=rows
    pin(H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md')
    PINS[str(Path(__file__).resolve())]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(status='complete_cached_signal_platoon_audit',previous_goal_turn='progress',
        native=native,critical_window_10s=table,model=model,
        source_pins=PINS,new_native=0,new_predictions=0,new_fzp_scans=0,coefficients_fitted=0,production_changes=0,
        limitations=['5s terminal appearances and source matches are sampled witnesses, not complete arrival counts.',
          'Current next-link observed in future frames is diagnostic evidence only; no forecast consumes it.',
          'Near-head stock/stopped counts do not uniquely establish lane service or future gap availability.',
          'Native LDP1s sampling verifies timing, not subsecond LSA.',
          'Signal timing and supply both respond to the city action; this audit is not an isolated causal replay.'],
        goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('BLOCKS',json.dumps({a:d['blocks'] for a,d in native.items()},ensure_ascii=False))
    print('MODEL',json.dumps(model,ensure_ascii=False))
    print('10S',json.dumps(table,ensure_ascii=False))
if __name__=='__main__':main()
