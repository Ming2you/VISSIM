"""One past-observed physical service floor, with no future data or bonus."""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
MOVEMENT='SC108_W_to_E_SC109'


def install(cfg, at_sec):
    path=HERE/'support.json'
    doc=json.loads(path.read_bytes())
    assert doc['status']=='past_only_service_floor' and not doc['future_inputs']
    assert doc['cutoff_sec']<=at_sec and all(r['end']<=at_sec for r in doc['blocks'])
    for p,h in doc['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    m=cfg.network.urban_movements[MOVEMENT]
    assert m['origin']=='in_SC108_W' and m['destination']==m['receiving_link']=='SC108_to_SC109'
    assert m['phase']=='SC108_p3' and m['beta']==1.0 and not m.get('unsignalized',False)
    route=cfg.network.control_area_routes['movement:'+MOVEMENT]
    turns=route['physical_turns']
    assert len(turns)==1
    assert all(turns[0][k]==v for k,v in doc['physical_route'].items() if k!='phase')
    assert '2' in cfg.network.signal_actuation_contract['nodes']['SC108']['phase_signal_groups']['p3']
    before=cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT]
    after=max(before,doc['achieved_floor_veh_h'])
    cfg.network.movement_capacity_by_movement_veh_h=copy.copy(cfg.network.movement_capacity_by_movement_veh_h)
    cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT]=after
    pins=dict(doc['source_pins']);pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(movement=MOVEMENT,before_veh_h=before,after_veh_h=after,source_pins=pins,
                scope='Past achieved throughput floor only; no changes to demand, initial stock, routes, timing, receiving or costs.')
