"""Physical and response review; no native rerun, fitted rates or future inputs."""
from collections import defaultdict
from pathlib import Path
import gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc109_initial320/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc109_routes321/forecast2400')
PINS={}
def data(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):
    b=data(p);return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)

def main():
    out=HERE/'review.json';assert not out.exists()
    cfg,_,_=pickle.loads(data(A/'citysplit287/forecast2400/initial.pickle'))
    start=read(A/'matched280/authority/hold.stocks.json')[0]
    actual=read(A/'exit_timing309/assessment.json')['native_delta']
    native=read(A/'sc109_initial320/review.json')['native_delta_omega_veh_h']
    result={};responses={};edges={}
    for name,folder in [('timing320',OLD),('routes321',NEW)]:
        s=read(folder/'summary.json')
        assert s['status']=='complete' and s['forecasts']==2 and not s['future_observation_inputs']
        for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        result[name]={};responses[name]={};edges[name]={}
        for arm in ('hold','city'):
            summary=s['results'][arm];r=read(folder/(arm+'.response.json.gz'));responses[name][arm]=r
            assert summary['shared_constraints']['feasible'] and summary['writer_three_blocks']
            assert summary['conservation_states']==4 and summary['resource_max_exceedance']<1e-7
            assert r['conditional_model_feasibility_witness'] and r['model_constraint_coverage']['complete']
            stocks={key for key in summary['costs_by_stock'] if key.startswith('movement:SC109_W_') or key=='storage:SC108_to_SC109'}
            through='movement:SC109_W_SC108_to_E'
            left='movement:SC109_W_SC108_to_N_SC16'
            flows={key:[sum(x['vehicles'] for x in r['transfers'] if x['source']==m and t<=x['start_sec']<t+150)
                        for t in (2400,2550,2700)] for key,m in [('through',through),('left',left)]}
            last=[x for x in r['residence'] if x['stage']=='urban'][-1]
            final=dict(stocks={k:dict(inside=v) for k,v in r['residence'][-1]['inside_veh'].items()})
            boundary=model_boundary(r,[start,final],summary['omega_ttt_veh_h'],cfg)
            grouped=defaultdict(lambda:dict(count=0.,cost=0.))
            for key,row in boundary['routes'].items():
                if abs(row['departed'])<1e-10:continue
                candidates={e['source']+'->'+e['target'] for turn in cfg.network.control_area_routes.get(key,{}).get('physical_turns',[])
                            for e in turn.get('crossing_edges',[]) if e['from_inside'] and not e['to_inside']}
                edge=next(iter(candidates)) if len(candidates)==1 else 'unresolved_model_route'
                grouped[edge]['count']+=row['departed'];grouped[edge]['cost']+=row['departure_cost']
            edges[name][arm]=dict(grouped)
            result[name][arm]=dict(omega_ttt_veh_h=summary['omega_ttt_veh_h'],flows_150=flows,
                local_cost_veh_h=sum(summary['costs_by_stock'][k] for k in stocks),
                terminal_veh={k:last['model_stock_veh'][k] for k in stocks},wall_sec=summary['wall_sec'],
                maximum_resource_exceedance=summary['resource_max_exceedance'],feasible=True)
    for arm in ('hold','city'):
        def incoming(r):return [x for x in r['transfers'] if x['target']=='storage:SC108_to_SC109' and x['source']!=x['target']]
        assert incoming(responses['timing320'][arm])==incoming(responses['routes321'][arm])
    assert read(OLD/'initial_calendar.json')==read(NEW/'initial_calendar.json')
    checks=read(NEW/'route_tag_consumption.json');assert len(checks)==2
    assert all(len(blocks)==3 and all(x['remaining']=={} for x in blocks) for blocks in checks)
    delta={v:d['city']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h'] for v,d in result.items()}
    errors=[]
    grouped=edges['routes321']
    for edge in set(grouped['hold'])|set(grouped['city'])|set(actual):
        model={k:grouped['city'].get(edge,{}).get(k,0)-grouped['hold'].get(edge,{}).get(k,0) for k in ('count','cost')}
        n=actual.get(edge,dict(count=0,cost=0))
        errors.append(dict(edge=edge,model=model,native=n,model_minus_native_cost=model['cost']-n['cost']))
    errors.sort(key=lambda x:abs(x['model_minus_native_cost']),reverse=True)
    report=dict(status='complete_known_routes_fixed_whole_city_gain_unqualified',results=result,delta_omega_veh_h=delta,
        native_delta_omega_veh_h=native,incremental_gain_error_improvement_veh_h=abs(native-delta['timing320'])-abs(native-delta['routes321']),
        initial_calendar_unchanged=True,future_accepted_sc109_sources_unchanged=True,initial_tags_consumed_all_blocks=True,
        ranked_exit_errors=errors,source_pins=PINS,goal_complete=False,production_adopted=False,
        budget=dict(fixed450=2,tests=5,new_fits=0,ad=0,optimizer=0,native=0,fzp_scans=0,production_changes=0),
        limits=['Initial same-time route correction is verified; unknown route prior remains an approximation.',
                'Large whole-city gain direction remains wrong; no native gain or autonomous selection claim.',
                'SC109 post-head owner still inherited; current null route is not proof of future decision eligibility.',
                'No full AD, unused-state response or controller selection qualification for this composite.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DELTA',delta,'NATIVE',native,'IMPROVEMENT',report['incremental_gain_error_improvement_veh_h'])
    print('SC109_FLOWS',{k:{arm:v['flows_150'] for arm,v in d.items()} for k,d in result.items()})
    print('TOP_EXITS',json.dumps(errors[:5]))

if __name__=='__main__':main()
