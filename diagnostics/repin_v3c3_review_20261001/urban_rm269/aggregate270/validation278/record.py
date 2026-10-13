"""Record completed bounded checks only; does not modify production or native."""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())

def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

report=read(HERE/'review.json')
assert report['status']=='bounded_clock_checks_complete' and report['new_predictions']==3
plan=read(HERE/'plan.json')
plan.update(status='complete_clock_candidate_retained_not_whole_plant_qualified',
    updated_utc=datetime.now(timezone.utc).isoformat(),completed_predictions=3,
    completed_full_selections=0,current_workers=[],source_production_changes=0,
    evidence=['review.json','unseen3300_fw5_urban10/group_flux.json','README.md'],
    vsl_omega_direction_retained=report['vsl_omega_direction_retained'],
    next_step='Keep FW5/urban10 opt-in. Decompose native52+58 inflow/outflow from saved observations before changing dynamics. Do not repeat unchanged clock checks or full optimizer. Native queue untouched.')
save(HERE/'plan.json',plan)
previous_path=HERE.parent/'urban_clock277/plan.json'
previous=read(previous_path)
previous.update(additional_validation='../validation278/plan.json',
    next_step=plan['next_step'])
save(previous_path,previous)
print(plan['status'])
