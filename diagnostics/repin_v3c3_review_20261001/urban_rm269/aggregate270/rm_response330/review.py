"""Compare330 joint to cached329 city and closed native outcomes."""
from pathlib import Path
import gzip,hashlib,json,math,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.rm_response330.scope import BASE,RUNS,NATIVE_CITY
from diagnostics.repin_v3c3_review_20261001.urban_rm269.audit_native2400_components import ramp_stock,ramp_balance,count_link,PHYSICAL_GROUPS
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
OUT=Path('E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2')
PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def cost_groups(costs,footprint):
    keys={k:set(v['initial_model_stock_keys']) for k,v in footprint.items()}
    keys['approach66'].add('transit:gate:in_SC1004_S')
    keys.update(ramp10681={'ramp:RM_C10681'},ramp10646={'ramp:RM_C10646'})
    result={k:sum(costs.get(x,0.) for x in vv) for k,vv in keys.items()}
    result['mainline']=sum(v for k,v in costs.items() if k.startswith('freeway:'))
    result['remaining_omega']=sum(costs.values())-sum(result.values());result['omega']=sum(costs.values())
    return result,keys

def main():
    assert not (HERE/'assessment.json').exists()
    summary=read(OUT/'summary.json');old=read(BASE/'summary.json')
    assert summary['new_forecasts']==1 and summary['start_sec']==2400 and summary['end_sec']==2850
    for s in (summary,old):
        for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    scope=read(OUT/'scope.json')
    assert scope['whole_RM_vector_not_single10681']
    native_city=read(NATIVE_CITY/'cached_summary.json')
    audit=read(H/'native2400_analysis/component_audit.json')
    foot=read(H/'native2400_component_footprint.json')['groups']
    mm={'joint':read(OUT/'joint.json'),'city':read(BASE/'city.json')}
    responses={'joint':read(OUT/'joint.response.json.gz'),'city':read(BASE/'city.response.json.gz')}
    modeled={};checks={}
    for arm,r in responses.items():
        x=mm[arm];assert x['conservation_states']==4 and x['writer_three_blocks'] and x['shared_constraints']['feasible']
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
        assert x['resource_max_exceedance']<1e-7
        modeled[arm],keys=cost_groups(x['costs_by_stock'],foot)
        outside=sum((sum(t['model_stock_veh'].values())-sum(t['inside_veh'].values()))*t['dt_h'] for t in r['residence'])
        checks[arm]=dict(model_tracked_outside_residence=outside,
            conservation_states=4,NP_NUF=True,writer_blocks=3,resource_max_exceedance=x['resource_max_exceedance'],
            merge=x['predicted_merge']['accepted_vehicles_by_ramp'])
    model_delta={k:modeled['joint'][k]-modeled['city'][k] for k in modeled['city']}
    mapping=read(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    physical={**PHYSICAL_GROUPS,'ramp10681':(10681,),'ramp10646':(10646,),
        'mainline':tuple({int(k) for v in mapping['freeway_model_links'].values() for k in v['chain_links']})}
    all_links=[x for v in physical.values() for x in v];assert len(all_links)==len(set(all_links))
    native={};native_metric={}
    for arm,p in [('joint',H/'native2400_analysis/selected/area_metrics.json'),('city',NATIVE_CITY/'selected/area_metrics.json')]:
        m=read(p);native_metric[arm]=m;r=m['physical_link_residence']
        assert all(r[str(k)]['inside'] for k in all_links)
        native[arm]={g:sum(r[str(k)]['ttt_veh_h'] for k in kk) for g,kk in physical.items()}
        native[arm]['remaining_omega']=m['ttt_veh_h']-sum(native[arm].values());native[arm]['omega']=m['ttt_veh_h']
    native_delta={k:native['joint'][k]-native['city'][k] for k in native['city']}
    assert abs(native_delta['omega']-scope['native_delta_omega_veh_h'])<1e-8
    # Current-frame and detector ledger only. No FZP read and no new simulation.
    city_actual={'ramps':{r:[] for r in checks['city']['merge']},'physical_link_stocks':[]}
    for sec in (2400,2550,2700,2850):
        p=RUNS['city']/f'state_{sec:06}.json';raw=read(p);bundle=oc.load_bundle(raw)
        assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
        lanes={str(k):count_link(bundle.frame_end,k) for vv in PHYSICAL_GROUPS.values() for k in vv}
        city_actual['physical_link_stocks'].append(dict(sim_sec=sec,lanes_by_link=lanes,
            grouped_total_vehicles={g:sum(sum(lanes[str(k)].values()) for k in kk) for g,kk in PHYSICAL_GROUPS.items()}))
        if sec==2400:continue
        obs=bundle.obs;detectors,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
        oc.validate_raw(obs,detectors,expected_simres=oc.EXPECTED_SIMRES);check_rule_crosscheck(obs,detectors)
        boundaries=oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
        removed=oc.window_removals(bundle.err_rows,sec-150,sec)
        for ramp in city_actual['ramps']:
            link=int(ramp.removeprefix('RM_C'))
            heads=sorted((d for d in detectors if d.link==link and d.role=='meter_head'),key=lambda d:d.lane)
            assert heads and [d.lane for d in heads]==list(range(1,len(heads)+1))
            positions={d.lane:d.geometry_assert['head_position_m'] for d in heads}
            result=ramp_balance(ramp_stock(bundle.frame_start,link,positions),ramp_stock(bundle.frame_end,link,positions),
                arrival=boundaries['ramp_arrival:'+ramp].cross,
                head_by_lane=[boundaries[d.boundary_ref].cross for d in heads],
                removed=sum(int(r['link'])==link for r in removed))
            result.update(start_sec=sec-150,end_sec=sec);city_actual['ramps'][ramp].append(result)
    native_ramps={'joint':audit['arms']['selected']['ramps'],'city':city_actual['ramps']}
    ramps={}
    for ramp in native_ramps['city']:
        actual={a:sum(x['merge'] for x in data[ramp]) for a,data in native_ramps.items()}
        predicted={a:x['merge'][ramp] for a,x in checks.items()}
        ramps[ramp]=dict(native=actual,model=predicted,native_delta=actual['joint']-actual['city'],
            model_delta=predicted['joint']-predicted['city'])
    model_stocks={};initial=summary['initial_stocks']
    for arm,r in responses.items():
        model_stocks[arm]=[]
        for sec in (2400,2550,2700,2850):
            if sec==2400:stock={k:v['inside']+v['outside'] for k,v in initial.items()}
            else:
                rows=[x for x in r['residence'] if abs(x['end_sec']-sec)<1e-7];assert len(rows)==1
                stock=rows[0]['model_stock_veh']
            model_stocks[arm].append(dict(sec=sec,initial_support={g:sum(stock.get(k,0.) for k in kk) for g,kk in keys.items()}))
    current_actual={'joint':audit['arms']['selected']['physical_link_stocks'],'city':city_actual['physical_link_stocks']}
    spatial=[]
    for i,sec in enumerate((2400,2550,2700,2850)):
        delta={g:current_actual['joint'][i]['grouped_total_vehicles'][g]-current_actual['city'][i]['grouped_total_vehicles'][g] for g in PHYSICAL_GROUPS}
        md={g:model_stocks['joint'][i]['initial_support'][g]-model_stocks['city'][i]['initial_support'][g] for g in PHYSICAL_GROUPS}
        spatial.append(dict(sec=sec,native_total_stock_delta=delta,model_initial_support_delta=md))
    result=dict(status='complete_latest_RM_response_direction_preserved',goal_complete=False,production_adopted=False,
        start_sec=2400,end_sec=2850,delta_definition='joint minus city; urban/VSL/caps identical; whole RM vector',
        model_cost_delta=model_delta,native_cost_delta=native_delta,ramp_merges=ramps,
        model_checks=checks,local_stocks=spatial,native_city_component_data=city_actual,
        outside_costs=dict(native_observed_delta=native_city['comparison']['native_joint_minus_hold_veh_h']*0
            +(sum(v['ttt_veh_h'] for v in native_metric['joint']['physical_link_residence'].values() if not v['inside'])
             -sum(v['ttt_veh_h'] for v in native_metric['city']['physical_link_residence'].values() if not v['inside'])),
            modeled_tracked_delta=checks['joint']['model_tracked_outside_residence']-checks['city']['model_tracked_outside_residence'],
            scopes_equal=False,uninserted_native_cost_known=False),
        old_RM_prediction_delta=native_city['comparison']['model_joint_minus_city_veh_h'],
        budget=dict(completed_new_forecasts450=1,reused_city_forecasts=1,unit_tests=3,native=0,fzp=0,fits=0,ad=0,optimizer=0,push=0),
        limitations=['52+58 and W_out keys use initial physical support; they are not exact geographic attribution after new routes mix.',
                    'Native ramp merge is conservation-derived whole-connector outflow, not meter-head passage.',
                    'One development state and executed controls; not isolated10681 or unseen-state joint selection qualification.',
                    '5s native quadrature includes final4.9s held tail; model uses10s urban end-stock quadrature.',
                    'Original older microscopic-history bit-exact failure preserved; current aggregate inputs and new paired native prefixes verified.',
                    'Outside model tracked population and native observed outside population differ; do not subtract them into a false all-network total.',
                    'Latest accumulated diagnostic model is not production-adopted and has no new AD/full-selection qualification.'],
        source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('RM_DELTA_COSTS_NATIVE',native_delta)
    print('RM_DELTA_COSTS_MODEL',model_delta)
    print('RM10681',ramps['RM_C10681'])
    print('STOCK_DELTA',spatial)
    print('OUTSIDE',result['outside_costs'])

if __name__=='__main__':main()

