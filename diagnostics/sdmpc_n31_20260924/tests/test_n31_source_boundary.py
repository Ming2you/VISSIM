"""T7/T7b (plan C6, NEW-13) and the AD:9401-9424 patch (patches/AD_C.patch).

T7:  forecast() block means == BF build_window(history_forecast) 10 s source
     values averaged per 150 s block (1e-9), on synthetic data always and on
     the B110 s31_v2nc observations when that read-only folder is reachable.
T7b: the v2 inpx timetable of inputs 1098/1099 == the calibration geometry's
     desired_source_demand; the contract schedule helpers == BF (contract tests).
AD:  the patched demand_from_state replaces the native mainline rates by the
     A1 block means exactly when the v2 lane plant declares it, else unchanged.
     Both adapter states pass: before the integrator applies AD_C.patch (old =
     live, new = forward patch) and after it (new = live, old = reverse patch).
"""
from __future__ import annotations

import ast
import builtins
import copy
import subprocess
import types
import unittest
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from typing import Any

import n31_fixtures as fx
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers import source_boundary as sb

CAL = fx.ROOT / 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
AD_ROOT = fx.ROOT                     # git apply --check runs here (patch paths are repo-relative)
AD = AD_ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'
PATCH = fx.N31D / 'patches/AD_C.patch'


def bf():
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1 import boundary_factory
    return boundary_factory


def recent_vph(data, cutoff, name, history=150):
    ends = [round(cutoff - history + d, 6) for d in range(30, history + 1, 30)]
    return sum(float(data.boundaries[t, name]['crossings']) for t in ends) * 3600 / history


def block_means(window, road, step, block=150):
    values = [s['source_demand_vph'][road] for s in window['boundary_steps']]
    per = block // step
    return [sum(values[i:i + per]) / per for i in range(0, len(values), per)]


class FakeData:
    """BF self-test shape with a stepped schedule and a real backlog."""

    def __init__(self):
        self.geometry = {'desired_source_demand': [
            {'road': 'FW_E', 'start_sec': 0.0, 'end_sec': 1000.0, 'desired_volume_vph': 4000.0},
            {'road': 'FW_E', 'start_sec': 1000.0, 'end_sec': None, 'desired_volume_vph': 2500.0}]}
        self.definitions = {'source_1': {'kind': 'source', 'road': 'FW_E'},
                            'off1': {'kind': 'offramp', 'road': 'FW_E', 'connector': 99, 'from_cell': 0}}
        self.cells = {900: [{'time_s': 900, 'road': 'FW_E', 'cell': i, 'n_veh': 20., 'v_kmh': 60.} for i in range(31)]}
        self.geometry['cells'] = self.cells[900]
        self.boundaries = {(t, name): {'crossings': 30. if name == 'source_1' else 3., 'cumulative_crossings': 800.,
                                       'snapshot_n_veh': 4.} for t in range(780, 901, 30) for name in self.definitions}
        self.flows = {(t, 'FW_E', 0): {'downstream_crossings': 6., 'off_departures': 3.} for t in range(780, 901, 30)}

    def demand_vph(self, road, time_s):
        return 4000.0 if time_s < 1000 else 2500.0

    def desired_before(self, road, cutoff):
        return 4000.0 * min(cutoff, 1000) / 3600 + 2500.0 * max(0.0, cutoff - 1000) / 3600


class ForecastTests(unittest.TestCase):

    def test_contract_signature(self):
        oc.check_module('evaluation.controllers.source_boundary')

    def test_synthetic_equals_bf(self):
        data = FakeData()
        schedule = sb.geometry_schedules({'desired_source_demand': [dict(r, road='FW_E') for r in
                                                                    data.geometry['desired_source_demand']]
                                          + [dict(r, road='FW_W') for r in data.geometry['desired_source_demand']]})
        backlog = max(0.0, data.desired_before('FW_E', 900) - 800.0)
        self.assertGreater(backlog, 100.0)
        recent = recent_vph(data, 900, 'source_1')
        for step in (10, 1):
            window = bf().build_window(data, 900, 'history_forecast', model_step_sec=step, horizon_sec=450)
            got = sb.forecast(recent, backlog, schedule['FW_E'], 900.0, 150, 3, step_s=step)
            for a, b in zip(got, block_means(window, 'FW_E', step)):
                self.assertLessEqual(abs(a - b), 1e-9)

    def test_recursion_details(self):
        schedule = (oc.ScheduleRow(0.0, 150.0, 1800.0), oc.ScheduleRow(150.0, None, 0.0))
        # Backlog drains at the recent rate cap and never goes negative.
        self.assertEqual(sb.forecast(3600.0, 0.0, schedule, 0.0, 150, 2), [1800.0, 0.0])
        out = sb.forecast(1000.0, 50.0, schedule, 0.0, 150, 2)
        self.assertEqual(out[0], 1000.0)
        self.assertGreater(out[1], 0.0)
        with self.assertRaises(ValueError):
            sb.forecast(-1.0, 0.0, schedule, 0.0, 150, 1)
        with self.assertRaises(ValueError):
            sb.forecast(1.0, 0.0, schedule, 0.0, 155, 1)
        with self.assertRaises(ValueError):
            sb.forecast(1.0, 0.0, schedule, 0.0, 150, 1, step_s=3)
        with self.assertRaises(ValueError):
            sb.forecast(1.0, 0.0, schedule, 0.0, 150, 0)

    @unittest.skipUnless(fx.B110_OBSERVATIONS.is_dir(), 'B110 s31_v2nc observations are not reachable')
    def test_b110_observations_equal_bf(self):
        data = bf().ObservationData(fx.B110_OBSERVATIONS)
        schedules = sb.geometry_schedules(data.geometry)
        names = {b['road']: n for n, b in data.definitions.items() if b['kind'] == 'source'}
        self.assertEqual(set(names), {'FW_E', 'FW_W'})
        for cutoff in (900.1, 1500.1, 2700.1, 4200.1):
            for step in (10, 1):
                window = bf().build_window(data, cutoff, 'history_forecast', model_step_sec=step, horizon_sec=450)
                backlog = window['meta']['external_backlog_estimate_at_cutoff']
                for road, name in names.items():
                    got = sb.forecast(recent_vph(data, cutoff, name), backlog[road], schedules[road], cutoff, 150, 3,
                                      step_s=step)
                    for a, b in zip(got, block_means(window, road, step)):
                        self.assertLessEqual(abs(a - b), 1e-9, (cutoff, step, road))


class ScheduleTests(unittest.TestCase):

    def test_native_rows_and_equality(self):
        rows = sb.schedule_rows([{'start_sec': 0, 'rate_veh_h': 10.0}, {'start_sec': 900, 'rate_veh_h': 20.0}])
        self.assertEqual(rows, (oc.ScheduleRow(0.0, 900.0, 10.0), oc.ScheduleRow(900.0, None, 20.0)))
        self.assertTrue(sb.same_schedule(rows, rows))
        self.assertFalse(sb.same_schedule(rows, rows[:1] + (oc.ScheduleRow(900.0, None, 20.1),)))
        self.assertFalse(sb.same_schedule(rows, (oc.ScheduleRow(0.0, None, 10.0),)))

    @unittest.skipUnless(fx.NET_INPX.is_file() or fx.E_INPX.is_file(), 'v2 network not reachable')
    def test_v2_timetable_equals_calibration_demand(self):
        network = fx.E_INPX if fx.E_INPX.is_file() else fx.NET_INPX
        self.assertEqual(fx.sha256(network), fx.make_plant_n31.NETWORK_SHA256)
        tree = ET.parse(network).getroot()
        native = {}
        for no, road in (('1098', 'FW_E'), ('1099', 'FW_W')):
            node = tree.find(f"./vehicleInputs/vehicleInput[@no='{no}']")
            rows = [{'start_sec': float(x.get('timeInt').split()[1]) / 1000, 'rate_veh_h': float(x.get('volume'))}
                    for x in node.findall('./timeIntVehVols/timeIntervalVehVolume')]
            native[road] = sb.schedule_rows(rows)
        calibration = fx.calibration_schedules()
        for road in ('FW_E', 'FW_W'):
            self.assertTrue(sb.same_schedule(native[road], calibration[road], tol=0.0), road)

    def test_road_schedules(self):
        timetable = {'freeway_link_by_input': {'1098': 'FW_E', '1099': 'FW_W'},
                     'inputs': {'1098': {'schedule': [{'start_sec': 0, 'rate_veh_h': 5.0}]},
                                '1099': {'schedule': [{'start_sec': 0, 'rate_veh_h': 6.0}]}}}
        self.assertEqual(sb.road_schedules(timetable)['FW_W'], (oc.ScheduleRow(0.0, None, 6.0),))
        with self.assertRaises(ValueError):
            sb.road_schedules({'freeway_link_by_input': {'1098': 'FW_E'}, 'inputs': timetable['inputs']})


def cfg_stub(*, enabled=True, block=None, observed=True, cutoff=900, interval=150, directed=True):
    schedule = [{'start_sec': 0, 'rate_veh_h': 4000.0}, {'start_sec': 1000, 'rate_veh_h': 2500.0}]
    timetable = {'schema': 'native-input-schedule/v1',
                 'freeway_link_by_input': {'1098': 'FW_E', '1099': 'FW_W'} if directed else {},
                 'inputs': {'1098': {'schedule': schedule}, '1099': {'schedule': copy.deepcopy(schedule)}}}
    observation = {'information_cutoff_s': cutoff, 'source_boundary': {}}
    for road, (window, cum) in (('FW_E', (100, 700)), ('FW_W', (160, 1200))):
        integral = oc.schedule_integral_veh(sb.schedule_rows(schedule), 0.0, float(cutoff))
        interval_s = 1 if cutoff == 1 else 150
        observation['source_boundary'][road] = {
            'admitted_window': window, 'admitted_cum': cum, 'interval_s': interval_s,
            'recent_vph': 3600.0 * window / interval_s, 'schedule_integral_veh': integral,
            'backlog_veh': max(0.0, integral - cum)}
    network = types.SimpleNamespace(native_input_schedule=timetable, freeway_links=['FW_E', 'FW_W'],
                                    lane_plant_enabled=enabled,
                                    lane_plant_sources={'source_boundary': dict(block or oc.SOURCE_BOUNDARY_BLOCK)})
    if observed:
        network.freeway_source_boundary_observed = sb.observed_block(observation, sb.road_schedules(timetable)) \
            if directed else {'mode': sb.MODE, 'information_cutoff_s': cutoff, 'by_road': {}}
    return types.SimpleNamespace(network=network, simulation=types.SimpleNamespace(control_interval=interval)), observation


class DemandBlockTests(unittest.TestCase):

    def test_blocks_are_forecasts(self):
        cfg, observation = cfg_stub()
        blocks = sb.demand_blocks(cfg, 900.0, 4)
        schedules = sb.road_schedules(cfg.network.native_input_schedule)
        for road in ('FW_E', 'FW_W'):
            row = observation['source_boundary'][road]
            self.assertEqual(blocks[road], sb.forecast(row['recent_vph'], row['backlog_veh'], schedules[road],
                                                       900.0, 150, 4, step_s=10))
            self.assertEqual(len(blocks[road]), 4)

    def test_off_cases(self):
        cfg, _ = cfg_stub(enabled=False)
        self.assertIsNone(sb.demand_blocks(cfg, 900.0, 3))
        cfg, _ = cfg_stub()
        cfg.network.lane_plant_sources = {'schema': 'coupled-lane-plant/v1'}
        self.assertIsNone(sb.demand_blocks(cfg, 900.0, 3))
        cfg, _ = cfg_stub(cutoff=1)
        self.assertIsNone(sb.demand_blocks(cfg, 1.0, 3))

    def test_refusals(self):
        cfg, _ = cfg_stub(observed=False)
        with self.assertRaisesRegex(ValueError, 'observed cutoff record'):
            sb.demand_blocks(cfg, 900.0, 3)
        cfg, _ = cfg_stub()
        with self.assertRaisesRegex(ValueError, 'not at the forecast start'):
            sb.demand_blocks(cfg, 1050.0, 3)
        cfg, _ = cfg_stub(block={**oc.SOURCE_BOUNDARY_BLOCK, 'model_step_sec': 5})
        with self.assertRaisesRegex(ValueError, 'Unsupported source boundary'):
            sb.demand_blocks(cfg, 900.0, 3)
        cfg, _ = cfg_stub(interval=150.5)
        with self.assertRaises(ValueError):
            sb.demand_blocks(cfg, 900.0, 3)

    def test_observed_block_checks_the_integral(self):
        cfg, observation = cfg_stub()
        bad = copy.deepcopy(observation)
        bad['source_boundary']['FW_W']['schedule_integral_veh'] += 1.0
        with self.assertRaisesRegex(ValueError, 'integral'):
            sb.observed_block(bad, sb.road_schedules(cfg.network.native_input_schedule))


def patched_function(text, name='demand_from_state'):
    """Compile one top-level function of the adapter text in an isolated namespace."""
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    code = compile(ast.Module(body=[node], type_ignores=[]), 'vissim_stackelberg_adapter(' + name + ')', 'exec')
    namespace = {'Any': Any, 'Mapping': Mapping, '__builtins__': builtins, '_LAST_GATE_PEELOFF_META': None,
                 'profiled_demand_rates': lambda observed, cfg, calibration, mapping: (
                     {'FW_E': -1.0, 'FW_W': -1.0}, {'gate': 1.0}, {'RM': 2.0}, None)}
    exec(code, namespace)
    return namespace[name]


def patch_blocks(patch_text):
    """(old, new) text of the single AD_C.patch hunk."""
    old, new = [], []
    started = False
    for line in patch_text.splitlines():
        if line.startswith('@@'):
            if started:
                raise ValueError('AD_C.patch must be one hunk')
            started = True
            continue
        if not started:
            continue
        tag, body = line[:1], line[1:]
        if tag in (' ', ''):
            old.append(body)
            new.append(body)
        elif tag == '-':
            old.append(body)
        elif tag == '+':
            new.append(body)
    return '\n'.join(old) + '\n', '\n'.join(new) + '\n'


def adapter_versions(text, patch_text):
    """('unapplied'|'applied', old adapter text, new adapter text) of the live adapter.

    Exactly one side of the hunk occurs, exactly once: the integrator may or
    may not have applied AD_C.patch (and AD_B1.patch) yet.
    """
    old, new = patch_blocks(patch_text)
    counts = text.count(old), text.count(new)
    if counts == (1, 0):
        return 'unapplied', text, text.replace(old, new)
    if counts == (0, 1):
        return 'applied', text.replace(new, old), text
    raise ValueError('AD_C.patch is neither cleanly applied nor cleanly unapplied: %r' % (counts,))


def git_apply_check(*extra):
    return subprocess.run(['git', 'apply', '--check', *extra, str(PATCH)], cwd=AD_ROOT, capture_output=True, text=True)


class DemandStep:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class AdapterPatchTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.state, old, new = adapter_versions(AD.read_text(encoding='utf-8'), PATCH.read_text(encoding='utf-8'))
        cls.new = staticmethod(patched_function(new))
        cls.old = staticmethod(patched_function(old))

    def setUp(self):
        from evaluation.controllers import native_demand_forecast
        self.module = native_demand_forecast
        self.saved = native_demand_forecast.forecast_states

        def forecast_states(raw, cfg, horizon_steps):
            return [{'demand': {'native_freeway_mainline_veh_h': {'FW_E': 5000.0 + i, 'FW_W': 4000.0 + i}}}
                    for i in range(max(1, int(horizon_steps)))]
        native_demand_forecast.forecast_states = forecast_states

    def tearDown(self):
        self.module.forecast_states = self.saved

    def test_patch_applies_to_the_live_adapter(self):
        forward = git_apply_check()
        if self.state == 'unapplied':
            self.assertEqual(forward.returncode, 0, forward.stderr)
        else:   # applied by the integrator: only the reverse applies
            self.assertNotEqual(forward.returncode, 0)
            reverse = git_apply_check('--reverse')
            self.assertEqual(reverse.returncode, 0, reverse.stderr)
        lines = [l for l in PATCH.read_text(encoding='utf-8').splitlines() if l.startswith('@@')]
        start = int(lines[0].split()[1].split(',')[0][1:])
        self.assertGreaterEqual(start, 9401)
        self.assertLessEqual(start + int(lines[0].split()[1].split(',')[1]), 9424 + 1)

    def test_a1_replaces_the_mainline_rates(self):
        cfg, _ = cfg_stub()
        steps = self.new({'sim_sec': 900}, cfg, DemandStep, 5)
        blocks = sb.demand_blocks(cfg, 900.0, 5)
        self.assertEqual(len(steps), 5)
        for index, step in enumerate(steps):
            self.assertEqual(step.freeway_mainline, {road: blocks[road][index] for road in ('FW_E', 'FW_W')})
            self.assertEqual(step.urban_boundary, {'gate': 1.0})
            self.assertEqual(step.ramp_arrival, {'RM': 2.0})

    def test_unchanged_without_a1(self):
        for cfg, t in ((cfg_stub(enabled=False)[0], 900), (cfg_stub(cutoff=1)[0], 1)):
            new = self.new({'sim_sec': t}, cfg, DemandStep, 3)
            old = self.old({'sim_sec': t}, cfg, DemandStep, 3)
            self.assertEqual([s.__dict__ for s in new], [s.__dict__ for s in old])
            self.assertEqual(new[2].freeway_mainline, {'FW_E': 5002.0, 'FW_W': 4002.0})

    def test_a1_requires_directed_inputs(self):
        cfg, _ = cfg_stub(directed=False)
        cfg.network.freeway_source_boundary_observed = {'mode': sb.MODE, 'information_cutoff_s': 900, 'by_road': {}}
        with self.assertRaises(ValueError):
            self.new({'sim_sec': 900}, cfg, DemandStep, 3)


if __name__ == '__main__':
    unittest.main()
