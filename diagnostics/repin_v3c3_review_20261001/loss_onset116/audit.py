"""Reuse closed-run 150s frames/predictions and existing 5s TTT summaries.

No new simulation, forecasts, fitting, or full FZP scan. Endpoint stock errors
are absolute prediction errors, not common-state policy-response estimates.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIOR=HERE.parent/'runtime7050_115'
read=lambda p:json.loads(p.read_bytes())
spec=importlib.util.spec_from_file_location('proof115',PRIOR/'prove_balance.py')
proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
bin_frame=proof.function(ROOT/'evaluation/controllers/lane_plant_runtime.py','bin_frame')
geometry=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
runs={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
      'sdmpc':Path('D:/VISSIM_runs/20261003_service66_queuezero_s29_9000/sdmpc')}
dec={arm:path/('decisions_sdmpc31_'+arm+'9000_s29') for arm,path in runs.items()}

def save(name,x):
    (HERE/name).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def write(name,rows):
    with (HERE/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not (HERE/'summary.json').exists(), 'Do not duplicate a completed audit'
    pins={}
    def pinned(p):
        data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
        return json.loads(data)
    frames={}; observations=[]; prediction=[]; commands=[]; frame_totals=[]
    for arm in runs:
        for t in range(900,7051,150):
            f=pinned(dec[arm]/f'lane_observations/frame_{t:06d}.json')
            assert f['complete'] and f['time_s']==t
            for road in ('FW_E','FW_W'):
                cells,bins,dropped=bin_frame(geometry,f['vehicles'],road,drop_before_start=True)
                assert len(cells)==31 and not dropped
                values=[]
                for i,b in enumerate(bins):
                    v=dict(arm=arm,time_s=t,road=road,cell=i,n=len(b),
                           speed_kph=statistics.mean(z[4] for z in b) if b else 0,
                           stopped_lt5=sum(z[4]<5 for z in b))
                    observations.append(v);values.append(v)
                frames[arm,t,road]=values
                frame_totals.append(dict(arm=arm,time_s=t,road=road,n=sum(v['n'] for v in values),
                    stopped_lt5=sum(v['stopped_lt5'] for v in values)))
    assert all(frames['nc',900,r]==[dict(v,arm='nc') for v in frames['sdmpc',900,r]]
               for r in ('FW_E','FW_W'))
    for t in range(900,6901,150):
        a=pinned(dec['sdmpc']/f'action_{t:06d}.json')
        p=a['prediction'];assert p['status']=='ok' and p['from_sim_sec']==t and p['target_sim_sec']==t+150
        for road in ('FW_E','FW_W'):
            predicted=p['state_summary']['freeway_segment_vehicles'][road]
            assert len(predicted)==31
            for i,n in enumerate(predicted):
                actual=frames['sdmpc',t+150,road][i]
                prediction.append(dict(from_s=t,target_s=t+150,road=road,cell=i,
                    initial_n=frames['sdmpc',t,road][i]['n'],predicted_n=n,
                    actual_n=actual['n'],error_pred_minus_actual=n-actual['n']))
        command=dict(time_s=t,NP=a['N_P_star'],NUF=a['N_UF_star'],
                     feasible=a['metadata']['sdmpc_constraints']['feasible'])
        command.update({k:v for k,v in a['diagnostics'].items() if k.startswith('rw_meter_green_')})
        for road in ('FW_E','FW_W'):
            commands_road={k:v for k,v in a['vsl'].items() if k.startswith(road+'__')}
            command[road+'_vsl']=json.dumps(commands_road,sort_keys=True)
        commands.append(command)
    # Native FZP-based per-link residence already computed by review115.
    metrics={a:pinned(PRIOR/f'partial7050/{a}/metrics.json') for a in runs}
    contributions=[]
    for link in metrics['nc']['physical_link_residence'].keys()|metrics['sdmpc']['physical_link_residence'].keys():
        x=metrics['nc']['physical_link_residence'].get(link,{});y=metrics['sdmpc']['physical_link_residence'].get(link,{})
        address=geometry['addresses'].get(link)
        contributions.append(dict(link=int(link),road=address[0] if address else 'other',inside=x.get('inside',y.get('inside')),
             nc=x.get('ttt_veh_h',0),sdmpc=y.get('ttt_veh_h',0),delta=y.get('ttt_veh_h',0)-x.get('ttt_veh_h',0)))
    contributions.sort(key=lambda r:abs(r['delta']),reverse=True)
    totals={a:list(csv.DictReader((PRIOR/f'partial7050/{a}/timeseries.csv').open(encoding='utf8'))) for a in runs}
    assert [r['sim_sec'] for r in totals['nc']]==[r['sim_sec'] for r in totals['sdmpc']]
    time_delta=[]
    for x,y in zip(totals['nc'],totals['sdmpc']):
        time_delta.append(dict(sim_sec=float(x['sim_sec']),delta_Omega_cum_veh_h=float(y['ttt_veh_h_cumulative'])-float(x['ttt_veh_h_cumulative']),
                              delta_Omega_stock=int(y['inside_vehicles'])-int(x['inside_vehicles']),
                              delta_network_stock=int(y['network_vehicles'])-int(x['network_vehicles'])))
    selected_times=[900,1200,1500,1800,2250,2700,3150,3600,4050,4500,5400,6300,7050]
    coarse=[]
    for t in selected_times:
        row=min(time_delta,key=lambda r:abs(r['sim_sec']-t)).copy()
        row['decision_s']=t
        for road in ('FW_E','FW_W'):
            for arm in runs:row[arm+'_'+road+'_n']=sum(v['n'] for v in frames[arm,t,road])
            row[road+'_delta_n']=row['sdmpc_'+road+'_n']-row['nc_'+road+'_n']
        coarse.append(row)
    cell_errors=[]
    for road in ('FW_E','FW_W'):
        for i in range(31):
            rows=[r for r in prediction if r['road']==road and r['cell']==i]
            errors=[r['error_pred_minus_actual'] for r in rows]
            cell_errors.append(dict(road=road,cell=i,mae=statistics.mean(abs(x) for x in errors),
                bias=statistics.mean(errors),worst=max(rows,key=lambda r:abs(r['error_pred_minus_actual']))))
    cell_errors.sort(key=lambda r:r['mae'],reverse=True)
    write('native_cells150.csv',observations);write('prediction150_errors.csv',prediction)
    write('commands.csv',commands);write('native_link_ttt.csv',contributions)
    write('native_Omega_time_delta.csv',time_delta);write('native_frame_totals.csv',frame_totals)
    save('pins.json',pins)
    summary=dict(previous_turn='PROGRESS: matched7050 TTT and proven runtime fix',
        qualification='Absolute first150 forecast/closed-loop history only, not isolated RM/VSL causal gain',
        runs={k:str(v) for k,v in runs.items()},new_native_runs=0,new_forecasts=0,new_fits=0,fzp_scans=0,
        time_checkpoints=coarse,largest_link_contributions=contributions[:18],
        largest_cell_prediction_errors=cell_errors[:16],
        all_selected_quantity_constraints_feasible=all(r['feasible'] for r in commands),
        rm_green_values={k:sorted({r[k] for r in commands}) for k in commands[0] if k.startswith('rw_meter_green_')},
        original_sources_preserved=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items()))
    assert summary['original_sources_preserved']
    save('summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('largest_cell_prediction_errors','largest_link_contributions')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
