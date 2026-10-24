"""Reuse two closed responses and existing native metrics; no new forecasts."""
from pathlib import Path
import gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary
HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')
OLD=Path('E:/VISSIM_analysis/20261010_sc12_phase305/forecast2400')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'comparison.json').exists()
    new,old=read(OUT/'summary.json'),read(OLD/'summary.json')
    assert new['status']=='complete' and new['canonical_state_error_before_projection']==0 and new['forecasts']==2
    assert new['fits']==new['native_runs']==new['optimizer_calls']==0
    for p,h in new['source_pins'].items():assert sha(p)==h,p
    cfg,_,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    initial=read(A/'matched280/authority/hold.stocks.json')[0]
    truth=read(A/'cityresponse290/assessment.json')
    wanted={'movement:SC6_S_SC12_to_N_SC103','movement:SC6_S_SC12_to_E_SC104'}
    west={'movement:SC12_W_SC11_to_N_SC6','movement:SC12_W_to_N_SC6'}
    arms={};boundaries={};pins={}
    for version,folder,doc in (('old',OLD,old),('new',OUT,new)):
        boundaries[version]={}
        for arm in ('hold','city'):
            v=doc['results'][arm]
            assert v['writer_three_blocks'] and v['shared_constraints']['feasible']
            assert v['conservation_states']==4 and v['resource_max_exceedance']<1e-7
            path=folder/(arm+'.response.json.gz');pins[str(path)]=sha(path)
            r=json.loads(gzip.decompress(path.read_bytes()))
            assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
            rows=[t for t in r['transfers'] if t['source'] in wanted and t['source']!=t['target']]
            counts=[sum(t['vehicles'] for t in rows if sec<=t['start_sec']<sec+150) for sec in (2400,2550,2700)]
            native=[x['actual'] for x in truth['head_counts'][arm] if x['group']=='SC6_S' and x['phase']=='p1']
            w=[t for t in r['transfers'] if t['source'] in west and t['target']=='storage:SC12_to_SC6']
            final={'stocks':{k:dict(inside=n) for k,n in r['residence'][-1]['inside_veh'].items()}}
            b=model_boundary(r,[initial,final],v['omega_ttt_veh_h'],cfg);boundaries[version][arm]=b
            costs=v['costs_by_stock']
            arms.setdefault(arm,{})[version]=dict(omega_ttt=v['omega_ttt_veh_h'],sc6_p1_blocks=counts,
                sc6_native_blocks=native,sc6_mae=sum(abs(a-b) for a,b in zip(counts,native))/3,
                sc6_head_time_cost=-sum(t['vehicles']*(2850-t['start_sec'])/3600 for t in rows),
                west_blocks=[sum(t['vehicles'] for t in w if sec<=t['start_sec']<sec+150) for sec in (2400,2550,2700)],
                final_omega_stock=sum(x['inside'] for x in final['stocks'].values()),
                mainline_cost=sum(n for k,n in costs.items() if k.startswith('freeway:')),
                ramp_cost=sum(n for k,n in costs.items() if k.startswith('ramp:')),
                predicted_merge=v['predicted_merge'],endpoint_wall_seconds=v['wall_sec'])
    deltas={mode:arms['city'][mode]['omega_ttt']-arms['hold'][mode]['omega_ttt'] for mode in ('old','new')}
    routes={}
    for version,b in boundaries.items():
        routes[version]={}
        for key in b['city']['routes'].keys()|b['hold']['routes'].keys():
            d={k:b['city']['routes'].get(key,{}).get(k,0)-b['hold']['routes'].get(key,{}).get(k,0)
               for k in ('entry_cost','departure_cost','generation_cost')}
            if max(abs(x) for x in d.values())>1e-9:routes[version][key]=d
        assert abs(sum(sum(d.values()) for d in routes[version].values())-deltas[version])<1e-7
    cost_changes={}
    for arm in ('hold','city'):
        a=old['results'][arm]['costs_by_stock'];b=new['results'][arm]['costs_by_stock']
        cost_changes[arm]={k:b.get(k,0)-a.get(k,0) for k in a.keys()|b.keys() if abs(b.get(k,0)-a.get(k,0))>1e-8}
    for p in (OUT/'summary.json',OLD/'summary.json',OUT/'initial_projection.json',HERE/'tests_v3.log',
              HERE/'candidate.py',Path(__file__),A/'cityresponse290/assessment.json'):
        pins[str(p)]=sha(p)
    result=dict(status='complete_current_route_projection_pair',goal_complete=False,
        arms=arms,omega_delta_veh_h=deltas,native_omega_delta_veh_h=5.28666666666649,
        boundary_routes=routes,changed_cost_by_stock=cost_changes,initial_projection=read(OUT/'initial_projection.json'),
        source_pins=pins,budget=dict(full450=2,new_fits=0,optimizer=0,ad=0,native=0,fzp_scans=0),
        limitations=['Only current terminal-link cohort corrected; upstream five vehicles unchanged.',
          'Unknown destination remains explicit lane-conditioned prior; no future observed route input.',
          'SC6 head passage is not an Omega exit. Native and model boundaries retain prior definitions.',
          'Fixed command development-state response; not a full optimizer or native gain validation.'])
    (HERE/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('OMEGA',deltas,'native',result['native_omega_delta_veh_h'])
    print('SC6/WEST',{a:{v:{k:d[k] for k in ('sc6_p1_blocks','sc6_mae','west_blocks')} for v,d in x.items()} for a,x in arms.items()})
if __name__=='__main__':main()
