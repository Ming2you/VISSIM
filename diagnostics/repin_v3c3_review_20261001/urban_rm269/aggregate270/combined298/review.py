"""Review the two completed joint-service/gate forecasts without new runs."""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE = Path(__file__).resolve().parent
A = HERE.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'assessment.json').exists()
    s = read(HERE/'forecast2400/summary.json')
    assert s['status']=='complete' and s['forecasts']==2
    assert all(sha(p)==h for p,h in s['source_pins'].items())
    previous = read(A/'gate296/assessment.json')
    truth = read(A/'cityresponse290/assessment.json')
    cfg, _, _ = pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    initial = read(A/'matched280/authority/hold.stocks.json')[0]
    sources = [Path(__file__), HERE/'forecast2400/summary.json', A/'gate296/assessment.json',
               A/'cityresponse290/assessment.json', A/'citysplit287/forecast2400/initial.pickle',
               A/'matched280/authority/hold.stocks.json']
    head_groups = {'SC6_S': {'movement:SC6_S_SC12_to_N_SC103','movement:SC6_S_SC12_to_E_SC104'},
                   'SC101_S': {'movement:SC101_S_SC1_to_N_SC2005'}}
    arms = {}
    for arm in ('hold','city'):
        rpath = HERE/'forecast2400'/f'{arm}.response.json.gz'
        gpath = HERE/'forecast2400'/f'{arm}.gate.json'
        sources.extend([rpath,gpath])
        r = json.loads(gzip.decompress(rpath.read_bytes()))
        g = read(gpath)
        v = s['results'][arm]
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
        assert v['writer_three_blocks'] and v['conservation_states']==4
        assert v['resource_max_exceedance']<1e-7
        assert all(x['discharged']<=x['budget']+1e-7 for x in g['history'])
        assert all(x['discharged']==0 for x in g['history'] if x['green_sec']==0)
        final = {'stocks': {k:dict(inside=n) for k,n in r['residence'][-1]['inside_veh'].items()}}
        boundary = model_boundary(r,[initial,final],v['omega_ttt_veh_h'],cfg)
        heads = {}
        for group, movements in head_groups.items():
            counts = [sum(t['vehicles'] for t in r['transfers'] if t['source'] in movements
                          and t['source']!=t['target'] and start<=t['start_sec']<start+150)
                      for start in (2400,2550,2700)]
            actual = [x['actual'] for x in truth['head_counts'][arm] if x['group']==group and x['phase']=='p1']
            heads[group] = dict(model=counts,native=actual,mae=sum(abs(x-y) for x,y in zip(counts,actual))/3)
        by_source = Counter()
        for t in r['transfers']:
            if t['target']=='storage:SC12_to_SC6' and (t['source'] or '').startswith('movement:SC12_'):
                by_source[t['source'].split(':')[1].split('_')[1]]+=t['vehicles']
        arms[arm]=dict(omega=v['omega_ttt_veh_h'],heads=heads,sc12_sources=dict(by_source),
            endpoint_wall_sec=v['wall_sec'],np=v['shared_constraints']['np'],nuf=v['shared_constraints']['nuf'],
            shared_feasible=v['shared_constraints']['feasible'],resource_max_exceedance=v['resource_max_exceedance'],
            gate_red_release=0.,boundary=boundary)
    difference=arms['city']['omega']-arms['hold']['omega']
    bd={}
    for route in arms['city']['boundary']['routes'].keys()|arms['hold']['boundary']['routes'].keys():
        c=arms['city']['boundary']['routes'].get(route,{})
        h=arms['hold']['boundary']['routes'].get(route,{})
        bd[route]={k:c.get(k,0)-h.get(k,0) for k in ('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')}
    totals={k:sum(v[k] for v in bd.values()) for k in next(iter(bd.values()))}
    assert abs(sum(totals[k] for k in ('entry_cost','departure_cost','generation_cost'))-difference)<1e-7
    native=previous['native_city_minus_hold_veh_h']
    report=dict(status='complete_combined_diagnostic_not_adopted',arms=arms,
        city_minus_hold_veh_h=difference,native_city_minus_hold_veh_h=native,
        prior_gate296_city_minus_hold_veh_h=previous['candidate_city_minus_hold_veh_h'],
        material_native_direction_matched=difference*native>0,
        boundary_delta=bd,boundary_delta_totals=totals,
        decision='Preserve independently supported local corrections and composite evidence, but do not claim full gain calibration or launch full optimization/native from this diagnostic.',
        next='Local source discharge improves but joint city-effect direction remains wrong. Use exact boundary decomposition to identify which modeled urban exit benefit remains unsupported; no further service-rate grid.',
        budget_used=dict(fixed450=2,optimizer=0,ad=0,native=0,fzp=0,new_coefficient_fits=0),
        limits=['Native and model temporal quadratures differ; each has its own verified conservation identity.',
                'Source witnesses297 are lower bounds at a downstream road, not identical head boundaries.',
                'No full AD or heldout composite qualification: this is not a production deployment.',
                'Gate296 aggregate-storage, initial-reservation and provisional5600 service limitations remain.'],
        source_pins={str(p):sha(p) for p in sources},goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('city_minus_hold_veh_h','native_city_minus_hold_veh_h','boundary_delta_totals')},ensure_ascii=False))
    print(json.dumps({a:{k:x[k] for k in ('heads','sc12_sources','shared_feasible')} for a,x in arms.items()},ensure_ascii=False))
    print('Largest boundary costs',sorted([(k,sum(v[f] for f in ('entry_cost','departure_cost','generation_cost'))) for k,v in bd.items()],key=lambda x:abs(x[1]),reverse=True)[:8])


if __name__=='__main__':
    main()
