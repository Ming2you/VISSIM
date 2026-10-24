"""Compare the two completed autonomous forecasts with closed native targets.

No FZP scan, model rollout, coefficient search or VISSIM launch.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.lane_plant_runtime import bin_frame

pins={}
def load(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

native=load(HERE/'analysis/summary.json')
assert native['counterfactual_valid'] and native['paired_prefix_exact']
models={name:load(HERE.parent/f'closedloop_recorded2700_lever450_rm_pair_s47_{suffix}/summary.json')
        for name,suffix in [('baseline','baseline_v1'),('cell23','cell23_v4')]}
audits={name:load(HERE.parent/f'closedloop_recorded2700_lever450_rm_pair_s47_{suffix}/ramp_response_audit.json')
        for name,suffix in [('baseline','baseline_v1'),('cell23','cell23_v4')]}
baseline=load(HERE/'prediction_baseline_config.json')
candidate=load(HERE.parent/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_full_config.json')
baseline['freeway']['lane_plant']=candidate['freeway']['lane_plant']
assert baseline==candidate, 'Only the frozen plant variant may differ'
manifest=load(ROOT/candidate['freeway']['lane_plant'])
geometry_path=ROOT/manifest['sources']['geometry']['path'];geometry=load(geometry_path)
assert pins[str(geometry_path)]==manifest['sources']['geometry']['sha256']
runs=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3')
cells=[]
for arm,case in [('hold','held_actual'),('release','release_actual')]:
    folder=runs/arm/f'decisions_sdmpc31_g_2700_{arm}_s47'
    for index,sec in enumerate((2700,2850,3000,3150)):
        raw=load(folder/f'state_{sec:06d}.json');obs=raw['obs150']
        ref=obs['frames']['current'];path=oc.resolve(obs,ref['path'])
        frame=oc.load_frame(path,ref['sha256'],sec)
        pins[str(path)]=ref['sha256']
        physical,vehicles,dropped=bin_frame(geometry,frame['vehicles'],'FW_E',drop_before_start=True)
        assert not dropped and len(physical)==31
        for cell in range(21,26):
            n=len(vehicles[cell]);speed=sum(v[4] for v in vehicles[cell])/n if n else None
            row=dict(arm=arm,time_sec=sec,cell_zero_based=cell,actual_stock=n,actual_speed_kmh=speed)
            for name,prediction in models.items():
                state=prediction['results'][case]['physical_cell_states'][index]
                rho=state['density']['FW_E'][cell];v=state['speed_kmh']['FW_E'][cell]
                predicted_n=rho*physical[cell]['length_km']*state['effective_lanes']['FW_E'][cell]
                row[name]=dict(stock=predicted_n,speed_kmh=v,speed_error_kmh=None if speed is None else v-speed)
                if sec==2700:
                    assert abs(predicted_n-n)<1e-7
                    if n:assert abs(v-speed)<1e-7
            cells.append(row)

comparison=[]
for name,prediction in models.items():
    assert prediction['start_sec']==2700 and prediction['duration_sec']==450
    assert prediction['future_observation_inputs'] is False and prediction['optimizer_iterations']==0
    held,released=(prediction['results'][case] for case in ('held_actual','release_actual'))
    comparison.append(dict(model=name,delta_omega_ttt_veh_h=released['delta_ttt_omega_veh_h'],
        delta_with_tracked_outside_veh_h=released['delta_with_tracked_outside_veh_h'],
        native_delta_omega_ttt_veh_h=native['delta_TTT_veh_h'],
        rank_matches_native=(released['delta_ttt_omega_veh_h']>0)==(native['delta_TTT_veh_h']>0),
        ramp10484={arm:audits[name]['arms'][arm]['RM_C10484'] for arm in ('hold','release')},
        physical_predictions=2,forecast_coefficient_fit=False))

for path in (Path(__file__),HERE.parent/'probe_selected_arrival_path.py',
             HERE.parent/'native_pair1200/analyze_pair.py',
             ROOT/'evaluation/controllers/physical_ramp_branches.py',
             ROOT/'evaluation/controllers/lane_plant_runtime.py',ROOT/'evaluation/controllers/freeway_fd.py',
             ROOT/'evaluation/controllers/lane_offramp_runtime.py',ROOT/'evaluation/controllers/runtime_setup.py'):
    pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in pins.items())
report=dict(comparison=comparison,cell_snapshots=cells,files=pins,
    common2700_initial_cell_state_verified=True,source_bytes_unchanged=True,
    new_native_runs=0,new_forecasts_in_this_verifier=0,cooperative_lane_change=False,
    limitations=['Seed47 was inspected previously; this is not a pristine unseen seed.',
        '150s endpoint snapshots show a recovery bias but do not isolate its cause or precise onset.',
        'Native residence uses 5s samples starting2700.1 and holds the final4.9s stock; prediction uses450s internal1s integration.',
        'Tracked model outside residence excludes unrepresented external demand; native uninserted delay remains separate.',
        'Four physical forecasts and rank checks do not certify SDMPC selection or VSL gain.'],
    goal_qualified=False,old9000_stop_preserved=(runs.parent/'20260928_sd31_d4e2_9000/STOP').is_file())
target=HERE/'prediction_comparison.json'
assert not target.exists(),'Preserve the completed comparison'
target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(comparison,ensure_ascii=False))
print(json.dumps([r for r in cells if r['cell_zero_based'] in (24,25)],ensure_ascii=False))
