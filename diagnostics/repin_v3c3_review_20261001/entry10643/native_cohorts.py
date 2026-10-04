"""Existing native MER and complete frames; no FZP pass or model future input."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from evaluation.controllers import obs150_contract as oc, offramp_routing as routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def main():
    assert not (HERE/'native_cohorts.json').exists()
    contract=read(HERE.parent/'unrouted10646/route_contract.json')
    runtime=routing.compile_inventory(contract,read(ROOT/contract['mapping']['path']))
    assert runtime['branches']['10643']['source_cell']==9
    table=I/'selected/obs150/obs150_detectors_v2.csv'
    detectors,digest=oc.read_detector_csv(table);pins[str(table)]=digest
    groups=oc.group_boundaries(detectors)
    audit=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    expected=read(HERE.parent/'offramp_drain_profile/eight_offramps.json')
    result={}
    for arm in ('hold','selected'):
        raws={}
        for name,digest in audit['input_sha256'].items():
            p=Path(name)
            if arm not in p.parts:continue
            d=read(p);assert pins[str(p)]==digest;raws[int(d['sim_sec'])]=d
        frames={t:read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json') for t,raw in raws.items()}
        assert set(frames)=={2700,2850,3000,3150}
        initial=frames[2700]
        initial_by_id={r[0]:r for r in initial['vehicles']}
        entries=[];window_counts=[]
        for t in (2850,3000,3150):
            bundle=oc.load_bundle(raws[t]);window=oc.assign_window(bundle.obs,bundle.mer_rows)
            local=[]
            for det in groups['off_entry:10643']:
                assert window.tails[det.dcp_no]==0
                local.extend(dict(vehicle=e.veh,time_sec=e.t_entry,lane=det.lane) for e in window.entries[det.dcp_no])
            entries.extend(local);window_counts.append(dict(start=t-150,end=t,count=len(local)))
        assert len({e['vehicle'] for e in entries})==len(entries)
        assert len(entries)==expected['arms'][arm]['10643']['native_entry'], 'Do not omit boundary corrections'
        known={};uncertain={};physical={}
        for vid,row in initial_by_id.items():
            if str(row[1]) not in runtime['physical']:continue
            road,position,cell=routing._position(runtime,row[1],row[3])
            physical[vid]=dict(road=road,position_m=position,cell=cell,link=row[1],lane=row[2],speed=row[4],route=row[6:9])
            if road!='FW_E' or position>runtime['branches']['10643']['source_chain_m']:continue
            if row[6] is None:
                weights=routing._future_distribution(runtime,road,position)
            else:
                path=runtime['routes'][f'{int(row[6])}:{int(row[7])}']
                weights=routing._route_distribution(runtime,path,road,position)
            weight=weights.get('10643',0.)
            if row[6] is not None and weight==1:known[vid]=physical[vid]
            elif weight>0:uncertain[vid]=dict(physical[vid],expected_exit_weight=weight)
        observed_by_id={e['vehicle']:e for e in entries}
        classes=Counter();witnesses=[]
        for e in entries:
            vid=e['vehicle']
            group=('initial_assigned10643' if vid in known else 'initial_future_choice' if vid in uncertain
                   else 'initial_other_mainline' if vid in physical else 'not_in_initial_modelled_mainline')
            classes[group]+=1
            witnesses.append(dict(e,group=group,initial=physical.get(vid)))
        snapshots=[]
        for t,frame in sorted(frames.items()):
            lookup={r[0]:r for r in frame['vehicles']};remaining=Counter();other=[]
            exited={e['vehicle'] for e in entries if e['time_sec']<=t+.1}
            for vid in known:
                if vid in exited:continue
                row=lookup.get(vid)
                if row and str(row[1]) in runtime['physical']:
                    road,position,cell=routing._position(runtime,row[1],row[3]);remaining[(road,cell)]+=1
                else:other.append(dict(vehicle=vid,current=row))
            snapshots.append(dict(time_sec=t,known_initial=len(known),known_exited=len(set(known)&exited),
                known_remaining_mainline=[dict(road=k[0],cell=k[1],count=n) for k,n in sorted(remaining.items())],
                unaccounted_as_mainline_or10643=other))
        result[arm]=dict(total_entry=len(entries),windows=window_counts,entry_cohorts=dict(classes),
            initial_assigned10643=[dict(vehicle=k,**v) for k,v in known.items()],
            initial_uncertain=[dict(vehicle=k,**v) for k,v in uncertain.items()],snapshots=snapshots,witnesses=witnesses)
        print(arm,'entries',classes,'known_initial',len(known),'windows',window_counts)
        print('COHORT',snapshots)
    output=dict(status='COMPLETED_NATIVE_10643_ENTRY_COHORTS',cases=result,route_runtime=runtime,
        source_pins=pins,new_native=0,new_fzp_scan=0,
        limitations=['Only the currently assigned10643 cohort is deterministic at initialization.',
          'Not in initial modelled mainline does not necessarily mean newly generated in the network.',
          'Later frames/MER classify realized outcomes only, never autonomous forecast input.',
          'Missing IDs are not assumed to have exited normally or to have been deleted.'])
    (HERE/'native_cohorts.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
