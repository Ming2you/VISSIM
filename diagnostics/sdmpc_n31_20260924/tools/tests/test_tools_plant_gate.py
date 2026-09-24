"""WP-D D7: plant_gate.py - frame binning, held VSL mapping, metrics/verdict, run plumbing, real 31-cell zones."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import plant_gate as pg  # noqa: E402
from n31_common import ROOT, ToolError, oc  # noqa: E402

B110_GEOMETRY = ROOT / ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
                        'observations/s31_v2nc_observations/geometry.json')
REFERENCE = ROOT / 'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json'

GEOMETRY = {
    'chains': {'FW_E': [{'link': 1, 'offset_m': 0.0, 'length_m': 100.0, 'lanes': 2},
                        {'link': 2, 'offset_m': 100.0, 'length_m': 50.0, 'lanes': 2}],
               'FW_W': [{'link': 3, 'offset_m': 0.0, 'length_m': 90.0, 'lanes': 2}]},
    'bounds': {'FW_E': [0.0, 60.0, 120.0, 150.0], 'FW_W': [0.0, 45.0, 90.0]},
    'cells': [{'road': 'FW_E', 'cell': 0, 'parent_cell': 0}, {'road': 'FW_E', 'cell': 1, 'parent_cell': 0},
              {'road': 'FW_E', 'cell': 2, 'parent_cell': 1}, {'road': 'FW_W', 'cell': 0, 'parent_cell': 0},
              {'road': 'FW_W', 'cell': 1, 'parent_cell': 1}]}


def frame(t, vehicles):
    rows = [[v, link, 1, float(pos), float(speed), 4.5] + [None] * 9 for v, (link, pos, speed) in enumerate(vehicles, 1)]
    return {'schema': oc.FRAME_SCHEMA, 'complete': True, 'time_s': t, 'run_id': 'r', 'vehicles': rows}


class Cells(unittest.TestCase):
    def test_binning(self):
        cm = pg.CellMap(GEOMETRY)
        cells = cm.bin(frame(900, [(1, 10.0, 50.0), (1, 60.0, 70.0), (2, 19.9, 90.0), (2, 50.0, 30.0),
                                   (3, 44.9, 20.0), (99, 1.0, 10.0)]), 900)
        got = {(c['road'], c['cell']): (c['n_veh'], c['v_kmh']) for c in cells}
        self.assertEqual(got[('FW_E', 0)], (1.0, 50.0))
        self.assertEqual(got[('FW_E', 1)], (2.0, 80.0))          # 60 m is the start of cell 1; link 2 @19.9 = 119.9
        self.assertEqual(got[('FW_E', 2)], (1.0, 30.0))          # the chain end falls in the last cell
        self.assertEqual(got[('FW_W', 0)], (1.0, 20.0))
        self.assertEqual(got[('FW_W', 1)], (0.0, None))          # empty: speed None
        self.assertEqual(len(cells), 5)                          # link 99 is not on a chain
        with self.assertRaises(ToolError):
            cm.bin(frame(900, [(1, 104.0, 10.0)]), 900)          # beyond its link

    def test_metrics_and_verdict(self):
        observed = {lead: [{'road': 'FW_E', 'cell': 0, 'n_veh': 10.0, 'v_kmh': 50.0},
                           {'road': 'FW_E', 'cell': 1, 'n_veh': 2.0, 'v_kmh': 90.0}] for lead in pg.LEADS}
        predicted = {lead: [{'road': 'FW_E', 'cell': 0, 'n_veh': 12.0, 'v_kmh': 50.0 + lead / 10},
                            {'road': 'FW_E', 'cell': 1, 'n_veh': 1.0, 'v_kmh': 10.0}] for lead in pg.LEADS}
        m = pg.compare_cells(predicted, observed, ('FW_E',))['FW_E']
        self.assertEqual(m['speed']['count'], 3)                 # N < 5 cells are not speed samples
        self.assertAlmostEqual(m['horizons']['300']['speed']['rmse'], 30.0)
        self.assertEqual(m['horizons']['450']['total_n_predicted'], 13.0)
        verdict = pg.verdict({'FW_E': m}, {'FW_E': 40.0})
        self.assertEqual(verdict, {'FW_E': 'PASS'})
        self.assertEqual(pg.verdict({'FW_E': m}, {'FW_E': 20.0}), {'FW_E': 'OUTSIDE_BAND'})
        self.assertEqual(pg.verdict({'FW_E': m}, {'FW_E': 10.0}), {'FW_E': 'STOP_ASK'})
        self.assertEqual(pg.parse_band('FW_E=20'), {'FW_E': 20.0, 'FW_W': 17.0})


def stub_component():
    net = types.SimpleNamespace(freeway_vsl_zone_heads={'FW_E': [0, 2], 'FW_W': [0]},
                                freeway_segment_lanes={'FW_E': [2, 2, 2], 'FW_W': [2, 2]})
    return types.SimpleNamespace(roads=('FW_E', 'FW_W'), base=types.SimpleNamespace(network=net))


class HeldAction(unittest.TestCase):
    def test_parent_commands_on_refined_zone_heads(self):
        cm = pg.CellMap(GEOMETRY)
        action = {'vsl': {'FW_E__seg0': 110.0, 'FW_E__seg1': 80.0, 'FW_W__seg0': 60.0, 'FW_W__seg1': 60.0}}
        commands, spread = pg.held_vsl_commands(action, stub_component(), cm)
        self.assertEqual(commands, {'FW_E__seg0': 110.0, 'FW_E__seg2': 80.0, 'FW_W__seg0': 60.0})
        self.assertEqual(spread, {})
        action['vsl']['FW_W__seg1'] = 110.0                      # two commands inside one zone: reported
        self.assertEqual(pg.held_vsl_commands(action, stub_component(), cm)[1], {'FW_W__seg0': [60.0, 110.0]})
        del action['vsl']['FW_E__seg1']
        with self.assertRaises(ToolError):
            pg.held_vsl_commands(action, stub_component(), cm)

    @unittest.skipUnless(B110_GEOMETRY.is_file() and REFERENCE.is_file(), 'b110 copies not in the worktree')
    def test_real_31_cell_zones(self):
        from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
        geometry = json.loads(B110_GEOMETRY.read_text(encoding='utf-8-sig'))
        component = CanonicalFreewayModel(geometry, REFERENCE)
        action = {'vsl': {f'{r}__seg{i}': (80.0 if 10 <= i < 15 else 110.0) for r in ('FW_E', 'FW_W') for i in range(21)}}
        commands, spread = pg.held_vsl_commands(action, component, pg.CellMap(geometry))
        # C4(d): FW_E [0]*5+[5]*9+[10]*11+[15]*6, FW_W [0]*5+[5]*10+[10]*10+[15]*6
        self.assertEqual(commands, {'FW_E__seg0': 110.0, 'FW_E__seg5': 110.0, 'FW_E__seg14': 80.0, 'FW_E__seg25': 110.0,
                                    'FW_W__seg0': 110.0, 'FW_W__seg5': 110.0, 'FW_W__seg15': 80.0, 'FW_W__seg25': 110.0})
        self.assertEqual(spread, {})


B110 = ROOT / 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923'
B110_OBSERVATIONS = Path(r'D:\VISSIM-merge\sim3') / ('diagnostics/demand_sweep/user_native_20260914/'
                                                    'metanet_calibration_v1/res10_b110_20260923/observations/s31_v2nc_observations')


@unittest.skipUnless(B110_GEOMETRY.is_file() and REFERENCE.is_file() and (B110_OBSERVATIONS / 'cells_30s.csv').is_file(),
                     'b110 copies or the read-only B110 observations are not available')
class RealComponent(unittest.TestCase):
    """The gate's machinery reproduces the calibration's own held-out number (the pass band's source)."""

    paths = {'geometry': B110_GEOMETRY, 'parameters': B110 / 'train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json'}

    def test_boundary_family_history_forecast_band(self):
        paths = {**self.paths, 'reference_config': B110 / 'train_s31_v2nc/boundary_literature_v1/boundary_config.json'}
        component, geometry = pg._component(paths)
        sys.path.insert(0, str(ROOT / pg.CAL))
        from boundary_factory import ObservationData, build_window
        data = ObservationData(B110_OBSERVATIONS)
        cutoff = 2700.1
        window = build_window(data, cutoff, 'history_forecast', None,
                              model_step_sec=int(component.base.simulation.T_f_sec), horizon_sec=pg.HORIZON)
        commands, _ = pg.held_vsl_commands({'vsl': {f'{r}__seg{i}': 110.0 for r in ('FW_E', 'FW_W') for i in range(21)}},
                                           component, pg.CellMap(geometry))
        for step in window['boundary_steps']:
            step['vsl_commands'] = dict(commands)
        params = json.loads(Path(paths['parameters']).read_text(encoding='utf-8'))['parameters']
        result = component.rollout(window['initial_cells'], window['boundary_steps'], params,
                                   window['initial_origin_queue'], horizon_sec=pg.HORIZON)
        predicted = {lead: [c for c in result['cells'] if abs(float(c['time_s']) - (cutoff + lead)) < 1e-6]
                     for lead in pg.LEADS}
        observed = {lead: data.cells[round(cutoff + lead, 6)] for lead in pg.LEADS}
        metrics = pg.compare_cells(predicted, observed, component.roads)
        self.assertEqual(pg.verdict(metrics, pg.DEFAULT_BAND), {'FW_E': 'PASS', 'FW_W': 'PASS'})
        self.assertGreater(metrics['FW_E']['speed']['rmse'], 20.0)       # inside the quoted 20-25 / 13-17 band
        self.assertGreater(metrics['FW_W']['speed']['rmse'], 13.0)

    def test_receiving_nodes_need_ramp_dynamics(self):
        paths = {**self.paths, 'reference_config': REFERENCE, 'port_profile': REFERENCE}
        tmp = Path(tempfile.mkdtemp(prefix='n31_gate_rx_'))
        try:
            window = tmp / 'w.json'
            window.write_text(json.dumps({'boundary_steps': [{'window_start_s': 900.0, 'window_end_s': 901.0}]}),
                              encoding='utf-8')
            with mock.patch.object(pg, 'plant_sources', return_value=(ROOT, {}, paths)):
                with self.assertRaises(ToolError) as caught:
                    pg.run_gate('t.json', tmp, window)
            self.assertIn('ramp_dynamics', str(caught.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _read_csv(path):
    import csv
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


@unittest.skipUnless(B110_GEOMETRY.is_file() and (B110_OBSERVATIONS / 'manifest.json').is_file(),
                     'b110 geometry copy or the read-only B110 observations are not available')
class RealExtraction(unittest.TestCase):
    """extract = the calibration extractor on the same FZP, cut at the cutoff: B110's own rows, value for value."""

    CUTOFF = 900.1

    @classmethod
    def setUpClass(cls):
        manifest = json.loads((B110_OBSERVATIONS / 'manifest.json').read_text(encoding='utf-8'))
        cls.fzp = Path(manifest['fzp']['path'])
        cls.errs = [Path(e['path']) for e in manifest['errors']]
        if not cls.fzp.is_file() or not cls.errs or not all(e.is_file() for e in cls.errs):
            raise unittest.SkipTest('the NET run FZP/.err behind B110 is not available')
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_extract_'))
        cls.out = cls.tmp / 'obs'
        cls.network = json.loads(B110_GEOMETRY.read_text(encoding='utf-8-sig'))['network']['sha256']
        cls.manifest = pg.extract_observations(cls.fzp, cls.errs, B110_GEOMETRY, cls.CUTOFF, cls.out,
                                               network_sha256=cls.network)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_rows_equal_the_calibration_extraction_up_to_the_cutoff(self):
        self.assertEqual(self.manifest['native_phase_sec'], 0.1)
        self.assertEqual(self.manifest['terminal_sec'], self.CUTOFF)
        for name, key in (('cells_30s', 'time_s'), ('flows_30s', 'window_end_s'), ('boundaries_30s', 'window_end_s')):
            mine = _read_csv(self.out / f'{name}.csv')
            theirs = [r for r in _read_csv(B110_OBSERVATIONS / f'{name}.csv') if float(r[key]) <= self.CUTOFF + 1e-9]
            self.assertEqual(len(mine), len(theirs), name)
            self.assertEqual(mine, theirs, name)
        self.assertTrue((self.out / 'ports_30s.csv').is_file())
        cohorts = json.loads((self.out / 'port_cohorts_30s.json').read_text(encoding='utf-8'))
        self.assertIn(str(self.CUTOFF), cohorts)

    def test_history_forecast_window_is_the_same_as_from_b110(self):
        sys.path.insert(0, str(ROOT / pg.CAL))
        from boundary_factory import ObservationData, build_window
        mine = build_window(ObservationData(self.out), self.CUTOFF, 'history_forecast', model_step_sec=1, horizon_sec=450)
        theirs = build_window(ObservationData(B110_OBSERVATIONS), self.CUTOFF, 'history_forecast', model_step_sec=1,
                              horizon_sec=450)
        self.assertEqual(mine, theirs)

    def test_refusals(self):
        with self.assertRaisesRegex(ToolError, 'off the 30 s observation grid'):
            pg.extract_observations(self.fzp, self.errs, B110_GEOMETRY, 900.0, self.tmp / 'x1')
        with self.assertRaisesRegex(ToolError, 'another network'):
            pg.extract_observations(self.fzp, self.errs, B110_GEOMETRY, self.CUTOFF, self.tmp / 'x2',
                                    network_sha256='0' * 64)
        with self.assertRaisesRegex(ToolError, 'never reused'):
            pg.extract_observations(self.fzp, self.errs, B110_GEOMETRY, self.CUTOFF, self.out)
        self.assertEqual(self.manifest['lane_change_removals'], 270)       # NEW-8: the NET run's 270 removals


class G1Sources(unittest.TestCase):
    """extract --run finds the FZP in the obs150 EvalOutDir and both .err files of the network folder."""

    def test_sources_of_a_watchdog_run(self):
        import synthetic_run as sr
        tmp = Path(tempfile.mkdtemp(prefix='n31_g1src_'))
        try:
            syn = sr.SyntheticRun(tmp)
            eval_dir = Path(syn.states[900][oc.RAW_STATE_KEY]['mer']['source']).parent
            eval_dir.mkdir(parents=True)
            (eval_dir / f'sdmpc31_{syn.name}_001.fzp').write_bytes(b'$VEHICLE:SIMSEC;NO\n')
            prov = json.loads(syn.provenance_path.read_text(encoding='utf-8'))
            prov['files']['network'] = {'path': str(syn.inpx), 'sha256': 'a' * 64}
            syn.provenance_path.write_text(json.dumps(prov), encoding='utf-8')
            fzp, errs, network = pg.g1_sources(syn.run)
            self.assertEqual(fzp.parent, eval_dir)
            self.assertEqual(errs, [syn.err])                      # no <stem>.err was written
            self.assertEqual(network, 'a' * 64)
            network_err = syn.err.with_name(f'sdmpc31_{syn.name}.err')
            network_err.write_text('network messages\r\n', encoding='utf-8')
            self.assertEqual(pg.g1_sources(syn.decisions)[1], [network_err, syn.err])
            (eval_dir / 'second.fzp').write_bytes(b'')
            with self.assertRaisesRegex(ToolError, 'Exactly one FZP'):
                pg.g1_sources(syn.run)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RunPlumbing(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='n31_gate_'))
        self.dec = self.tmp / 'decisions_sdmpc31_g1'
        (self.dec / 'lane_observations').mkdir(parents=True)
        for t in (900, 1050, 1200, 1350):
            (self.dec / 'lane_observations' / f'frame_{t:06d}.json').write_text(
                json.dumps(frame(t, [(1, 10.0, 50.0 + t / 100)] * 5 + [(3, 10.0, 40.0)] * 6)), encoding='utf-8')
        (self.dec / 'action_000900.json').write_text(json.dumps(
            {'vsl': {'FW_E__seg0': 110.0, 'FW_E__seg1': 80.0, 'FW_W__seg0': 110.0, 'FW_W__seg1': 110.0},
             'ramp_metering': {'RM_C10480': 900.0}}), encoding='utf-8')
        steps = [{'window_start_s': 900.0 + 10 * i, 'window_end_s': 910.0 + 10 * i} for i in range(45)]
        self.window = self.tmp / 'window.json'
        self.window.write_text(json.dumps({'initial_cells': [], 'boundary_steps': steps,
                                           'initial_origin_queue': {'FW_E': 0.0, 'FW_W': 0.0},
                                           'port_dynamics': {'schema': 'physical-off-storage/v1',
                                                             'occupancy_lane_loss': True}, 'meta': {}}), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_rollout_variants_and_report(self):
        calls = []

        class Model:
            roads = ('FW_E', 'FW_W')
            base = stub_component().base

            def rollout(self, initial, steps, parameters, queue, *, port_dynamics, horizon_sec):
                calls.append({'initial': initial, 'vsl': steps[0]['vsl_commands'], 'lane_loss': port_dynamics['occupancy_lane_loss'],
                              'n_steps': len(steps), 'horizon': horizon_sec, 'parameters': parameters})
                bias = 5.0 if port_dynamics['occupancy_lane_loss'] else 60.0     # off: above 2 x 25 and 2 x 17
                cells = []
                for lead in pg.LEADS:
                    for c in pg.CellMap(GEOMETRY).bin(frame(900 + lead, [(1, 10.0, 50.0 + (900 + lead) / 100)] * 5
                                                            + [(3, 10.0, 40.0)] * 6), 900 + lead):
                        cells.append({**c, 'v_kmh': None if c['v_kmh'] is None else c['v_kmh'] + bias})
                return {'cells': cells}

        paths = {'geometry': self.tmp / 'g.json', 'parameters': self.tmp / 'p.json', 'port_profile': self.tmp / 'pp.json'}
        paths['parameters'].write_text(json.dumps({'parameters': {'by_direction': {}}}), encoding='utf-8')
        paths['port_profile'].write_text(json.dumps({'occupancy_lane_loss': True}), encoding='utf-8')
        with mock.patch.object(pg, 'plant_sources', return_value=(ROOT, {}, paths)), \
                mock.patch.object(pg, '_component', return_value=(Model(), GEOMETRY)):
            report = pg.run_gate('t.json', self.dec, self.window, out=self.tmp / 'gate.json')
        self.assertEqual([c['lane_loss'] for c in calls], [True, False])
        self.assertEqual(calls[0]['vsl'], {'FW_E__seg0': 110.0, 'FW_E__seg2': 80.0, 'FW_W__seg0': 110.0})
        self.assertEqual((calls[0]['n_steps'], calls[0]['horizon']), (45, 450))
        initial = {(c['road'], c['cell']): c['n_veh'] for c in calls[0]['initial']}
        self.assertEqual(initial[('FW_E', 0)], 5.0)                # the G1 frame at the cutoff, binned
        self.assertEqual(report['default_variant'], 'lane_loss_on')
        self.assertEqual(report['verdict'], {'FW_E': 'PASS', 'FW_W': 'PASS'})
        self.assertEqual(report['variants']['lane_loss_off']['verdict'], {'FW_E': 'STOP_ASK', 'FW_W': 'STOP_ASK'})
        self.assertAlmostEqual(report['variants']['lane_loss_on']['metrics']['FW_E']['speed']['rmse'], 5.0)
        self.assertEqual(report['meter_rates_held'], {'RM_C10480': 900.0})
        self.assertTrue((self.tmp / 'gate.json').is_file())

    def test_g1_window_on_the_fzp_phase(self):
        """A window extracted from the G1 FZP starts at 900.1: predictions are read at 900.1 + lead."""
        starts = []

        class Model:
            roads = ('FW_E', 'FW_W')
            base = stub_component().base

            def rollout(self, initial, steps, parameters, queue, *, port_dynamics, horizon_sec):
                starts.append((steps[0]['window_start_s'], {c['time_s'] for c in initial}))
                cells = []
                for lead in pg.LEADS:
                    t = steps[0]['window_start_s'] + lead
                    cells += pg.CellMap(GEOMETRY).bin(frame(900 + lead, [(1, 10.0, 50.0 + (900 + lead) / 100)] * 5
                                                            + [(3, 10.0, 40.0)] * 6), t)
                return {'cells': cells}

        paths = {'geometry': self.tmp / 'g.json', 'parameters': self.tmp / 'p.json', 'port_profile': self.tmp / 'pp.json'}
        paths['parameters'].write_text(json.dumps({'parameters': {}}), encoding='utf-8')
        paths['port_profile'].write_text(json.dumps({'occupancy_lane_loss': True}), encoding='utf-8')
        for offset, ok in ((0.1, True), (1.5, False)):
            window = json.loads(self.window.read_text(encoding='utf-8'))
            for step in window['boundary_steps']:
                step['window_start_s'] += offset
                step['window_end_s'] += offset
            path = self.tmp / f'window_{offset}.json'
            path.write_text(json.dumps(window), encoding='utf-8')
            with mock.patch.object(pg, 'plant_sources', return_value=(ROOT, {}, paths)), \
                    mock.patch.object(pg, '_component', return_value=(Model(), GEOMETRY)):
                if ok:
                    report = pg.run_gate('t.json', self.dec, path, out=self.tmp / 'gate_g1.json')
                    self.assertEqual(report['window_offset_s'], 0.1)
                    self.assertEqual(report['verdict'], {'FW_E': 'PASS', 'FW_W': 'PASS'})
                    self.assertEqual(starts[0], (900.1, {900.1}))      # the 900 frame is the state at 900.1
                else:
                    with self.assertRaisesRegex(ToolError, 'not at the cutoff'):
                        pg.run_gate('t.json', self.dec, path, out=self.tmp / 'gate_bad.json')


if __name__ == '__main__':
    unittest.main()
