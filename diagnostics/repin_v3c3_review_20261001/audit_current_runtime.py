"""One existing-state initialization; no optimizer, rollout, native run or refit."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
from evaluation.controllers import obs150_contract as oc, runtime_setup


def verify_existing(raw, derived):
    obs = raw[oc.RAW_STATE_KEY]
    path = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
    assert path.read_bytes() == oc.derived_bytes(derived)
    return path


oc.write_derived = verify_existing
script = I / 'probe_selected_arrival_path.py'
spec = importlib.util.spec_from_file_location('current_runtime_review', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
configure = runtime_setup.configure_runtime
captured = {}


def capture(*args, **kwargs):
    result = configure(*args, **kwargs)
    captured.update(cfg=args[1], state=result[0], metadata=result[2])
    return result


runtime_setup.configure_runtime = capture
tuning = I / 'expanded036_9000_20260930/loss_onset2250/source_sc101/readiness_candidate/candidate_config.json'
sys.argv = [str(script), '--closedloop-recorded', '--at=2700', '--warm-head-history',
    '--replay-vsl-history', '--initialize-only', '--output-suffix=upstream_bd39205',
    '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
    '--fixed-replay-summary=' + str(I / 'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
    '--tuning-json=' + str(tuning)]
module.main()
net = captured['cfg'].network
movements = {m: dict(spec=s, capacity_veh_h=net.movement_capacity_by_movement_veh_h.get(m))
    for m,s in net.urban_movements.items() if s.get('off_ramp') in ('OR_D_W','OR_D_E')}
ramps = net.physical_ramp_branches['ramps']
service = {}
for key, row in ramps.items():
    table = row['service_by_green_veh_h']
    groups = {}
    for g,rate in table.items(): groups.setdefault(rate, []).append(g)
    service[key] = dict(table=table, duplicate_groups={str(q):g for q,g in groups.items() if len(g)>1})
head = getattr(net, 'head_service_resources', {})
resources = {k:v for k,v in head.get('resources',{}).items()
             if set(v.get('members',{})).intersection(movements)}
result = dict(network_sha256='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc',
    seed=47, sim_sec=captured['state'].time_sec, autonomous_rollouts=0, optimizations=0, native_runs=0,
    tuning=dict(path=str(tuning),sha256=hashlib.sha256(tuning.read_bytes()).hexdigest()),
    off_movements=movements, shared_head_resources=resources, ramp_services=service,
    limitations='Installed capacities only: not realized flow, no new traffic response evidence.')
(OUT/'current_runtime_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(off_capacities={m:r['capacity_veh_h'] for m,r in movements.items()},
    duplicate_ramp_services={m:r['duplicate_groups'] for m,r in service.items() if r['duplicate_groups']},
    shared_head_resource_count=len(resources))))
