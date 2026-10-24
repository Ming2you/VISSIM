"""Evaluate completed, bounded predictions against cached native observations."""
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
I=HERE.parent
OUT=HERE/'physical_path_comparison'


def main():
    def read(p):return json.loads(p.read_bytes())
    assert read(OUT/'completion.json')['forecasts']==4
    target=OUT/'assessment.json';assert not target.exists()
    location=Path(read(OUT/'results_location.json')['output'])
    actual=read(HERE/'analysis/ramp_response_audit.json')['arms']
    native=read(HERE/'analysis/summary.json')
    base=I/'closedloop_recorded2250_lever450_RM_C10484_trace10484_of2'
    candidates={name:{arm:read(folder/(arm+'.json')) for arm in actual}
                for name,folder in [('baseline',base),('physical_path',location)]}
    native_cells={(r['arm'],int(r['sim_sec']),r['road'],int(r['cell'])):r for r in csv.DictReader(
        (HERE/'analysis/mainline_snapshots.csv').open(encoding='utf-8-sig'))}
    geometry=read(I/'selected/port_gain/geometry.json')
    cells=sorted([c for c in geometry['cells'] if c['road']=='FW_E'],key=lambda c:c['cell'])
    result={}
    for name,model in candidates.items():
        errors={};cost={}
        for arm,pred in model.items():
            r=actual[arm];first=pred['first_interval']['ramps']
            for ramp,p in pred['ramps'].items():
                a=r[ramp]['actual']
                assert abs(a['initial_stock']+p['arrival']-p['merge']-p['final_stock'])<1e-7
            err={k:sum(abs(pred['ramps'][ramp][k]-r[ramp]['actual'][k]) for ramp in r)
                 for k in ('arrival','merge','final_stock')}
            first_errors={k:sum(abs(first[ramp][k]-r[ramp]['actual']['windows'][0][k]) for ramp in r)
                          for k in ('arrival','head','merge','final_stock')}
            cell_err=[]
            for state in pred['physical_cell_states'][1:]:
                t=int(state['time_sec'])
                for c in cells:
                    i=c['cell'];a=native_cells[arm,t,'FW_E',i]
                    count=state['density']['FW_E'][i]*state['effective_lanes']['FW_E'][i]*c['length_km']
                    cell_err.append((abs(count-int(a['vehicles'])),abs(state['speed_kmh']['FW_E'][i]-float(a['speed_kph']))))
            errors[arm]=dict(ramp450_sum_abs_veh=err,first150_sum_abs_veh=first_errors,
                east31_three_snapshots_count_mae_veh=sum(x[0] for x in cell_err)/len(cell_err),
                east31_three_snapshots_speed_mae_kmh=sum(x[1] for x in cell_err)/len(cell_err),
                ramp10484=pred['ramps']['RM_C10484'])
            delta=pred['ttt_omega_veh_h']-model['held_actual']['ttt_omega_veh_h']
            cost[arm]=dict(predicted_delta_ttt=delta,actual_delta_ttt=native['comparisons'][arm]['delta_TTT_veh_h'],
                          delta_error=delta-native['comparisons'][arm]['delta_TTT_veh_h'])
        result[name]=dict(errors=errors,cost=cost,rank=sorted(cost,key=lambda a:cost[a]['predicted_delta_ttt']))
    report=dict(stage='complete_no_adoption',models=result,
        native_rank=sorted(actual,key=lambda a:native['comparisons'][a]['delta_TTT_veh_h']),
        new_forecasts=4,optimizer_iterations=0,coefficient_fits=0,new_native_runs=0,
        history_qualification_sha256=hashlib.sha256((HERE/'history_qualification.json').read_bytes()).hexdigest(),
        limitations=['Native response already known; this is a bounded assessment, not blind validation.',
                     'Original9000 raw-prefix reproduction remains failed.',
                     'One onset state with small native net effects; do not fit its signs or claim global RM/VSL inefficacy.'])
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(native_rank=report['native_rank'],models={k:dict(rank=v['rank'],cost=v['cost'],held_errors=v['errors']['held_actual']) for k,v in result.items()})))


if __name__=='__main__':main()
