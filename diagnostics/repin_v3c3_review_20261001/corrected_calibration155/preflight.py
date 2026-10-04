"""Check source/config/cache equivalence before the bounded155 calibration."""
import ast
from pathlib import Path
from evaluation.controllers import lane_plant_runtime as lpr
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common

out = Path(__file__).resolve().parent
assert not (out/'status.json').exists(), 'Do not preflight over an active or finished fit'
before = (out/'helper_before.py.txt').read_text(encoding='utf-8')
after = Path(h.__file__).read_text(encoding='utf-8')
def fs(s):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
a,b = fs(before),fs(after)
assert a.keys() == b.keys()
assert all(a[k] == b[k] for k in a if k != 'calibrate_response127')
source = h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
assert source == h.spatial_context148_source(h.spatial_speed144_source(h.read(h.R/'junction_fifo124/dynamic/executed_function_sources.json')))
preservation = h.read(h.R/'spatial_context148/forecast/preservation.json')
for p,digest in preservation['input_sha256'].items(): assert h.sha(p) == digest,p
protocol = h.read(h.R/'spatial_context148/forecast/protocol.json')
for p,digest in protocol['protected_sha256'].items(): assert h.sha(p) == digest,p
assert h.sha(protocol['STOP']['path']) == protocol['STOP']['sha256']
context,replay,Obs = common.setup()
manifest = h.R/'lane_state132/eval_01/manifest.json'
assert protocol['manifest'] == str(manifest)
model = lpr.load_sources(manifest)['component']
catalog = h.read(h.C/'data_catalog.json')['checked_records']
records = [r for r in catalog if r['case'] == 's29_late']+common.records(False)
prior = {(r['case'],r['arm']):r for r in h.read(h.R/'spatial_context148/forecast/training/rows.json')}
checks = []
for r in records:
    p = h.R/'spatial_context148/forecast/training'/(r['case']+'_'+r['arm']+'.json.gz')
    pred = h.read(p)
    row = replay._cellwise_measure(model,pred,r,Obs(r['truth']))
    for k in ('actual','predicted','conservation_max'):
        assert row[k] == prior[(r['case'],r['arm'])][k],(r['case'],r['arm'],k)
    checks.append(dict(case=r['case'],arm=r['arm'],sha256=h.sha(p)))
h.save(out/'preflight.json',dict(status='pass',helper_sha256=h.sha(h.__file__),other_functions_unchanged=len(a)-1,
    physical_source_exact148=True,cached_baseline_checks=checks,forecast_count=0,protected_files=True,STOP=True,
    budget_new450=90,training_new450=80,coefficient_axes=4,
    previous_failed_fixture="AttributeError: helper module has no attribute lpr; use the existing controller module import. Zero model forecasts before repair."))
(out/'executed_helper.py.txt').write_text(after,encoding='utf-8')
print('PREFLIGHT PASS: source148,',len(checks),'cached outcomes,',len(a)-1,'unmodified helper functions; no forecasts')
