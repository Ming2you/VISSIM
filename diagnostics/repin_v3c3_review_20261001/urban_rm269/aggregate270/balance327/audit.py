"""Exact inventory-time decomposition of existing326 and native city/hold.

No forecast, FZP read, controller selection or coefficient fit.
"""
from collections import defaultdict
from pathlib import Path
import csv,gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
NATIVE=Path('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289')
MODEL=Path('E:/VISSIM_analysis/20261010_sc12_head326/forecast2400')
PINS={}
def raw(path):
    p=Path(path);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(path):
    p=Path(path);b=raw(p);return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def native_accounts():
    cols=('observed_entry_events','appeared_inside_events','reappeared_inside_events',
          'observed_exit_events','terminal_exit_inferred_events','unresolved_inside_disappearances')
    arms={}
    for arm,sub in (('hold','hold'),('city','selected')):
        allrows=list(csv.DictReader(raw(NATIVE/sub/'area_timeseries.csv').decode('utf-8-sig').splitlines()))
        rows=[r for r in allrows if 2400<float(r['sim_sec'])<=2850]
        values={c:dict(vehicles=0.,cost=0.) for c in cols}
        for r in rows:
            assert abs(float(r['stock_closure_residual_veh']))<1e-8
            weight=(2850-float(r['sim_sec'])+float(r['interval_sec'])/2)/3600
            for i,c in enumerate(cols):
                values[c]['vehicles']+=float(r[c]);values[c]['cost']+=float(r[c])*weight*(1 if i<3 else -1)
        first_prior=[r for r in allrows if float(r['sim_sec'])<=2400][-1]
        arms[arm]=dict(events=values,initial_sample_sec=float(first_prior['sim_sec']),
            initial_stock=float(first_prior['inside_vehicles']),final_stock=float(rows[-1]['inside_vehicles']),
            observed_last_sec=float(rows[-1]['sim_sec']),
            sampled_ttt_change=float(rows[-1]['ttt_veh_h_cumulative'])-float(first_prior['ttt_veh_h_cumulative']))
        assert abs(arms[arm]['initial_stock']+sum(v['vehicles']*(1 if i<3 else -1) for i,v in enumerate(values.values()))-arms[arm]['final_stock'])<1e-7
    assert arms['hold']['initial_stock']==arms['city']['initial_stock']
    delta={c:{f:arms['city']['events'][c][f]-arms['hold']['events'][c][f] for f in ('vehicles','cost')} for c in cols}
    pair_ttt=arms['city']['sampled_ttt_change']-arms['hold']['sampled_ttt_change']
    assert abs(sum(v['cost'] for v in delta.values())-pair_ttt)<1e-7
    return dict(arms=arms,delta=delta,delta_ttt=pair_ttt,
        note='First common2395.1→2400.1 transition cancels between arms. Final4.9s sampled hold tail retained; unresolved disappearance is not normal discharge.')

def main():
    assert not (HERE/'assessment.json').exists()
    source=read(NATIVE/'cached_summary.json');closure=read(NATIVE/'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and source['paired_prefix_exact'] and source['common_start_vehicle_records_exact']
    assert all(v['native_execution_passed'] for v in source['arms'].values())
    previous=read(A/'sc12_head326/completion.json')
    for p,h in previous['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    summary=read(MODEL/'summary.json')
    for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    assert not summary['future_observation_inputs']
    cfg,_,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    initial=read(A/'matched280/authority/hold.stocks.json')[0]
    accounts={};edges={}
    for arm in ('hold','city'):
        r=read(MODEL/(arm+'.response.json.gz'));s=summary['results'][arm]
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
        assert s['resource_max_exceedance']<1e-7 and s['conservation_states']==4 and s['writer_three_blocks']
        final=dict(stocks={k:dict(inside=v) for k,v in r['residence'][-1]['inside_veh'].items()})
        accounts[arm]=model_boundary(r,[initial,final],s['omega_ttt_veh_h'],cfg)
        grouped=defaultdict(lambda:dict(count=0.,cost=0.,routes=[]))
        for key,row in accounts[arm]['routes'].items():
            if abs(row['departed'])<1e-10:continue
            possible={e['source']+'->'+e['target'] for turn in cfg.network.control_area_routes.get(key,{}).get('physical_turns',[])
                      for e in turn.get('crossing_edges',[]) if e['from_inside'] and not e['to_inside']}
            edge=next(iter(possible)) if len(possible)==1 else 'unresolved_model_physical_route'
            grouped[edge]['count']+=row['departed'];grouped[edge]['cost']+=row['departure_cost'];grouped[edge]['routes'].append(key)
        edges[arm]=dict(grouped)
    fields=('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')
    routes={k:{f:accounts['city']['routes'].get(k,{}).get(f,0.)-accounts['hold']['routes'].get(k,{}).get(f,0.) for f in fields}
            for k in accounts['city']['routes'].keys()|accounts['hold']['routes'].keys()}
    md={f:sum(r[f] for r in routes.values()) for f in fields}
    model_delta=summary['results']['city']['omega_ttt_veh_h']-summary['results']['hold']['omega_ttt_veh_h']
    assert abs(md['entry_cost']+md['departure_cost']+md['generation_cost']-model_delta)<1e-7
    assert abs(md['entered']+md['generated_inside']-md['departed']-(accounts['city']['final_inside']-accounts['hold']['final_inside']))<1e-7
    native=native_accounts();assert abs(native['delta_ttt']-source['delta_TTT_veh_h'])<1e-7
    nd=native['delta']
    native_parts=dict(input_and_appearance=sum(nd[k]['cost'] for k in ('observed_entry_events','appeared_inside_events','reappeared_inside_events')),
        normal_observed_and_terminal=sum(nd[k]['cost'] for k in ('observed_exit_events','terminal_exit_inferred_events')),
        unresolved_disappearance=nd['unresolved_inside_disappearances']['cost'])
    model_parts=dict(input_and_generation=md['entry_cost']+md['generation_cost'],departures=md['departure_cost'])
    error_parts=dict(input=native_parts['input_and_appearance']-model_parts['input_and_generation'],
        normal_departures=native_parts['normal_observed_and_terminal']-model_parts['departures'],
        unresolved_native_loss=native_parts['unresolved_disappearance'])
    assert abs(sum(error_parts.values())-(native['delta_ttt']-model_delta))<1e-7
    observed=read(A/'exit_timing309/assessment.json');ranked=[]
    for edge in edges['hold'].keys()|edges['city'].keys()|observed['native_delta'].keys():
        m={f:edges['city'].get(edge,{}).get(f,0.)-edges['hold'].get(edge,{}).get(f,0.) for f in ('count','cost')}
        n=observed['native_delta'].get(edge,dict(count=0.,cost=0.))
        ranked.append(dict(edge=edge,native_observed=n,model=m,error_native_minus_model=n['cost']-m['cost'],
                           model_routes=sorted(set(edges['hold'].get(edge,{}).get('routes',[])+edges['city'].get(edge,{}).get('routes',[])))))
    ranked.sort(key=lambda x:-abs(x['error_native_minus_model']))
    older=read(A/'source_boundary318/review.json')
    rm=read(NATIVE/'cached_summary.json')['comparison']
    for p in ('upstream_worklog/07_fww_sc1001eb/sc1001eb/F2_FORECAST_ACCEPT.md','upstream_worklog/02_urban_b2/diag_c3_r2/U7.md'):
        raw(A.parent.parent/p)
    report=dict(status='complete_whole_inventory_time_error_partition327',previous_goal_turn='progress326_nominal_shared_cap_rejected',
        model_accounts=accounts,model_route_deltas=routes,native=native,
        delta_omega=dict(model326=model_delta,native=native['delta_ttt']),native_parts=native_parts,model_parts=model_parts,
        error_native_minus_model=error_parts,ranked_exit_errors=ranked,
        modeled_endpoint_stock_delta=accounts['city']['final_inside']-accounts['hold']['final_inside'],
        native_endpoint_stock_delta=native['arms']['city']['final_stock']-native['arms']['hold']['final_stock'],
        earlier_source318_conditioning=dict(base='317, NOT326',autonomous=older['autonomous_delta_veh_h'],conditional=older['future_source_conditional_delta_veh_h'],
            effect=older['delta_shift_from_conditioning_veh_h'],not_additive_correction_to326=True),
        prior_rm_comparison=rm,goal_complete=False,production_adopted=False,
        budget=dict(new_forecasts=0,new_native=0,new_fzp=0,optimizer=0,ad=0,fits=0,production_changes=0),
        limitations=['Accounting is exact within each existing quadrature, not a causal attribution to a control actuator.',
                    'Native appearance can include missed between-sample area entry; not all appearance is vehicle input.',
                    'Model departures include normal terminal exits; physical unresolved group must not be compared to only observed exits as if exhaustive.',
                    'Source318 future admissions are diagnostic only and belong to317; cannot add its effect to326 without a new controlled comparison.',
                    'No real future arrivals are used in model326. Whole gain direction remains unqualified.'],source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('PAIR',report['delta_omega'],'NATIVE_PARTS',native_parts,'MODEL_PARTS',model_parts,'ERROR_PARTS',error_parts)
    print('END_STOCK',report['modeled_endpoint_stock_delta'],report['native_endpoint_stock_delta'])
    print('TOP_EXIT',json.dumps(ranked[:7],ensure_ascii=False))
    print('RM_COMPARISON',rm)

if __name__=='__main__':main()
