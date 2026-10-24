"""Export reviewed historical constants, never a saved traffic state, for native348."""
from pathlib import Path
import hashlib,json,pickle

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]

def main():
    path=A/'worker334/capture_v2/request.pickle'
    request=pickle.loads(path.read_bytes())
    net=request['owned'][0].cfg.network
    groups={k:v for k,v in net.regular_alias_pool['groups'].items()
            if k in ('1220012103:10242:p4:typed','1220011200:180601:p3')}
    movements={m for g in groups.values() for m in g['members']}
    floors=('SC101_S_SC1_to_N_SC2005','SC109_W_SC108_to_N_SC16','SC108_W_to_E_SC109')
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import settings
    rates,evidence=settings()
    support_path=A/'sc101_route_tags303/support.json'
    support=json.loads(support_path.read_bytes())
    sc16_path=A/'sc16_aggregate323/support.json'
    sc16=json.loads(sc16_path.read_bytes())
    assert sc16['service_after_veh_h']==min(r['left_achieved_veh_h'] for r in sc16['rows'][-2:])
    assert abs(sum(sc16['beta_after'].values())-1)<1e-12
    assert all(net.urban_movements[m]['beta']==b for m,b in sc16['beta_after'].items())
    # Validate the historical support once, at its original training cutoff.
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_route_tags303.candidate import validate
    validate(request['owned'][0].cfg,3300,support)
    native={s['decision']:s['native_fixed_service']['calibrated_service_veh_h']
            for s in net.route_choice_corridor['corridors'] if s['decision'] in ('1099','1100')}
    data=dict(schema='calibrated-urban-native348/v1',
        training='Prior closed seed29 runs; fixed before the new runs. This is an in-sample experiment, not held-out validation.',
        historical_cutoff_sec=2400,
        network=net.regular_alias_pool['network'],
        shared_groups=groups,
        movement_rates={m:net.movement_capacity_by_movement_veh_h[m] for m in sorted(movements)},
        service_floors={m:net.movement_capacity_by_movement_veh_h[m] for m in floors},
        movement_contracts={m:net.urban_movements[m] for m in sorted(movements|set(floors))},
        peeloff=dict(movement='SC101_S_SC1_to_E_SC5',spec=net.urban_movements['SC101_S_SC1_to_E_SC5']),
        native_fixed_service=native,branch_service=rates,
        source_route_support={k:v for k,v in support.items() if k!='source_pins'},
        sc16={k:sc16[k] for k in ('beta_before','beta_after','service_before_veh_h','service_after_veh_h','cutoff_sec')},
        provenance={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (path,support_path,evidence,sc16_path)},
        omitted=['342 competing hypotheses','343/345 unqualified local rate candidates'],
        projection='Current paused records only: 306,339,323,325/339,340',
        rollout='299/303,311,317,296,325,329 and static347')
    target=HERE/'calibration.json'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('BUNDLE',target,'sha256',hashlib.sha256(target.read_bytes()).hexdigest())

if __name__=='__main__':main()
