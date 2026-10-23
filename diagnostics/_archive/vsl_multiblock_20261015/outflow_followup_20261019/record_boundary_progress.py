"""Persist ownership and diagnostic progress without starting any process."""
import datetime,hashlib,json
from pathlib import Path
A=Path(__file__).resolve().parent;H=A.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert not (A/'refine_boundary_owner.json').exists()
audit=read(A/'refine15_residual_audit.json')
cells=next(x['cells'] for x in audit['training'] if x['label']=='fitted2' and x['start']=='all')
record=dict(status='running_bounded_boundary_identification',pid=15112,
    creation_utc='2026-10-19T03:55:47.5135840Z',exec_session=13530,
    recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_sha256=hashlib.sha256((A/'run_refine_boundary_fit.py').read_bytes()).hexdigest(),
    previous_goal_turn_classification='progress:38 finite calibration forecasts and8 independent predictions completed; transfer was not consistent',
    current_goal_turn_classification='progress:saved residual and sensitivity audit completed; finite boundary-response identification running',
    residual_outside_cell15_fraction=sum(x['error_share'] for x in cells if not x['cell'].startswith('15')),
    measured_local_tangent_removable_fraction=[x['unconstrained_tangent_removable_fraction'] for x in audit['tangent']],
    max_new_forecasts=16,max_parameter_updates=1,baseline_forecasts_reused=3,
    native_runs=0,production_edits=0,candidate_adopted=False,goal_complete=False,app_goal_status='active',automation_status='PAUSED',
    next='Poll exact existing exec session13530/PID15112 creation time. No duplicate or edits to active script. After normal exit, assess saved baseline/candidate and conditional VSL response once. Independent seed outcomes are never training targets. Retain previous failures, unchanged production and all native results. No native/grid/full optimization/push.')
save(A/'refine_boundary_owner.json',record)
for name in ('plan.json','summary.json'):
    path=H/name;d=read(path);d['boundary_identification_20261019']=record;d['next']=record['next'];save(path,d)
print(json.dumps(record,ensure_ascii=False,indent=2))
