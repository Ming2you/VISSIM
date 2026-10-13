"""Review conditional predictions without representing them as deployable gains."""
from pathlib import Path
from collections import defaultdict
import gzip
import hashlib
import json
import pickle

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent
A=HERE.parent
NEW=Path('E:/VISSIM_analysis/20261010_source_boundary318/forecast2400')
OLD=Path('E:/VISSIM_analysis/20261010_sc109_transport317/forecast2400')
PINS={}


def read(path, compressed=False):
    path=Path(path)
    data=path.read_bytes()
    PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if compressed else data)


def main():
    out=HERE/'review.json'
    assert not out.exists()
    audit=read(HERE/'audit.json')
    old=read(OLD/'summary.json')
    new=read(NEW/'summary.json')
    for summary in (old,new):
        for p,h in summary['source_pins'].items():
            assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    assert new['forecasts']==2 and new['optimizer_calls']==new['native_runs']==0
    assert new['future_observation_inputs'] and not new['autonomous_validation']
    assert not old['future_observation_inputs']
    assert old['initial_projection']==new['initial_projection']
    assert old['prehead_geometry']==new['prehead_geometry']
    receipts=read(NEW/'source_conditioning.json')
    assert [r['arm'] for r in receipts]==['hold','city']
    for r in receipts:
        for road in ('FW_E','FW_W'):
            assert [d[road]/24 for d in r['conditioned_vph']]==audit['comparison'][road][r['arm']]['corrected_admissions_150s']
    cfg,_,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    initial=read(A/'matched280/authority/hold.stocks.json')[0]
    native=read(A/'exit_timing309/assessment.json')
    native_delta=read(A/'sc109_transport317/comparison.json')['native_delta_omega_veh_h']
    accounts={}
    grouped={}
    for arm in ('hold','city'):
        result=new['results'][arm]
        response=read(NEW/(arm+'.response.json.gz'),True)
        assert result['conservation_states']==4 and result['writer_three_blocks']
        assert result['resource_max_exceedance']<1e-7
        assert response['model_constraint_coverage']['complete']
        assert response['conditional_model_feasibility_witness']
        last=dict(stocks={k:dict(inside=v) for k,v in response['residence'][-1]['inside_veh'].items()})
        accounts[arm]=model_boundary(response,[initial,last],result['omega_ttt_veh_h'],cfg)
        groups=defaultdict(lambda:dict(count=0.,cost=0.))
        for key,row in accounts[arm]['routes'].items():
            if abs(row['departed'])<1e-10:continue
            possible={e['source']+'->'+e['target'] for turn in cfg.network.control_area_routes.get(key,{}).get('physical_turns',[])
                      for e in turn.get('crossing_edges',[]) if e['from_inside'] and not e['to_inside']}
            group=next(iter(possible)) if len(possible)==1 else 'unresolved_model_physical_route'
            groups[group]['count']+=row['departed']
            groups[group]['cost']+=row['departure_cost']
        grouped[arm]=dict(groups)
    delta=lambda s:s['results']['city']['omega_ttt_veh_h']-s['results']['hold']['omega_ttt_veh_h']
    boundary_delta={k:sum(r[k] for r in accounts['city']['routes'].values())-sum(r[k] for r in accounts['hold']['routes'].values())
                    for k in ('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')}
    assert abs(sum(boundary_delta[k] for k in ('entry_cost','departure_cost','generation_cost'))-delta(new))<1e-7
    ranked=[]
    for edge in set(grouped['city'])|set(grouped['hold'])|set(native['native_delta']):
        m={f:grouped['city'].get(edge,{}).get(f,0)-grouped['hold'].get(edge,{}).get(f,0) for f in ('count','cost')}
        n=native['native_delta'].get(edge,dict(count=0,cost=0))
        ranked.append(dict(edge=edge,native=n,conditional_model=m,model_minus_native_cost=m['cost']-n['cost']))
    ranked.sort(key=lambda x:abs(x['model_minus_native_cost']),reverse=True)
    report=dict(status='complete_source_forecast_explains_material_part_of_wrong_direction',
                autonomous_delta_veh_h=delta(old),future_source_conditional_delta_veh_h=delta(new),native_delta_veh_h=native_delta,
                delta_shift_from_conditioning_veh_h=delta(new)-delta(old),
                remaining_native_minus_conditional_veh_h=native_delta-delta(new),
                error_reduction_fraction=(abs(native_delta-delta(old))-abs(native_delta-delta(new)))/abs(native_delta-delta(old)),
                boundary_delta=boundary_delta,ranked_exit_errors=ranked,
                checks={arm:{k:new['results'][arm][k] for k in ('wall_sec','resource_max_exceedance','writer_three_blocks','conservation_states','shared_constraints')}
                        for arm in ('hold','city')},
                source_pins=PINS,production_adopted=False,goal_complete=False,
                budget=dict(scalar450=2,tests=3,ad=0,optimizer=0,native=0,fzp_scans=0,fits=0),
                limitations=[
                    'Actual future admissions are used separately in each arm; this is conditional diagnosis, not autonomous prediction or isolated causal policy gain.',
                    'Different realized admissions remain under identical offered schedules and seed. No attribution to randomness or receiving alone is proven.',
                    '150s uniform conditioned inflow does not reproduce within-block arrivals.',
                    'Source-schedule-minus-admissions backlog is not measured stochastic uninserted demand.',
                    'Do not subtract the diagnosed shift from native TTT or claim calibrated SDMPC selection.',
                    'Native5s midpoint and model10s endpoint accounting differ; unclassified losses are not normal exits.'
                ])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('autonomous_delta_veh_h','future_source_conditional_delta_veh_h','native_delta_veh_h','delta_shift_from_conditioning_veh_h','remaining_native_minus_conditional_veh_h','error_reduction_fraction','boundary_delta')},indent=2))
    print('TOP_EXIT_ERRORS',json.dumps(ranked[:5]))
    print('NP_NUF', {a:r['shared_constraints']['feasible'] for a,r in report['checks'].items()})


if __name__=='__main__':main()
