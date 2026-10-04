"""Verify the saved observation audit without rerunning traffic or forecasts."""
import gzip
import hashlib
import json
from pathlib import Path

from evaluation.controllers import offramp_routing as routing

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
F=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    target=HERE/'completion.json'
    assert not target.exists(),target
    audit=json.loads((HERE/'audit.json').read_bytes())
    for p,h in audit['source_pins'].items():
        assert sha(Path(p))==h,p
    old=json.loads((HERE.parent/'lane10682_transport/completion.json').read_bytes())
    production={}
    for p,h in {**old['restored_exact'],**old['previous7production_pins_exact']}.items():
        path=Path(p)
        if not path.is_absolute():path=ROOT/path
        assert sha(path)==h,p
        production[str(path)]=h
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop)==old['stop_sha256']
    runtime=json.loads((HERE.parent/'entry10643/native_cohorts.json').read_bytes())['route_runtime']
    gate=runtime['bounds']['FW_E'][9]
    near={}
    for seed,t,d in [(43,2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        (47,2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
        raw=json.loads((Path(d)/f'state_{t:06d}.json').read_bytes())
        frame=json.loads((Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json').read_bytes())
        counts={z:{g:[0]*4 for g in ('10643','10682')} for z in (250,500,1000)}
        for v in frame['vehicles']:
            if str(v[1]) not in runtime['physical'] or v[6] is None:continue
            road,x,cell=routing._position(runtime,v[1],v[3])
            group=runtime['routes'][f'{int(v[6])}:{int(v[7])}']['target']
            if road!='FW_E' or group not in ('10643','10682'):continue
            for distance in counts:
                if gate-distance<=x<gate:counts[distance][group][int(v[2])-1]+=1
        near[str(seed)]=dict(time_sec=t,upstream_distance_m=counts)
    pairs={}
    for seed in (29,43):
        frames=[json.loads(gzip.decompress((F/f'cohort_early/s{seed}_{arm}_frames.json.gz').read_bytes()))['frames'] for arm in ('none','vsl')]
        times=sorted(frames[0],key=float)
        assert set(times)==set(frames[1])
        initial=set(frames[0][times[0]])
        def region(vs):return {k:v for k,v in vs.items() if k in initial and 9<=v[0]<=12}
        differences=[float(t) for t in times if region(frames[0][t])!=region(frames[1][t])]
        a=audit['trajectories'][f'{seed}_none'];b=audit['trajectories'][f'{seed}_vsl']
        assert a['crossings']==b['crossings']
        assert a['change_records']==b['change_records']
        pairs[str(seed)]=dict(total_frames=len(times),different_full_frames=sum(frames[0][t]!=frames[1][t] for t in times),
            different_initial_cohort_region_times=differences,
            inlet_crossings_and_lane_change_records_identical=True,
            independent_control_response_validation=False)
    result=dict(status='completed_observation_audit',goal_status='ACTIVE/NOT_QUALIFIED',
        known_initial_cohort_inlet_counts={str(s):audit['trajectories'][f'{s}_none']['crossing_summary'] for s in (29,43)},
        near_current_profiles=near,duplicate_evidence_check=pairs,
        adopted_physics=False,new_forecasts=0,new_vissim=0,new_fzp_scans=0,push=0,
        owned_processes_started=0,production_exact=production,stop_sha256=sha(stop),
        source_pins=audit['source_pins'],audit_sha256=sha(HERE/'audit.json'),
        limitations=['Only initially observed cohorts, not all arrivals or native boundary flow.',
            'Five-second endpoints do not identify exact lateral event times; missing exposure is not a zero rate.',
            'NC/VSL identical cohort crossings cannot count as independent controlled-response evidence.',
            'Near-current occupancy supports lane eligibility, not an exact future flow split.',
            'No autonomous lane model or cell calibration was qualified by this observation audit.'],
        next='Resolve destination-conditioned inlet/approach before cell FD fit; retain real initial wrong-lane stock and shared receiving constraints. Test a single bounded connection candidate against both43congestion and47recovery, then all8off balances and common-state gains.')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','near_current_profiles','duplicate_evidence_check','adopted_physics','new_forecasts','new_vissim')},ensure_ascii=False))

if __name__=='__main__':main()
