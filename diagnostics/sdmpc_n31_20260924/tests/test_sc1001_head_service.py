"""A measured unique boundary-out service must not disappear in the kind filter."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from evaluation.controllers import head_service_resources as service
from evaluation.controllers import signal_head_observation as observer

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/head_service_resource_10698.json'
NAME = 'SC1001_S_SC1003_to_W_RAMP'


def fixture():
    doc = json.loads(CONTRACT.read_bytes())
    member = copy.deepcopy(doc['resources']['10698']['members'][NAME])
    member['beta'] = .755
    cfg = NS(network=NS(urban_movements={NAME: member},
        urban_link_storage_veh={'SC1001_W_out': 100.},
        movement_capacity_by_movement_veh_h={NAME: 206.53, 'unrelated': 999.}))
    tuning = {'urban': {'shared_local_service_pool': True, 'capacity': {
        'head_observation': {'enabled': True}, 'head_resource_contract': str(CONTRACT)}}}
    raw = {'network_path': str(ROOT/doc['network']['path'])}
    plan = {'controllers': {'1001': {'phase_signal_groups': {'p2': ['3']}},
        '1004': {'phase_signal_groups': {'p3': ['6']}}, '107': {'phase_signal_groups': {'p3': ['6']}}}}
    return cfg, tuning, raw, plan


def test_exact_native_boundary_out_resource_accepts_one_service():
    cfg, tuning, raw, plan = fixture()
    service.configure(cfg, tuning, raw, plan)
    doc = service.view(cfg)
    doc['resources'] = {'10698': doc['resources']['10698']}
    doc['observations'] = {'10698': {'observed_only_floor_veh_h': 1800.}}
    service.finalize(cfg)
    assert cfg.network.movement_capacity_by_movement_veh_h == {NAME: 1800., 'unrelated': 999.}
    assert doc['extra_pool_groups'] == {}


def test_pool_is_local_to_the_verified_head():
    cfg, tuning, raw, plan = fixture()
    service.configure(cfg, tuning, raw, plan)
    assert observer.green_exposure_windows(cfg, ('40', 'p2')) == 4
    assert observer.green_exposure_windows(cfg, ('40', 'p1')) == 0
    assert observer.green_exposure_windows(cfg, ('52', 'p3')) == 0
    cfg.network.head_green_exposure_windows = 6
    assert observer.green_exposure_windows(cfg, ('40', 'p2')) == 4
    assert observer.green_exposure_windows(cfg, ('52', 'p3')) == 6


def test_competing_model_movement_rejected():
    cfg, tuning, raw, plan = fixture()
    cfg.network.urban_movements['phantom'] = dict(cfg.network.urban_movements[NAME])
    with pytest.raises(ValueError, match='another model consumer'):
        service.configure(cfg, tuning, raw, plan)


def test_local_pool_reaches_installed_observer_without_global_enable(tmp_path):
    from diagnostics.test_signal_observation_window_patch import InstalledConsumerTests, OPTIONS, save_previous
    cfg, raw, plan, distribute = InstalledConsumerTests().fixture(tmp_path, green=20, count=10, start=300, end=450)
    cfg.network.head_service_resources = {'resources': {'test': {'group':'66|p1','green_exposure_windows':4}}}
    prior = tmp_path/'prior.json'
    for i, count in enumerate((10, 12, 9, 12)):
        raw['sim_sec'] = 450+i*150
        w = raw['local_observation']['signal_observation_window']
        w.update(start_sec=raw['sim_sec']-150, end_sec=raw['sim_sec'])
        w['heads'][0].update(crossings=count, qualified_crossings=count)
        meta = observer.install(cfg, raw, prior if prior.exists() else None, {'through':200.}, plan, distribute, OPTIONS)
        save_previous(prior, meta)
        if i < 3: assert cfg.network.movement_capacity_by_movement_veh_h['through'] == 200.
    assert cfg.network.movement_capacity_by_movement_veh_h['through'] == pytest.approx(3600*21/40)
    # Removing the local opt-in must not carry the pooled rate into the default path.
    del cfg.network.head_service_resources
    cfg.network.movement_capacity_by_movement_veh_h = {'through':200.}
    raw['sim_sec'] += 150
    w.update(start_sec=raw['sim_sec']-150, end_sec=raw['sim_sec'])
    observer.install(cfg, raw, prior, {'through':200.}, plan, distribute, OPTIONS)
    assert cfg.network.movement_capacity_by_movement_veh_h['through'] == 200.


@pytest.mark.parametrize('bad', ['phase', 'receiver', 'pool', 'lane'])
def test_invalid_boundary_resource_rejected(tmp_path, bad):
    cfg, tuning, raw, plan = fixture()
    doc = json.loads(CONTRACT.read_bytes()); row = doc['resources']['10698']
    if bad == 'phase': row['members'][NAME]['phase'] = 'SC1001_p1'
    if bad == 'receiver': row['receiver'] = 'SC1001_to_SC2002'
    if bad == 'pool': row['green_exposure_windows'] = 3
    if bad == 'lane': row['heads'][0]['lane'] = 3
    p = tmp_path/'bad.json'; p.write_text(json.dumps(doc))
    tuning['urban']['capacity']['head_resource_contract'] = str(p)
    with pytest.raises(ValueError): service.configure(cfg, tuning, raw, plan)


def combined_fixture():
    cfg, tuning, raw, plan = fixture()
    path = CONTRACT.with_name('head_service_resource_10633_10698.json')
    doc = json.loads(path.read_bytes())
    other = 'SC1004_S_to_W'
    cfg.network.urban_movements[other] = dict(doc['resources']['10633']['members'][other], beta=.27)
    cfg.network.urban_link_storage_veh['SC1004_W_out'] = 100.
    cfg.network.movement_capacity_by_movement_veh_h[other] = 206.53
    plan['controllers']['1004']['phase_signal_groups']['p2'] = ['3']
    tuning['urban']['capacity']['head_resource_contract'] = str(path)
    return cfg, tuning, raw, plan


def test_two_unique_heads_keep_separate_service_and_local_history():
    cfg, tuning, raw, plan = combined_fixture()
    service.configure(cfg, tuning, raw, plan)
    doc = service.view(cfg)
    doc['resources'] = {k: doc['resources'][k] for k in ('10633', '10698')}
    doc['observations'] = {'10633': {'observed_only_floor_veh_h': 1330.},
                           '10698': {'observed_only_floor_veh_h': 1800.}}
    service.finalize(cfg)
    assert cfg.network.movement_capacity_by_movement_veh_h == {
        NAME: 1800., 'SC1004_S_to_W': 1330., 'unrelated': 999.}
    assert doc['extra_pool_groups'] == {}
    assert observer.green_exposure_windows(cfg, ('40', 'p2')) == 4
    assert observer.green_exposure_windows(cfg, ('66', 'p2')) == 4
    assert observer.green_exposure_windows(cfg, ('66', 'p1')) == 0
    tuning['urban']['capacity'].pop('head_resource_contract')
    service.configure(cfg, tuning, raw, plan)
    assert service.view(cfg) is None


@pytest.mark.parametrize('movement', [NAME, 'SC1004_S_to_W'])
def test_combined_contract_still_rejects_competing_consumers(movement):
    cfg, tuning, raw, plan = combined_fixture()
    cfg.network.urban_movements['phantom'] = dict(cfg.network.urban_movements[movement])
    with pytest.raises(ValueError, match='another model consumer'):
        service.configure(cfg, tuning, raw, plan)
