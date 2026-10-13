"""Connect existing current-destination initialization to selected native1124.

Scenario evidence/config only; no production code, native network or live queue
is edited. The current native decision has equal weights, not legacy beta.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.physical_movement_routes import load_evidence
read=lambda p:json.loads(p.read_bytes())
OUT=HERE/'route66'
OUT.mkdir(exist_ok=False)
cfg=read(HERE/'config_candidate.json')
k=read(ROOT/cfg['urban']['arrival']['kinematic_contract'])
evidence=read(ROOT/cfg['urban']['movements']['physical_route_topology'])
_,routes,_=load_evidence(cfg['urban']['movements']['physical_route_topology'])
assert k['network']['sha256']==evidence['network']['sha256']
k['network']=copy.deepcopy(evidence['network'])
source=k['sources']['in_SC1004_S']
names={'1124:1':'SC1004_S_to_W','1124:2':'SC1004_S_to_N_SC1003','1124:3':'SC1004_S_to_E_SC1005'}
specs=read(HERE/'local2400_v2/network.json')['urban_movements']
weights={m:routes[r]['weight'] for r,m in names.items()}
assert set(weights.values())=={1.0}
group='SC1004_S_native1124'
evidence['native_choice_groups']={group:dict(decision='1124',origin='in_SC1004_S',
    signal='SC1004',stopline='66',route_to_movement=names,
    expected_specs={m:{key:v for key,v in specs[m].items() if key!='beta'} for m in names.values()},
    rationale='Current native destination retention and native prior for as-yet uncommitted vehicles; not a fitted routing ratio.')}
source['native_choice_group']=group
for m,row in source['movements'].items():
    row['expected_spec']=dict(specs[m],beta=weights[m]/sum(weights.values()))
k['native_choice_evidence_path']=(OUT/'physical_routes.json').relative_to(ROOT).as_posix()
k['scope']='Existing U7 ETA plus native1124 current destinations and equal future priors. Lane gap/service dynamics unchanged; not native benefit validation.'
cfg['urban']['arrival']['kinematic_contract']=(OUT/'contract.json').relative_to(ROOT).as_posix()
for name,doc in [('physical_routes.json',evidence),('contract.json',k),('config.json',cfg)]:
    (OUT/name).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
plan=dict(status='prepared_not_activated',reason='4 current frames show known right-turn vehicles redrawn into through movement',
    existing_code='observation_projection native_choice_group; REVIEW222 implementation reused',
    budget=dict(initialization_checks=2,first150_forecasts_max=2,full_selection_max=0,native_launches=0),
    states=[2400,3300],
    gates=['Match native current destinations and preserve initial Omega and all ramp stocks',
           'Check unchanged total boundary demand, original physical source/receiver and non-target config',
           'Replay same first150 executed command, validate conservation and local discharge with new gate transit included',
           'No fitting loop and no claim of RM/VSL gain from inventory correction alone'],
    config=(OUT/'config.json').relative_to(ROOT).as_posix(),
    source_pins={str((OUT/n).relative_to(ROOT)).replace('\\','/'):hashlib.sha256((OUT/n).read_bytes()).hexdigest()
                 for n in ('config.json','contract.json','physical_routes.json')})
(OUT/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Prepared bounded native1124 candidate; production and frozen queue unchanged.')

