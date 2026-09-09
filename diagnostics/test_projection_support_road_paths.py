"""Deterministic transit-road evidence; actual1350 with10634 explicitly isolated."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics'), str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import adapter, build_projected
from diagnostics.route_input_fixtures import decisions, ENVIRONMENT
from evaluation.controllers import area_runtime, projection_support

RUN = 'codex_area_beta0_retry_s13_20260910'
FOLDER = decisions()
SUPPORT = ROOT/'diagnostics/physical_projection_support_635_proposal.json'
CONTRACT = ROOT/'diagnostics/control_area_route_contract_physical_routes.json'


def road_evidence():
    return {'reason': 'Unsignalled pre-head bypass transit road; canonical receiver is unique. No signal-service correction.',
        'downstream_path': {'links': ['336', '10529', '1210014303'],
            'movement': 'SC101_S_SC1_to_E_SC5',
            'canonical_contract': {'path': CONTRACT.relative_to(ROOT).as_posix(),
                'sha256': hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
            'native_route_ids': ['1014:3']}}


class RoadPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='road-support-', dir=ROOT/'diagnostics')
        cls.directory = Path(cls.temp.name).resolve()
        if not cls.directory.is_relative_to((ROOT/'diagnostics').resolve()):
            raise ValueError('Unexpected temporary fixture directory')
        cls.original = json.loads((FOLDER/'state_001350.json').read_text(encoding='utf-8'))
        cls.raw = deepcopy(cls.original)
        envelope = cls.raw['vehicle_records']
        cls.removed = [v for v in envelope['records'] if str(v['link_no']) == '10634']
        assert len(cls.removed) == 3
        envelope['records'] = [v for v in envelope['records'] if str(v['link_no']) != '10634']
        envelope['full_network_link_counts'].pop('10634', None)
        for name in ('record_count', 'collection_count_before', 'collection_count_after'):
            envelope[name] = len(envelope['records'])
        for name in ('link_counts', 'link_stopped_counts', 'link_speeds_kph'):
            cls.raw['local_observation'].get(name, {}).pop('10634', None)
        projection_support.complete_records(cls.raw)
        cls.data = json.loads(SUPPORT.read_text(encoding='utf-8'))
        cls.data['link_to_storage']['336'] = 'SC101_to_SC5'
        cls.data['evidence']['336'] = road_evidence()
        cls.data['full_area_coverage_audit']['unresolved_physical_links'] = [
            key for key in cls.data['full_area_coverage_audit']['unresolved_physical_links'] if key != '336']
        cls.support_path = cls.directory/'support.json'
        cls.support_path.write_text(json.dumps(cls.data), encoding='utf-8')
        raw_path = cls.directory/'state.json'
        raw_path.write_text(json.dumps(cls.raw), encoding='utf-8')
        tuning = adapter.load_optional_json(str(ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json'))
        tuning['observation']['physical_support_repair'] = str(cls.support_path)
        config_path = cls.directory/'config.json'
        config_path.write_text(json.dumps(tuning), encoding='utf-8')
        cls.cfg, cls.state, cls.detectors, cls.tuning, _, _, cls.metadata = build_projected(
            config_path, raw_path, FOLDER/'action_001200.json', fixture_inputs=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def validate(self, data):
        path = self.directory/'case.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return projection_support.configure(self.cfg,
            {'observation': {'physical_support_repair': str(path)}}, self.detectors, self.raw)

    def test_actual_road_vehicle_once_initial_events_zero_and_area_stock_exact(self):
        assigned = self.state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assigned['336'], {'storage:SC101_to_SC5': 1.0})
        self.assertEqual(self.detectors['transit_storage_projection']['336'], 'SC101_to_SC5')
        self.assertNotIn('336', self.detectors['link_to_movements'])
        ledger = self.state._control_area_ledger
        self.assertEqual((ledger.entered_veh, ledger.ttd_veh, ledger.event_count), (0, 0, 0))
        physical = set(json.loads((ROOT/'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))['inside_links'])
        count = sum(value for key, value in self.raw['vehicle_records']['full_network_link_counts'].items() if key in physical)
        self.assertAlmostEqual(sum(row['inside'] for row in ledger.stocks.values()), count, places=7)
        ledger.assert_stocks(area_runtime.model_inventory(self.state, self.cfg))

    def test_disconnected_or_branched_path_rejected(self):
        data = deepcopy(self.data)
        data['evidence']['336']['downstream_path']['links'][1] = '10528'
        with self.assertRaisesRegex(ValueError, 'single physical next connector'):
            self.validate(data)
        data = deepcopy(self.data)
        data['link_to_storage']['141'] = 'SC12_to_SC6'
        data['evidence']['141'] = road_evidence()
        data['evidence']['141']['downstream_path']['links'] = ['141', '10220', '1220018302']
        with self.assertRaisesRegex(ValueError, 'single physical next connector'):
            self.validate(data)

    def test_terminal_alias_cannot_replace_proved_receiver(self):
        data = deepcopy(self.data)
        data['link_to_storage']['336'] = 'SC5_to_SC11'
        with self.assertRaisesRegex(ValueError, 'terminal lacks receiving storage'):
            self.validate(data)

    def test_contract_hash_and_native_route_are_required(self):
        data = deepcopy(self.data)
        data['evidence']['336']['downstream_path']['canonical_contract']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'contract fingerprint mismatch'):
            self.validate(data)
        data = deepcopy(self.data)
        data['evidence']['336']['downstream_path']['native_route_ids'] = ['1014:1']
        with self.assertRaisesRegex(ValueError, 'Native route does not traverse'):
            self.validate(data)

    def test_existing_signal_cannot_be_treated_as_transit_road(self):
        data = deepcopy(self.data)
        data['link_to_storage']['187'] = 'SC7_to_SC108'
        data['evidence']['187'] = road_evidence()
        data['evidence']['187']['downstream_path']['links'] = ['187', '10308', '1220007401']
        with self.assertRaisesRegex(ValueError, 'signal or input'):
            self.validate(data)

    def test_old_guard_and_disabled_configuration_remain(self):
        old_data = deepcopy(self.data)
        old_data['link_to_storage'].pop('336')
        old_data['full_area_coverage_audit']['unresolved_physical_links'].append('336')
        with self.assertRaisesRegex(ValueError, 'unresolved physical stock support.*336'):
            self.validate(old_data)
        from diagnostics.fixed_source_reference import function
        old = function('evaluation/controllers/projection_support.py', 'configure', vars(projection_support))
        tuning = {'observation': {'physical_support_repair': 'diagnostics/physical_projection_support_ver2.json'}}
        self.assertEqual(old(deepcopy(self.cfg), tuning, self.detectors, self.raw),
            projection_support.configure(deepcopy(self.cfg), tuning, self.detectors, self.raw))
        detectors, raw, meta = projection_support.configure(self.cfg, {}, self.detectors, self.raw)
        self.assertIs(detectors, self.detectors)
        self.assertIs(raw, self.raw)
        self.assertEqual(meta, {})

    def test_recovered_stock_has_transit_release_and_future_mass_closure(self):
        from src.models.demand import DemandStep
        from src.models.state import ControlAction
        from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
        control = adapter.control_from_json(FOLDER/'action_001200.json', self.cfg, ControlAction)
        calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(calibration, self.tuning.get('calibration_override', {}))
        forecast = adapter.demand_from_state(self.raw, self.cfg, DemandStep, 1, calibration, self.detectors)
        self.assertGreaterEqual(sum(self.state.urban_storage_release_buffer['SC101_to_SC5'].values()), 1.)
        initial = pickle.dumps(self.state, protocol=5)
        result = evaluate_price_point(self.state, control, forecast, [], ObjectiveSpec(
            self.cfg, depth_override=1, box_walk=False, score_mode='raw'))
        final = result.states[-1]
        final._control_area_ledger.assert_stocks(area_runtime.model_inventory(final, self.cfg))
        self.assertEqual(pickle.dumps(self.state, protocol=5), initial)
        self.assertEqual(final.time_sec, self.raw['sim_sec']+150)
        self.assertFalse(result.aborted)
        (ROOT/'diagnostics'/('road_support_336_portable_regression.json' if os.environ.get(ENVIRONMENT) else 'road_support_336_regression.json')).write_text(json.dumps({
            'snapshot': str((FOLDER/'state_001350.json').relative_to(ROOT)),
            'snapshot_sha256': hashlib.sha256((FOLDER/'state_001350.json').read_bytes()).hexdigest(),
            'isolated_outstanding_10634_records': self.removed,
            'production_support_data_written_by_test': False,
            'production_support_sha256': hashlib.sha256(SUPPORT.read_bytes()).hexdigest(),
            '336_support_present_in_production_data': '336' in json.loads(SUPPORT.read_text(encoding='utf-8'))['link_to_storage'],
            'initial_assignment_336': {'storage:SC101_to_SC5': 1},
            'initial_entry_exit_events': [0, 0, 0],
            'paired_transit_release_veh': sum(self.state.urban_storage_release_buffer['SC101_to_SC5'].values()),
            'future_150sec_stocks_closed': True,
            'area': {key: value for key, value in result.control_area.items() if key != 'flow_counts'},
            'scope': 'Actual1350 with three10634 observations removed from a copied fixture only; shared10634 architecture is a separate unresolved task.'}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    unittest.main(verbosity=2)
