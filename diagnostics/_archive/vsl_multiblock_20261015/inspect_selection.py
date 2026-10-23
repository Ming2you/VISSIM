import json
from pathlib import Path
p=Path(__file__).resolve().parent/'full_selection3300'
j=json.loads((p/'unused.joint.json').read_bytes())
s=j['selection']
print(json.dumps(dict(root_keys=list(j), selection_keys=list(s),
    completed=j['completed'],feasible=s['feasible'],converged=s['converged'],
    vsl_audit=s['vsl_schedule_audit'], final_constraints=s['final_constraints'],
    selected_objective=s['selected_objective'],held_objective=s['held_objective']),indent=2))
print((p/'unused.joint_written.json').read_text(encoding='utf8'))
