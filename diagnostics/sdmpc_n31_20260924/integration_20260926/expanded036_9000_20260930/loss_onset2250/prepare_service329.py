"""Pin a single observed-head ownership candidate, using no future traffic."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

L = Path(__file__).resolve().parent
I = L.parent.parent
U = I.parents[2]
OUT = L/'service329'
OUT.mkdir(exist_ok=False)
pins = {}
def read(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest();return raw
def pin(p):
    return dict(path=str(p.relative_to(U)),sha256=hashlib.sha256(read(p)).hexdigest())
def write(name,doc):
    (OUT/name).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

base=json.loads(read(L/'city_path/head_lane_config.json'))
source=U/base['urban']['capacity']['head_resource_contract']
contract=json.loads(read(source))
assert contract['schema']=='physical-head-resource-join/v6'
contract['schema']='physical-head-resource-join/v7'
proof=L/'city_path/head_lane_support.json'
lane=json.loads(read(proof))
network=U/contract['network']['path']
tree=ET.fromstring(read(network))
assert pins[str(network)]==contract['network']['sha256']==lane['network']['sha256']
through='SC1002_E_SC101_to_W_SC1001';right='SC1002_E_SC101_to_N_SC2004'
authority=json.loads(read(U/lane['authority']['path']))['network']
heads=[]
for head in tree.findall('./signalHeads/signalHead'):
    road,ln=head.get('lane').split();sc,sg=head.get('sg').split()
    if road=='329' and sg=='6':
        heads.append(dict(head_id=head.get('no'),link=road,lane=int(ln),position_m=float(head.get('pos')),sc=sc,sg=sg))
assert {h['lane'] for h in heads}=={2,3}
decision=tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1113']")
route=decision.find("./vehRoutSta/vehicleRouteStatic[@no='2']")
path=[decision.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
assert path[-3:]==['329','10692','73']
mapping=U/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
contract['resources']['10691']=dict(group='329|p3',heads=heads,mode='regular_unique',
    members={through:lane['movements'][through]['expected_spec']},receiver='SC1002_to_SC1001',
    target_link='29',proof=pin(proof),disjoint_consumers={right:dict(
        expected_spec={**lane['movements'][right]['expected_spec'],'turn':'right'},
        path=path[-3:],native_route='1113:2',native_route_path=path,destination_mapping=pin(mapping))})
contract['scope']='Existing v6 plus329 lanes2/3 SG6 ->10691->29. The disjoint lane1 right turn receives no SG6 throughput. No new rate/pool parameter.'
contract['diagnostic_source']=pin(source)
write('head_resources.json',contract)
base['urban']['capacity']['head_resource_contract']=str((OUT/'head_resources.json').relative_to(U))
write('candidate_config.json',base)
source=U/'evaluation/controllers/head_service_resources.py'
(OUT/'head_service_resources.before.py.txt').write_bytes(read(source))
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
observations=[]
for at in range(1800,3751,150):
    derived=json.loads(read(D/f'obs150/derived_{at:06d}.json'))['head_window']
    rows=[r for r in derived['heads'] if r['link']=='329' and r['sg']=='6']
    action=json.loads(read(D/f'action_{at:06d}.json'))
    meta={k:v for k,v in action['metadata'].items() if k.startswith(('head_discharge_floor_329_p3','head_candidate_rate_329_p3'))}
    observations.append(dict(end=at,heads=rows,metadata=meta,
        achieved_rate=sum(3600*r['qualified_crossings']/r['green_sec'] if r['green_sec'] else 0 for r in rows)))
write('past_observations.json',dict(rows=observations,scope='Saved native observations. Forecast at t only replays windows ending <=t; later rows are retrospective diagnosis only.'))
write('protocol.json',dict(pins=pins,forecasts_budget=2,states=[2250,3600],candidate_count=1,
    controls='same held commands',previous_goal_turn='progress',new_native=0,fzp_scans=0,
    forbidden='No saturation-rate fitting, future traffic input, production adoption or live CTG polling.'))
print(json.dumps({'contract':'v7','head_lanes':[h['lane'] for h in heads],
    'rows':[{'end':r['end'],'achieved_rate':r['achieved_rate'],'metadata':r['metadata']} for r in observations]}))
