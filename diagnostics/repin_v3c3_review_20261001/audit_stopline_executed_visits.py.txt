"""Finite read of two closed 64cf runs, retaining only SC1001 approach trajectories.

No model fitting or native simulation. Crossing times remain sampling brackets.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'stopline'
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
NETWORK = I / 'selected/network/native_seed29.inpx'
SOURCES = {
    's47_rm_hold': Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/vissim_eval/sdmpc31_g_2700_hold_s47_001.fzp'),
    's29_nc': Path('D:/VISSIM_runs/20260924_bottleneck90_full_s29/none/run/vissim_eval/mtfc_s29_none_001.fzp'),
}
LINKS = {10491,10481,129,127,32,10778,10777,10490,10482,10118,10368,10695,30,39,38}


def load(path):
    data=path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def save(path, obj):
    assert not path.exists(), path
    data=json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
    path.write_bytes(gzip.compress(data,mtime=0) if path.suffix=='.gz' else data)


def extract(case):
    OUT.mkdir(exist_ok=True)
    source=SOURCES[case]; target=OUT/(case+'_frames.json.gz')
    assert not target.exists(), target
    before=source.stat(); h=hashlib.sha256(); frames={}; rows=0; kept=0
    with source.open('rb') as f:
        header=None
        for raw in f:
            h.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                header=raw.decode('ascii').strip().split(':',1)[1].split(';')
                ix={k:header.index(k) for k in ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','ROUTDECNO','ROUTENO','NEXTLINK\\NO')}
                continue
            if header is None or not raw[:1].isdigit(): continue
            v=raw.strip().split(b';'); rows+=1
            link=int(v[ix['LANE\\LINK\\NO']])
            if link not in LINKS: continue
            sec=float(v[ix['SIMSEC']]); ident=int(v[ix['NO']])
            fields=[link,int(v[ix['LANE\\INDEX']]),float(v[ix['POS']]),float(v[ix['SPEED']]),
                    v[ix['ROUTDECNO']].decode(),v[ix['ROUTENO']].decode(),v[ix['NEXTLINK\\NO']].decode()]
            frame=frames.setdefault(str(sec),{})
            assert str(ident) not in frame,(sec,ident)
            frame[str(ident)]=fields; kept+=1
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    save(target,dict(source=str(source),sha256=h.hexdigest(),bytes=after.st_size,rows=rows,kept_rows=kept,
         fields=['link','lane','pos_m','speed_kmh','route_decision','route','next_link'],frames=frames))
    print(json.dumps(dict(case=case,rows=rows,kept=kept,frames=len(frames),source_sha256=h.hexdigest())),flush=True)


def signal(sec, lane):
    phase=(sec-75.)%150.
    if lane in (1,2): return 'G' if phase<45 else 'A' if phase<48 else 'R'
    return 'G' if 48<=phase<72 else 'A' if 72<=phase<75 else 'R'


def bracket_signal(lo,hi,lane):
    states={signal(lo+(hi-lo)*k/100,lane) for k in range(101)}
    return next(iter(states)) if len(states)==1 else 'uncertain'


def quantiles(values):
    if not values:return dict(n=0)
    v=sorted(values)
    return dict(n=len(v),min=v[0],median=statistics.median(v),mean=statistics.mean(v),p95=v[math.ceil(.95*len(v))-1],max=v[-1])


def analyze(case):
    path=OUT/(case+'_frames.json.gz');data=load(path)
    net=ET.parse(NETWORK).getroot()
    assert hashlib.sha256(NETWORK.read_bytes()).hexdigest()=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    manifest=load(NETWORK.parent/'sig_manifest.json')
    sig=next(x for x in manifest['files'] if any(c['sc']=='1001' for c in x['controllers']))
    assert hashlib.sha256((NETWORK.parent/sig['name']).read_bytes()).hexdigest()==sig['sha256']
    prog=ET.parse(NETWORK.parent/sig['name']).getroot().find("./progs/prog[@id='1']")
    assert prog.get('cycletime')=='150000' and prog.get('offset')=='75000'
    assert [(x.get('display'),x.get('begin')) for x in prog.findall("./sgs/sg[@sg_id='2']/cmds/cmd")]==[('3','0'),('1','48000')]
    assert [(x.get('display'),x.get('begin')) for x in prog.findall("./sgs/sg[@sg_id='5']/cmds/cmd")]==[('3','48000'),('1','75000')]
    for sg in ('2','5'):
        assert prog.find(f"./sgs/sg[@sg_id='{sg}']/fixedstates/fixedstate").attrib=={'display':'4','duration':'3000'}
    heads={int(x.get('lane').split()[1]):float(x.get('pos')) for x in net.findall('./signalHeads/signalHead') if x.get('lane').split()[0]=='127'}
    assert set(heads)=={1,2,3}
    outgoing={10118:{30},10368:{39},10695:{38}}
    destinations=set(outgoing)|set.union(*outgoing.values())
    prev={};last=None;origins={};port_exits={};events=[];snapshots=[];seen_heads=set();seen_port_exits=set()
    for secstr,frame in sorted(data['frames'].items(),key=lambda x:float(x[0])):
        sec=float(secstr)
        assert last is None or abs(sec-last-5.)<1e-6,(last,sec)
        stocks=collections.Counter();stopped=collections.Counter();near_queue=collections.Counter()
        for ident,row in frame.items():
            link,lane,pos,speed,*_=row;stocks[str(link)]+=1
            if speed<=5:stopped[str(link)]+=1
            if link==127 and speed<=5 and 0<=heads[lane]-pos<=120:near_queue[str(lane)]+=1
            if link in (10491,10481):origins[ident]=str(link)
            elif link==32 and ident not in origins:origins[ident]='city32'
            old=prev.get(ident)
            if old is None:continue
            ol,ola,op,*_=old
            if ol in (10491,10481) and link!=ol and ident not in seen_port_exits:
                valid=({129,10777,127,10490,119} if ol==10491 else {127,10118,10368,10695,30,39,38})
                assert link in valid,(ident,ol,link)
                port_exits[ident]=(last,sec,str(ol));seen_port_exits.add(ident)
            if ol!=127 or ident in seen_heads:continue
            same=link==127 and op<=heads[ola]<pos
            departed=link in destinations and op<=heads[ola]
            if not (same or departed):continue
            if link==127 and lane!=ola:continue
            seen_heads.add(ident)
            event=dict(vehicle=ident,lower=last,upper=sec,lane=ola,source=origins.get(ident,'unseen'),
                       state=bracket_signal(last,sec,ola),evidence='same_link' if same else 'downstream_link',
                       observed_nextlink_before=old[6])
            if ident in port_exits:
                lo,hi,source=port_exits[ident]
                event['port_to_head_delay_sec']=[max(0.,last-hi),sec-lo]
                event['port_exit_bracket']=[lo,hi]
                event['port_exit_signal_state']=bracket_signal(lo,hi,ola)
                event['source']=source
            events.append(event)
        snapshots.append(dict(sec=sec,stocks=dict(stocks),stopped=dict(stopped),near_queue=dict(near_queue)))
        prev=frame;last=sec
    # Complete signal cycles only; startup losses remain in total/green estimates.
    end=float(next(reversed(sorted(data['frames'],key=float))))
    cycles=[]
    for cycle_start in range(975,int(end)-150+1,150):
        row=dict(start=cycle_start,end=cycle_start+150,lanes={})
        for lane in (1,2,3):
            ev=[e for e in events if e['lane']==lane and cycle_start<e['upper']<=cycle_start+150]
            samples=[s for s in snapshots if cycle_start<=s['sec']<cycle_start+150 and signal(s['sec'],lane)=='G']
            assert samples
            # Sustained queue over the sampled green is evidence of saturation, not exact sub-step truth.
            queued=all(s['near_queue'].get(str(lane),0)>0 for s in samples)
            green=45. if lane<3 else 24.
            row['lanes'][str(lane)]=dict(crossings=len(ev),green_sec=green,sampled_sustained_queue=queued,
                queue_samples=len(samples),crossings_by_signal=dict(collections.Counter(e['state'] for e in ev)),
                cycle_discharge_per_green_hour=len(ev)*3600/green)
        cycles.append(row)
    qualified=[e for e in events if e['lower']>=900]
    source_report={}
    for source in ('10491','10481','city32','unseen'):
        ev=[e for e in qualified if e['source']==source]
        delay=[e for e in ev if 'port_to_head_delay_sec' in e]
        source_report[source]=dict(head_crossings=len(ev),known_port_head_pairs=len(delay),
            delay_lower_sec=quantiles([e['port_to_head_delay_sec'][0] for e in delay]),
            delay_upper_sec=quantiles([e['port_to_head_delay_sec'][1] for e in delay]),
            port_exit_signal_states=dict(collections.Counter(e['port_exit_signal_state'] for e in delay)))
    service={str(lane):quantiles([c['lanes'][str(lane)]['cycle_discharge_per_green_hour'] for c in cycles
             if c['lanes'][str(lane)]['sampled_sustained_queue']]) for lane in (1,2,3)}
    result=dict(case=case,source=data['source'],source_sha256=data['sha256'],frame_cache_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        network_sha256=manifest['network']['sha256'],signal_sha256=sig['sha256'],last_sec=end,
        source_report=source_report,saturated_service_per_lane=service,
        limitations=['5 s brackets, not exact transition times; signal phase from pinned native program; integer detector checks reported separately.',
                    'Port-head pairs require both connector and downstream crossing observed; fast connector skips excluded.',
                    'Saturated service uses total cycle crossings divided by green: includes startup and amber passage, not pure saturation flow.',
                    'Only held native-city signal policies; RM-only47 and NC29 are different experiments, not paired policies.'],
        events=events,cycles=cycles,snapshots=snapshots)
    save(OUT/(case+'_audit.json.gz'),result)
    save(OUT/(case+'_summary.json'),{k:v for k,v in result.items() if k not in ('events','cycles','snapshots')})
    print(json.dumps({k:result[k] for k in ('case','source_report','saturated_service_per_lane')},ensure_ascii=False),flush=True)


def visits(case):
    """Track approach visits, including a vehicle that returns through the network.

    Uses only the saved local frames. The first-pass audit's global vehicle
    de-duplication intentionally remains archived and is not reused here.
    """
    path=OUT/(case+'_frames.json.gz'); data=load(path)
    heads={1:621.666240433568,2:621.5682806829368,3:621.461546643362}
    destination={10118:'E',30:'E',10368:'S',39:'S',10695:'N',38:'N'}
    active={};sequence=collections.Counter();events=[];previous={};last=None
    for text,frame in sorted(data['frames'].items(),key=lambda x:float(x[0])):
        sec=float(text)
        for ident,row in frame.items():
            link,lane,pos,speed,decision,route,nextlink=row
            old=previous.get(ident);visit=active.get(ident)
            fresh=(link in (10491,10481,32) and (old is None or old[0]!=link))
            # Re-entering the approach after a completed passage starts a new
            # visit even if a short connector was missed by the 5-second sample.
            fresh=fresh or (link==127 and (visit is None or visit.get('head') is not None)
                           and (old is None or old[0]!=127))
            if fresh or (visit is None and link in (129,10777,127)):
                sequence[ident]+=1
                source=str(link) if link in (10491,10481) else 'city32' if link==32 else 'unseen'
                visit=dict(vehicle=ident,visit=sequence[ident],source=source,first_sec=sec,
                           entry_route=[decision,route],head=None)
                active[ident]=visit
            if visit is None:continue
            if old is not None and old[0] in (10491,10481) and link!=old[0]:
                visit['port_exit']=[last,sec]
            if visit.get('head') is None and old is not None and old[0]==127:
                # An actual cross-link passage or an across-all-heads position
                # bracket proves the total even if lane changed inside the step.
                crossed=(link in destination and old[2]<=heads[old[1]]) or (
                    link==127 and old[2]<=min(heads.values()) and pos>max(heads.values()))
                if crossed:
                    event=dict(vehicle=ident,visit=visit['visit'],source=visit['source'],
                        entry_route=visit['entry_route'],lower=last,upper=sec,
                        previous_lane=old[1],lane_changed_in_bracket=link==127 and lane!=old[1],
                        previous_route=old[4:6],destination=None)
                    if 'port_exit' in visit:
                        lo,hi=visit['port_exit']
                        event.update(port_exit_bracket=[lo,hi],port_to_head_delay_sec=[max(0.,last-hi),sec-lo],
                            both_red_at_port_exit=all(bracket_signal(lo,hi,g)=='R' for g in (1,3)))
                    visit['head']=event;events.append(event)
            event=visit.get('head')
            if event is not None and event['destination'] is None and link in destination:
                event['destination']=destination[link]
                event['destination_sec']=sec
                event['destination_link']=link
        previous=frame;last=sec
    summaries={}
    for source in ('10491','10481','city32','unseen'):
        e=[x for x in events if x['source']==source and x['lower']>=900]
        pairs=[x for x in e if 'port_exit_bracket' in x]
        summaries[source]=dict(head_visits=len(e),distinct_vehicles=len({x['vehicle'] for x in e}),
            known_pairs=len(pairs),both_red_pairs=sum(x['both_red_at_port_exit'] for x in pairs),
            median_delay_lower=quantiles([x['port_to_head_delay_sec'][0] for x in pairs]),
            median_delay_upper=quantiles([x['port_to_head_delay_sec'][1] for x in pairs]),
            by_entry_route={key:dict(collections.Counter(x['destination'] or 'unresolved' for x in e
                                  if ':'.join(x['entry_route'])==key)) for key in sorted({':'.join(x['entry_route']) for x in e})})
    check=[]
    if case=='s47_rm_hold':
        for p in sorted((I/'closedloop_recorded2700_init_upstream_bd39205/derived_history').glob('derived_*.json')):
            d=load(p);end=d['sim_sec'];start=end-150
            if end<1050:continue
            native=sum(h['crossings'] for h in d['head_window']['heads'] if h['link']=='127')
            low=sum(x['lower']>=start and x['upper']<=end for x in events)
            high=sum(x['upper']>start and x['lower']<end for x in events)
            check.append(dict(start=start,end=end,native=native,guaranteed=low,possible=high,
                              native_in_bracket=low<=native<=high))
    result=dict(case=case,frame_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        scope='Observed visits; completed native trajectories used for diagnosis, not future controller input.',
        summaries=summaries,events=events,head_crosscheck=check,
        caveats=['5-second brackets; fast unseen connectors and end-censored visits excluded from delay distribution.',
                 'Destination priors differ by route family; totals do not identify a calibrated capacity.',
                 'A route-free entry is not equivalent to a specified new static-route choice.',
                 'No counters from the original single-passage audit are silently overwritten.'])
    save(OUT/(case+'_visits.json.gz'),result)
    print(json.dumps(dict(case=case,events=len(events),repeated_vehicles=len(events)-len({x['vehicle'] for x in events}),
        summary=summaries,head_windows_outside_bracket=sum(not x['native_in_bracket'] for x in check))),flush=True)


def validate(case):
    """Check cached event evidence; never promote sampled counts to exact service."""
    path=OUT/(case+'_audit.json.gz'); audit=load(path)
    network_paths={
        's47_rm_hold':Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/network/sdmpc31_g_2700_hold_s47.inpx'),
        's29_nc':Path('D:/VISSIM_runs/20260924_bottleneck90_full_s29/prepared_none/network/mtfc_s29_none.inpx'),
    }
    network=network_paths[case]
    network_sha=hashlib.sha256(network.read_bytes()).hexdigest()
    assert network_sha==audit['network_sha256']
    sig=load(NETWORK.parent/'sig_manifest.json')
    sig=next(x for x in sig['files'] if any(c['sc']=='1001' for c in x['controllers']))
    assert hashlib.sha256((network.parent/sig['name']).read_bytes()).hexdigest()==audit['signal_sha256']
    events=[e for e in audit['events'] if e['lower']>=900]
    both_red={}
    for source in ('10491','10481'):
        pairs=[e for e in events if e['source']==source and 'port_exit_bracket' in e]
        robust=[e for e in pairs if all(bracket_signal(*e['port_exit_bracket'],lane)=='R' for lane in (1,3))]
        assert robust
        both_red[source]=dict(pairs=len(pairs),both_signal_groups_red=len(robust),
                             fraction=len(robust)/len(pairs),vehicle_ids=[e['vehicle'] for e in robust])
    result=dict(case=case,audit_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        executed_analysis_sha256=hashlib.sha256((OUT.parent/'audit_stopline_executed_extract_analyze.py.txt').read_bytes()).hexdigest(),
        network_path=str(network),network_sha256=network_sha,signal_sha256=audit['signal_sha256'],
        both_signal_groups_red_at_port_exit=both_red,
        saturation_service_adoption=False,
        qualifications=['Positive observed port/head pairs prove separated physical boundaries; not a complete crossing census.',
                        'Both-red subset does not depend on uncertain lane at the later head crossing.',
                        'Phase uses the unchanged pinned native SC1001 program; head lane can change inside a 5 s bracket.'])
    if case=='s47_rm_hold':
        comparisons=[]
        for file in sorted((I/'closedloop_recorded2700_init_upstream_bd39205/derived_history').glob('derived_*.json')):
            d=load(file);end=d['sim_sec'];start=end-150
            if end<1050:continue
            native={str(h['lane']):h['crossings'] for h in d['head_window']['heads'] if h['link']=='127'}
            native_total=sum(native.values())
            lower=collections.Counter(str(e['lane']) for e in audit['events'] if e['lower']>=start and e['upper']<=end)
            upper=collections.Counter(str(e['lane']) for e in audit['events'] if e['upper']>start and e['lower']<end)
            endpoint=collections.Counter(str(e['lane']) for e in audit['events'] if start<e['upper']<=end)
            comparisons.append(dict(start_sec=start,end_sec=end,native_by_lane=native,
                fzp_endpoint_assignment_by_lane=dict(endpoint),fzp_guaranteed_by_lane=dict(lower),fzp_possible_by_lane=dict(upper),
                native_total=native_total,fzp_endpoint_total=sum(endpoint.values()),
                fzp_guaranteed_total=sum(lower.values()),fzp_possible_total=sum(upper.values()),
                native_within_sample_brackets=sum(lower.values())<=native_total<=sum(upper.values()),
                derived_path=str(file.relative_to(ROOT)),derived_sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        result['head_crosscheck']=dict(status='FAIL_EXACT_CENSUS',windows=comparisons,
            native_total=sum(x['native_total'] for x in comparisons),
            fzp_endpoint_total=sum(x['fzp_endpoint_total'] for x in comparisons),
            native_outside_sample_brackets=sum(not x['native_within_sample_brackets'] for x in comparisons),
            interpretation='Some lane changes/skips are omitted; time brackets alone do not close all differences. Do not calibrate service from this sampled counter.')
        model_path=I/'expanded036_9000_20260930/loss_onset2250/source_sc101/residual_timing/native_response_trace/execution_intervals.json'
        native_path=I/'closedloop_recorded2700_native_selected_res47v2/analysis/boundary_response.json'
        model=load(model_path)['held_actual'];native=load(native_path)['native']['hold'];balances=[]
        for m,n in zip(model,native,strict=True):
            assert (m['start_sec'],m['end_sec'])==(n['start_sec'],n['end_sec'])
            for off in ('10491','10481'):
                mn=m['offramps'][off];nn=n['offramps'][off]
                model_res=mn['initial_stock']+mn['arrival']-mn['drain']-mn['final_stock']
                native_res=nn['initial']+nn['entry']-nn['drain']-nn['removals']-nn['final']
                assert abs(model_res)<1e-7 and native_res==0
                balances.append(dict(start_sec=m['start_sec'],end_sec=m['end_sec'],offramp=off,
                    model=mn,native=nn,model_conservation_residual=model_res,native_conservation_residual=native_res))
        result['saved_port_balance_comparison']=dict(windows=balances,
            model_path=str(model_path.relative_to(ROOT)),model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
            native_path=str(native_path.relative_to(ROOT)),native_sha256=hashlib.sha256(native_path.read_bytes()).hexdigest(),
            limitation='Native drain is entry detector minus stock change/removals; not an independent port-exit detector. No new forecast.')
    else:
        result['head_crosscheck']=dict(status='NOT_AVAILABLE',interpretation='No matching saved head-window history used for seed29; sampled counter is not exact service evidence.')
    save(OUT/(case+'_validation.json'),result)
    print(json.dumps(dict(case=case,head_crosscheck=result['head_crosscheck']['status'],
        red_pairs={k:(v['both_signal_groups_red'],v['pairs']) for k,v in both_red.items()})),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['extract','analyze','validate','visits']);parser.add_argument('case',choices=SOURCES)
    args=parser.parse_args()
    {'extract':extract,'analyze':analyze,'validate':validate,'visits':visits}[args.mode](args.case)
