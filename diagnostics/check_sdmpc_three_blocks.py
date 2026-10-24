"""Saved-state qualification for 231 direct sensitivities; never runs VISSIM."""
from pathlib import Path
import copy
import hashlib
import json
import pickle
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def context(request):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, area_follower_objective as joint
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers import sdmpc_sequence as seq
    follower,state,reference,forecast=request['owned']
    cfg=follower.cfg
    bootstrap=request['bootstrap']
    install_worker_runtime(adapter,cfg,bootstrap['state_json'],bootstrap['detector_mapping'])
    for k,v in copy.deepcopy(request['runtime']).items():setattr(adapter,k,v)
    adapter._PHASE_VECTOR_FOLLOWER['ref']=follower
    tuning=json.loads((ROOT/'diagnostics/tangent_900_h1/config.json').read_text())
    options=adapter.joint_owner_game_settings(tuning,cfg,'wu-link')
    mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
    with joint.shared_query_runtime_scope():
        callbacks,ctx,_=joint._joint_runtime_callbacks(follower,state,forecast,reference,reference,
            mapping,bootstrap['runtime_sources'],reference=reference,total_budget=None,directional={},
            tolerance=options['nuf_tolerance_veh_h'],price_probe=False)
    coord=seq.SequenceCoordinates(cfg,reference,callbacks['move_box'],cfg.network.sdmpc_options)
    return coord,callbacks,ctx,options


def main():
    from evaluation.controllers import sdmpc_sequence as seq, sdmpc_tangent
    source,out=Path(sys.argv[1]),Path(sys.argv[2])
    out.mkdir(parents=True,exist_ok=False)
    with (source/'request.pickle').open('rb') as f: old=pickle.load(f)
    cfg=old['owned'][0].cfg
    cfg.network.sdmpc_options.update(fifo_batch=True,control_blocks=3)
    coord,callbacks,ctx,options=context(old)
    follower,state,reference,forecast=old['owned']
    action=seq.pack([reference.copy() for _ in range(3)])
    request=sdmpc_tangent.prepare_request(follower,state,forecast,reference,action,coord,old['bootstrap'])
    request['diagnostic_checkpoint']=str((out/'prediction.pickle').resolve())
    data=pickle.dumps(request,protocol=5)
    inp,result=out/'request.pickle',out/'result.pickle'
    inp.write_bytes(data)
    started=time.perf_counter()
    child=subprocess.run([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
        str(inp.resolve()),str(result.resolve()),hashlib.sha256(data).hexdigest()])
    receipt=pickle.loads(result.read_bytes())
    receipt['wall_sec_including_spawn']=time.perf_counter()-started
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if child.returncode:
        print(receipt.get('error'),flush=True)
        return child.returncode
    baseline=json.loads((source/'result.json').read_text())
    checks={}
    for key in ('costs','resources'):
        checks[key+'_error']=float(np.max(abs(np.asarray(receipt[key])-np.asarray(baseline[key]))))
    for key in ('cost_jacobian','resource_jacobian'):
        expanded=np.asarray(receipt[key])
        collapsed=expanded.reshape(len(expanded),3,coord.width).sum(axis=1)
        checks[key+'_sum_blocks_error']=float(np.max(abs(collapsed-np.asarray(baseline[key]))))
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    with (source/'prediction.pickle').open('rb') as f: before=pickle.load(f)
    with (out/'prediction.pickle').open('rb') as f: after=pickle.load(f)
    checks['scalar_states_max_primal_error']=state_error(before['scalar_states'],after['scalar_states'])
    if not receipt['complete_primal_state_match'] or not baseline['complete_primal_state_match']:
        raise ValueError('Both runs must independently compare every scalar/tangent state field')
    checks['tangent_states_error_bound']=(checks['scalar_states_max_primal_error']+
        receipt['max_primal_state_error']+baseline['max_primal_state_error'])
    report=dict(checks=checks,axes=len(coord.axes),control_blocks=3,
        same_hold_reference=True,scalar_sec=receipt['scalar_sec'],tangent_sec=receipt['tangent_sec'],
        native_applied=False,pass_all=max(checks.values())<=1e-7)
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
