"""Current-only66 destination audit against saved model initialization.

No fit, rollout, config change, future routes, native run or FZP scan.
Reuses the native route parser and selected-network evidence contract.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.physical_movement_routes import load_evidence

F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)

contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/urban66_u7/contract.json')
evidence_path='diagnostics/repin_v3c3_review_20261001/rm_restart219/native_routes222/physical_routes.json'
evidence,routes,edges=load_evidence(evidence_path)
assert evidence['network']['sha256']==contract['network']['sha256']
read(ROOT/evidence_path)
pins[str(ROOT/evidence['network']['path'])]=evidence['network']['sha256']
names={'1124:1':'SC1004_S_to_W','1124:2':'SC1004_S_to_N_SC1003','1124:3':'SC1004_S_to_E_SC1005'}
spec=contract['sources']['in_SC1004_S']
assert set(names.values())==set(spec['movements'])
weights={m:routes[rid]['weight'] for rid,m in names.items()}
for rid,m in names.items():
    route=routes[rid]
    assert route['path'][:2]==['66',spec['movements'][m]['connector']]
    assert all(edge in edges for edge in zip(route['path'],route['path'][1:]))
    assert route['weight']>0
decision_pos=float(routes['1124:1']['decision']['pos'])
rows=[]
for at,leaf in ((1800,'local1800'),(2400,'local2400_v2'),(3300,'local3300'),(4500,'local4500')):
    state=read(HERE/leaf/'state.json')
    net=read(HERE/leaf/'network.json')
    frame=read(F/'lane_observations'/f'frame_{at:06}.json')
    assert frame['complete'] and frame['time_s']==at
    vehicles=[v for v in frame['vehicles'] if v[1]==66]
    named=dict.fromkeys(names.values(),0.)
    prechoice=[];unsupported=[]
    for v in vehicles:
        rid=f'{int(v[6])}:{int(v[7])}' if v[6] is not None and v[7] is not None else None
        if v[8]=='STATIC' and rid in names:named[names[rid]]+=1
        elif v[3]<decision_pos:prechoice.append(v[0])
        else:unsupported.append(v[0])
    initial=dict.fromkeys(names.values(),0.)
    assert not unsupported, ('Missing supported route after decision',at,unsupported)
    for m in initial:
        initial[m]=state['urban_movement_queue'].get(m,0.)+sum(
            tag.get(m,0.) for tag in state['gate_initial_route_tags']['in_SC1004_S'].values())
    assert abs(sum(initial.values())-len(vehicles))<1e-7
    # Separate the exactly known routes from the honest prior for predecision
    # vehicles. Never redraw a known destination from current lane or beta.
    known_plus_prior={m:named[m]+len(prechoice)*weights[m]/sum(weights.values()) for m in initial}
    assert abs(sum(known_plus_prior.values())+len(unsupported)-len(vehicles))<1e-7
    rows.append(dict(at=at,initial_vehicles=len(vehicles),known=sum(named.values()),
        predecision=len(prechoice),unsupported_after_decision=unsupported,
        known_current_destinations=named,model_initial_destinations=initial,
        known_plus_native_prior=known_plus_prior,
        model_minus_known_plus_prior={m:initial[m]-known_plus_prior[m] for m in initial},
        current_beta={m:net['urban_movements'][m]['beta'] for m in initial}))
result=dict(schema='urban66-current-route-audit/v1',rows=rows,
    scope='Current destination composition only. Different receiving supply/ETA and actual head discharge still require testing; no causal gain claim.',
    existing_implementation='observation_projection native_choice_group optional path added by REVIEW222; current66 contract does not activate it.',
    claude_history='Claude U7 and prior urban66_service/native_routes222 reports reviewed; do not repeat kinematic/service fixes or infer gains from inventory alone.',
    source_pins=pins)
(HERE/'urban66_route_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
