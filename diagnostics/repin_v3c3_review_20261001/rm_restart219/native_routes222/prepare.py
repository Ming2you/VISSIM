"""Prepare a native1125 candidate using current pinned scenario sources."""
from pathlib import Path
import copy
import hashlib
import json
from evaluation.controllers import obs150_contract as oc

OUT=Path(__file__).resolve().parent
B=OUT.parent
ROOT=B.parents[2]

def read(p):return json.loads(p.read_bytes())
def save(name,data):
    p=OUT/name
    assert not p.exists(), p
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    d=read(B/'projection222v2/projection.json'); c=read(B/'config.json')
    k=read(ROOT/c['urban']['arrival']['kinematic_contract'])
    t=read(ROOT/c['urban']['movements']['physical_route_topology'])
    assert k['network']['sha256']==t['network']['sha256']
    assert all(hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in (k['network'],t['network']))
    k['network']=copy.deepcopy(t['network'])
    names={'1':'SC1004_N_SC1003_to_W','2':'SC1004_N_SC1003_to_S','3':'SC1004_N_SC1003_to_E_SC1005'}
    specs=d['movements'];w={'1':.75,'2':.125,'3':.125};connectors={'1':'10625','2':'10626','3':'10627'}
    group=dict(decision='1125',origin='SC1003_to_SC1004',signal='SC1004',stopline='46',
        route_to_movement={'1125:'+r:m for r,m in names.items()},
        expected_specs={m:{key:v for key,v in s.items() if key!='beta'} for m,s in specs.items()},
        rationale='Selected native1125 future prior; initial known choices retained separately. No capacity/demand fitting.')
    t['native_choice_groups']={'SC1004_N_SC1003':group}
    save('physical_routes.json',t)
    north=dict(link='46',native_choice_group='SC1004_N_SC1003',movements={m:dict(connector=connectors[r],expected_spec=dict(specs[m],beta=w[r])) for r,m in names.items()})
    k['sources']['SC1003_to_SC1004']=north
    k['native_choice_evidence_path']=(OUT/'physical_routes.json').relative_to(ROOT).as_posix()
    k['scope']='Existing kinematic ETA; selected1125 future priors and observed initial destinations. Independent congestion/gain validation pending.'
    save('contract.json',k)
    kt=copy.deepcopy(k);kt['sources']={'SC1003_to_SC1004':north}
    save('contract_test.json',kt)
    c['urban']['arrival']['kinematic_contract']=(OUT/'contract.json').relative_to(ROOT).as_posix()
    save('candidate_config.json',c)
    path=Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29/state_000900.json')
    raw=read(path);bundle=oc.load_bundle(raw)
    rows=[v for v in bundle.frame_end['vehicles'] if v[1]==46]
    save('fixture900.json',dict(projection=d['supports']['46'],queue=d['queue'],source_stock=d['source_stock'],arrivals=d['arrivals'],releases=d['releases'],
        records=[v for v in raw['vehicle_records']['records'] if v['link_no']==46],
        routes={str(v[0]):dict(veh_no=v[0],route_decision_no=int(v[6]),route_no=int(v[7]),route_decision_type=v[8]) for v in rows},network=k['network'],
        raw_state_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    print('Prepared native1125 diagnostic candidate; live config unchanged.')

if __name__=='__main__':main()
