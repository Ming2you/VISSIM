"""Known external timetable, independent generation and observation isolation."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.native_demand_forecast import forecast_states
from src.models.demand import DemandStep


def setup(start=750., interval=150.):
    def source(role, status, gate, before, after):
        return {'role': role, 'status': status, 'gate': gate, 'physical_source': '1',
                'schedule': [{'start_sec': 0., 'rate_veh_h': before},
                             {'start_sec': 900., 'rate_veh_h': after}]}
    inputs = {'f1': source('freeway_mainline_input', '', '', 1000., 2000.),
              'f2': source('freeway_feeder_input_candidate', '', '', 1000., 2000.),
              'u1': source('urban_input', 'mapped', 'in_A', 10., 20.),
              'u2': source('urban_input', 'mapped', 'in_A', 15., 30.),
              'u3': source('urban_input', 'internal', '', 99., 198.),
              'u4': source('urban_input', 'shared_stem_unmapped', '', 50., 100.)}
    cfg = SimpleNamespace(simulation=SimpleNamespace(control_interval=interval),
        network=SimpleNamespace(freeway_links=['FW_E', 'FW_W'], ramps=['R'],
            boundary_in_links=['in_A', 'in_internal'], boundary_out_links=[],
            native_input_schedule={'schema': 'native-input-schedule/v1',
                'run_id': 'test', 'network_sha256': '0'*64, 'inputs': inputs}))
    factor = 1 if start < 900 else 2
    raw = {'sim_sec': start, 'run_provenance': {'run_id': 'test'},
           'ramp_counts': {'R': 7}, 'local_observation': {'sentinel': [3, 4]},
           'demand': {'demand_profile': 'real_world_inpx_time_profile_scaled',
               'freeway_volume_vph': factor*1000., 'urban_volume_vph': factor*43.5,
               'urban_volume_vph_by_gate': {'in_A': factor*25.},
               'urban_internal_volume_vph': factor*99.,
               'urban_unmapped_volume_vph': factor*50., 'ramp_volume_vph': 9.}}
    return raw, cfg


class NativeDemandForecastTests(unittest.TestCase):
    def test_opt_in_cannot_silently_skip_source_validation(self):
        from evaluation.controllers.runtime_setup import configure_runtime
        for flag in (True, 'true'):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                configure_runtime(None, None, {'prediction': {'native_input_schedule': flag}},
                                  None, None, None, None, None, None)

    def test_actual_adapter_uses_interval_future_and_excludes_internal_shared(self):
        raw, cfg = setup()
        before = copy.deepcopy((raw, cfg))
        rows = adapter.demand_from_state(raw, cfg, DemandStep, 3)
        self.assertEqual([r.freeway_mainline['FW_E'] for r in rows], [1000., 2000., 2000.])
        self.assertEqual([r.urban_boundary['in_A'] for r in rows], [25., 50., 50.])
        self.assertEqual([r.urban_boundary['in_internal'] for r in rows], [0., 0., 0.])
        self.assertEqual([r.ramp_arrival['R'] for r in rows], [9., 9., 9.])
        self.assertEqual((raw, cfg), before)
        rows[0].urban_boundary['in_A'] = 999.
        self.assertEqual(rows[1].urban_boundary['in_A'], 50.)

    def test_straddling_interval_preserves_declared_vehicle_integral(self):
        raw, cfg = setup(875.)
        rows = adapter.demand_from_state(raw, cfg, DemandStep, 2)
        self.assertAlmostEqual(rows[0].freeway_mainline['FW_W'] * 150/3600,
                               (1000*25 + 2000*125)/3600)
        self.assertAlmostEqual(rows[0].urban_boundary['in_A'] * 150/3600,
                               (25*25 + 50*125)/3600)
        self.assertEqual(rows[1].freeway_mainline['FW_E'], 2000.)

    def test_exact_boundary_starts_new_interval(self):
        raw, cfg = setup(900.)
        self.assertEqual(adapter.demand_from_state(raw, cfg, DemandStep, 1)[0].urban_boundary['in_A'], 50.)

    def test_legacy_without_declared_timetable_retains_persistence(self):
        raw, cfg = setup()
        del cfg.network.native_input_schedule
        rows = adapter.demand_from_state(raw, cfg, DemandStep, 3)
        self.assertEqual([r.freeway_mainline['FW_E'] for r in rows], [1000.]*3)
        self.assertEqual([r.urban_boundary['in_A'] for r in rows], [25.]*3)

    def test_current_provenance_rates_and_gate_set_must_match(self):
        for change in ('run', 'gate', 'value', 'profile'):
            raw, cfg = setup()
            if change == 'run': raw['run_provenance']['run_id'] = 'another'
            elif change == 'gate': raw['demand']['urban_volume_vph_by_gate']['extra'] = 0.
            elif change == 'value': raw['demand']['urban_internal_volume_vph'] = 98.
            else: raw['demand']['demand_profile'] = 'unknown'
            with self.subTest(change=change), self.assertRaises(ValueError):
                forecast_states(raw, cfg, 3)

    def test_invalid_rates_order_and_asymmetric_future_are_rejected(self):
        for change in ('negative', 'nan', 'order', 'asymmetric'):
            raw, cfg = setup()
            rows = cfg.network.native_input_schedule['inputs']['f2']['schedule']
            if change == 'negative': rows[1]['rate_veh_h'] = -1.
            elif change == 'nan': rows[1]['rate_veh_h'] = float('nan')
            elif change == 'order': rows[1]['start_sec'] = 0.
            else: rows[1]['rate_veh_h'] = 2001.
            with self.subTest(change=change), self.assertRaises(ValueError):
                forecast_states(raw, cfg, 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
