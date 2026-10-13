"""Review the single candidate without more fitting or forecasts."""
from pathlib import Path
import gzip,hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc109_routes321/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc16_aggregate323/forecast2400')
PINS={}
def read(path):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if path.suffix=='.gz' else b)
def main():
    assert not (HERE/'review.json').exists()
    actual=read(A/'city_loss322/assessment.json');prior=read(A/'sc109_routes321/review.json')
    results={}
    for label,folder in [('routes321',OLD),('aggregate323',NEW)]:
        summary=read(folder/'summary.json');assert summary['forecasts']==2 and not summary['future_observation_inputs']
        for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        results[label]={}
        for arm in ('hold','city'):
            s=summary['results'][arm];r=read(folder/(arm+'.response.json.gz'))
            assert s['writer_three_blocks'] and s['conservation_states']==4 and s['shared_constraints']['feasible']
            assert s['resource_max_exceedance']<1e-8 and r['model_constraint_coverage']['complete']
            target='movement:SC16_N_SC12_to_E'
            events=[x for x in r['transfers'] if x['source']==target and x['target']!=target]
            phases=[sum(x['vehicles'] for x in events if t<=x['start_sec']<t+150) for t in (2400,2550,2700)]
            upstream={}
            for x in r['transfers']:
                if x['target']=='storage:SC12_to_SC16' and x['source']!=x['target']:
                    key=x['source'] or 'exogenous';upstream[key]=upstream.get(key,0.)+x['vehicles']
            results[label][arm]=dict(omega_ttt_veh_h=s['omega_ttt_veh_h'],left_head_counts=phases,
                left_head_time_cost=-sum(x['vehicles']*(2850-x['start_sec'])/3600 for x in events),
                native_left_counts=[b['count'] for b in actual['native'][arm]['SC16_N_left'] if b['start_sec']>=2400],
                source_accepted=upstream,endpoint_sec=s['wall_sec'],resource_max_exceedance=s['resource_max_exceedance'],
                conservation_states=s['conservation_states'],shared_feasible=True,writer_three_blocks=True)
    delta={label:r['city']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h'] for label,r in results.items()}
    native=prior['native_delta_omega_veh_h']
    # Incoming accepted SC12 flows are a preserved operand of this diagnostic.
    for arm in ('hold','city'):assert results['aggregate323'][arm]['source_accepted']==results['routes321'][arm]['source_accepted']
    tags=read(NEW/'route_tag_consumption.json');assert len(tags)==2 and all(len(xs)==3 and all(not x['sc16'] and not x['sc109'] for x in xs) for xs in tags)
    application=read(NEW/'sc16_application.json');assert application['cutoff_sec']==2400 and not application['future_traffic_inputs']
    budget=dict(candidate_sets=1,fixed450_forecasts=2,tests=5,new_ad=0,optimizer=0,native=0,fzp=0,production_changes=0,push=0)
    report=dict(status='complete_sc16_volume_improved_gain_not_qualified',results=results,delta_omega_veh_h=delta,
        native_delta_omega_veh_h=native,whole_gain_error_reduction_veh_h=abs(native-delta['routes321'])-abs(native-delta['aggregate323']),
        unchanged_upstream_accepted=True,current_tags_consumed=True,source_pins=PINS,budget=budget,
        candidate_adopted=False,goal_complete=False,
        next_step='Stop SC16 rate/beta/ETA search. Only0.0321vehh gain-error reduction; inspect SC12north supplying low capped/platooned flow using existing past current records, retained321/323 operands and native head curves. Do not inject future arrivals. Keep source318 admission difference separate; no unchanged optimizer/AD/native. Needed upstream aggregate correction must improve meaningful paired response before unused-state/AD/choice qualification.',
        limits=['Past terminal lane balance is an aggregate effective split with unresolved lateral exchange and remaining through/right prior.',
            'Native total left28/20 remains11.19/10.52; whole gain remains wrong-sign. Local level improvement is not control-gain validation.',
            'This is the development state; no unused-state response or full AD/SDMPC qualification of latest composite.'])
    (HERE/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DELTA',delta,'NATIVE',native,'GAIN_ERROR_REDUCTION',report['whole_gain_error_reduction_veh_h'])
    print('HEAD_TOTAL',{k:{arm:sum(v['left_head_counts']) for arm,v in r.items()} for k,r in results.items()})

if __name__=='__main__':main()
