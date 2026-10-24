"""Decompose saved200/199 forecasts; native observations are labels only."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(p):
    data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

def main():
    assert not (HERE/'summary.json').exists()
    from evaluation.controllers import lane_plant_runtime,obs150_observation
    g=read(I/'selected/port_gain/geometry.json')
    mapping=read(I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/route_inventory/mapping31.json')
    geom=mapping['freeway_model_links']['FW_E']
    widths=geom['segment_lanes'];lengths=geom['segment_length_profile_km']
    assert g['network']['sha256']==mapping['network']['sha256']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    ports=[p for p in g['boundaries'] if p['road']=='FW_E']
    merges={p['id']:p['to_cell'] for p in ports if p['kind']=='ramp'}
    branches={str(p['connector']):p['from_cell'] for p in ports if p['kind']=='offramp'}
    assert len(merges)==len(branches)==4
    native_root=R/'replication_s73_95'
    native_summary=read(native_root/'analysis/summary.json')
    assert native_summary['counterfactual_valid'] and native_summary['paired_prefix_exact'] and native_summary['common_start_vehicle_records_exact']
    audit=read(I/'closedloop_recorded2700_lever450_s73_replication95/ramp_response_audit.json')
    labels=read(native_root/'snapshot_errors95.json')
    tuning=read(R/'rm47_service66_response/candidate_config.json')
    context=lane_plant_runtime.load_sources(tuning['freeway']['lane_plant'])
    flows=[];snapshots=[];max_residual=0.
    def reconcile(mode,arm,t,n0,n1,source,terminal,off,ramp):
        nonlocal max_residual
        assert len(n0)==len(n1)==31
        output=terminal
        rows=[]
        for c in reversed(range(31)):
            exited=sum(v for name,v in off.items() if branches[name]==c)
            entered=sum(v for name,v in ramp.items() if merges[name]==c)
            incoming=output+n1[c]-n0[c]+exited-entered
            assert incoming>=-1e-7 and output>=-1e-7,(mode,arm,t,c,incoming,output)
            rows.append(dict(mode=mode,arm=arm,start_sec=t,end_sec=t+150,cell=c,
                initial_n=n0[c],final_n=n1[c],mainline_in=incoming,mainline_out=output,
                merge=entered,off=exited))
            output=incoming
        residual=output-source
        assert abs(residual)<1e-7,(mode,arm,t,residual)
        max_residual=max(max_residual,abs(residual));flows.extend(reversed(rows))
    for arm in ('release','release_vsl90'):
        stock={t:[next(z['actual_stock'] for z in labels if z['arm']==arm and z['time_sec']==t and z['cell']==c)
                  for c in range(31)] for t in (2700,2850,3000,3150)}
        folder=Path('D:/VISSIM_runs/20261003_s73_vsl_replication95')/arm/f'decisions_sdmpc31_g_2700_{arm}_s73'
        for t in (2700,2850,3000):
            raw=read(folder/f'state_{t+150:06d}.json')
            d=obs150_observation.derive(raw,context['obs150'])
            assert d['window']==dict(start_s=t,end_s=t+150)
            off={o:d['boundaries']['off_entry:'+o]['cross'] for o in branches}
            ramp={name:next(w['merge'] for w in audit['arms'][arm][name]['actual']['windows'] if w['start_sec']==t) for name in merges}
            reconcile('native',arm,t,stock[t],stock[t+150],d['boundaries']['source:FW_E']['cross'],
                d['boundaries']['chain_end:FW_E']['cross'],off,ramp)
    protocols={'deployed':R/'heldout73_199/forecast_protocol.json','coupled':R/'coupled_lane200/enabled_protocol.json'}
    for mode,path in protocols.items():
        protocol=read(path);directory=Path(protocol['output']);summary=read(directory/'summary.json')
        assert not summary['future_observation_inputs'] and summary['optimizer_iterations']==0
        for arm in ('release','release_vsl90'):
            result=summary['results'][arm+'_actual']
            lane_profiles={s['time_sec']:s['effective_lanes']['FW_E'] for s in result['physical_cell_states']}
            for window in result['executed_intervals']:
                t=window['start_sec'];assert window['end_sec']==t+150
                first,last=window['physical_cell_states']
                n0,n1=(s['vehicle_count']['FW_E'] for s in (first,last))
                for s in (first,last):
                    assert max(abs(n-rho*l*w) for n,rho,l,w in zip(s['vehicle_count']['FW_E'],s['density']['FW_E'],lengths,lane_profiles[s['time_sec']]))<1e-7
                transfers=window['transfers']
                def amount(source=None,target=None):
                    return sum(r['vehicles'] for r in transfers if (source is None or r['source']==source) and (target is None or r['target']==target))
                off={o:amount('freeway:FW_E','storage:'+window['offramps'][o]['storage']) for o in branches}
                ramp={name:amount('merge_pending:'+name,'freeway:FW_E') for name in merges}
                reconcile(mode,arm,t,n0,n1,amount('origin:FW_E','freeway:FW_E'),
                    amount('freeway:FW_E','external:terminal:FW_E'),off,ramp)
                for c in range(31):
                    snapshots.append(dict(mode=mode,arm=arm,time_sec=t+150,cell=c,
                        speed_kmh=last['speed_kmh']['FW_E'][c],n=n1[c]))
    native_link=[]
    ma,mb=(read(native_root/f'analysis/{arm}/area_metrics.json') for arm in ('release','release_vsl90'))
    for link in geom['chain_links']:
        a,b=(m['physical_link_residence'][str(link)] for m in (ma,mb))
        assert a['inside'] and b['inside']
        native_link.append(dict(link=link,delta_ttt_veh_h=b['ttt_veh_h']-a['ttt_veh_h'],
            delta_slow_veh_h=b['slow_veh_h']-a['slow_veh_h']))
    deltas=[]
    for mode in ('native','deployed','coupled'):
        for t in (2700,2850,3000):
            for c in range(31):
                a,b=(next(r for r in flows if r['mode']==mode and r['arm']==arm and r['start_sec']==t and r['cell']==c) for arm in ('release','release_vsl90'))
                deltas.append(dict(mode=mode,start_sec=t,cell=c,**{k:b[k]-a[k] for k in ('initial_n','final_n','mainline_in','mainline_out','merge','off')}))
    for name,rows in [('cell_flows.csv',flows),('response_deltas.csv',deltas)]:
        with (HERE/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save('snapshots.json',snapshots)
    save('summary.json',dict(status='SAVED_RESPONSE_LEDGER_COMPLETE',previous_goal_turn='PROGRESS200 full coupling and response evaluation',
        native_link_deltas=native_link,balance_checks=18,max_abs_source_residual=max_residual,
        inferred_cell_windows=len(flows),new_forecasts=0,fits=0,new_native=0,FZP_reads=0,
        native_observation_files=6,goal='ACTIVE_NOT_QUALIFIED',production_adopted=False,
        limitations=['Native cell flows are NET transfers inferred from complete snapshots, port counters and adjacent-cell conservation, not newly tracked individual crossings.',
            'Native per-link cost difference cancels the verified identical pre2700 prefix; no per-cell native TTT is fabricated from link lengths.',
            'Use exported cell vehicle_count, retaining time-varying effective lanes. No cell TTT is inferred with constant lane widths from incomplete1s records.',
            'One common-state seed73 response; not proof of causal calibration or general RM/VSL qualification.'],input_sha256=pins))
    print(json.dumps(dict(native_link_deltas=native_link,max_residual=max_residual)))

if __name__=='__main__':main()
