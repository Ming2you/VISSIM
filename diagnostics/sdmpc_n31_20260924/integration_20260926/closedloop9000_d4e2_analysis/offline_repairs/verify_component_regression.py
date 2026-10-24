"""Two saved seed53 component replays; no native, fitting or city-gain claim."""
import gzip
import hashlib
import json
from pathlib import Path

from evaluation.controllers.lane_plant_runtime import load_sources
from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
source=BASE/'heldout53_response_v2'
capture=json.loads((source/'capture.json').read_bytes())
context=load_sources(source/'candidate_manifest.json')
model=context['component']
results=[]
for arm in ('hold','release'):
    row=next(r for r in capture['records'] if r['arm']==arm)
    args,kwargs=read_primitive_capture(row['input'],row['sha256'])
    result=json.loads(json.dumps(model.rollout(*args,**kwargs),allow_nan=False))
    with gzip.open(source/'candidate'/(arm+'_prediction.json.gz'),'rt',encoding='utf-8') as f:
        old=json.load(f)
    keys=('cells','flows','ports','ramps')
    equal={key:result[key]==old[key] for key in keys}
    assert all(equal.values()), equal
    results.append(dict(arm=arm,physical_arrays_exact=equal,input_sha256=row['sha256']))
receipt=dict(results=results,new_native=0,coefficient_refit=False,
    scope='Canonical component unchanged: this is regression only, not validation of the coupled city destination repair.',
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(HERE/'seed53_component_regression.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt),flush=True)
