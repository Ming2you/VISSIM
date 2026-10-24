"""Run only the existing matched seed47 pair with the bounded candidate."""
import contextlib
import ctypes
import json
from pathlib import Path
import runpy
import sys
import time

from evaluation.controllers import obs150_contract as oc

O=Path(__file__).resolve().parent;L=O.parent
for stage in ('2250','3600'):
    assert json.loads((O/f'assessment_{stage}.json').read_bytes())['physical_screen_passed']

def readonly(raw,derived):
    obs=raw[oc.RAW_STATE_KEY];p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
    assert p.read_bytes()==oc.derived_bytes(derived)
    return p

oc.write_derived=readonly
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
args=(L/'head10490_timing/response/invocation47.txt').read_text(encoding='utf-8').splitlines()
args=[('--tuning-json='+str((O/'candidate_config.json').relative_to(Path.cwd())) if a.startswith('--tuning-json=') else
       '--probe-label=clock_ind47_20261001' if a.startswith('--probe-label=') else a) for a in args]
assert args.count('--lever-probe450')==1
(O/'invocation47.txt').write_text('\n'.join(args)+'\n',encoding='utf-8')
sys.argv=args
started=time.perf_counter()
with (O/'run47.log').open('x',encoding='utf-8',buffering=1) as log:
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        runpy.run_path(args[0],run_name='__main__')
(O/'run47_completion.json').write_text(json.dumps(dict(status='complete',wall_total_sec=time.perf_counter()-started,
    forecasts=2,new_native=0,fit=0,optimizer_iterations=0),indent=2)+'\n',encoding='utf-8')
