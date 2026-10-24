"""Record the static choice mismatch and its old-table alias provenance."""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import physical_movement_routes as routes
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_path=ROOT/'outputs/movement_beta_routing_20260824.json'
old=read(old_path)
document,native,edges=routes.load_evidence((HERE/'physical_routes.json').relative_to(ROOT).as_posix())
initialized=read(HERE/'init2400_checked/network.json')
prior=read(HERE.parent/'sc6_queue/forecast2400_service/network.json')
groups={}
for key in ('SC12_S_SC16','SC16_S_SC109'):
    row=document['native_choice_groups'][key]
    total=sum(native[r]['weight'] for r in row['route_to_movement'])
    actual={m:native[r]['weight']/total for r,m in row['route_to_movement'].items()}
    observed={m:initialized['urban_movements'][m]['beta'] for m in actual}
    assert observed==actual
    groups[key]=dict(native_decision=row['decision'],native_routes={r:dict(path=native[r]['path'],weight=native[r]['weight']) for r in row['route_to_movement']},
        old_table={m:v for m,v in old['beta'].items() if m.startswith(key+'_')},
        before={m:prior['urban_movements'][m]['beta'] for m in actual},after=actual,
        total_route_weight=total,mode='Static prior only; no observed future flow used as a predictor')
assert abs(old['beta']['SC12_S_SC16_to_W']+old['beta']['SC12_S_SC16_to_W_SC11']-groups['SC12_S_SC16']['before']['SC12_S_SC16_to_W_SC11'])<1e-12
assert abs((old['beta']['SC16_S_SC109_to_W']+old['beta']['SC16_S_SC109_to_W_SC7'])/(1-old['beta']['SC16_S_SC109_to_S'])-groups['SC16_S_SC109']['before']['SC16_S_SC109_to_W_SC7'])<1e-12
files=[Path(__file__),old_path,ROOT/'scripts/derive_routing_turn_beta.py',ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
       ROOT/'evaluation/controllers/physical_movement_routes.py',HERE/'physical_routes.json',
       HERE.parent.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md',HERE.parent.parent/'sc105_supply/physical_routes.json']
out=HERE/'source_audit.json'
assert not out.exists()
out.write_text(json.dumps(dict(status='confirmed',groups=groups,old_table_source=old['source'],
    cause='Old generator reserves the mass of unreachable aliases; runtime merges/prunes them into physical choices. Complete current native RD ratios avoid that alias reserve.',
    precedent='Claude STAGE3 U1 complete physical beta and the existing local SC105 pinned native-choice repair.',
    production_code_changes=0,source_pins={str(p):sha(p) for p in files}),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Two complete native choice groups confirmed; old alias mass reproduced.')
