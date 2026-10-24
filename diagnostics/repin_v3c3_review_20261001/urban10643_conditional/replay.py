"""Actual local arrival cohorts, native signals, unchanged finite lane model.

Retrospective component diagnosis only. All unmet boundary demand is retained;
none of these future observations is supplied to an autonomous plant forecast.
"""
import ast
import copy
import gzip
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.physical_urban_transport import UrbanTransport, FIFO, observe, geometry, unassigned_continuation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVIEW=HERE.parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
LOCAL={126,10641,71}
START,END=2700.1,3145.1
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def raw_frame(rows,t):
    # Existing FZP cache columns are declared in its extraction receipt.
    return dict(time_s=t,vehicles=[[r[1],r[2],r[3],r[4],r[5],r[13],r[6],r[7],r[8],
        r[9],r[10],r[11],r[12],None,None] for r in rows])


class NativeProgram:
    def __init__(self,windows):
        self.green={sg:[tuple(iv) for w in windows for iv in w['clocks'][f'1004-{sg}']['green']]
                    for sg in (2,5)}

    def green_at(self,t,sg):return any(a<=t<b for a,b in self.green[sg])

    def state_at(self,t,sg,*,controller_offset_sec):
        assert controller_offset_sec==0
        # Same start-of-one-second service convention as CandidateSignalProgram.
        return 'GREEN' if self.green_at(t-1,sg) else 'RED'


def run(current,network,protocol,events,program,exit_room,timing,receiver,removals):
    model=UrbanTransport(copy.deepcopy(current),network,program,0,
        protocol['urban_free_speed_m_s'],6.,protocol['wave_m_s'],
        lateral_access=protocol['lateral_access'],continuation=protocol['unrouted_continuation'])
    model.prefer_more_receiving_space=protocol['prefer_more_receiving_space']
    model.defer_mandatory_while_forward_open=protocol['defer_mandatory_while_forward_open']
    model.defer_destinations=protocol['defer_destinations']
    model.compact_equal_behavior=True
    pending={};targets={};scheduled=defaultdict(list)
    for e in events:
        due=e['bracket'][0 if timing=='early' else 1]
        scheduled[round(due,1)].append(e)
    admitted=Counter();heads=Counter();snapshots=[];max_residual=0.;rejected=Counter()
    seen=[];removed=Counter();removal_log=[]
    initial=sum(model.counts().values())

    def enqueue(t):
        for e in sorted(scheduled.get(round(t,1),[]),key=lambda e:e['order']):
            name=e['source']+':'+str(e['entry_lane'])
            target=((126,e['entry_lane'],len(model.edges[126])-2) if e['source']=='off10643'
                    else (126,e['entry_lane'],0) if e['source']=='upstream70'
                    else (71,e['entry_lane'],0))
            assert name not in targets or targets[name]==target
            targets[name]=target
            label=(e['destination'],e['visit_label'])
            if e['unassigned_continuation']:model.unrouted_labels.add(label)
            pending.setdefault(name,FIFO()).append(label,1.)
            seen.append(e)

    started=time.perf_counter()
    for step in range(int(round(END-START))):
        t=round(START+step,1);assert abs(model.time-t)<1e-6
        enqueue(t)
        offered={name:q.stock for name,q in pending.items()}
        receipts=model.step({name:(targets[name],q) for name,q in pending.items()},
            exit_receiving=None if receiver=='unrestricted_exit' else exit_room[int(t)])
        for name,packets in receipts.items():admitted[name]+=math.fsum(n for label,n in packets)
        for name,n in offered.items():rejected[name]+=n-math.fsum(v for _,v in receipts.get(name,()))
        for source,target,packets in model.last_transfers:
            if source[0]==71 and source[2]==3 and target[0]=='exit':
                heads[str(source[1])]+=math.fsum(n for _,n in packets)
        for event in removals:
            if not t < event['time_sec'] <= model.time:continue
            # Diagnostic-only abnormal sink. Keep it OUT of normal departure,
            # head discharge and termination-event reports. No production law
            # uses this future removal schedule.
            amount=0.
            for queue in model.cells.values():
                for label,n in list(queue.counts().items()):
                    if label[1]!=event['vehicle_id']:continue
                    queue.take_label(label,n)
                    model.departed[label]+=n
                    removed[label]+=n;amount+=n
            removal_log.append(dict(vehicle=event['vehicle_id'],native_time_s=event['time_sec'],
                model_time_s=model.time,removed_remaining_mass=amount))
            model.check()
        residual=initial+len(seen)-sum(model.counts().values())-sum(model.departed.values())-sum(q.stock for q in pending.values())
        max_residual=max(max_residual,abs(residual))
        if step+1 in (150,300,445):
            snapshots.append(dict(time_s=round(model.time,1),local_n=sum(model.counts().values()),
                normal_departures=sum(model.departed.values())-sum(removed.values()),
                abnormal_removed=sum(removed.values()),source_backlog={k:q.stock for k,q in pending.items()}))
    enqueue(END)  # Late bracket endpoint may arrive at the final observation itself.
    assert len(seen)==len(events)
    balance=initial+len(events)-sum(model.counts().values())-sum(model.departed.values())-sum(q.stock for q in pending.values())
    assert abs(balance)<1e-7 and max_residual<1e-7
    lane_stocks=Counter()
    for (road,lane,cell),queue in model.cells.items():lane_stocks[f'{road}:{lane}']+=queue.stock
    label_wait=Counter()
    for q in model.cells.values():label_wait.update(q.counts())
    return dict(timing=timing,receiver=receiver,initial_n=initial,requested=len(events),
        admitted_by_source=dict(admitted),backlog_by_source={k:q.stock for k,q in pending.items()},
        final_n=sum(model.counts().values()),final_lane_stocks=dict(lane_stocks),
        departed_by_destination={str(d):sum(n-removed[(target,vid)] for (target,vid),n in model.departed.items() if target==d)
                                 for d in {label[0] for label in model.departed}},
        departures=sum(model.departed.values())-sum(removed.values()),abnormal_removed=sum(removed.values()),
        removal_log=removal_log,head_connector_discharge=dict(heads),
        retained_labels=[dict(label=list(k),vehicles=v) for k,v in label_wait.items()],
        local_residence_veh_h=model.vehicle_seconds/3600.,snapshots=snapshots,
        balance_residual=balance,max_step_balance_residual=max_residual,wall_sec=time.perf_counter()-started)


def main():
    assert not (HERE/'assessment.json').exists()
    prior=read(REVIEW/'junction10643/completion.json')
    for p,h in prior['production7_unchanged'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    cache=read(REVIEW/'lane10643_native/rows.json.gz')
    assert cache['columns']==['time','vehicle','link','lane','position','speed','decision','route',
        'route_type','next_link','dest_lane','lane_change','interaction','length']
    assert cache['epochs'][-1]==END
    frames=defaultdict(dict)
    for r in cache['rows']:frames[r[0]][r[1]]=r
    routes,exits=geometry(network)
    current=observe(raw_frame([r for r in frames[START].values() if r[2] in LOCAL],START),routes,exits)
    clocks=read(REVIEW/'local10643_receiver/head_audit.json')['cases']['47hold']
    program=NativeProgram(clocks)
    last={};visits=Counter();events=[];transitions=[]
    for t,rows in sorted(frames.items()):
        for vid,r in rows.items():
            old=last.get(vid)
            if t>START and r[2] in LOCAL and (old is None or old[2] not in LOCAL):
                assert old is not None and abs(t-old[0]-5)<1e-6,'Unknown local entry boundary'
                assert old[2] in (70,10776,10643,10640,10700),old
                obs=observe(raw_frame([r],t),routes,exits)['vehicles'][0]
                source=('off10643' if old[2]==10643 else 'upstream70' if old[2] in (70,10776)
                        else 'city10640' if old[2]==10640 else 'side10700')
                lane=old[3] if source=='off10643' else old[3]+3 if source=='city10640' else r[3]
                assert (lane in (1,2) if source in ('off10643','upstream70') else lane in (1,4,5))
                visits[vid]+=1
                # Keep repeated visits distinct from initial or earlier local residence.
                label=f'{vid}:visit{visits[vid]}'
                events.append(dict(vehicle=vid,visit_label=label,source=source,entry_lane=lane,
                    bracket=[old[0],t],destination=obs['connector'],unassigned_continuation=unassigned_continuation(obs,routes),
                    order=[-old[4],vid],first_local_link=r[2],first_local_lane=r[3],first_local_position=r[4],
                    last_outside_link=old[2],last_outside_position=old[4],observed_route=r[6:9]))
            if t>START and old is not None and old[2] in LOCAL and r[2] not in LOCAL:
                transitions.append(dict(vehicle=vid,bracket=[old[0],t],target=r[2]))
            last[vid]=r
    assert len(events)==204
    initial_ids={v['vehicle'] for v in current['vehicles']}
    final_rows=[r for r in frames[END].values() if r[2] in LOCAL]
    # No repeat visit in this bounded source cache; explicitly fail instead of global de-dup.
    assert max(visits.values())==1 and not (initial_ids & set(visits))
    native_final=Counter(f'{r[2]}:{r[3]}' for r in final_rows)
    folder=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
    detectors,digest=oc.read_detector_csv(I/'selected/obs150/obs150_detectors_v2.csv')
    heads={d.dcp_no:d for d in detectors if d.role=='head' and d.link==71}
    assert len(heads)==5
    head_events=[];removed=[];seen_mer=set()
    for t in (2850,3000,3150):
        raw=read(folder/f'state_{t:06d}.json');bundle=oc.load_bundle(raw)
        removed.extend(e for e in oc.window_removals(bundle.err_rows,START,END) if e['link'] in LOCAL)
        for e in bundle.mer_rows:
            if e.dcp not in heads or e.t_entry is None or not START<e.t_entry<=END:continue
            key=(e.dcp,e.ordinal)
            if key in seen_mer:continue
            seen_mer.add(key);lane=heads[e.dcp].lane;sg=2 if lane<=3 else 5
            head_events.append(dict(vehicle=e.veh,time=e.t_entry,lane=lane,green=program.green_at(e.t_entry,sg)))
    # ERR writing can lag its event window. Read all completed bundles first,
    # then classify by event time, retaining its source chunk provenance.
    assert len({e['raw_line_sha256'] for e in removed})==len(removed)
    native_green=Counter(str(e['lane']) for e in head_events if e['green'])
    native_all=Counter(str(e['lane']) for e in head_events)
    missing=(initial_ids|set(visits))-{r['vehicle'] for r in transitions}-{r[1] for r in final_rows}
    unresolved=missing-{e['vehicle'] for e in head_events}-{e['vehicle_id'] for e in removed}
    trace=read(I/'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    exit_room=defaultdict(dict)
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind']=='lane_urban_exit_receiving':exit_room[int(r['start_sec'])][int(r['resource'])]=r['available_veh']
    assert all(set(exit_room[t])==set(exits) for t in range(2700,3145))
    specification=dict(status='prepared_eight_conditional_replays',initial_epoch_s=START,end_epoch_s=END,
        future_native_input=True,autonomous_forecast=False,max_component_replays=8,
        variations=['early vs late5s entry bracket','frozen existing exit budgets vs unrestricted exits',
                    'no deletion vs2 recorded removals, abnormal mass accounted separately'],
        amended_before_any_replay='Preflight found2 delayed ERR removals. Never count these as normal discharge or calibrate them into a physical service law.',
        controls='same verified native signal windows',geometry_and_parameters='unchanged retained10638',
        source_rows=len(cache['rows']),arrivals=len(events),new_fzp_scans=0,new_native=0,
        limitations=['Inlet lane can change between5s snapshots; use last off/city source lane, first126 lane for upstream70.',
        'Order within simultaneous5s brackets uses upstream position thenID; it is not a complete microscopic chronology.',
        'Actual off drainage is boundary demand; any rejected portion stays in an explicit backlog.',
        'Unrestricted exit removes downstream constraints for diagnosis only; not feasible full-network control.',
        'Stored control/no-control gains cannot be inferred from this single-policy conditional replay.'])
    (HERE/'protocol.json').write_text(json.dumps(specification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    outcomes={}
    for timing in ('early','late'):
        for receiver in ('frozen_exit','unrestricted_exit'):
            for removal_mode in ('conserved','native_removal_diagnosis'):
                key=timing+'_'+receiver+'_'+removal_mode
                outcomes[key]=run(current,network,protocol,events,program,exit_room,timing,receiver,
                                  [] if removal_mode=='conserved' else removed)
                r=outcomes[key]
                (HERE/(key+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(key,'departed',r['departures'],'removed',r['abnormal_removed'],'stock',r['final_n'],
                      'backlog',r['backlog_by_source'],'heads',r['head_connector_discharge'],flush=True)
    for p,h in prior['production7_unchanged'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP');assert hashlib.sha256(stop.read_bytes()).hexdigest()==prior['stop_sha256']
    out=dict(status='completed_retrospective_conditional_component_diagnosis',cases=outcomes,events=events,
        native=dict(initial_n=len(current['vehicles']),arrivals=len(events),final_n=len(final_rows),
            implied_normal_departures=len(current['vehicles'])+len(events)-len(final_rows)-len(removed),local_removals=removed,
            final_lane_stocks=dict(native_final),known_exit_pairs=transitions,missing_exit_samples=sorted(missing),
            missing_exit_samples_not_seen_at_heads=sorted(unresolved),head_green=dict(native_green),head_all=dict(native_all),head_events=head_events),
        production_unchanged=prior['production7_unchanged'],stop_sha256=prior['stop_sha256'],source_pins=PINS,
        new_fits=0,new_full_forecasts=0,new_fzp_scans=0,new_native=0,goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NATIVE',out['native']['implied_normal_departures'],dict(native_final),'GREEN',dict(native_green),'UNRESOLVED',sorted(unresolved))


if __name__=='__main__':main()
