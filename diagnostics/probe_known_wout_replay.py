"""Private known-route candidate, one held150s endpoint at a time."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import pickle
import sys
import time
from pathlib import Path
from unittest.mock import patch
from diagnostics.probe_model_area_integration import ROOT, adapter
from diagnostics.test_known_wout_routes import actual_case, option
from diagnostics.prepare_known_wout_routes import installed
from diagnostics.known_wout_fixtures import input_path
from evaluation.controllers import area_runtime
from src.controllers.rollout_endpoint import evaluate_price_point,ObjectiveSpec
from src.models.state import ControlAction
from src.models.demand import DemandStep
from src.simulation import coupling


def provenance(*inputs):
    # Avoid recursively opening historical paths embedded in evidence reports.
    # Their values are not prediction inputs; hashing them is unnecessary work.
    manifest=ROOT/'diagnostics/contract_candidate_configs/manifest.json'
    paths={ROOT/p for p in json.loads(manifest.read_text())['source_sha256']}
    paths.update(Path(p).resolve() for p in inputs)
    paths.add(manifest)
    for module in tuple(sys.modules.values()):
        path=Path(getattr(module,'__file__','') or '').resolve()
        if path.suffix=='.py' and path.is_relative_to(ROOT): paths.add(path)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start',type=int,choices=(1200,3300),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',action='store_true',help='Same current runtime and input with the scoped route flag OFF')
    args=parser.parse_args(); output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'diagnostics'):raise ValueError('New diagnostic output required')
    start=time.perf_counter()
    cfg,state,detectors,tuning,raw,mapping,metadata=actual_case(args.start)
    action_path=input_path(f'action_{args.start:06d}.json')
    action=adapter.control_from_json(action_path,cfg,ControlAction)
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)
    pins=provenance(action_path,input_path(f'state_{args.start:06d}.json'),
        input_path(f'action_{args.start-150:06d}.json'),Path(__file__),
        ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',
        ROOT/'diagnostics/known_wout_route_proposal.py',ROOT/'diagnostics/prepare_known_wout_routes.py',
        ROOT/'diagnostics/known_wout_routes_ver2_proposal.json',ROOT/'diagnostics/fixtures/known_wout_v1.zip')
    source_model_fields=pickle.dumps((cfg.network.urban_link_storage_veh,cfg.network.off_ramp_split_ratio,
        cfg.network.offramp_direct_share_by_offramp,cfg.network.boundary_out_ramp_split))
    with installed() as route:
        route.configure_known_legsplit(cfg,tuning if args.baseline else option(tuning),state,raw)
        original=pickle.dumps((cfg,state,action,forecast))
        trace=[]; actual_step=coupling.freeway_substep
        keys=('green_times','offsets','vsl','ramp_metering')
        expected={k:copy.deepcopy(getattr(action,k)) for k in keys}
        def observe(*pos,**kw):
            assert all(getattr(pos[1],k)==expected[k] for k in keys)
            result=actual_step(*pos,**kw)
            s=pos[0]; counts=Counter()
            for c in getattr(s,'known_legsplit_route_state',{}).get('cohorts',[]):counts[c['target']]+=c['vehicles']
            trace.append({'elapsed_sec':(len(trace)+1)*cfg.simulation.T_f_sec,
                'W_out_stock':cfg.network.urban_link_storage_veh['SC1004_W_out']-s.urban_link_storage['SC1004_W_out'],
                'tagged_destinations':dict(counts),'ramp_queues':dict(s.ramp_queue),
                'off_FE_vph':result[1]['offramp_flow_OR_F_E'],
                'E8_speed_kph':s.freeway_speed['FW_E'][8],'E9_speed_kph':s.freeway_speed['FW_E'][9]})
            return result
        with patch.object(coupling,'freeway_substep',observe):
            point=evaluate_price_point(state,action,forecast,[],ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'))
        assert not point.aborted and len(trace)==15
        last=point.states[-1]
        route._known_check(last,cfg)
        last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last,cfg))
        assert original==pickle.dumps((cfg,state,action,forecast))
        assert source_model_fields==pickle.dumps((cfg.network.urban_link_storage_veh,cfg.network.off_ramp_split_ratio,
            cfg.network.offramp_direct_share_by_offramp,cfg.network.boundary_out_ramp_split))
        result={'schema':'known-wout-private-replay/v1','start_sec':args.start,'baseline':args.baseline,'elapsed_sec':time.perf_counter()-start,
            'scope':'One canonical coupled150s endpoint with only proposed known W_out route subset/hooks; source-run config and held action, no future truth/capacity fitting/MPC/VISSIM.',
            'source_sha256':pins,'source_changes':[p for p,h in pins.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h],
            'input_objects_unchanged':True,'capacity_and_prior_fields_unchanged':True,'held_control_all15_exact':True,
            'stock_closure':True,'metrics':point.control_area,'trace':trace,
            'final_known_wout_state':getattr(last,'known_legsplit_route_state',None),
            'final_E8_speed_kph':last.freeway_speed['FW_E'][8], 'final_E9_speed_kph':last.freeway_speed['FW_E'][9],
            'final_ramp_queues':dict(last.ramp_queue)}
        assert not result['source_changes']
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:result[k] for k in ('start_sec','elapsed_sec','final_E8_speed_kph','final_E9_speed_kph','final_ramp_queues')},indent=2))

if __name__=='__main__':main()
