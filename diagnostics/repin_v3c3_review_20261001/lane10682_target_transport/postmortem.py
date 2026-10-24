"""Saved endpoints only: locate false queues after fixing exit class access."""
import gzip
import hashlib
import json
from pathlib import Path
from evaluation.controllers import offramp_routing as routing
from evaluation.controllers.projection_support import complete_records

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def main():
    output=HERE/'postmortem.json';assert not output.exists()
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    cases={}
    for seed,name,directory in [(43,'closedloop_recorded2250_lever450_trace10681_lane10682_target43',
        'D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43'),
        (47,'closedloop_recorded2700_select_check_trace10681_lane10682_target47v2',
        'D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')]:
        trace=read(I/name/'held_actual_RM_C10681_trace.json.gz')
        rows=[]
        for state in trace['offramp_network_diagnostics']['route_states']:
            time=state['time_sec'];raw=read(Path(directory)/f'state_{int(time):06d}.json')
            assert raw['sim_sec']==time
            observed={i:[[] for _ in range(4)] for i in (9,10,11,12)}
            for v in complete_records(raw):
                if str(v['link_no']) not in runtime['physical']:continue
                road,x,cell=routing._position(runtime,v['link_no'],v['position_m'])
                if road=='FW_E' and cell in observed:
                    observed[cell][v['lane_no']-1].append(v['speed_kph'])
            lane=state['inventory']['lane_cells']['FW_E']
            for cell in observed:
                for g in range(4):
                    native=observed[cell][g]
                    row=dict(time_sec=time,cell=cell,lane=g+1,native_n=len(native),
                        native_speed=sum(native)/len(native) if native else None,
                        model_n=sum(lane[cell][g].values()),model_speed=state['lane_region']['speed'][str(cell)][g],
                        model_target10643=sum(n for k,n in lane[cell][g].items() if k.endswith('|10643')),
                        model_target10682=sum(n for k,n in lane[cell][g].items() if k.endswith('|10682')))
                    if state is trace['offramp_network_diagnostics']['route_states'][0]:
                        assert abs(row['model_n']-len(native))<1e-7
                        if native:assert abs(row['model_speed']-row['native_speed'])<1e-7
                    rows.append(row)
        cases[str(seed)]=rows
        final=rows[-16:]
        print(seed,'end',json.dumps(final,ensure_ascii=False))
        assert sum(r['model_target10643'] for r in final if r['cell']==9 and r['lane'] in (3,4))<1e-9
    output.write_text(json.dumps(dict(cases=cases,source_pins=PINS,
        initial_lane_stock_and_speed_exact=True,inaccessible10643_final_zero=True,
        new_forecasts=0,new_fzp=0,new_native=0,
        limitations=['150-second snapshots localize remaining error but cannot identify its causal speed term.',
            'Future observations are evaluation-only; no future boundary is fed to a prediction.']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
