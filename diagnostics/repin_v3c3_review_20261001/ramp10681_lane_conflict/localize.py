"""Locate remaining lane errors using existing native snapshots and completed predictions."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def main():
    output=HERE/'localization.json';assert not output.exists()
    actual=read(HERE.parent/'entry10682/spatial.json')
    cases={}
    for seed,arm,prefix in [('43','nc','closedloop_recorded2250_lever450_trace10681_'),
                            ('47','hold','closedloop_recorded2700_select_check_trace10681_')]:
        folder=I/(prefix+'ramp10681_lane_conflict'+seed)
        tr=read(folder/'held_actual_RM_C10681_trace.json.gz')
        rows=[]
        for s in tr['offramp_network_diagnostics']['route_states']:
            for c in (9,10,11,12):
                obs=next(x for x in actual['cases'][seed+'_'+arm]['rows']
                         if x['time_sec']==s['time_sec'] and x['cell']==c)
                for lane in range(1,5):
                    native=obs['by_native_lane'].get(str(lane),{})
                    stock=s['inventory']['lane_cells']['FW_E'][c][lane-1]
                    rows.append(dict(time_sec=s['time_sec'],cell=c,lane=lane,
                        native_n=native.get('count',0),native_v=native.get('mean_speed'),
                        model_n=sum(stock.values()),model_v=s['lane_region']['speed'][str(c)][lane-1]))
        terms=tr['mainline_diagnostics']['speed_terms']
        mean_terms=[]
        for c in (9,10,11,12):
            for lane in range(1,5):
                selected=[x for x in terms if x['cell']==c and x.get('lane_index')==lane
                    and x.get('lane_equation')=='physical_lane' and x['time_sec']>=tr['end_sec']-150]
                assert len(selected)==150
                mean_terms.append(dict(cell=c,lane=lane,rows=len(selected),**{
                    k:sum(x[k] for x in selected)/len(selected) for k in
                    ('rho','downstream_rho','relaxation','convection','anticipation','post_equation_change','speed_final')}))
        cases[seed]=dict(snapshots=rows,last150_step_mean=mean_terms)
        print(seed,'final_lane2',[x for x in rows[-16:] if x['lane']==2])
        print(seed,'cell12_terms',[x for x in mean_terms if x['cell']==12])
    output.write_text(json.dumps(dict(cases=cases,source_pins=PINS,new_forecasts=0,new_native=0,new_fzp=0,
        limitation='Saved native snapshots are evaluation only; speed-term decomposition is descriptive, not causal substitution.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
