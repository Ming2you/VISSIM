"""Attribute completed RM arrivals to initial chosen stock vs later cohorts.

No forecast, fitting or FZP pass. Native IDs use canonical ordinal assignment
and the same one-metre boundary stock/removal identity as obs150.
"""
import ctypes,gzip,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
from qualify_native2400 import validate_scope
RUNS=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS={};W={68,121,10772,10625,10629,10633};R='RM_C10681';KEY='storage:SC1004_W_out'
def read(p,gz=False):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if gz else b)
def pin(p):PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
def cohort_key(c):return (tuple(c['lane68']['order']),tuple(sorted(c['lane68']['shares'].items())))
def native(arm):
    folder=RUNS/arm/f'decisions_sdmpc31_g_2400_{arm}_s29';blocks=[];initial=None
    all_counts=Counter();originals={};proved=set();deleted=set()
    for end in (2550,2700,2850):
        raw=read(folder/f'state_{end:06}.json');b=oc.load_bundle(raw);o=b.obs
        for p in [Path(o['detector_config']['path']),folder/o['mer']['chunk'],folder/o['err']['chunk'],
                  folder/o['frames']['previous']['path'],folder/o['frames']['current']['path']]:pin(p)
        ds,_=oc.read_detector_csv(o['detector_config']['path'],o['detector_config']['sha256'])
        oc.validate_raw(o,ds,expected_simres=10);check_rule_crosscheck(o,ds)
        assigned=oc.assign_window(o,b.mer_rows)
        if initial is None:
            initial={v[0]:v for v in b.frame_start['vehicles']}
            originals={vid:v for vid,v in initial.items() if v[1]==68 and v[8]=='STATIC' and (v[6],v[7])==(1135,4)}
            assert len(originals)==40
        def group(vid):
            v=initial.get(vid)
            if vid in originals:return 'initial_RM_lane'+str(v[2])
            if v is not None and v[1] in W:return 'initial_other_W_out'
            return 'later_W_out_inflow'
        detectors=[d for d in ds if d.boundary_ref=='ramp_arrival:'+R]
        assert len(detectors)==2 and all(d.orientation=='down' and d.link==10681 and d.pos==1. for d in detectors)
        terms=oc.evaluate_boundary(detectors,o['detectors'],b.frame_end,b.frame_start,b.err_rows,end-150,end)
        id_counts=Counter();tails=0;entry_times={}
        end_ids=set();start_ids=set()
        for d in detectors:
            for event in assigned.entries[d.dcp_no]:
                id_counts[event.veh]+=1;entry_times[event.veh]=event.t_entry
            tails+=assigned.tails[d.dcp_no]
            end_ids |= oc.vehicles_in_segment(b.frame_end['vehicles'],d.segment,'down')
            start_ids |= oc.vehicles_in_segment(b.frame_start['vehicles'],d.segment,'down')
        for vid in end_ids:id_counts[vid]+=1
        for vid in start_ids:id_counts[vid]-=1
        for vid in terms.removed_vehicles:id_counts[vid]+=1
        assert sum(id_counts.values())+tails==terms.cross
        # Negative/duplicate identities would require a lane-crossing audit;
        # do not silently clamp them or pretend tails have observed IDs.
        assert all(n in (0,1) for n in id_counts.values()),dict(id_counts)
        counts=Counter()
        for vid,n in id_counts.items():
            if n:counts[group(vid)]+=n;proved.add(vid)
        if tails:counts['unassigned_mer_tail']=tails
        all_counts.update(counts)
        removals=oc.window_removals(b.err_rows,end-150,end)
        deleted.update(x['vehicle_id'] for x in removals)
        now={v[0]:v for v in b.frame_end['vehicles']}
        disposition={}
        for lane in (1,2,3,4):
            ids=[vid for vid,v in originals.items() if v[2]==lane]
            disposition[str(lane)]=dict(initial=len(ids),still68=sum(vid in now and now[vid][1]==68 for vid in ids),
                proved_entry10681=sum(vid in proved for vid in ids),removed=sum(vid in deleted for vid in ids),
                absent_unexplained=[vid for vid in ids if vid not in now and vid not in proved and vid not in deleted])
        blocks.append(dict(start_sec=end-150,total_arrival=terms.cross,by_initial_group=dict(counts),
            cumulative=dict(all_counts),initial_RM_disposition=disposition,unassigned_tails=tails,
            measured_entry_time_by_vehicle={str(v):t for v,t in entry_times.items() if v in originals}))
    return blocks
def model(folder,arm):
    initial=read(folder/'state.json')['known_legsplit_route_state']['cohorts']
    original=[c.copy() for c in initial if c['target']==R]
    assert sum(c['vehicles'] for c in original)==40
    keys={cohort_key(c) for c in original};assert len(keys)==40
    summary=read(folder/(arm+'.json'))
    response=read(folder/(arm+'.response.json.gz'),True)
    resources={x['start_sec']:x for x in response['resource_allocations']
        if x['kind']=='legsplit_source_reach_share' and x['resource']=='SC1004_W_out:'+R}
    transfers=Counter();incoming=defaultdict(Counter);outgoing=defaultdict(Counter)
    for x in response['transfers']:
        at=x['start_sec'];window=2400+150*int((at-2400)//150)
        if x['source']==KEY and x['target']=='ramp:'+R:transfers[at]+=x['vehicles']
        if x['source']==x['target']:continue
        if x['target']==KEY:incoming[window][x['source'] or x['route_key']]+=x['vehicles']
        if x['source']==KEY:outgoing[window][x['target'] or x['route_key']]+=x['vehicles']
    assert set(resources)==set(transfers)
    rows=[];debits=Counter();total=0.
    for at in range(2400,2850):
        rr=resources.get(at)
        if rr:
            request,accepted=rr['available_veh'],rr['accepted_total_veh'];total+=accepted
            assert abs(accepted-transfers[at])<1e-8 and 0<=accepted<=request+1e-8
            for c in original:
                if c['due']<=at:
                    debit=c['vehicles']*accepted/request if request else 0.
                    c['vehicles']-=debit
                    for lane,s in c['lane68']['shares'].items():debits['initial_RM_lane'+lane]+=debit*s
        if at+1 in (2550,2700,2850):
            j=(at+1-2550)//150;end_cohorts=summary.get('known_endpoint_cohorts',[[],[],[]])[j]
            saved=[c for c in end_cohorts if c['target']==R and 'lane68' in c and cohort_key(c) in keys]
            rem={lane:sum(c['vehicles']*c['lane68']['shares'].get(lane,0) for c in original) for lane in ('1','2','3','4')}
            if 'known_endpoint_cohorts' in summary:
                for lane,n in rem.items():
                    assert abs(n-sum(c['vehicles']*c['lane68']['shares'].get(lane,0) for c in saved))<1e-7
                verification='saved_endpoint_cohorts'
            else:
                # Older baseline saved only the physical response. Crosscheck
                # its reconstruction against the existing independently
                # reviewed attribution, not imaginary serialized cohorts.
                old=read(H/'wout_response/lane_access.json')['arms'][arm][j]['by_initial_lane']
                for lane,n in rem.items():assert abs(n-old[lane]['model_still_W_out'])<1e-7
                verification='existing_baseline_attribution; endpoint_cohorts_not_serialized'
            window=at+1-150
            target_sources=defaultdict(Counter)
            for c in end_cohorts:target_sources[c['source']][c['target']]+=c['vehicles']
            rows.append(dict(start_sec=window,total_arrival=total,initial_RM_arrival_by_lane=dict(debits),
                noninitial_RM_arrival=total-sum(debits.values()),initial_RM_still_by_lane=rem,
                initial_cohort_check=verification,
                endpoint_by_source_target={k:dict(v) for k,v in target_sources.items()},
                W_out_incoming=dict(incoming[window]),W_out_outgoing=dict(outgoing[window])))
            total=0.;debits=Counter()
    return rows
def main():
    assert not (HERE/'assessment.json').exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    closure=read(H/'native2400_analysis/runtime_closure.json');assert closure['all_owned_processes_closed']
    result={}
    for arm in ('hold','selected'):
        n=native(arm);q=model(H/'sc1_supply/forecast2400',arm);c=model(H/'connector_stage/forecast2400',arm)
        result[arm]=[dict(native=n[i],baseline=q[i],connector_stage=c[i]) for i in range(3)]
        for row in result[arm]:
            a=row['native'];m=row['connector_stage']
            print(arm,a['start_sec'],'native',a['by_initial_group'],'modelinitial',m['initial_RM_arrival_by_lane'],'modelother',m['noninitial_RM_arrival'],flush=True)
    for name in ('route_choice_corridor','urban_flow_accounting'):
        p=H/'connector_stage'/f'{name}.candidate.py.preserved';pin(p)
        rec=read(H/'connector_stage/restoration.json')['files'];r=next(r for r in rec if Path(r['candidate_archive']).name==p.name)
        assert PINS[str(p)]==r['candidate_sha256']
    for p in (H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md',H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md',Path(__file__)):pin(p)
    output=dict(status='complete_attribution',arms=result,new_forecasts=0,new_native=0,new_parameter_fits=0,
        limitations=['Completed response fractions attribute a saved prediction; this is not an autonomous conditional rollout.',
            'Native ordinal tails without IDs stay unassigned; absent IDs are not normal exits.',
            'Noninitial RM combines initial prechoice and new arrivals in the model; do not claim these are individually identified.',
            'City signals and multiple RM commands differ jointly; not isolated10681 causality.'],source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
if __name__=='__main__':main()
