"""Audit the remaining frozen inlet split from current snapshots only."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from evaluation.controllers.lane_plant_runtime import bind_current_routes

HERE=Path(__file__).resolve().parent
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)

def main():
    output=HERE/'inlet_check.json';assert not output.exists()
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime'];gate=runtime['bounds']['FW_E'][9]
    result={}
    for seed,t,directory in [(43,2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        (47,2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
        raw=read(Path(directory)/f'state_{t:06d}.json')
        frame=read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
        raw=bind_current_routes(raw,{'frames':[frame]});routes=complete_vehicle_routes(raw,required=True)
        pools={key:defaultdict(lambda:[0.]*4) for key in ('previous_cell','current500_count','current500_speed_weight')}
        for v in complete_records(raw):
            if str(v['link_no']) not in runtime['physical']:continue
            road,x,cell=routing._position(runtime,v['link_no'],v['position_m'])
            if road!='FW_E' or x>=gate:continue
            selected=routes[v['veh_no']]
            if selected['route_decision_no'] is None:weights=routing._future_distribution(runtime,road,x,retain_route=True)
            else:
                key=f"{selected['route_decision_no']}:{selected['route_no']}"
                weights=routing._route_distribution(runtime,runtime['routes'][key],road,x,retain_route=True)
            for key,n in weights.items():
                target=key.rsplit('|',1)[-1];g=v['lane_no']-1
                if cell==8:pools['previous_cell'][target][g]+=n
                if gate-500<=x:
                    pools['current500_count'][target][g]+=n
                    pools['current500_speed_weight'][target][g]+=n*v['speed_kph']
        result[str(seed)]={k:{g:dict(weights=v,shares=[n/sum(v) for n in v] if sum(v) else [0.]*4) for g,v in pool.items()} for k,pool in pools.items()}
        print(seed,'terminal', {k:pool.get('terminal') for k,pool in result[str(seed)].items()})
    output.write_text(json.dumps(dict(cases=result,source_pins=PINS,
        conclusion='Current previous-cell sample freezes terminal/future downstream destinations to only3vehicles inseed47. A broad current window changes the lane allocation materially. Counterfactual profiles are not observed future boundary flows; autonomous validation is still required.',
        new_forecasts=0,new_native=0,new_fzp=0),ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
