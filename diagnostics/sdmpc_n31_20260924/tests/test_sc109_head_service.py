"""Measured boundary exits use their own native heads once; outside queues remain."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from evaluation.controllers import head_service_resources as service

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/sc109_capacity_20260929/head_resources.json'


def fixture():
    doc = json.loads(CONTRACT.read_bytes())
    movements = {name: dict(spec, beta=1.) for row in doc['resources'].values()
                 if row['mode'] in ('regular_unique', 'regular_exit')
                 for name, spec in row['members'].items()}
    cfg = NS(network=NS(urban_movements=movements,
        urban_link_storage_veh={'SC1001_W_out': 100., 'SC1004_W_out': 100., 'SC109_E_out':220.},
        movement_capacity_by_movement_veh_h={m: 619.5918 for m in movements}))
    tuning = {'urban': {'shared_local_service_pool': True, 'capacity': {
        'head_observation': {'enabled': True}, 'head_resource_contract': str(CONTRACT)}}}
    plan = {'controllers': {'1001': {'phase_signal_groups': {'p2': ['3']}},
        '1004': {'phase_signal_groups': {'p2': ['3'], 'p3': ['6']}},
        '107': {'phase_signal_groups': {'p3': ['6']}},
        '109': {'phase_signal_groups': {'p2': ['7'], 'p3': ['2','6'], 'p4': ['5']}}}}
    return cfg, tuning, {'network_path': str(ROOT/doc['network']['path'])}, plan


def test_two_native_exit_heads_update_only_their_unique_consumers():
    cfg, tuning, raw, plan = fixture()
    before = copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    service.configure(cfg, tuning, raw, plan)
    doc = service.view(cfg)
    doc['resources'] = {k:v for k,v in doc['resources'].items() if v['mode']=='regular_exit'}
    doc['observations'] = {k: {'observed_only_floor_veh_h': 3000.} for k in doc['resources']}
    service.finalize(cfg)
    for name in ('SC109_W_SC108_to_E','SC109_N_SC16_to_E'):
        before[name] = 3000.
    assert cfg.network.movement_capacity_by_movement_veh_h == before
    assert doc['extra_pool_groups'] == {}  # each head has exactly one consumer


@pytest.mark.parametrize('bad', ['competitor', 'receiver', 'phase'])
def test_exit_service_cannot_be_copied_or_used_as_internal_service(bad):
    cfg, tuning, raw, plan = fixture()
    member = cfg.network.urban_movements['SC109_W_SC108_to_E']
    if bad == 'competitor': cfg.network.urban_movements['alias'] = dict(member)
    if bad == 'receiver': member['receiving_link'] = 'SC1001_W_out'
    if bad == 'phase': member['phase'] = 'SC109_p4'
    with pytest.raises(ValueError): service.configure(cfg, tuning, raw, plan)


@pytest.mark.parametrize('bad', ['lane', 'target', 'membership'])
def test_changed_physical_exit_evidence_is_rejected(tmp_path, bad):
    cfg, tuning, raw, plan = fixture()
    doc = json.loads(CONTRACT.read_bytes()); row = doc['resources']['10285']
    if bad == 'lane': row['heads'][0]['lane'] = 4
    if bad == 'target': row['target_link'] = '1220009502'
    if bad == 'membership': row['membership']['sha256'] = '0'*64
    path = tmp_path/'bad.json'; path.write_text(json.dumps(doc))
    tuning['urban']['capacity']['head_resource_contract'] = str(path)
    with pytest.raises(ValueError): service.configure(cfg, tuning, raw, plan)
