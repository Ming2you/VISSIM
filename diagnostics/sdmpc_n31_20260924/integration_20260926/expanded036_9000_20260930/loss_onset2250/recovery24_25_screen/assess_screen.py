"""Apply prespecified two-state criteria before inspecting independent response."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def close(a,b,label):assert abs(a-b)<1e-7,(label,a,b)
def main():
    assert not (O/'frozen_selection.json').exists()
    protocol=read(O/'protocol.json');assert read(O/'run_status.json')['status']=='complete'
    native=read(L/'mainline_balance/summary.json')
    terms_base=read(L/'mainline_balance/terms_verification.json')
    base_rows=list(csv.DictReader((L/'mainline_balance/cells.csv').open(encoding='utf-8')))
    geo=read(I/'selected/port_gain/geometry.json')
    cells=[c for c in geo['cells'] if c['road']=='FW_E']
    ports=[b for b in geo['boundaries'] if b['road']=='FW_E' and b['kind'] in ('ramp','offramp')]
    summaries={};cell_rows=[];times={}
    for label in protocol['candidates']:
        manifest=read(O/label/'manifest.json')
        component_parameters=read(Path(manifest['sources']['parameters']['path']))
        critical_multiplier=component_parameters['parameters']['by_direction']['FW_E']['rho_crit_multiplier']
        metrics=[]
        for start in protocol['fixed_initial_states']:
            tag=label+'r1'
            r=read(I/f'closedloop_recorded{start}_lever450_RM_C10484_city{start}_ps_all8_{tag}/held_actual.json')
            baseline=read(I/f'closedloop_recorded{start}_lever450_RM_C10484_city{start}_ps_all8_clockcandidate/held_actual.json')
            assert r['commands']==baseline['commands'] and r['physical_cell_states'][0]==baseline['physical_cell_states'][0]
            assert r['validation']['all_actuator_and_step_constraints_checked']
            assert max(abs(x['residual']) for x in r['ramps'].values())<1e-7
            times[f'{label}_{start}']=r['wall_sec']
            trace=read(L/f'city_path/{start}_ps_all8_{tag}/trace.json.gz')
            terms=read(L/f'city_path/{start}_ps_all8_{tag}/mainline_terms.json.gz')
            assert len(terms)==1350
            # Verify actual effective coefficient changes, not just JSON contents.
            for c in (24,25):
                first=next(x for x in terms if x['cell']==c and x['time']==start)
                old=next(x for x in terms_base['rows'] if x['cell']==c and x['start']==start)['first_step']
                if label=='fd125':
                    close(first['critical'],protocol['candidates'][label]['after'][str(c)]['rho_crit']*critical_multiplier,'effective critical')
                    close(first['tau_sec'],old['tau_sec'],'unchanged tau')
                else:
                    close(first['tau_sec'],old['tau_sec']*2,'effective tau')
                    close(first['nu']/first['tau_sec'],old['nu']/old['tau_sec'],'nu/tau retained')
                    close(first['desired'],old['desired'],'same initial target')
            transfers={}
            for x in trace['transfers']:
                if start<=x['start_sec']<start+150:
                    key=(x['source'],x['target']);transfers[key]=transfers.get(key,0)+x['vehicles']
            def flow(a,b):return transfers.get((a,b),0.)
            port={}
            for b in ports:
                if b['kind']=='ramp':port[b['id']]=flow('merge_pending:'+b['id'],'freeway:FW_E')
                else:port[b['id']]=flow('freeway:FW_E','storage:'+('lane_off_'+str(b['connector']) if b['branch']=='direct' else b['group']+'_storage'))
            ns=[[rho*lane*c['length_km'] for rho,lane,c in zip(s['density']['FW_E'],s['effective_lanes']['FW_E'],cells)] for s in r['physical_cell_states'][:2]]
            base=[x for x in base_rows if int(x['start'])==start and x['model']=='candidate']
            assert len(base)==31
            source=flow('origin:FW_E','freeway:FW_E');q=source;local=[]
            for c in range(31):
                q+=sum((1 if b['kind']=='ramp' else -1)*port[b['id']] for b in ports if b['to_cell' if b['kind']=='ramp' else 'from_cell']==c)
                q-=ns[1][c]-ns[0][c]
                row=dict(label=label,start=start,cell=c,native_n=float(base[c]['native_n1']),model_n=ns[1][c],stock_error=ns[1][c]-float(base[c]['native_n1']),
                    native_out=float(base[c]['native_downstream']),model_out=q,out_error=q-float(base[c]['native_downstream']))
                cell_rows.append(row);local.append(row)
            close(q,flow('freeway:FW_E','external:terminal:FW_E'),'terminal conservation')
            close(source,next(w for w in native['windows'] if w['start']==start)['model']['candidate']['source'],'source unchanged')
            target_stock=sum(abs(local[c]['stock_error']) for c in (24,25))
            baseline_stock=sum(abs(float(base[c]['stock_error'])) for c in (24,25))
            target_out=abs(local[25]['out_error']);baseline_out=abs(float(base[25]['downstream_error']))
            all_l1=sum(abs(x['stock_error']) for x in local);base_l1=sum(abs(float(x['stock_error'])) for x in base)
            v=next(x for x in terms_base['rows'] if x['start']==start and x['cell']==23)
            speed=r['physical_cell_states'][1]['speed_kmh']['FW_E'][23]
            speed_err=abs(speed-v['native_end_speed']);base_err=abs(v['model_end_speed']-v['native_end_speed'])
            valid=(target_stock<=baseline_stock+1e-7 and target_out<=baseline_out+1e-7 and all_l1<=1.05*base_l1+1e-7 and speed_err<=base_err+2+1e-7)
            metrics.append(dict(start=start,stock_error=target_stock,baseline_stock_error=baseline_stock,out_error=target_out,baseline_out_error=baseline_out,
                all31_L1=all_l1,baseline_all31_L1=base_l1,cell23_speed_error=speed_err,baseline_cell23_speed_error=base_err,
                score=(target_stock/baseline_stock+target_out/baseline_out)/2,guards_passed=valid,
                native_end_speeds={c:next(x for x in terms_base['rows'] if x['start']==start and x['cell']==c)['native_end_speed'] for c in (23,24,25)},
                model_end_speeds={c:r['physical_cell_states'][1]['speed_kmh']['FW_E'][c] for c in (23,24,25)}))
        score=sum(x['score'] for x in metrics)/len(metrics)
        summaries[label]=dict(metrics=metrics,mean_score=score,passed=all(x['guards_passed'] for x in metrics) and score<=.8)
    eligible=[k for k,v in summaries.items() if v['passed']]
    selected=min(eligible,key=lambda k:summaries[k]['mean_score']) if eligible else None
    frozen=dict(status='screen_complete',selected=selected,candidates=summaries,forecast_compute_sec=sum(times.values()),forecast_times=times,
        fits=2,forecasts=4,optimizer_iterations=0,new_native=0,adopted=False,pins=pins,
        heldout_used_for_selection=False,next_action='At most selected candidate in existing seed47 pair' if selected else 'No more coefficient search in this screen; report structural limit')
    (O/'frozen_selection.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (O/'cell_results.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cell_rows[0]));w.writeheader();w.writerows(cell_rows)
    print(json.dumps({k:v for k,v in frozen.items() if k not in ('pins',)},ensure_ascii=False))

if __name__=='__main__':main()
