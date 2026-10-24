"""Bounded live-path meter selection and exact replay on saved native state."""
import copy
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEC = Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def save(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def check(captured, reference, coord, options, evaluate, selected_path, output, **unused):
    from evaluation.controllers import sdmpc, sdmpc_sequence as seq, sdmpc_pfo
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    cfg, state = captured['cfg'], captured['state']
    selected = adapter.control_from_json(selected_path, cfg, ControlAction)
    if seq.KEY not in selected.diagnostics:
        selected = seq.pack(seq.actions(selected, 3))
    coord.validate(selected)
    saved = json.loads(selected_path.with_suffix('.joint.json').read_bytes())['selection']
    follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
    def budget(action, quantities):
        return constraints.shared_quantity_constraints(follower, action, quantities,
            start_sec=state.time_sec, horizon_steps=3, np_mode='cap', target_np_veh=action.N_P_star,
            np_tolerance_veh=1e-7, nuf_mode='cap', target_nuf_veh_h=action.N_UF_star,
            nuf_tolerance_veh_h=1e-7)
    def feasible(action, item):
        return budget(action,item['quantities'])['feasible'] and sdmpc_pfo.model_feasible(item,options['shared_tolerance'])
    before = evaluate([selected])[0]
    assert abs(before['objective_veh_h']-saved['selected_objective']) < 1e-7
    started = time.perf_counter()
    best, proof = sdmpc.audit_meter_neighbors(coord,(selected,before,None),1e-7,evaluate,feasible)
    proof['seconds'] = time.perf_counter()-started
    assert proof['additional_predictions'] <= 20
    save('neighbor_audit.json',proof)
    result = dict(original_model_parity=True, audit=proof, execution={}, future_truth_used=False)
    for label, action in [('held',selected),('chosen',best[0])]:
        coord.validate(action)
        with seq.prediction_scope(action,cfg,state.time_sec,3):
            point = endpoint.evaluate_price_point(state,action,copy.deepcopy(captured['forecast']),(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        assert not point.aborted and len(point.states)==3
        response=point.control_area_response
        for s in (state,*point.states):get_ledger(s).assert_stocks(model_inventory(s,cfg))
        exceed=max((x['exceedance_veh'] for x in response['resource_allocations']),default=0.)
        assert exceed<1e-7
        q=constraints.shared_urban_quantities(follower,response,start_sec=state.time_sec,horizon_steps=3)
        checked=budget(action,q);assert checked['feasible']
        result['execution'][label]=dict(ttt=point.ttt,constraints=checked,resource_exceedance=exceed,
            commands=[dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}) for c in seq.actions(action,3)],
            merge={r:sum(x['vehicles'] for x in response['transfers'] if x['source']=='ramp:'+r and x['target']=='merge_pending:'+r)
                   for r in cfg.network.ramps})
    result['execution_delta_veh_h']=result['execution']['chosen']['ttt']-result['execution']['held']['ttt']
    assert result['execution_delta_veh_h'] <= 1e-7
    assert result['audit']['selected'] is not None
    save('saved4500_validation.json',result)
    print(json.dumps(dict(status='PASS',selected=proof['selected'],surrogate=best[1]['objective_veh_h'],
                         exact_delta=result['execution_delta_veh_h'])),flush=True)


def main():
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    original=probe.probe_selected_meter;probe.probe_selected_meter=check
    sys.argv=[str(probe.__file__),'--closedloop-recorded','--at=4500','--selected-meter-check',
        '--recorded-selection-check','--warm-head-history','--replay-vsl-history','--probe-label=rm219v3',
        '--recording-dir='+str(DEC),'--tuning-json='+str(HERE.parent/'fixedvsl9000_197/config.json')]
    try:probe.main()
    finally:probe.probe_selected_meter=original


if __name__=='__main__':main()
