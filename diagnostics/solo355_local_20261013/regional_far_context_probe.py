"""Task5 I1: actual far-rate producer inputs, context cut and selected-action equivalence."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['RW_OFFSET_WRITER'] = 'experiment'
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import types
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc_regional_context as current
from evaluation.controllers import area_follower_objective as joint
from evaluation.controllers.sdmpc_tangent_surrogate import Query
from diagnostics.solo355_local_20261013.regional_context_probe import load, inputs, token, canonical
from src.models.state import ControlAction

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path('D:/VISSIM_analysis/20261013_solo355_local/task5')
CAPTURE = ARTIFACTS.parent/'projected.pkl'
FIELD = 'far_ramp_capacity_veh_h'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(canonical(value), indent=2, allow_nan=False)+'\n', encoding='utf-8')


def prepare(factory, x):
    c,s,f,h,m = x['args']
    return factory.prepare(c,s,f,h,m,derived=x['obs']['merged']['obs150_derived'],
        bootstrap=dict(x['kwargs']['worker_bootstrap'],runtime_sources={}))


def producer_contexts(mode, out):
    """Replay the named producer before its legacy ramp names are projected.

    Only the producer's four mutated cfg fields are propagated into the captured
    initialized graph. This is dependency-specific preparation, not full raw or
    transport replay; all own traffic, physical history and boundary inputs stay fixed.
    """
    x = load(mode, CAPTURE)
    tuning = json.loads((ROOT/'diagnostics/solo355_local_20261013'/f'{mode}_config.json').read_text())
    calibration = json.loads((ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json').read_text(encoding='utf-8-sig'))
    calibration = adapter.deep_update(calibration,tuning.get('calibration_override',{}))
    adapter.install_config_switches(tuning)
    previous = json.loads(Path(x['kwargs']['previous_path']).read_text(encoding='utf-8'))
    groups = adapter._far_measurement_reservoirs()
    rows = {}
    for variant in ('base','measurement','previous_estimate'):
        raw = copy.deepcopy(x['obs']['merged'])
        prior = copy.deepcopy(previous)
        for reservoir, links in groups.items():
            if not reservoir.startswith('ramp_'):
                continue
            if variant == 'measurement':
                for link in links:
                    raw['local_observation']['far_measurement']['link_volume_veh_h'][link] = 100000.
            elif variant == 'previous_estimate':
                prior['metadata']['far_rate_est_'+reservoir] = 300000.
        previous_path = out/f'{mode}_{variant}_previous.json'
        previous_path.write_text(json.dumps(prior),encoding='utf-8')
        cfg = adapter.build_config(ROOT/'vendor/NumSim-mine',150.,8100.,'integrated',
            calibration,tuning,local_observation=True,flagship=True)
        producer = adapter.install_measured_far_reservoir_rates(cfg,tuning,raw,previous_path)
        y = copy.deepcopy(x)
        destination = y['args'][0].cfg
        setattr(destination.network, FIELD, copy.deepcopy(getattr(cfg.network,FIELD)))
        for field in ('leader_mfd_far_g_cong','leader_mfd_far_g_free','leader_mfd_far_g_fw'):
            setattr(destination.mpc, field, getattr(cfg.mpc,field))
        local = prepare(current,y)
        view = inputs(local,y).view
        rows[variant] = dict(context_sha256=token(view), produced=getattr(cfg.network,FIELD),
            retained=getattr(local['controller'].cfg.network,FIELD,None), producer=producer,
            previous_path=str(previous_path), previous_sha256=sha(previous_path),
            own_boundary_sha256=token(raw['obs150_derived']))
    assert len({r['own_boundary_sha256'] for r in rows.values()}) == 1
    assert rows['base']['produced'] != rows['measurement']['produced']
    assert rows['base']['produced'] != rows['previous_estimate']['produced']
    if mode == 'urban_only':
        assert len({r['context_sha256'] for r in rows.values()}) == 1
        assert all(r['retained'] is None for r in rows.values())
    else:
        assert len({r['context_sha256'] for r in rows.values()}) == 3
        assert all(r['retained'] == r['produced'] for r in rows.values())
    return rows


def selected_response(prepared, action, x):
    query = Query(prepared.template,lambda *_:None,lambda *a,**k:None)
    start = time.perf_counter()
    try:
        item = query.evaluate([action],derivatives=True)[0]
        derivative = query.derivative(action)
        hold = joint.validate_actual_decision_hold(prepared.local['controller'].nash_solver,
            prepared.local['state'],action,item,callbacks=prepared.callbacks,context=prepared.context,
            source_fingerprint='task5-fix1-selected-action-equivalence',options=x['kwargs']['options'])
        assert hold['feasible']
        return dict(response=item,derivative=derivative,writer=hold['command_evidence'],
            feasible=hold['feasible'],seconds=time.perf_counter()-start)
    finally:
        query.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output);out.mkdir(exist_ok=False)
    prior_source=ARTIFACTS/'fix1/executed_sources/evaluation/controllers/sdmpc_regional_context.py'
    original=types.ModuleType('task5_executed_context')
    exec(compile(prior_source.read_bytes(),str(prior_source),'exec'),original.__dict__)
    modes={mode:producer_contexts(mode,out) for mode in current.regional_modes()}
    x=load('freeway_only',CAPTURE)
    before=inputs(prepare(original,x),x);after=inputs(prepare(current,x),x)
    assert token(before.view)==token(after.view)
    fw_hash=token(after.view)
    x=load('urban_only',CAPTURE)
    before=inputs(prepare(original,x),x);after=inputs(prepare(current,x),x)
    old_view=canonical(before.view);new_view=canonical(after.view)
    removed=[]
    def strip(value,path=()):
        if isinstance(value,dict):
            result={}
            for k,v in value.items():
                if k==FIELD:
                    assert path[-1]=='fields'
                    removed.append('/'.join(path+(k,)))
                else:result[k]=strip(v,path+(k,))
            return result
        if isinstance(value,list):return [strip(v,path+(str(i),)) for i,v in enumerate(value)]
        return value
    assert strip(old_view)==new_view and removed
    selected=json.loads((ARTIFACTS/'full_urban900/selection.json').read_text())
    action=ControlAction(**copy.deepcopy(selected['response']['control']))
    old_result=selected_response(before,action,x)
    new_result=selected_response(after,action,x)
    exclusions=set(json.loads((ARTIFACTS/'input_gate.json').read_text())['excluded_fields'])
    def normalize(value):
        if isinstance(value,dict):return {k:normalize(v) for k,v in value.items() if k not in exclusions}
        if isinstance(value,list):return [normalize(v) for v in value]
        return value
    for field in ('response','derivative','writer'):
        assert normalize(canonical(old_result[field]))==normalize(canonical(new_result[field])),field
    assert abs(new_result['response']['objective_veh_h']-selected['selection']['selected_objective'])<1e-9
    write(out/'old_selected_response.json',old_result)
    write(out/'new_selected_response.json',new_result)
    write(out/'receipt.json',dict(passed=True,scope='Task5 I1 actual-producer preparation and selected-action equivalence',
        native_runs=0,full_selections=0,modes=modes,freeway_old_new_graph_identical=True,
        freeway_context_sha256=fw_hash,urban_removed_graph_paths=removed,
        urban_old_context_sha256=token(before.view),urban_new_context_sha256=token(after.view),
        urban_selected_response_jacobian_writer_equal=True,
        urban_selected_objective=new_result['response']['objective_veh_h'],
        old_factory=dict(path=str(prior_source),sha256=sha(prior_source)),
        current_factory=dict(path=str(Path(current.__file__)),sha256=sha(current.__file__)),
        old_selected_response=dict(path=str(out/'old_selected_response.json'),sha256=sha(out/'old_selected_response.json')),
        new_selected_response=dict(path=str(out/'new_selected_response.json'),sha256=sha(out/'new_selected_response.json')),
        exclusions=sorted(exclusions),
        limits='Producer-specific replay, not upstream transport replay or new full selection; numerical equivalence is at the saved selected urban action. Regional endpoint directly computes ledger TTT without the legacy far function.'))
    print(json.dumps(dict(passed=True,freeway_graph_identical=True,urban_selected_equal=True,
        urban_selected_objective=new_result['response']['objective_veh_h'],old_seconds=old_result['seconds'],new_seconds=new_result['seconds'])))


if __name__=='__main__':
    main()