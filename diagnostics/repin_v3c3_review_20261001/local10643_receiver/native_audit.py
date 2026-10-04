"""Saved complete frames only; future frames are evaluation, never model input."""
import collections
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def main():
    target=HERE/'native_audit.json'
    if target.exists():raise FileExistsError(target)
    contract=read(HERE.parent/'unrouted10646/route_contract.json')
    path=ROOT/contract['network']['path'];raw=path.read_bytes()
    pins[str(path)]=hashlib.sha256(raw).hexdigest()
    assert pins[str(path)]==contract['network']['sha256']
    xml=ET.fromstring(raw)
    decisions={int(d.get('no')):d for d in xml.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    route=decisions[1133].find("./vehRoutSta/vehicleRouteStatic[@no='2']")
    assert int(route.get('destLink'))==126
    decision_pos=float(decisions[1140].get('pos'))
    folders={
        '47hold':Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47/lane_observations'),
        '47selected':Path('D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/decisions_sdmpc31_g_2700_selected_s47/lane_observations'),
        '43nc':Path('D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43/lane_observations')}
    cases={};witnesses=[]
    local_links=(10643,10638,70,10776,126,10641,71,10700,10640)
    for case,folder in folders.items():
        snapshots=[]
        for t in ((2250,2400,2550,2700) if case=='43nc' else (2700,2850,3000,3150)):
            frame=read(folder/f'frame_{t:06d}.json')
            assert frame['complete'] and frame['time_s']==t
            rows=[v for v in frame['vehicles'] if v[1] in local_links]
            roads={str(link):dict(stock=sum(v[1]==link for v in rows),
                stopped=sum(v[1]==link and v[4]<5 for v in rows),
                lanes={str(lane):sum(v[1]==link and v[2]==lane for v in rows)
                       for lane in sorted({v[2] for v in rows if v[1]==link})}) for link in local_links}
            routes=collections.Counter((v[1],v[6],v[7]) for v in rows)
            snapshots.append(dict(time_sec=t,roads=roads,
                routes=[dict(link=k[0],decision=k[1],route=k[2],vehicles=n) for k,n in sorted(routes.items(),key=str)]))
            for v in rows:
                if v[6:8]==[1133.,2.] and ((v[1]==70 and v[3]>decision_pos) or v[1] in (10776,126)):
                    witnesses.append(dict(case=case,time_sec=t,vehicle=v[0],link=v[1],lane=v[2],position_m=v[3],speed_kmh=v[4]))
        cases[case]=snapshots
    assert witnesses
    result=dict(status='ACTIVE_1133_ROUTE_OBSERVED_PAST_1140_DECISION',
        geometry=dict(decision1140_link=70,decision1140_position_m=decision_pos,
                      route1133_2_dest_link=126,route1133_2_dest_position_m=float(route.get('destPos'))),
        cases=cases,active_route_witnesses=witnesses,source_pins=pins,
        limitations=['150s snapshots measure stocks, not direct continuous drainage.',
                     'Observed1133:2 continuation is not a claim that every10638 vehicle bypasses1140.',
                     'Future frames used only to evaluate the model, never to construct its forecast.'],
        new_native=0,new_fzp_scan=0)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('1133:2 retained past1140 witnesses',len(witnesses))
    for case,snapshots in cases.items():
        print(case,[(s['time_sec'],{k:v['stock'] for k,v in s['roads'].items() if k in ('10643','126','10641','71')}) for s in snapshots])

if __name__=='__main__':main()
