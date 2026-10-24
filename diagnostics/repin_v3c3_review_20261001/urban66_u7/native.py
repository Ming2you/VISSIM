"""Completed native MER +150s snapshots, evaluation only; no FZP scan."""
import hashlib
import json
from pathlib import Path
from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(p):
    p=Path(p);b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)

def main():
    target=HERE/'native.json';assert not target.exists()
    roots={'47hold':Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47'),
           '47selected':Path('D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/decisions_sdmpc31_g_2700_selected_s47'),
           '43nc':Path(read(I/'seed43_fullplant_20260929/analysis_v2/observation_reuse.json')['recording_dir'])}
    result={}
    for case,folder in roots.items():
        start=2250 if case=='43nc' else 2700
        states=[];windows=[]
        for t in range(start,start+451,150):
            raw=read(folder/f'state_{t:06d}.json')
            rows=[r for r in raw['vehicle_records']['records'] if r['link_no']==66]
            states.append(dict(time_sec=t,link66_vehicles=len(rows),stopped=sum(r['stopped'] for r in rows),
                               by_lane={lane:sum(r['lane_no']==lane for r in rows) for lane in (1,2,3,4)},
                               connector10633_vehicles=sum(r['link_no']==10633 for r in raw['vehicle_records']['records'])))
            if t==start:continue
            pin=raw['obs150']['detector_config'];detectors,_=oc.read_detector_csv(pin['path'],pin['sha256'])
            targets={d.dcp_no:d for d in detectors if d.role=='head' and int(d.link)==66}
            assert len(targets)==4
            bundle=oc.load_bundle(raw)
            native={lane:[] for lane in (1,2,3,4)}
            for row in bundle.mer_rows:
                if row.dcp in targets and row.t_entry is not None and t-150<row.t_entry<=t:
                    native[targets[row.dcp].lane].append(dict(vehicle=row.veh,time_sec=row.t_entry))
            windows.append(dict(start_sec=t-150,end_sec=t,head_crossings={k:len(v) for k,v in native.items()},events=native))
        result[case]=dict(states=states,windows=windows)
    target.write_text(json.dumps(dict(cases=result,source_pins=pins,
        scope='Native head crossings after right-turn divergence. Lane1-3 approximate10631 and lane4 approximate10633 with a small spatial offset. 10632 pre-head right exits not counted. Observed stopped stock is not the same as model virtual point queue. No future values supplied to forecasts.'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({c:dict(stock=[s['link66_vehicles'] for s in v['states']],
        N=sum(sum(n for k,n in w['head_crossings'].items() if k<=3) for w in v['windows']),
        W=sum(w['head_crossings'][4] for w in v['windows'])) for c,v in result.items()}))

if __name__=='__main__':main()
