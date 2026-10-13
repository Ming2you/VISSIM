"""Review completed340 forecasts; no model call or future-data assimilation."""
from pathlib import Path
from collections import defaultdict
import gzip, hashlib, json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.flow_scope333.groups import boundary_ledger, stock_total

HERE=Path(__file__).resolve().parent
A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
NEW=HERE/'forecast3300_v2'
PINS={}

def read(path):
    path=Path(path); data=path.read_bytes()
    PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)

def main():
    assert not (HERE/'assessment.json').exists(), 'Preserve completed review'
    proof=read(NEW/'summary.json')
    assert proof['status']=='complete' and proof['forecasts']==3
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in proof['source_pins'].items())
    assert read(NEW/'commands.json')==read(OLD/'commands.json')
    native=read(A/'flow_scope333/assessment.json')
    previous=read(A/'response332/assessment.json')
    groups={k:set(v) for k,v in native['group_keys'].items()}
    groups.update({k:set(v) for k,v in previous['initial_support_keys'].items() if k!='approach52_with58'})
    service=read(A/'flow_scope333/service_review.json')
    service_by={(r['start_sec'],r['movement']):r for r in service['rows']}
    target='SC105_N_SC1002_to_S_SC1005'
    ports={'headfree:10565':'SC1005_N_SC105_to_W_SC1004','headfree:10570':'SC1005_N_SC105_to_E_SC107'}
    models={}
    for version,root in (('old332',OLD),('current340',NEW)):
        models[version]={}
        for arm in ('hold','release','recorded'):
            scalar=read(root/(arm+'.json')); stocks=read(root/(arm+'.stocks.json'))
            response=read(root/(arm+'.response.json.gz'))
            assert scalar['conservation_states']==4 and scalar['writer_three_blocks']
            assert scalar['resource_max_exceedance']<1e-7
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            c=scalar['costs_by_stock']
            assert abs(sum(c.values())-scalar['omega_ttt_veh_h'])<1e-7
            windows=[]
            for j,start in enumerate((3300,3450,3600)):
                row={'start_sec':start,'end_sec':start+150,'groups':{}}
                for group,keys in groups.items():
                    balance=boundary_ledger(response['transfers'],keys,start,start+150)
                    balance.update(initial=stock_total(stocks[j],keys),final=stock_total(stocks[j+1],keys))
                    error=balance['initial']+balance['incoming']-balance['outgoing']-balance['final']
                    assert abs(error)<1e-7,(version,arm,group,start,error)
                    balance['error']=error;row['groups'][group]=balance
                resources=[x for x in response['resource_allocations'] if x['resource']==target and
                           x['kind']=='urban_movement_intended_limit' and start<=x['start_sec'] and x['end_sec']<=start+150]
                assert len(resources)==15
                row['SC105_north_through']=sum(x['accepted_total_veh'] for x in resources)
                row['SC105_north_receiving_loss']=sum(x['available_veh']-x['accepted_total_veh'] for x in resources)
                if arm=='recorded' and version=='old332':
                    assert abs(row['SC105_north_through']-service_by[start,target]['accepted'])<1e-7
                row['ports']={port:sum(x['vehicles'] for x in response['transfers'] if
                        x['source']=='movement:'+movement and x['target'] not in groups['parent_SC105_to_SC1005'] and
                        start<=x['start_sec'] and x['end_sec']<=start+150) for port,movement in ports.items()}
                windows.append(row)
            models[version][arm]=dict(omega=scalar['omega_ttt_veh_h'],
                costs={g:sum(c.get(k,0.) for k in keys) for g,keys in groups.items()},
                merge10681=scalar['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
                constraints={k:scalar['shared_constraints'][k] for k in ('np','nuf','feasible')},
                outside_ttt=sum(scalar['outside_costs_by_stock'].values()),
                windows=windows,wall_sec=scalar['wall_sec'])
    delta={v:dict(omega=m['release']['omega']-m['hold']['omega'],
                 merge10681=m['release']['merge10681']-m['hold']['merge10681'],
                 costs={g:m['release']['costs'][g]-m['hold']['costs'][g] for g in groups}) for v,m in models.items()}
    comparisons=[]
    for j,n in enumerate(native['native'][1:]):
        heads=n['upstream_heads']; lower=sum(heads[k]['cross'] for k in ('head:1050401','head:1050402'))
        upper=lower+heads['head:1050403']['cross']
        comparisons.append(dict(start_sec=n['sec']-150,native_through_exclusive_lower=lower,
            native_through_with_all_shared_upper=upper,native_parent_entries=n['entries_balance_derived'],
            native_parent_exits=n['exits'],native_ports={k:r['cross'] for k,r in n['boundary'].items()},
            model={v:dict(through=m['recorded']['windows'][j]['SC105_north_through'],
                         ports=m['recorded']['windows'][j]['ports'],
                         parent=m['recorded']['windows'][j]['groups']['parent_SC105_to_SC1005']) for v,m in models.items()}))
    checks=read(HERE/'check.json')
    projections={t:{k:r[k] for k in ('physical_vehicles','source_vehicles','ready_before','ready_after','moved_queue_to_storage','retained_posthead')}
                 for t,r in checks['results'].items()}
    assert all(models[v][a]['constraints']['feasible'] for v in models for a in ('hold','release'))
    assert not any(models[v]['recorded']['constraints']['feasible'] for v in models)
    result=dict(status='review_complete',goal_complete=False,production_adopted=False,
        projections=projections,model=models,release_minus_hold=delta,recorded_comparison=comparisons,
        rm_delta_change=delta['current340']['omega']-delta['old332']['omega'],
        command_equality=True,source_pins=PINS,
        verdict='Current-position/turn projection improves local timing; it does not repair material whole-Omega gain error.',
        limitations=[
          'Native head bounds are turn-identification bounds, not exact downstream connector departure times.',
          'Recorded actions are conditional response diagnostics. Their initial3300 NP cap is exceeded in both versions; not feasible selected policies.',
          'Hold/release are same-state10681-only model comparisons, not new paired native observations.',
          'Other-state checks cover initial conservation, not450s out-of-sample dynamics.',
          'Within-lane FIFO/start-wave is not solved. Existing post-head reservations remain approximate.',
          'Three forecasts were already completed; this review adds zero forecasts, AD, optimizations, fits, FZP reads or native runs.'])
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('RM_DELTA',delta)
    print('SC105_TIMING',[(r['start_sec'],r['native_through_exclusive_lower'],{v:x['through'] for v,x in r['model'].items()}) for r in comparisons])
    for v,m in models.items():
        print(v,'port10565',sum(w['ports']['headfree:10565'] for w in m['recorded']['windows']),
              'NP_recorded',m['recorded']['constraints']['np']['violation'],
              '52cost',m['recorded']['costs']['approach52_all_origins'])

if __name__=='__main__':main()
