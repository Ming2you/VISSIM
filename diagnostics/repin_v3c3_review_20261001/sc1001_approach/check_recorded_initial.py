"""One local one-second structural check, not a coupled prediction or fit."""
import copy
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from evaluation import parameters
from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
NETWORK=I/'selected/network/native_seed29.inpx'
FRAME=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47/lane_observations/frame_002700.json')


def main():
    target=OUT/'recorded_initial.json'
    assert not target.exists()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(NETWORK)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    assert sha(FRAME)=='7058b319c57ffa37fc9136319e4f9eec2c857c358dcb2583a4921e4644f350f9'
    frame=json.loads(FRAME.read_bytes());tree=ET.parse(NETWORK).getroot()
    assert frame['time_s']==2700 and frame['complete']
    rows=[r for r in frame['vehicles'] if r[1]==127]
    heads={n.get('lane').split()[1]:float(n.get('pos')) for n in tree.findall('./signalHeads/signalHead')
           if n.get('lane').split()[0]=='127'}
    spacing=parameters.require('network','urban_avg_vehicle_length_m')
    service=parameters.require('network','movement_capacity_veh_h')
    speed=parameters.require('network','urban_avg_speed_km_h')
    lanes={lane:dict(capacity_veh=position/spacing,service_veh_h=service,
                    movements=('E','S') if lane=='1' else ('E',) if lane=='2' else ('N',))
           for lane,position in heads.items()}
    decision=tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1117']")
    route_exit={int(r.get('no')):{'10118':'E','10368':'S','10695':'N'}[r.find('./linkSeq/intObjectRef').get('key')]
                for r in decision.findall('./vehRoutSta/vehicleRouteStatic')}
    initial=[];evidence=[]
    for r in sorted(rows,key=lambda x:-x[3]):
        lane=str(r[2]);position=r[3]
        assert position<=heads[lane], 'Post-head vehicles need their downstream owner, not a second signal wait'
        if r[6]==1117 and r[8]=='STATIC':
            movement=route_exit[int(r[7])];source='initial_route_1117';mode='observed_static_exit'
        else:
            if r[6] is None:assert position>float(decision.get('pos'))
            else:assert (int(r[6]),int(r[7])) in ((1132,2),(1131,2),(1136,2))
            # Explicit test closure: lane-compatible continuation after the
            # reviewed route; not a recovered hidden route or fitted turn prior.
            movement='N' if lane=='3' else 'E';source='initial_continuation';mode='current_lane_continuation_closure'
        due=2700+math.ceil(max(0.,heads[lane]-position)/(speed/3.6))
        initial.append(dict(lane=lane,source=source,movement=movement,vehicles=1.,ready_sec=due))
        evidence.append(dict(vehicle=r[0],lane=lane,position_m=position,route=r[6:9],movement=movement,
                             binding=mode,ready_sec=due,needs_lane_change=movement not in lanes[lane]['movements']))
    # No future traffic is injected in this one-step initialization check.
    entries={'unused_probe':[dict(lane='1',movement='E',share=1.,delay_sec=1)]}
    approach=SharedSignalApproach(lanes,entries,initial,2700)
    assert len(rows)==69 and approach.stock()==69
    wrong=[e for e in evidence if e['needs_lane_change']]
    assert len(wrong)==2 and all(e['movement']=='S' for e in wrong)
    before={g:approach.stock(g) for g in lanes}
    # Both native groups are red during [2700,2701); verify the pinned program.
    manifest=json.loads((NETWORK.parent/'sig_manifest.json').read_bytes())
    sig=next(s for s in manifest['files'] if any(c['sc']=='1001' for c in s['controllers']))
    assert sha(NETWORK.parent/sig['name'])==sig['sha256']
    p=ET.parse(NETWORK.parent/sig['name']).getroot().find("./progs/prog[@id='1']")
    assert p.get('cycletime')=='150000' and p.get('offset')=='75000'
    assert [(c.get('display'),c.get('begin')) for c in p.findall("./sgs/sg[@sg_id='2']/cmds/cmd")]==[('3','0'),('1','48000')]
    assert [(c.get('display'),c.get('begin')) for c in p.findall("./sgs/sg[@sg_id='5']/cmds/cmd")]==[('3','48000'),('1','75000')]
    out=approach.advance(2700,dict.fromkeys(lanes,0.),dict(E=1.,S=1.,N=1.))
    assert out==[] and approach.stock()==69
    assert abs(approach.residence_veh_h-69/3600)<1e-12
    summary=dict(status='LOCAL_INITIALIZATION_AND_ONE_RED_STEP_PASS',frame=str(FRAME),frame_sha256=sha(FRAME),
        network_sha256=sha(NETWORK),signal_sha256=sig['sha256'],cutoff=2700,local_steps=1,
        full_network_forecasts=0,fit=0,native_runs=0,vehicles_before=69,vehicles_after=approach.stock(),
        lanes=lanes,initial_lane_stocks=before,final_lane_stocks={g:approach.stock(g) for g in lanes},
        known_wrong_lane_vehicles=wrong,lateral_transfers=approach.last_lateral,head_departures=out,
        residence_veh_h=approach.residence_veh_h,initial=evidence,
        closure='Nominal existing speed/service from parameters.py for structural check only; not calibrated head capacity.',
        limits=['Full-network stock migration, city/port arrival hooks, area/NP ledger and SDMPC rollout are not connected yet.',
                'Current-lane continuation for unresolved destinations is explicit approximation; no future route observations.',
                'Lateral space is lane-aggregate, not a validated microscopic gap acceptance model.'])
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k in ('status','vehicles_before','vehicles_after','local_steps','full_network_forecasts','known_wrong_lane_vehicles','lateral_transfers')}))


if __name__=='__main__':main()
