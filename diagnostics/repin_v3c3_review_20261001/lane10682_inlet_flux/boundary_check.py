"""Read existing complete native snapshots to test the cell12/13 lane-average hypothesis."""
import hashlib
import json
from pathlib import Path
from evaluation.controllers.offramp_routing import _position
from evaluation.controllers.projection_support import complete_records

HERE=Path(__file__).resolve().parent
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    output=HERE/'boundary_check.json';assert not output.exists()
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    bounds=runtime['bounds']['FW_E']
    cases={}
    for seed,at,directory in [('43',2250,'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        ('47',2700,'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
        rows=[]
        for time in range(at,at+451,150):
            raw=read(Path(directory)/f'state_{time:06d}.json');assert raw['sim_sec']==time
            groups={c:[[] for _ in range(4)] for c in (12,13,14)}
            for vehicle in complete_records(raw):
                if str(vehicle['link_no']) not in runtime['physical']:continue
                road,x,cell=_position(runtime,vehicle['link_no'],vehicle['position_m'])
                if road=='FW_E' and cell in groups:
                    groups[cell][vehicle['lane_no']-1].append(vehicle['speed_kph'])
            for cell,lanes in groups.items():
                length=(bounds[cell+1]-bounds[cell])/1000
                average=sum(len(lane) for lane in lanes)/(4*length)
                for lane,values in enumerate(lanes,1):
                    rows.append(dict(time_sec=time,cell=cell,lane=lane,n=len(values),
                        rho=len(values)/length,aggregate_rho=average,
                        speed=sum(values)/len(values) if values else None))
        cases[seed]=rows
        print(seed,'final lane2',[x for x in rows[-12:] if x['lane']==2])
    output.write_text(json.dumps(dict(cases=cases,source_pins=PINS,
        purpose='Evaluation-only lane13 density check; no measured future density enters forecasts.',
        new_forecasts=0,new_native=0,new_fzp=0),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
