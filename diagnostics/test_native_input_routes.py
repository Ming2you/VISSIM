"""Native fixed route: source evidence, subset conservation and real runtime."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected
from diagnostics.route_input_fixtures import fixture_path
from evaluation.controllers import native_input_routes as routes, area_runtime
from src.models.state import ControlAction
from src.models.demand import DemandStep


def input_row():
    path = ROOT/'diagnostics/native_input_1096_route_ver2.json'
    return {'kind': 'native_fixed_route', 'physical_source': '201',
            'target_storage': 'SC16_to_SC7', 'physical_projection_links': ['201','10319'],
            'approach_path': ['201','10319','199','10314','194','10322','1210009600'],
            'route_evidence': {'path': str(path.relative_to(ROOT)),
                               'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}


class NativeRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='native1096_test_', dir=ROOT/'diagnostics')
        folder = Path(cls.directory.name)
        data = json.loads((ROOT/'diagnostics/native_internal_inputs_extended_ver2.json').read_text())
        data['inputs'] = {no: row for no,row in data['inputs'].items() if no in {'1091','1096'}}
        data['inputs']['1096'] = input_row()
        inputs = folder/'inputs.json'; inputs.write_text(json.dumps(data))
        tuning = json.loads((ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json').read_text())
        tuning['urban']['route_choice_corridor']['evidence_paths'] = [
            'diagnostics/route_choice_corridor_ver2.json',
            'diagnostics/route_choice_corridor_1128_ver2.json']
        tuning['urban']['movements'].pop('native_input_signal_authority', None)
        tuning['urban']['native_internal_inputs'] = str(inputs)
        config = folder/'config.json'; config.write_text(json.dumps(tuning))
        run = fixture_path(ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910')
        cls.raw_path = run/'state_000900.json'
        cls.raw_bytes = cls.raw_path.read_bytes()
        with patch.dict('os.environ', {'RW_MAINLINE_SG_ONLY':'1','RW_OFFSET_WRITER':'experiment'}):
            cls.built = build_projected(config, cls.raw_path, run/'action_000001.json', fixture_inputs=False)
            cls.action = adapter.control_from_json(run/'action_000001.json', cls.built[0], ControlAction)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_actual_initial_stock_is_subset_no_events_no_raw_mutation(self):
        cfg,state,detectors,_,raw,_,metadata = self.built
        initial = sum(str(r['link_no']) in {'201','10319'} for r in raw['vehicle_records']['records'])
        self.assertEqual(state.native_input_route_state['initial_veh'], initial)
        self.assertEqual(metadata['native_input_route_initial_veh'], initial)
        for link in ('201','10319'):
            self.assertEqual(detectors['transit_storage_projection'][link], 'SC16_to_SC7')
        self.assertEqual((state._control_area_ledger.entered_veh,state._control_area_ledger.ttd_veh,state._control_area_ledger.event_count),(0,0,0))
        state._control_area_ledger.assert_stocks(area_runtime.model_inventory(state,cfg))
        self.assertEqual(self.raw_path.read_bytes(),self.raw_bytes)
        stages = cfg.network.native_internal_inputs['inputs']['1096']['route_stages']
        self.assertEqual([s['movement'] for s in stages],['SC7_E_SC16_to_S_SC108','SC108_N_SC7_to_S'])
        self.assertGreater(stages[0]['distance_m'],0)
        self.assertGreater(stages[1]['distance_m'],0)

    def test_actual_450_seconds_conserves_and_candidate_copy_is_private(self):
        from diagnostics.probe_route_choice_integration import direct
        cfg,state,detectors,tuning,raw,_,_ = self.built
        payload = dict(cfg=cfg,state=state,detectors=detectors,tuning=tuning,raw=raw,
                       action=self.action,forecast=adapter.demand_from_state(raw,cfg,DemandStep,3))
        frozen = pickle.dumps(payload)
        on = direct(payload,True); off = direct(payload,False)
        self.assertEqual(on,off)
        self.assertEqual(frozen,pickle.dumps(payload))
        local = on['native_input_route_state']
        self.assertAlmostEqual(local['received_veh'],on['native_internal_input_state']['inputs']['1096']['admitted_veh'])
        self.assertAlmostEqual(sum(c['vehicles'] for c in local['cohorts'])+local['completed_veh'],local['initial_veh']+local['received_veh'])

    def test_actual_450_seconds_fresh_worker_and_repeat_match(self):
        from diagnostics.probe_route_choice_integration import direct
        cfg,state,detectors,tuning,raw,_,_ = self.built
        payload = dict(cfg=cfg,state=state,detectors=detectors,tuning=tuning,raw=raw,
                       action=self.action,forecast=adapter.demand_from_state(raw,cfg,DemandStep,3))
        original = pickle.dumps(payload)
        expected = direct(payload,False)
        self.assertEqual(expected,direct(payload,False))
        folder = Path(self.directory.name)
        source,destination = folder/'worker_in.pkl',folder/'worker_out.pkl'
        source.write_bytes(original)
        child = subprocess.run([sys.executable,'-X','utf8',str(ROOT/'diagnostics/probe_route_choice_integration.py'),
                                '--worker-off',str(source),str(destination)],cwd=ROOT,timeout=45,capture_output=True)
        self.assertEqual(child.returncode,0,child.stderr.decode('utf-8',errors='replace'))
        self.assertEqual(expected,pickle.loads(destination.read_bytes()))
        self.assertEqual(original,pickle.dumps(payload))

    def _reconfigure(self, tree=None, evidence=None):
        from diagnostics.audit_native_sc8_gate import NETWORK, MEMBERSHIP, CONTRACT
        tree = tree or ET.parse(NETWORK)
        row = input_row()
        if evidence is not None:
            file = Path(self.directory.name)/'private_route.json'
            file.write_text(json.dumps(evidence),encoding='utf-8')
            row['route_evidence'] = {'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        links = {n.get('no'):n for n in tree.findall('./links/link')}
        inside = set(map(str,json.loads(MEMBERSHIP.read_text())['inside_links']))
        return routes.configure_input(self.built[0],row,tree,links,{k:k in inside for k in links},
                                      json.loads(CONTRACT.read_text()),self.built[4])

    def test_gate_geometry_is_split_and_stale_head_or_missing_gate_fails(self):
        from diagnostics.audit_native_sc8_gate import NETWORK
        stages = self._reconfigure()['route_stages']
        gate = stages[1]['native_fixed_gate']
        self.assertTrue(gate['timing_only'])
        self.assertAlmostEqual(gate['pre_gate_distance_m']+gate['post_gate_distance_m'],stages[1]['distance_m'])
        self.assertAlmostEqual(gate['lane_position_spread_m'],0.05663)
        doc = json.loads((ROOT/'diagnostics/native_input_1096_route_ver2.json').read_text())
        doc['stages'][1].pop('native_fixed_gate')
        with self.assertRaisesRegex(ValueError,'unselected native signal head'):
            self._reconfigure(evidence=doc)
        tree = ET.parse(NETWORK)
        tree.find('./signalHeads/signalHead[@no="150401"]').set('pos','200.0')
        with self.assertRaisesRegex(ValueError,'head authority changed'):
            self._reconfigure(tree=tree)

    def test_unlisted_native_head_or_wrong_controller_offset_fails(self):
        from diagnostics.audit_native_sc8_gate import NETWORK
        tree = ET.parse(NETWORK)
        extra = deepcopy(tree.find('./signalHeads/signalHead[@no="150401"]'))
        extra.set('no','extra'); extra.set('pos','100'); extra.set('sg','8 1')
        tree.find('./signalHeads').append(extra)
        with self.assertRaisesRegex(ValueError,'unselected native signal head'):
            self._reconfigure(tree=tree)
        tree = ET.parse(NETWORK)
        tree.find('./signalControllers/signalController[@no="8"]').set('offset','1')
        with self.assertRaisesRegex(ValueError,'controller/program binding changed'):
            self._reconfigure(tree=tree)

    def _waiting_state(self, amount=3.):
        cfg = deepcopy(self.built[0])
        stage = cfg.network.native_internal_inputs['inputs']['1096']['route_stages'][1]
        origin,movement = stage['origin'],stage['movement']
        state = SimpleNamespace(urban_link_speed_kph={origin:36.},urban_movement_queue={movement:0.},
            urban_link_storage={origin:cfg.network.urban_link_storage_veh[origin]-amount},
            native_input_route_state={'last_step':14,'initial_veh':amount,'received_veh':0.,'completed_veh':0.,
                'cohorts':[dict(input='1096',stage=1,vehicles=amount,due=15,queued=False,native_gate_passed=False)]})
        return cfg,state,stage

    def test_actual_clock_red_hold_once_only_green_and_residual_transit(self):
        cfg,state,stage = self._waiting_state()
        origin,movement = stage['origin'],stage['movement']
        initial = pickle.dumps(state)
        for step in range(15,24):  # [75,120): all RED
            routes.advance(state,cfg,step)
            self.assertEqual(state.urban_movement_queue[movement],0.)
            self.assertFalse(state.native_input_route_state['cohorts'][0]['native_gate_passed'])
        self.assertEqual(cfg.network.urban_link_storage_veh[origin]-state.urban_link_storage[origin],3.)
        routes.advance(state,cfg,24)  # [120,125): GREEN starts at121, not120
        cohort = state.native_input_route_state['cohorts'][0]
        self.assertEqual(cohort['native_gate_passage_sec'],121.)
        due = cohort['due']
        self.assertGreater(due,24)
        self.assertEqual(state.urban_movement_queue[movement],0.)
        frozen = pickle.dumps(state)
        with self.assertRaisesRegex(ValueError,'sequential'):
            routes.advance(state,cfg,24)
        self.assertEqual(frozen,pickle.dumps(state))
        # Failing if queried again proves the passed gate is not reapplied while
        # completing transit or waiting for the ordinary movement queue.
        with patch.object(routes,'_first_native_green',side_effect=AssertionError('gate repeated')):
            for step in range(25,due+2): routes.advance(state,cfg,step)
        self.assertEqual(state.urban_movement_queue[movement],3.)
        self.assertEqual(state.urban_link_storage[origin],cfg.network.urban_link_storage_veh[origin])
        self.assertEqual(cohort['native_gate_passage_sec'],121.)
        self.assertNotEqual(initial,pickle.dumps(state))

    def test_finite_existing_queue_admits_partial_and_tiny_tags_survive_gate(self):
        from src.models import urban_queue_model as uqm
        cfg,state,stage = self._waiting_state()
        movement,origin = stage['movement'],stage['origin']
        for step in range(15,25): routes.advance(state,cfg,step)
        due = state.native_input_route_state['cohorts'][0]['due']
        maximum = uqm._queue_max(cfg,movement,cfg.network.urban_movements[movement])
        state.urban_movement_queue[movement] = maximum-0.5
        for step in range(25,due+1): routes.advance(state,cfg,step)
        self.assertEqual(state.urban_movement_queue[movement],maximum)
        self.assertEqual(sum(c['vehicles'] for c in state.native_input_route_state['cohorts'] if c['queued']),0.5)
        self.assertAlmostEqual(cfg.network.urban_link_storage_veh[origin]-state.urban_link_storage[origin],2.5)
        cfg,tiny,stage = self._waiting_state(1.2e-8)
        tiny.native_input_route_state['cohorts'] = [dict(tiny.native_input_route_state['cohorts'][0],vehicles=0.6e-8) for _ in range(2)]
        for step in range(15,25): routes.advance(tiny,cfg,step)
        self.assertEqual(len(tiny.native_input_route_state['cohorts']),2)
        self.assertEqual(sum(c['vehicles'] for c in tiny.native_input_route_state['cohorts']),1.2e-8)

    def test_pinned_clock_audit_and_canonical_boundaries(self):
        # The producer performs the complete LSA comparison. This portable
        # regression consumes its recorded evidence and calls the real clock;
        # it never falls back to original runs or claims a fresh LSA replay.
        proof = json.loads((ROOT/'diagnostics/native_1096_sc8_gate_ver2.json').read_text(encoding='utf-8'))
        self.assertTrue(proof['clock_audit']['valid'])
        self.assertEqual(proof['clock_audit']['event_count'],135)
        gate = self.built[0].network.native_internal_inputs['inputs']['1096']['route_stages'][1]['native_fixed_gate']
        self.assertIsNone(routes._first_native_green(gate,72.,75.))  # AMBER
        self.assertIsNone(routes._first_native_green(gate,75.,120.))
        self.assertIsNone(routes._first_native_green(gate,120.,121.))  # half-open end
        self.assertEqual(routes._first_native_green(gate,120.,125.),121.)
        self.assertEqual(routes._first_native_green(gate,131.,135.),131.)
        self.assertEqual(routes._first_native_green(gate,240.,245.),241.)


class TinyResidualTests(unittest.TestCase):
    def test_two_small_positive_residuals_survive_shared_queue_service(self):
        cfg = SimpleNamespace(network=SimpleNamespace(
            native_internal_inputs={'inputs': {'1096': {'route_stages':[{'movement':'m','origin':'a','target':'b'}]}}},
            urban_movements={'m':{'receiving_link':'b'}},urban_link_storage_veh={'a':10.,'b':10.}))
        state = SimpleNamespace(urban_movement_queue={'m':1.2e-8},urban_link_storage={'a':10.,'b':8.+1.2e-8},
            urban_arrival_buffer={},urban_storage_release_buffer={},
            native_input_route_state={'last_step':0,'initial_veh':2.,'received_veh':0.,'completed_veh':0.,
                'cohorts':[dict(input='1096',stage=0,vehicles=1.,due=0,queued=True) for _ in range(2)]})
        with patch('src.models.urban_queue_model._link_delay_steps',return_value=1), patch('src.models.urban_queue_model.approach_routing',return_value={}):
            self.assertTrue(routes.receive_accepted(state,cfg,'m',2.-1.2e-8,0))
        self.assertEqual(len(state.native_input_route_state['cohorts']),2)
        self.assertAlmostEqual(sum(c['vehicles'] for c in state.native_input_route_state['cohorts']),1.2e-8)


if __name__ == '__main__':
    unittest.main()
