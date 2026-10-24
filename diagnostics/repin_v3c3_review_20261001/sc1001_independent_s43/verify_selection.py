"""Two canonical replays of an already completed SDMPC decision; no optimizer."""
import hashlib
import json
import importlib.util
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
LABEL='sc1001_shared_history_s43_r2'
selected=I/('closedloop_recorded2250_select_'+LABEL)
target=HERE/'selection_replay_resources.json'
if target.exists():raise FileExistsError(target)
assert json.loads((selected/'unused_action.joint.json').read_bytes())['completed']
from evaluation.controllers import obs150_contract as oc


def existing(raw,derived):
    obs=raw[oc.RAW_STATE_KEY];path=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
    assert path.read_bytes()==oc.derived_bytes(derived)
    return path


oc.write_derived=existing
script=I/'probe_selected_arrival_path.py'
from src.controllers import rollout_endpoint as endpoint
rows=[]


# The existing probe passes ObjectiveSpec as the fifth positional argument.
def capture(*args,**kwargs):
    if len(rows)>=2:raise RuntimeError('Two-replay budget exhausted')
    point=evaluate(*args,**kwargs)
    cfg=args[4].cfg
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    for state in (args[0],*point.states):
        get_ledger(state).assert_stocks(model_inventory(state,cfg))
        state.sc1001_approach.assert_network_mirror(state,cfg)
    maximum=max(r['exceedance_veh'] for r in point.control_area_response['resource_allocations'])
    assert maximum<1e-7
    rows.append(dict(ttt_veh_h=point.ttt,max_resource_exceedance_veh=maximum))
    return point


spec=importlib.util.spec_from_file_location('sc1001_selection_replay',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
probe=module.probe_levers
def instrument(*args,**kwargs):
    # Runtime installation wraps the endpoint to attach response ledgers.
    # Capture that installed endpoint, not the raw vendor function.
    global evaluate
    evaluate=endpoint.evaluate_price_point
    endpoint.evaluate_price_point=capture
    try:return probe(*args,**kwargs)
    finally:endpoint.evaluate_price_point=evaluate
module.probe_levers=instrument
sys.argv=[str(script),'--closedloop-recorded','--at=2250','--selection-check',
    '--warm-head-history','--replay-vsl-history',
    '--recording-dir=D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43',
    '--four-arm-receipt='+str(I/'seed43_fullplant_20260929/analysis_v2/observation_reuse.json'),
    '--tuning-json=diagnostics/repin_v3c3_review_20261001/sc1001_connection/candidate_config.json',
    '--probe-label='+LABEL,'--output-suffix=replay_v3']
module.main()
assert len(rows)==2
target.write_text(json.dumps(dict(rows=rows,optimizer_calls=0,new_native=0,
    script_sha256=hashlib.sha256(script.read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf-8')
