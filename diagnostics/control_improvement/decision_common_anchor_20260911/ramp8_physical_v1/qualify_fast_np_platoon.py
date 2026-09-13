"""Two held forecasts, retaining only SC1004 arrival/service timing for native comparison."""
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    output = D / (sys.argv[1]+'.json')
    if output.exists():
        raise FileExistsError(output)
    os.chdir(ROOT)
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as a, area_follower_objective as area
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    from src.controllers import rollout_endpoint as ep
    b = ROOT/'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
    config = D/'joint_config_fast_np_v2.json'
    selected_file = D/'fast_np_selected_v2_selected_action.json'
    paths = [Path(__file__), config, selected_file, b/'state_000900.json',
             b/'action_000750.json', b/'action_000900.json', D/'fast_np_recorded900_v3.pickle']
    paths += list((ROOT/'evaluation/controllers').glob('*.py'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p):sha(p) for p in paths}
    report = {'completed':False, 'source_sha256':pins, 'arms':{},
        'scope':'Same 900-state held 450s model forecasts; native runs already complete. SC1004 movements only; no model/config/command modifications.'}
    started = time.perf_counter()
    try:
        cfg,state,det,tuning,raw,mapping,_ = build_projected(config,b/'state_000900.json',b/'action_000750.json',fixture_inputs=False)
        cal = a.deep_update(dict(a.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
        forecast = a.demand_from_state(raw,cfg,DemandStep,3,cal,det)
        movements = {k:v for k,v in cfg.network.urban_movements.items() if k.startswith('SC1004_')}
        report['effective_movements'] = movements
        report['effective_routes'] = {k:v for k,v in cfg.network.control_area_routes.items()
                                     if k.startswith(('movement:SC1004_', 'arrival:SC1004_'))}
        report['physical_link_origins'] = {k:det.get('link_to_origins',{}).get(k) for k in ('52','66')}
        inputs = pickle.dumps((cfg,state,forecast),protocol=5)
        for label,path in (('baseline',b/'action_000900.json'),('selected',selected_file)):
            control = a.control_from_json(path,cfg,ControlAction)
            with area.shared_query_runtime_scope():
                point = ep.evaluate_price_point(state,control,forecast,(),ep.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
            response = point.control_area_response
            assert not point.aborted and len(point.states)==3 and response['model_constraint_coverage']['complete']
            assert pickle.dumps((cfg,state,forecast),protocol=5)==inputs
            transfers = [r for r in response['transfers'] if str(r['route_key']).startswith(('movement:SC1004_', 'arrival:SC1004_'))]
            bins = {str(t):{} for t in range(900,1350,30)}
            for row in transfers:
                start,end = row['start_sec'],row['end_sec']
                bucket = max(900, int((end-1e-8)//30)*30)
                assert bucket in range(900,1350,30) and bucket <= start <= end <= bucket+30
                values = bins[str(bucket)]
                values[row['route_key']] = values.get(row['route_key'],0.)+row['vehicles']
            report['arms'][label] = {'objective_veh_h':point.objective,
                'area':point.control_area, 'transfers':transfers, 'bins30s':bins,
                'response_sha256':sha_bytes(response)}
        selected = pickle.loads((D/'fast_np_recorded900_v3.pickle').read_bytes())['selected']['response']['final_score']
        counts = report['arms']['selected']['area']['flow_counts']
        report['selected_sc1004_services_exact_recorded_game'] = all(
            value == selected['control_area']['flow_counts'].get(key,0.)
            for key,value in counts.items() if key.startswith(('movement:SC1004_', 'arrival:SC1004_')))
        assert report['selected_sc1004_services_exact_recorded_game']
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        report['source_changes'] = [p for p,h in pins.items() if sha(Path(p))!=h]
        report['completed'] = report['completed'] and not report['source_changes']
        report['wall_sec'] = time.perf_counter()-started
        output.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({k:report.get(k) for k in ('completed','wall_sec','source_changes','error','selected_sc1004_services_exact_recorded_game')}))
    return 0 if report['completed'] else 1


def sha_bytes(value):
    return hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()


if __name__ == '__main__':
    sys.exit(main())
