"""Bounded offline lever attribution; use the existing canonical diagnostic."""
import ast
import ctypes
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

O = Path(__file__).resolve().parent
PS = O.parent.parent
I = PS.parent.parent.parent
helper = I/'probe_selected_arrival_path.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
old = json.loads((O.parent/'protocol.json').read_bytes())['source_pins']
assert sha(O/'probe_before.py.txt') == old[str(helper)]
for p,h in old.items():
    if Path(p) != helper:
        assert sha(p) == h, p
before = ast.parse((O/'probe_before.py.txt').read_text(encoding='utf-8'))
after = ast.parse(helper.read_text(encoding='utf-8'))
funcs = lambda tree: {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a,b = funcs(before),funcs(after)
assert a.keys() == b.keys()
changed = [k for k in a if a[k] != b[k]]
assert set(changed) == {'main','probe_selected_meter'}, changed
selection = I/'closedloop_recorded2700_select_ps47v1'
execution = I/'closedloop_recorded2700_select_check_ps47v1_resv3'
pins = {p:h for p,h in old.items() if Path(p) != helper}
for p in (helper,Path(__file__),O/'probe_before.py.txt',
          selection/'summary.json',selection/'unused_action.json',selection/'unused_action.joint.json',
          selection/'unused_action.joint_written.json',execution/'summary.json',
          Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')):
    pins[str(p)] = sha(p)
args = [str(helper),'--closedloop-recorded','--at=2700','--warm-head-history','--replay-vsl-history',
    '--selected-local-neighbors','--selected-local-factorial','--probe-label=ps47factor1',
    '--selection-reference='+str(selection),'--selection-execution-reference='+str(execution),
    '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
    '--fixed-replay-summary='+str(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
    '--tuning-json='+str((PS/'candidate_config.json').relative_to(Path.cwd()))]
protocol = dict(purpose='Fixed selected-city RM/VSL two-by-two attribution, model predictions only',
    new_cases=3,selected_parity_case=1,surrogate_budget=4,execution_budget=4,optimizer_budget=0,
    native_budget=0,fit_budget=0,first_vsl_block_only=True,history_read_only=True,
    fixed_caps=True,future_observed_inputs=False,source_pins=pins,argv=args,
    helper_functions_changed=changed,other_helper_functions_unchanged=len(a)-len(changed))
assert not (O/'protocol.json').exists(), 'Preserve completed or failed attempts'
(O/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
from evaluation.controllers import obs150_contract as oc
def verify_existing(raw,derived):
    obs = raw[oc.RAW_STATE_KEY]
    path = oc.resolve(obs,oc.derived_path(obs['sim_sec']))
    assert path.read_bytes() == oc.derived_bytes(derived)
    return path
oc.write_derived = verify_existing
spec = importlib.util.spec_from_file_location('lever_factorial_probe',helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.argv = args
started = time.perf_counter()
module.main()
assert all(sha(p) == h for p,h in pins.items())
output = I/'closedloop_recorded2700_budget_check_selected_local_ps47factor1'
summary = json.loads((output/'summary.json').read_bytes())
assert summary['surrogate_rollouts'] == summary['execution_rollouts'] == 4
assert summary['selected_surrogate_and_execution_reproduced']
assert summary['first_block_lever_factorial'] and summary['selected_budget_caps_frozen']
completion = dict(status='complete',output=str(output),wall_sec=time.perf_counter()-started,
    source_pins_unchanged=True,summary_sha256=sha(output/'summary.json'),
    surrogate_rollouts=4,execution_rollouts=4,optimizer_iterations=0,native_runs=0)
(O/'completion.json').write_text(json.dumps(completion,indent=2)+'\n',encoding='utf-8')
print(json.dumps(completion),flush=True)
