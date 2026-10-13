"""Latest three-arm inventory-time accounts, using closed cached data only."""
from pathlib import Path
from collections import defaultdict
import csv,gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
BASE=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
JOINT=Path('E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2')
CITY=Path('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289')
PINS={}
COLS=('observed_entry_events','appeared_inside_events','reappeared_inside_events',
      'observed_exit_events','terminal_exit_inferred_events','unresolved_inside_disappearances')

def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b

def read(p):
    b=raw(p);return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)

def actual(folder):
    rows=list(csv.DictReader(raw(folder/'area_timeseries.csv').decode('utf-8-sig').splitlines()))
    before=[r for r in rows if float(r['sim_sec'])<=2400][-1]
    selected=[r for r in rows if 2400<float(r['sim_sec'])<=2850]
    assert selected and abs(float(selected[-1]['sim_sec'])-2850)<1e-7
    values={k:dict(count=0.,cost=0.) for k in COLS}
    for r in selected:
        assert abs(float(r['stock_closure_residual_veh']))<1e-7
        weight=(2850-float(r['sim_sec'])+float(r['interval_sec'])/2)/3600
        for j,k in enumerate(COLS):
            n=float(r[k]);values[k]['count']+=n;values[k]['cost']+=n*weight*(1 if j<3 else -1)
    start=float(before['inside_vehicles']);end=float(selected[-1]['inside_vehicles'])
    assert abs(start+sum(v['count']*(1 if j<3 else -1) for j,v in enumerate(values.values()))-end)<1e-7
    return dict(initial=start,final=end,events=values,
        ttt=float(selected[-1]['ttt_veh_h_cumulative'])-float(before['ttt_veh_h_cumulative']),
        initial_sample_sec=float(before['sim_sec']),last_sample_sec=float(selected[-1]['sim_sec']))

def main():
    assert not (HERE/'assessment.json').exists()
    for p in ('upstream_worklog/07_fww_sc1001eb/sc1001eb/F2_FORECAST_ACCEPT.md','upstream_worklog/02_urban_b2/diag_c3_r2/U7.md'):
        raw(H.parent/p)
    scope=read(JOINT/'scope.json');assert scope['whole_RM_vector_not_single10681']
    prior_rm=read(A/'rm_response330/assessment.json')
    prior_city=read(A/'balance327/assessment.json')
    cached=read(CITY/'cached_summary.json')
    assert cached['paired_prefix_exact'] and cached['common_start_vehicle_records_exact']
    assert read(CITY/'runtime_closure.json')['all_owned_processes_closed']
    summary=read(JOINT/'summary.json');initial=dict(stocks=summary['initial_stocks'])
    cfg,_,_=pickle.loads(raw(JOINT/'initial.pickle'))
    model={};native={}
    for arm in ('hold','city','joint'):
        folder=JOINT if arm=='joint' else BASE
        scalar=read(folder/(arm+'.json'));response=read(folder/(arm+'.response.json.gz'))
        assert scalar['conservation_states']==4 and scalar['writer_three_blocks']
        assert scalar['shared_constraints']['feasible'] and scalar['resource_max_exceedance']<1e-7
        final=dict(stocks={k:dict(inside=v) for k,v in response['residence'][-1]['inside_veh'].items()})
        account=model_boundary(response,[initial,final],scalar['omega_ttt_veh_h'],cfg)
        grouped=defaultdict(lambda:dict(departed=0.,cost=0.,routes=[]))
        for key,r in account['routes'].items():
            if r['departed']<1e-10:continue
            edges={e['source']+'->'+e['target'] for turn in cfg.network.control_area_routes.get(key,{}).get('physical_turns',[])
                   for e in turn.get('crossing_edges',[]) if e['from_inside'] and not e['to_inside']}
            edge=next(iter(edges)) if len(edges)==1 else 'unresolved_model_physical_route'
            grouped[edge]['departed']+=r['departed'];grouped[edge]['cost']+=r['departure_cost'];grouped[edge]['routes'].append(key)
        model[arm]=dict(ttt=scalar['omega_ttt_veh_h'],account=account,normal_edges=dict(grouped))
        folder=H/'native2400_analysis/selected' if arm=='joint' else CITY/('hold' if arm=='hold' else 'selected')
        native[arm]=actual(folder)
    assert len({n['initial'] for n in native.values()})==1
    contrasts={}
    for name,a,b in (('city_minus_hold','city','hold'),('joint_minus_city','joint','city'),('joint_minus_hold','joint','hold')):
        n={k:{f:native[a]['events'][k][f]-native[b]['events'][k][f] for f in ('count','cost')} for k in COLS}
        actual_delta=native[a]['ttt']-native[b]['ttt']
        assert abs(sum(v['cost'] for v in n.values())-actual_delta)<1e-7
        fields=('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')
        r1=model[a]['account']['routes'];r0=model[b]['account']['routes']
        route_delta={k:{f:r1.get(k,{}).get(f,0.)-r0.get(k,{}).get(f,0.) for f in fields} for k in r1.keys()|r0.keys()}
        totals={f:sum(r[f] for r in route_delta.values()) for f in fields}
        model_delta=model[a]['ttt']-model[b]['ttt']
        assert abs(totals['entry_cost']+totals['generation_cost']+totals['departure_cost']-model_delta)<1e-7
        parts=dict(native_input=sum(n[k]['cost'] for k in COLS[:3]),
                   native_normal_outflow=sum(n[k]['cost'] for k in COLS[3:5]),
                   native_unclassified_loss=n[COLS[5]]['cost'],
                   model_input=totals['entry_cost']+totals['generation_cost'],model_outflow=totals['departure_cost'])
        contrasts[name]=dict(native=actual_delta,model=model_delta,parts=parts,native_events=n,model_routes=route_delta,
            error=actual_delta-model_delta,
            native_outflow_plus_unclassified=parts['native_normal_outflow']+parts['native_unclassified_loss'],
            model_outflow=parts['model_outflow'])
    assert abs(contrasts['city_minus_hold']['native']-prior_city['delta_omega']['native'])<1e-7
    assert abs(contrasts['joint_minus_city']['native']-prior_rm['native_cost_delta']['omega'])<1e-7
    assert abs(contrasts['joint_minus_city']['model']-prior_rm['model_cost_delta']['omega'])<1e-7
    result=dict(status='complete_latest_three_arm_time_budget',goal_complete=False,model=model,native=native,
        contrasts=contrasts,source_pins=PINS,
        limitations=['Boundary impulse accounting is not an exogenous-input-matched causal effect.',
          'Subtracting native input-time contribution is descriptive, not a counterfactual prediction.',
          'Native appearances mix insertions and between-sample missing entries; unresolved loss is not normal exit.',
          'City-fixed contrast changes the full RM vector, not10681 alone.',
          'Native5s trapezoids and model10s endpoint integration are independently closed, not identical quadrature.',
          'No new forecast, coefficient, future-input assimilation, optimization, FZP scan or native run.'])
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for name,r in contrasts.items():print(name,{k:v for k,v in r.items() if k not in ('native_events','model_routes')},flush=True)

if __name__=='__main__':main()
