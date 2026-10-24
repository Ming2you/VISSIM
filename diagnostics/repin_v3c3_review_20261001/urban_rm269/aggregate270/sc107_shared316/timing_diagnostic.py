"""Reconcile retained transport timestamps; future native data is diagnosis only."""
from collections import defaultdict
from pathlib import Path
import gzip, hashlib, json, math, pickle, statistics

HERE=Path(__file__).resolve().parent;A=HERE.parent
MODEL=Path('E:/VISSIM_analysis/20261010_sc107_shared316/forecast2400')
KEY='SC108_to_SC109';STOCK='storage:'+KEY
RUNS={
 'hold':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
 'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
PINS={}

def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b

def unique(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['vehicle']].append(row['time'])
    return {k:v[0] for k,v in groups.items() if len(v)==1}

def main():
    out=HERE/'timing_diagnostic.json';assert not out.exists()
    cfg,state,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    chain=json.loads(raw(A/'exit_timing309/sc109_chain.json'))
    # These records already pin the retained native head events and physical support.
    for p,h in chain['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    for p in ('diag_c3_r2/U7.md','impl/STAGE3.md'):
        raw(A.parent.parent/'upstream_worklog/02_urban_b2'/p)
    capacity=cfg.network.urban_link_storage_veh[KEY]
    speed=state.urban_link_speed_kph[KEY];spacing=cfg.network.urban_avg_vehicle_length_m
    assert cfg.simulation.T_u_sec==10 and capacity==436.9
    initial_pending=sum(state.urban_arrival_buffer[KEY].values());assert initial_pending==43
    result={}
    for arm,folder in RUNS.items():
        r=json.loads(gzip.decompress(raw(MODEL/(arm+'.response.json.gz'))))
        releases=dict(state.urban_storage_release_buffer[KEY]);available=state.urban_link_storage[KEY]
        samples=[];cohorts=[];reconstruction_errors=[]
        for row in [x for x in r['residence'] if x['stage']=='urban']:
            t=row['start_sec'];step=round(t/10)
            arrival=sum(x['vehicles'] for x in r['transfers'] if x['source']==STOCK and x['start_sec']==t)
            expected_arrival=releases.pop(step,0.)
            reconstruction_errors.append(abs(arrival-expected_arrival))
            available=min(capacity,available+expected_arrival)
            inputs=[x for x in r['transfers'] if x['target']==STOCK and x['start_sec']==t]
            for x in inputs:
                n=x['vehicles'];available-=n
                delay=max(1,math.ceil(available*spacing/1000/speed/cfg.simulation.T_u_h))
                due=step+delay;releases[due]=releases.get(due,0.)+n
                cohorts.append(dict(start_sec=t,source=x['source'],vehicles=n,delay_sec=delay*10,due_sec=due*10))
            stock=row['model_stock_veh'][STOCK]
            reconstruction_errors.append(abs(stock-(capacity-available)))
            queues=sum(v for k,v in row['model_stock_veh'].items() if k.startswith('movement:SC109_W_SC108_'))
            samples.append(dict(start_sec=t,end_sec=row['end_sec'],input_veh=sum(x['vehicles'] for x in inputs),
                arrived_veh=arrival,transit_veh=stock,queue_veh=queues))
        # No production forecast: independent reconciliation of already-emitted receipts.
        assert max(reconstruction_errors)<1e-7,max(reconstruction_errors)
        entered=sum(x['input_veh'] for x in samples);arrived=sum(x['arrived_veh'] for x in samples)
        residual=samples[-1]['transit_veh']
        assert abs(initial_pending+entered-arrived-residual)<1e-7
        pending=sum(x['vehicles'] for x in cohorts if x['due_sec']>=2850)
        assert abs(pending-residual)<1e-7
        heads=chain['head_events'][arm];down=unique(heads['SC109_W_p3'])
        delay_pairs={}
        for source in ('SC108_W_p3','SC108_side_p3'):
            upstream=unique(heads[source]);pairs=[(i,down[i]-t) for i,t in upstream.items() if i in down and down[i]>=t]
            times=[v for _,v in pairs]
            delay_pairs[source]=dict(matched_count=len(times),mean_sec=statistics.mean(times) if times else None,
                median_sec=statistics.median(times) if times else None,
                minimum_sec=min(times) if times else None,maximum_sec=max(times) if times else None,
                pairs=[dict(vehicle=i,elapsed_sec=v) for i,v in pairs])
        physical=[]
        for end in (2400,2550,2700,2850):
            obs=json.loads(raw(folder/f'state_{end:06}.json'))
            v=obs['vehicle_records'];assert v['complete'] and v['record_count']==len(v['records'])
            allrows=[x for x in v['records'] if str(x['link_no']) in chain['initial_provenance']]
            end_model=next((x for x in samples if x['end_sec']==end),None)
            physical.append(dict(at_sec=end,native_whole_support_links_veh=len(allrows),
                native_stopped_veh=sum(x['stopped'] for x in allrows),
                native_average_speed_kph=statistics.mean(x['speed_kph'] for x in allrows) if allrows else None,
                model_transit_plus_queue_veh=(end_model['transit_veh']+end_model['queue_veh']) if end_model else 53.,
                note='Snapshot whole-link support diagnostic; not an Omega boundary ledger or exact stopline queue definition.'))
        result[arm]=dict(input_veh=entered,arrived_veh=arrived,final_transit_veh=residual,
            final_queue_veh=samples[-1]['queue_veh'],max_reconciliation_error=max(reconstruction_errors),
            delay_steps_veh={str(t):sum(x['vehicles'] for x in cohorts if x['delay_sec']==t) for t in sorted({x['delay_sec'] for x in cohorts})},
            pending_cohorts=[x for x in cohorts if x['due_sec']>=2850],samples=samples,
            native_head_elapsed=delay_pairs,physical_snapshots=physical)
    delta={k:result['city'][k]-result['hold'][k] for k in ('input_veh','arrived_veh','final_transit_veh','final_queue_veh')}
    assert abs(delta['input_veh']-delta['final_transit_veh']-delta['arrived_veh'])<1e-7
    raw(Path(__file__))
    report=dict(status='complete_retained_transport_reconciled',goal_complete=False,production_changes=0,
        initial_pending_veh=initial_pending,effective_speed_field=speed,results=result,city_minus_hold=delta,
        budget=dict(new_forecasts=0,ad=0,optimizer=0,native=0,fzp_scans=0,fits=0),source_pins=PINS,
        conclusions=['More horizon arrivals with fewer inputs is explained by less terminal transit; conservation holds.',
            'The effective speed field includes the existing lane-distance correction and is not a literal141km/h urban speed.',
            'Full-delay reconstruction checks10s indexing and retained scheduling; it does not establish physical travel-time accuracy.',
            'Native head-to-head elapsed times include queuing; compare cautiously with queue-tail travel delay.',
            'Joined completed crossings are survivor-conditioned and future diagnostic records, never autonomous inputs.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(delta=delta,errors={k:v['max_reconciliation_error'] for k,v in result.items()},
        snapshots={k:v['physical_snapshots'] for k,v in result.items()},
        head_delay={k:{s:{t:x for t,x in d.items() if t!='pairs'} for s,d in v['native_head_elapsed'].items()} for k,v in result.items()}),ensure_ascii=False))

if __name__=='__main__':main()
