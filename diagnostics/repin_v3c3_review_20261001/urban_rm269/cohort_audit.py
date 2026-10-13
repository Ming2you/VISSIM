"""Read saved lane frames only; future frames are diagnostic targets, not inputs."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'goal8_265/spillback2000/coupling268/lane2400'
FRAMES = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/lane_observations')
net = json.loads((BASE/'network.json').read_bytes())
spec = net['known_legsplit_routes']
local = spec['entry_lane_receiving']
speed_floor = net['urban_avg_speed_km_h']/2.5
pins = {}

def frame(t):
    p = FRAMES/f'frame_{t:06}.json'
    raw = p.read_bytes()
    pins[str(p)] = hashlib.sha256(raw).hexdigest()
    f = json.loads(raw)
    assert f['complete'] and f['time_s'] == t
    return {r[0]:r for r in f['vehicles']}

rows=[]
for t in (1800,2400,3300,4500):
    initial=frame(t)
    snapshots={150:frame(t+150)}
    records=[]
    for vid,r in initial.items():
        if r[1] != 68 or r[8] != 'STATIC': continue
        route=spec['routes'].get(f'{int(r[6])}:{int(r[7])}',{})
        target=route.get('target','prechoice')
        eta=math.ceil((local['road_length_m']-r[3])/(max(speed_floor,r[4])/3.6))
        ahead=[p for p in initial.values() if p[1]==68 and p[2]==r[2] and p[3]>r[3] and p[4]<5
               and p[6]==1135 and p[7]==4]
        observations={str(dt):dict(link=snap[vid][1],lane=snap[vid][2],position=snap[vid][3],speed=snap[vid][4])
                      if vid in snap else None for dt,snap in snapshots.items()}
        records.append(dict(id=vid,target=target,lane=r[2],position=r[3],speed=r[4],eta_local_exit_sec=eta,
                            stopped_ramp_vehicles_ahead=len(ahead),future_diagnostic=observations))
    nonramp=[r for r in records if r['target'] in ('free','RM_C10646')]
    rows.append(dict(sim_sec=t,initial68=len(records),nonramp=len(nonramp),
        nonramp_stopped=sum(r['speed']<5 for r in nonramp),
        nonramp_stopped_with_ramp_ahead=sum(r['speed']<5 and r['stopped_ramp_vehicles_ahead']>0 for r in nonramp),
        past_eta_still68={str(dt):sum(r['eta_local_exit_sec']<=dt and r['future_diagnostic'][str(dt)] is not None
                        and r['future_diagnostic'][str(dt)]['link']==68 for r in nonramp) for dt in snapshots},
        records=records))
out=dict(scope='Same vehicle ID local68 survival. Future frames diagnose error only. No causal RM counterfactual or FIFO proof.',
         speed_floor_kph=speed_floor,rows=rows,source_pins=pins)
(HERE/'cohort_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps([{k:v for k,v in r.items() if k!='records'} for r in rows],indent=2))
