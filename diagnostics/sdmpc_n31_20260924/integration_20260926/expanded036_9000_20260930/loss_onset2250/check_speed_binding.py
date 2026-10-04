"""Exercise the canonical recorded-state initializer; optionally run its existing probe."""
import ctypes
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
TARGET = HERE / 'speed_binding'
TARGET.mkdir(exist_ok=True)
mode, at = sys.argv[1], int(sys.argv[2])
assert mode in ('before', 'after', 'forecast') and at in (2250, 3600)
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)

from evaluation.controllers import obs150_contract as oc


def verify_existing(raw, derived):
    obs = raw[oc.RAW_STATE_KEY]
    path = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
    assert path.read_bytes() == oc.derived_bytes(derived)
    return path


oc.write_derived = verify_existing
helper = I / 'probe_selected_arrival_path.py'
spec = importlib.util.spec_from_file_location('binding_probe', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.probe_levers
tuning = I / 'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
config = json.loads(tuning.read_bytes())
manifest = json.loads((U/config['freeway']['lane_plant']).read_bytes())
pin = manifest['sources']['reference_config']
data = (U/pin['path']).read_bytes()
assert hashlib.sha256(data).hexdigest() == pin['sha256']
declared = json.loads(data)['freeway']['physical_ramp_travel_speeds']


def audit(captured, reference, output, **kwargs):
    state = captured['state']
    actual = {r:b.metadata() for r,b in state.lane_ramp_runtime.buffers.items()}
    checks = {r:actual[r]['travel_speed_kmh'] == v['upstream_kmh'] and
        actual[r].get('posthead_travel_speed_kmh', actual[r]['travel_speed_kmh']) == v['posthead_kmh']
        for r,v in declared.items()}
    report = dict(mode=mode,at=at,declared=declared,actual=actual,checks=checks,
        future_observation_inputs=False,native_started=False,
        source_sha256=hashlib.sha256((U/'evaluation/controllers/lane_plant_runtime.py').read_bytes()).hexdigest())
    (TARGET/f'{mode}_{at}_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert all(checks.values()), 'Declared upstream/post-head travel calibration did not reach live buffers'
    if mode == 'forecast':
        return original(captured,reference,output,**kwargs)
    print(json.dumps(dict(binding_pass=True,at=at,forecasts=0)))


module.probe_levers = audit
sys.argv = [str(helper),'--closedloop-recorded',f'--at={at}','--lever-probe450','--meter-ramp=RM_C10484',
    '--trace-ramp=RM_C10484','--warm-head-history','--replay-vsl-history',
    '--recording-dir=D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
    '--tuning-json='+str(tuning),f'--probe-label=bnd_{mode}_{at}']
if at == 3600 or mode != 'forecast':
    sys.argv.append('--held450')
module.main()
