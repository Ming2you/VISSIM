"""Bounded reuse of a past SC109 observation; no new fitted coefficient."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = HERE.parents[4]
MOVEMENT = 'SC109_W_SC108_to_N_SC16'


def install(cfg, at_sec=2400):
    paths = [H/'sc109_service/init2400/network.json',
             H/'sc109_service/initialization_verification.json',
             H/'sc109_service/lane_support.json', H/'sc109_service/head_resources.json']
    blobs = {str(p):p.read_bytes() for p in paths}
    network = json.loads(blobs[str(paths[0])])
    evidence = network['head_service_resources']
    row = evidence['resources']['10286']
    observation = evidence['observations']['10286']
    assert at_sec == observation['snapshot_sec'] == 2400
    assert observation['current_pair_support_veh_h'] == 0
    assert observation['pooled_observed_support_veh_h'] == observation['carried_observed_support_veh_h']
    assert row['mode']=='regular_unique' and set(row['members'])=={MOVEMENT}
    assert {h['lane'] for h in row['heads']}=={4,5}
    assert all(h['link']=='173' and h['sc']=='109' and h['sg']=='5' for h in row['heads'])
    actual = cfg.network.urban_movements[MOVEMENT]
    assert all(actual.get(k)==v for k,v in row['members'][MOVEMENT].items())
    turns = cfg.network.control_area_routes['movement:'+MOVEMENT]['physical_turns']
    assert len(turns)==1 and turns[0]['connector']=='10286' and turns[0]['from_link']=='173'
    assert turns[0]['to_link']=='1220009502'
    # The common phase also serves the opposing SG1; this resource owns SG5 only.
    assert set(cfg.network.signal_actuation_contract['nodes']['SC109']['phase_signal_groups']['p4'])=={'1','5'}
    proof = row['proof']
    assert hashlib.sha256((ROOT/proof['path']).read_bytes()).hexdigest()==proof['sha256']
    network_pin=evidence['network']
    network_path=ROOT/network_pin['path']
    assert hashlib.sha256(network_path.read_bytes()).hexdigest()==network_pin['sha256']
    floor = observation['observed_only_floor_veh_h']
    assert floor == 2000.0 and row['green_exposure_windows']==4
    before = cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT]
    updated = copy.copy(cfg.network.movement_capacity_by_movement_veh_h)
    updated[MOVEMENT] = max(before, floor)
    cfg.network.movement_capacity_by_movement_veh_h = updated
    pins={p:hashlib.sha256(b).hexdigest() for p,b in blobs.items()}
    pins[str(network_path)]=network_pin['sha256']
    # These are the actual causal-history files consumed by the saved initialization.
    for p in (H/'sc109_service/init2400/head_history').iterdir():
        if p.is_file(): pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(movement=MOVEMENT,before_veh_h=before,after_veh_h=updated[MOVEMENT],
                support=observation,source_pins=pins,
                scope='One physical movement service floor only; same queues, arrivals, receiving and objective. Old3300 overprediction remains unqualified.')
