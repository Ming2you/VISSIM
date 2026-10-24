"""Compare320 with the autonomous317 pair, reusing closed native evidence."""
from pathlib import Path
import copy,gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_arrival319.trace_initial import trace
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc109_transport317/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc109_initial320/forecast2400')
PINS={}

def data(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b

def read(p):
    b=data(p);return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)

def main():
    output=HERE/'review.json';assert not output.exists()
    cfg,original,_=pickle.loads(data(A/'citysplit287/forecast2400/initial.pickle'))
    calendar=read(NEW/'initial_calendar.json')
    native=read(A/'sc109_transport317/comparison.json')['native_delta_omega_veh_h']
    native_initial=read(A/'sc109_arrival319/initial_trace.json')['native_initial_local_exit_delta_veh_h']
    start=read(A/'matched280/authority/hold.stocks.json')[0]
    result={}
    responses={}
    for name,folder in (('transport317',OLD),('initial320',NEW)):
        summary=read(folder/'summary.json')
        assert summary['status']=='complete' and summary['forecasts']==2
        assert summary['future_observation_inputs'] is False and summary['production_changes']==0
        for path,digest in summary['source_pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        state=copy.deepcopy(original)
        if name=='initial320':
            state.urban_arrival_buffer['SC108_to_SC109']={int(k):v for k,v in calendar['new_calendar'].items()}
            state.urban_storage_release_buffer['SC108_to_SC109']=dict(state.urban_arrival_buffer['SC108_to_SC109'])
        result[name]={};responses[name]={}
        for arm in ('hold','city'):
            s=summary['results'][arm];r=read(folder/(arm+'.response.json.gz'));responses[name][arm]=r
            assert s['shared_constraints']['feasible'] and s['writer_three_blocks'] and s['conservation_states']==4
            assert s['resource_max_exceedance']<1e-7 and r['conditional_model_feasibility_witness']
            assert r['model_constraint_coverage']['complete']
            assert abs(sum(s['costs_by_stock'].values())-s['omega_ttt_veh_h'])<1e-7
            move='movement:SC109_W_SC108_to_E'
            flows=[sum(x['vehicles'] for x in r['transfers'] if x['source']==move and t<=x['start_sec']<t+150) for t in (2400,2550,2700)]
            arrivals=[sum(x['vehicles'] for x in r['transfers'] if x['source']=='storage:SC108_to_SC109'
                          and x['target']==move and t<=x['start_sec']<t+150) for t in (2400,2550,2700)]
            urban=[x for x in r['residence'] if x['stage']=='urban']
            final=dict(stocks={k:dict(inside=v) for k,v in r['residence'][-1]['inside_veh'].items()})
            account=model_boundary(r,[start,final],s['omega_ttt_veh_h'],cfg)
            boundary={k:sum(row[k] for row in account['routes'].values()) for k in ('entered','departed','entry_cost','departure_cost','generation_cost')}
            result[name][arm]=dict(omega_ttt_veh_h=s['omega_ttt_veh_h'],through_flows_150=flows,
                through_arrivals_150=arrivals,through_queue_end=[x['model_stock_veh'][move] for x in urban if x['end_sec'] in (2550,2700,2850)],
                wall_sec=s['wall_sec'],resource_max_exceedance=s['resource_max_exceedance'],boundary=boundary,
                initial_trace={policy:trace(r,cfg,state,policy) for policy in ('fifo','proportional')})
    # Retiming changes initial eligibility only. All future accepted incoming
    # source receipts in this pair happen to remain identical; verify, don't assume.
    for arm in ('hold','city'):
        def incoming(r):
            return [x for x in r['transfers'] if x['target']=='storage:SC108_to_SC109' and x['source']!=x['target']]
        assert incoming(responses['transport317'][arm])==incoming(responses['initial320'][arm])
    delta={v:d['city']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h'] for v,d in result.items()}
    traces={v:{p:d['city']['initial_trace'][p]['departure_time_cost_start']-d['hold']['initial_trace'][p]['departure_time_cost_start']
               for p in ('fifo','proportional')} for v,d in result.items()}
    boundary={v:{k:d['city']['boundary'][k]-d['hold']['boundary'][k] for k in d['hold']['boundary']} for v,d in result.items()}
    for v in result:
        assert abs(sum(boundary[v][k] for k in ('entry_cost','departure_cost','generation_cost'))-delta[v])<1e-7
    report=dict(status='complete_initial_timing_bias_reduced_whole_gain_unqualified',results=result,
        delta_omega_veh_h=delta,native_delta_omega_veh_h=native,
        improvement_veh_h=abs(native-delta['transport317'])-abs(native-delta['initial320']),
        initial_trace_delta_veh_h=traces,native_initial_exit_delta_veh_h=native_initial,
        model_boundary_delta=boundary,source_pins=PINS,goal_complete=False,production_adopted=False,
        budget=dict(fixed450=2,tests=6,new_fits=0,ad=0,optimizer=0,native=0,fzp_scans=0,production_changes=0),
        limitations=['Autonomous input forecast; not future-conditioned318.',
          'Passive initial FIFO/proportional labels are diagnostic; model and native initial cohorts differ.',
          'Original movement composition and one post-head owner remain; timing alone is not sufficient.',
          'No new AD, unused-state rollout, full-choice or native qualification.'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(delta=delta,native=native,improvement=report['improvement_veh_h'],initial_trace=traces,
                         native_initial=native_initial,flows={v:{arm:d[arm]['through_flows_150'] for arm in d} for v,d in result.items()})))

if __name__=='__main__':main()
