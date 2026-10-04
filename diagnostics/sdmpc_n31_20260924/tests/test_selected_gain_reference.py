"""Regressions for the selected gain network on current SDMPC code."""
from pathlib import Path
import copy
import json
import tempfile
import xml.etree.ElementTree as ET

import pytest

from evaluation.controllers import lane_plant_runtime as lpr
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel

ROOT = Path(__file__).resolve().parents[3]
SELECTED = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected'


@pytest.fixture
def tmp_path():
    # Component provenance deliberately requires a repository-relative config.
    with tempfile.TemporaryDirectory(prefix='selected-test-', dir=SELECTED.parent) as folder:
        path = Path(folder).resolve()
        assert path.is_relative_to(ROOT.resolve())
        yield path


@pytest.fixture(scope='module')
def context():
    return lpr.load_sources(str(SELECTED / 'plant_n31_v2.json'))


def test_physical_fd_applies_only_to_named_cells(context, tmp_path):
    reference = json.loads(context['paths']['reference_config'].read_bytes())
    without = copy.deepcopy(reference)
    without['freeway'].pop('physical_cell_fd')
    path = tmp_path / 'without_cell_fd.json'
    path.write_text(json.dumps(without), encoding='utf-8')
    plain = CanonicalFreewayModel(context['geometry'], path)
    calibrated = context['component']
    assert calibrated.cell_fd == reference['freeway']['physical_cell_fd']
    for road, rows in calibrated.base.network.freeway_segment_params.items():
        assert len(rows) == 31
        for cell, row in enumerate(rows):
            expected = dict(plain.base.network.freeway_segment_params[road][cell])
            expected.update(calibrated.cell_fd.get(road, {}).get(str(cell), {}))
            assert row == expected
    assert calibrated.base.network.freeway_segment_params['FW_E'][21]['rho_crit'] == 33.6
    assert calibrated.provenance['state_response_cell_indexing'] == 'observed physical cells, zero based'


@pytest.mark.parametrize('overrides', [
    {'FW_E': {'31': {'rho_crit': 20}}},
    {'FW_E': {'-1': {'rho_crit': 20}}},
    {'FW_E': {'01': {'rho_crit': 20}}},
    {'FW_E': {'21': {'rho_crit': True}}},
    {'FW_E': {'21': {'rho_crit': 999}}},
    {'FW_E': {'21': {'capacity_bonus': 10}}},
])
def test_bad_cell_fd_is_rejected(context, tmp_path, overrides):
    reference = json.loads(context['paths']['reference_config'].read_bytes())
    reference['freeway']['physical_cell_fd'] = overrides
    path = tmp_path / 'bad_fd.json'
    path.write_text(json.dumps(reference), encoding='utf-8')
    with pytest.raises(ValueError):
        CanonicalFreewayModel(context['geometry'], path)


def test_ignored_calibration_refuses_to_load(context):
    reference = json.loads(context['paths']['reference_config'].read_bytes())
    broken = copy.copy(context['component'])
    broken.cell_fd = {}
    with pytest.raises(ValueError, match='not installed'):
        lpr._validate_component_features(broken, reference)


def test_head_service_matches_executed_green_and_red(context):
    component = context['component']
    for ramp, curve in component.ramp_head_service_veh_per_cycle.items():
        for green in range(2, 11):
            command = {'mode': 'OFF' if green == 10 else 'METER', 'green_sec': green, 'service_veh': 99.0}
            original = dict(command)
            out = component._head_service(ramp, command, 10.0)
            assert out['service_veh'] == curve[str(green)]
            assert command == original
        red = {'mode': 'RED', 'green_sec': 0, 'service_veh': 0.0}
        assert component._head_service(ramp, red, 10.0) == red
    with pytest.raises(ValueError, match='10s'):
        component._head_service('RM_C10490', {'mode': 'OFF'}, 60.0)


def test_local_merge_coefficient_reaches_physical_transition(context):
    import pickle
    from evaluation.controllers.freeway_fd import configure_state_response
    source = SELECTED.parent / 'congested_replay' / 'hold_input.pickle'
    args, kwargs = pickle.loads(source.read_bytes())
    args = list(args)
    args[1] = args[1][:30]
    kwargs['horizon_sec'] = 30
    results = []
    for delta in (0.0, 6.0):
        component = copy.deepcopy(context['component'])
        configure_state_response(component.base, {'freeway': {'state_response': {
            'FW_E': {'cell_overrides': {'23': {'delta_merge': delta}}}}}})
        result = component.rollout(*copy.deepcopy(args), **copy.deepcopy(kwargs))
        results.append(result)
        assert all(abs(r['conservation_residual_veh']) < 1e-7 for r in result['ramps'] + result['ports'])
        assert result['diagnostics']['roads'][0]['continuity_residual_max_veh'] < 1e-7
    assert results[0]['cells'] != results[1]['cells'], 'Local merge coefficient is ignored'


@pytest.mark.parametrize('value', [-1.0, float('nan'), float('inf'), True])
def test_invalid_local_merge_coefficient(context, value):
    from evaluation.controllers.freeway_fd import configure_state_response
    with pytest.raises(ValueError):
        configure_state_response(copy.deepcopy(context['component'].base), {'freeway': {
            'state_response': {'FW_E': {'cell_overrides': {'23': {'delta_merge': value}}}}}})


def test_native_clock_source_relocation_preserves_plan(context):
    from evaluation.controllers import signal_actuation_contract as contract, signal_group_plan as sg
    tuning = json.loads((SELECTED / 'config_n31_v2.json').read_bytes())
    plan = json.loads((ROOT / tuning['urban']['plan']['actuation_plan_json']).read_bytes())
    before = copy.deepcopy(plan)
    network = context['paths']['network']
    controllers = {row.get('no'): row for row in ET.parse(network).getroot().findall('.//signalController')}
    assert len(plan['controllers']) == 17
    for number, raw in plan['controllers'].items():
        source = network.parent / controllers[number].get('supplyFile2').removeprefix('#data#')
        contract.verify_native_source(sg.node_plan_from_json(raw), plan['amber_sec'], plan['all_red_sec'], source)
    assert plan == before
    changed = copy.deepcopy(plan['controllers']['1'])
    changed['native_clock_basis']['reference_offset_sec'] += 1
    source = network.parent / controllers['1'].get('supplyFile2').removeprefix('#data#')
    with pytest.raises(ValueError, match='native clock differs'):
        contract.verify_native_source(sg.node_plan_from_json(changed), plan['amber_sec'], plan['all_red_sec'], source)
