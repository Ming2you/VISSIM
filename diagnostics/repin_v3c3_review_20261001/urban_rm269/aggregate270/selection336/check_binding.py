"""One scalar witness that cache repair preserves the qualified prediction."""
from pathlib import Path
import copy,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.selection336.binding import refresh
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.selection336.worker_runner import evaluate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.worker334.assess import numeric_error
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade

HERE=Path(__file__).resolve().parent;W=HERE.parent/'worker334'
request=pickle.loads((W/'capture_v2/request.pickle').read_bytes())
f=request['owned'][0]
binding=refresh(f,f.cfg)
request['diagnostic_stock_costs']=False
request['surrogate_evaluation']='scalar'
request['surrogate_context_sha256']=hashlib.sha256(pickle.dumps((request['owned'],request['runtime'],request['bootstrap'],3),protocol=5)).hexdigest()
result=evaluate(request)
old=pickle.loads((W/'scalar/result.pickle').read_bytes())
before=copy.deepcopy(old['surrogate_prediction']);after=copy.deepcopy(result['surrogate_prediction'])
before.pop('diagnostic_stock_costs_veh_h')
for p in (before,after):p.pop('frozen_context_token')
check_scalar_upgrade(before,after,1e-7)
errors={k:numeric_error(old[k],result[k],k) for k in ('costs','resources')}
assert max(errors.values())<1e-7
record=dict(status='passed',binding=binding,max_difference=errors,
            scalar_forecasts=1,ad_forecasts=0,full_selection=0,new_fit=False,
            cached_beta_repaired_before_coupling=True)
(HERE/'binding_check.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps(record),flush=True)
