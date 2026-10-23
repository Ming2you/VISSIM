"""Stage the opt-in controller integration without editing a frozen/native tree."""
import ast, hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path('D:/VISSIM_runtime/20261012_adopted355_vsl_three/frozen/sdmpc31_ca181e84_202610121132')
source = ROOT/'evaluation/controllers/sdmpc.py'
target = HERE/'staged/evaluation/controllers/sdmpc.py'
assert not target.exists(), 'Preserve existing staged revision'
text = source.read_text(encoding='utf8')
def replace(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new)
replace("'meter_activation_secant', 'meter_neighbor_audit'):",
        "'meter_activation_secant', 'meter_neighbor_audit', 'vsl_schedule_audit'):")
replace("    if options.get('meter_neighbor_audit') and options.get('control_blocks') != 3:\n        raise ValueError('Finite meter schedule audit requires three control blocks')",
        "    if options.get('meter_neighbor_audit') and options.get('control_blocks') != 3:\n        raise ValueError('Finite meter schedule audit requires three control blocks')\n"
        "    if options.get('vsl_schedule_audit') and options.get('control_blocks') != 3:\n        raise ValueError('Finite VSL schedule audit requires three control blocks')")
replace("        selected, item, signal = best\n        sequence_proof =",
        "        vsl_schedule_audit = None\n"
        "        if policy.get('vsl_schedule_audit'):\n"
        "            from evaluation.controllers.vsl_schedule_neighbors import audit as audit_vsl_schedules\n"
        "            finish_trial_derivatives()\n"
        "            emit('sdmpc_vsl_schedules_start')\n"
        "            vsl_started = perf_counter()\n"
        "            best, vsl_schedule_audit = audit_vsl_schedules(coord, best,\n"
        "                policy['objective_tolerance'], evaluate, feasible)\n"
        "            vsl_schedule_audit['seconds'] = perf_counter()-vsl_started\n"
        "            emit('sdmpc_vsl_schedules_done', **vsl_schedule_audit)\n"
        "        selected, item, signal = best\n        sequence_proof =")
replace("'finite_neighbor_audit_performed': meter_audit is not None, 'policy': policy}",
        "'finite_neighbor_audit_performed': meter_audit is not None or vsl_schedule_audit is not None, 'policy': policy}")
replace("        if meter_audit is not None:\n            metadata['meter_neighbor_audit'] = meter_audit",
        "        if meter_audit is not None:\n            metadata['meter_neighbor_audit'] = meter_audit\n"
        "        if vsl_schedule_audit is not None:\n            metadata['vsl_schedule_audit'] = vsl_schedule_audit")
ast.parse(text)
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(text, encoding='utf8')
helper = HERE/'vsl_schedule_neighbors.py'
(target.parent/helper.name).write_bytes(helper.read_bytes())
tuning = ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
cfg = json.loads(tuning.read_bytes())
cfg['adapter']['sdmpc_vsl_schedule_audit'] = True
(HERE/'staged_config.json').write_text(json.dumps(cfg, indent=2)+'\n', encoding='utf8')
(HERE/'integration_receipt.json').write_text(json.dumps(dict(
    source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    staged=str(target), staged_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
    default_off=True, objective_changed=False, dynamics_changed=False,
    production_modified=False, native_runs=0), indent=2)+'\n', encoding='utf8')
print('Staged opt-in VSL schedule audit; production and frozen source unchanged.')
