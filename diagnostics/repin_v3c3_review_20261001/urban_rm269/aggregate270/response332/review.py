"""Review existing332 forecasts against3300--3750 saved observations only."""
from pathlib import Path
import gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.audit_native2400_components import ramp_stock,ramp_balance,count_link,PHYSICAL_GROUPS
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
HERE=Path(__file__).resolve().parent;A=HERE.parent
OUT=Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def main():
    assert not (HERE/'assessment.json').exists()
    summary=read(OUT/'summary.json')
    assert summary['status']=='complete' and summary['forecasts']==3
    assert summary['start_sec']==3300 and summary['end_sec']==3750
    for p,h in summary['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    cfg,state,forecast=pickle.loads((A/'transfer331/build3300_v2/initial.pickle').read_bytes())
    assignment=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    keys={g:{k for link in links for k in assignment.get(str(link),{})} for g,links in PHYSICAL_GROUPS.items()}
    keys['approach66'].add('transit:gate:in_SC1004_S')
    keys.update(ramp10681={'ramp:RM_C10681'},ramp10646={'ramp:RM_C10646'})
    flat=[k for v in keys.values() for k in v];assert len(flat)==len(set(flat))
    models={arm:read(OUT/(arm+'.json')) for arm in ('hold','release','recorded')}
    stocks={arm:read(OUT/(arm+'.stocks.json')) for arm in models}
    costs={};model_stocks={}
    for arm,m in models.items():
        assert m['conservation_states']==4 and m['writer_three_blocks'] and m['resource_max_exceedance']<1e-7
        r=read(OUT/(arm+'.response.json.gz'))
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
        c=m['costs_by_stock'];costs[arm]={g:sum(c.get(k,0.) for k in ks) for g,ks in keys.items()}
        costs[arm]['mainline']=sum(v for k,v in c.items() if k.startswith('freeway:'))
        costs[arm]['remaining_omega']=sum(c.values())-sum(costs[arm].values())
        costs[arm]['omega']=sum(c.values())
        assert abs(costs[arm]['omega']-m['omega_ttt_veh_h'])<1e-7
        model_stocks[arm]=[]
        for s in stocks[arm]:
            total={k:v['inside']+v['outside'] for k,v in s['stocks'].items()}
            model_stocks[arm].append(dict(sec=s['time_sec'],groups={g:sum(total.get(k,0.) for k in ks) for g,ks in keys.items()}))
    assert all(models[a]['shared_constraints']['feasible'] for a in ('hold','release'))
    for k in ('np','nuf'):
        assert models['hold']['shared_constraints'][k]['target']==models['release']['shared_constraints'][k]['target']
    source=Path(read(A/'transfer331/build3300_v2/summary.json')['source'])
    actual={'ramps':{r:[] for r in models['recorded']['predicted_merge']['accepted_vehicles_by_ramp']},'stocks':[]}
    previous=None
    for sec in (3300,3450,3600,3750):
        raw=read(source/f'state_{sec:06}.json');bundle=oc.load_bundle(raw)
        assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
        assert raw['vehicle_records']['record_count']==len(bundle.frame_end['vehicles'])
        if previous is not None:assert bundle.frame_start['vehicles']==previous['vehicles']
        previous=bundle.frame_end
        lanes={str(k):count_link(bundle.frame_end,k) for links in PHYSICAL_GROUPS.values() for k in links}
        groups={g:sum(sum(lanes[str(k)].values()) for k in links) for g,links in PHYSICAL_GROUPS.items()}
        groups.update({g:sum(sum(count_link(bundle.frame_end,k).values()) for k in links)
                       for g,links in {'ramp10681':(10681,),'ramp10646':(10646,)}.items()})
        actual['stocks'].append(dict(sec=sec,groups=groups,lanes_by_link=lanes))
        if sec==3300:continue
        obs=bundle.obs
        detectors,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
        oc.validate_raw(obs,detectors,expected_simres=oc.EXPECTED_SIMRES);check_rule_crosscheck(obs,detectors)
        boundaries=oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
        removed=oc.window_removals(bundle.err_rows,sec-150,sec)
        for ramp in actual['ramps']:
            link=int(ramp.removeprefix('RM_C'))
            heads=sorted((d for d in detectors if d.link==link and d.role=='meter_head'),key=lambda d:d.lane)
            assert heads
            positions={d.lane:d.geometry_assert['head_position_m'] for d in heads}
            v=ramp_balance(ramp_stock(bundle.frame_start,link,positions),ramp_stock(bundle.frame_end,link,positions),
                arrival=boundaries['ramp_arrival:'+ramp].cross,head_by_lane=[boundaries[d.boundary_ref].cross for d in heads],
                removed=sum(int(row['link'])==link for row in removed))
            v.update(start_sec=sec-150,end_sec=sec);actual['ramps'][ramp].append(v)
    initial_errors={g:model_stocks['recorded'][0]['groups'][g]-actual['stocks'][0]['groups'][g] for g in keys}
    # A reservoir may also own fractions of neighboring connectors. Keep the
    # original physical group visible; do not subtract a fixed future offset.
    support_extra={g:{link:sum(v for k,v in entries.items() if k in keys[g])
                      for link,entries in assignment.items()
                      if int(link) not in links and any(k in keys[g] and v for k,v in entries.items())}
                   for g,links in PHYSICAL_GROUPS.items()}
    for g,error in initial_errors.items():
        assert abs(error-sum(support_extra.get(g,{}).values()))<1e-7,(g,error)
    merge={r:dict(actual=sum(x['merge'] for x in rows),
                   model=models['recorded']['predicted_merge']['accepted_vehicles_by_ramp'][r],
                   arrivals=sum(x['arrival'] for x in rows),head=sum(x['head'] for x in rows),
                   removed=sum(x['removals'] for x in rows)) for r,rows in actual['ramps'].items()}
    response=[dict(sec=n['sec'],actual=n['groups'],model=m['groups'],
                   error={g:m['groups'][g]-n['groups'][g] for g in keys})
              for n,m in zip(actual['stocks'],model_stocks['recorded'])]
    delta={g:costs['release'][g]-costs['hold'][g] for g in costs['hold']}
    constraints={a:{k:models[a]['shared_constraints'][k] for k in ('np','nuf','feasible')} for a in models}
    result=dict(status='complete_bounded_response_review',goal_complete=False,production_adopted=False,
        window=[3300,3750],model_costs=costs,release_minus_hold_cost=delta,actual_recorded=actual,
        recorded_merge_comparison=merge,recorded_stock_comparison=response,model_stocks=model_stocks,
        initial_support_keys={g:sorted(v) for g,v in keys.items()},initial_group_errors=initial_errors,
        initial_additional_connector_support=support_extra,
        constraints=constraints,wall_sec={a:m['wall_sec'] for a,m in models.items()},
        physical_checks_passed=True,current_clock=dict(freeway_exchange_sec=5,urban_exchange_sec=10,control_sec=150,horizon_sec=450,terminal_cost=False,internal_stability_substeps_retained=True),
        limitations=[
          'RM pair is model-only: city/VSL/otherRM held, only10681 released; no native paired gain at3300.',
          'Recorded future actions condition one response; no future observed traffic enters predictions.',
          'Recorded NP violation compares updated prediction of three reoptimized actions to first3300 target; not a certificate that original controller violated its own predicted cap.',
          'Physical resource/inventory constraints and shared NP/NUF caps are distinct.',
          'Local groups use initial3300 physical support;52/58 reservoir additionally owns1vehicle10498 and0.5vehicle10565 initially. Report raw group differences, not an exact geographic error; never subtract a fixed future offset.68 alone is not wholeWout.',
          'Current counts are inventory, not stopped queues or arrivals. Meter-head passage is not merge.',
          'Only150s actual frames and detector intervals used here; no exact native450s TTT claimed.',
          'No AD/full-selection or independent-seed qualification of accumulated diagnostic model.'],
        budget=dict(forecasts450=3,new_review_forecasts=0,native=0,fzp=0,fits=0,ad=0,optimizer=0,push=0),
        source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('COST_DELTA',delta);print('ACTUAL10681',merge['RM_C10681'])
    print('RECORDED_STOCKS',response);print('WALL',result['wall_sec'])
if __name__=='__main__':main()
