"""Pinned phase mappings, pre-head peel-offs and one head-free tunnel."""
import copy
import json
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected
from diagnostics.route_input_fixtures import decisions
from evaluation.controllers import physical_movement_routes as physical
from evaluation.controllers import vissim_stackelberg_adapter as adapter

EVIDENCE = 'diagnostics/physical_phase_authority_ver2.json'


class PhaseAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = decisions()
        cls.previous = run / 'action_001050.json'
        cls.tuning = adapter.load_optional_json(str(ROOT / 'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json'))
        cls.tuning.setdefault('urban', {}).setdefault('movements', {}).pop('physical_phase_authority', None)
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / 'config.json'
            config.write_text(json.dumps(cls.tuning), encoding='utf-8')
            cls.cfg, cls.state, cls.dm, _, cls.raw, cls.mapping, _ = build_projected(
                config, run / 'state_001200.json', cls.previous, fixture_inputs=False)
        cls.plan = adapter.load_signal_group_actuation_plan()
        cls.document = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))

    def configure(self, cfg=None, plan=None, path=EVIDENCE):
        tuning = copy.deepcopy(self.tuning)
        tuning['urban']['movements']['physical_phase_authority'] = path
        return physical.configure_phase_authority(cfg or self.cfg, tuning, plan or self.plan, state_json=self.raw)

    def configure_document(self, cfg, document):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'evidence.json'
            path.write_text(json.dumps(document), encoding='utf-8')
            return self.configure(cfg, path=str(path))

    def test_absent_flag_is_bit_identical_and_does_not_load_evidence(self):
        cfg = copy.deepcopy(self.cfg)
        before = pickle.dumps(cfg)
        self.assertEqual(physical.configure_phase_authority(cfg, {}, None), {})
        self.assertEqual(pickle.dumps(cfg), before)

    def test_exactly_three_phase_fields_change_and_snapshot_stock_is_untouched(self):
        cfg = copy.deepcopy(self.cfg)
        before = copy.deepcopy(vars(cfg.network))
        state_bytes = pickle.dumps(self.state)
        legacy = copy.deepcopy(self.document)
        legacy.pop('unsignalized_movements')
        legacy.pop('head_free_movements', None)
        meta = self.configure_document(cfg, legacy)
        for name, row in self.document['by_movement'].items():
            self.assertEqual(cfg.network.urban_movements[name]['phase'], row['new_phase'])
            before['urban_movements'][name]['phase'] = row['new_phase']
        self.assertEqual(vars(cfg.network), before)
        self.assertEqual(pickle.dumps(self.state), state_bytes)
        self.assertEqual(meta['physical_phase_authority_corrected_count'], 3)
        self.assertNotIn('physical_unsignalized_authority_changes', meta)

    def test_peeloffs_only_change_authority_preserving_all_other_fields_and_stock(self):
        from src.models import urban_queue_model as uqm
        cfg = copy.deepcopy(self.cfg)
        before = copy.deepcopy(vars(cfg.network))
        snapshot = pickle.dumps((self.state, self.raw))
        evidence = (ROOT / EVIDENCE).read_bytes()
        for name in self.document['unsignalized_movements']:
            self.assertFalse(uqm.movement_specs(cfg)[name].get('unsignalized'))
        meta = self.configure(cfg)
        for name, row in self.document['by_movement'].items():
            before['urban_movements'][name]['phase'] = row['new_phase']
        for name in self.document['unsignalized_movements']:
            before['urban_movements'][name]['unsignalized'] = True
            self.assertTrue(uqm.movement_specs(cfg)[name]['unsignalized'])
        for name in self.document.get('head_free_movements', {}):
            before['urban_movements'][name]['unsignalized'] = True
            self.assertTrue(uqm.movement_specs(cfg)[name]['unsignalized'])
        # Includes the original beta, receiving links, storage and all capacities.
        self.assertEqual(vars(cfg.network), before)
        self.assertEqual(pickle.dumps((self.state, self.raw)), snapshot)
        self.assertEqual((ROOT / EVIDENCE).read_bytes(), evidence)
        self.assertEqual(meta['physical_phase_authority_corrected_count'], 3)
        self.assertEqual(meta['physical_unsignalized_authority_corrected_count'], 4)

    def test_peeloff_local_and_global_fraction_one_when_same_phase_sg2_is_red(self):
        from evaluation.controllers import signal_actuation_contract as clock
        from src.models.state import ControlAction
        cfg = copy.deepcopy(self.cfg)
        self.configure(cfg)
        follower = adapter.build_priced_wu_link_controller(cfg, self.tuning).nash_solver
        names = set(self.document['unsignalized_movements'])
        model = follower._local_models['SC1004']
        gated = next(name for name in model.movements if name not in names
                     and model.specs[name]['phase'] == 'SC1004_p3'
                     and not model.specs[name].get('unsignalized'))
        self.assertIn('2', self.plan['controllers']['1004']['phase_signal_groups']['p3'])
        control = clock.prepare_control(ControlAction.uncontrolled(cfg), cfg)
        state_before = pickle.dumps((self.state, self.raw))
        start = int(round(self.state.time_sec / cfg.simulation.T_u_sec))
        for offset in range(int(cfg.network.signal_cycle_length('SC1004'))):
            control.offsets['SC1004'] = float(offset)
            if all(clock.phase_fraction(control, cfg, model.specs[gated], start + i) == 0 for i in range(2)):
                break
        else:
            self.fail('Fixture has no two-substep SG2 RED interval')
        greens = {p: control.green_times['SC1004_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
        fractions = follower._offset_green_fractions_vec('SC1004', greens, float(offset), 2, start)
        self.assertEqual(fractions[gated], [0.0, 0.0])
        for name in names:
            self.assertEqual(model.phase_of[name], 'p3')
            self.assertEqual(fractions[name], [1.0, 1.0])
            self.assertEqual([clock.phase_fraction(control, cfg, model.specs[name], start + i)
                              for i in range(2)], [1.0, 1.0])
        self.assertEqual(pickle.dumps((self.state, self.raw)), state_before)

    def test_invalid_peeloff_proof_fails_before_phase_or_authority_commit(self):
        for field in ('missing_alias', 'extra_alias', 'origin', 'connector', 'path', 'heads', 'head_position', 'route'):
            with self.subTest(field=field):
                document = copy.deepcopy(self.document)
                rows = document['unsignalized_movements']
                row = rows['SC1004_W_to_S']
                if field == 'missing_alias': rows.pop('SC1004_offE_to_S')
                if field == 'extra_alias': rows['SC1004_W_to_E'] = copy.deepcopy(row)
                if field == 'origin': row['expected_spec']['origin'] = 'OR_F_W'
                if field == 'connector': row['connector']['source_pos'] += 1
                if field == 'path': row['path'][-1] = '47'
                if field == 'heads': row['source_heads'].pop()
                if field == 'head_position': row['source_heads'][0]['pos_m'] = 30.0
                if field == 'route': row['native_routes'] = ['1126:3']
                cfg = copy.deepcopy(self.cfg)
                before = pickle.dumps(cfg)
                with self.assertRaises(ValueError):
                    self.configure_document(cfg, document)
                self.assertEqual(pickle.dumps(cfg), before)

    def test_actual_upstream_or_landing_heads_are_not_ignored(self):
        # Inject altered parsed geometry so even matching evidence cannot bless
        # a pre-branch head, or omit heads belonging to any other controller.
        original_tree = ET.parse(ROOT / self.document['network']['path'])
        for location in ('upstream', '10642', '67', 'other_controller'):
            with self.subTest(location=location):
                tree = copy.deepcopy(original_tree)
                document = copy.deepcopy(self.document)
                heads = tree.getroot().find('signalHeads')
                head = next(h for h in heads if h.get('no') == '90030883')
                if location == 'upstream':
                    head.set('pos', '30')
                    for row in document['unsignalized_movements'].values():
                        next(h for h in row['source_heads'] if h['head'] == '90030883')['pos_m'] = 30.0
                else:
                    head = copy.deepcopy(head)
                    head.set('no', '99999999')
                    if location == 'other_controller': head.set('sg', '1 1')
                    else: head.set('lane', location + ' 1')
                    heads.append(head)
                cfg = copy.deepcopy(self.cfg)
                before = pickle.dumps(cfg)
                with patch.object(physical.ET, 'parse', return_value=tree):
                    with self.assertRaises(ValueError):
                        self.configure_document(cfg, document)
                self.assertEqual(pickle.dumps(cfg), before)

    def test_stale_phase_and_selected_plan_fail_before_any_mutation(self):
        for phase_error in (True, False):
            cfg, plan = copy.deepcopy(self.cfg), copy.deepcopy(self.plan)
            if phase_error:
                cfg.network.urban_movements['SC11_W_to_N_SC5']['phase'] = 'SC11_p2'
            else:
                plan['controllers']['1']['phase_signal_groups']['p4'].append(6)
            before = pickle.dumps(cfg)
            with self.assertRaises(ValueError):
                self.configure(cfg, plan)
            self.assertEqual(pickle.dumps(cfg), before)

    def test_wrong_lane_position_route_or_new_phase_is_rejected(self):
        for field in ('head_lane', 'head_position', 'route', 'new_phase'):
            document = copy.deepcopy(self.document)
            row = document['by_movement']['SC1_E_to_S_SC107']
            if field == 'head_lane': row['source_heads'][0]['lane'] = 9
            if field == 'head_position': row['source_heads'][0]['pos_m'] = 99
            if field == 'route': row['native_routes'] = ['23:1']
            if field == 'new_phase': row['new_phase'] = 'SC1_p1'
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'bad.json'
                path.write_text(json.dumps(document), encoding='utf-8')
                cfg = copy.deepcopy(self.cfg)
                before = pickle.dumps(cfg)
                with self.assertRaises(ValueError): self.configure(cfg, path=str(path))
                self.assertEqual(pickle.dumps(cfg), before)

    def test_actual_local_follower_and_area_endpoint_follow_corrected_phase(self):
        from evaluation.controllers import signal_actuation_contract as clock, urban_flow_accounting
        from evaluation.controllers.control_area_objective import get_ledger
        from src.controllers import rollout_endpoint as endpoint
        from src.controllers.local_signal_plant import rollout_local_tts_phased
        from src.models.state import ControlAction
        from src.models.demand import DemandStep
        from src.models import urban_queue_model as uqm

        cfg = copy.deepcopy(self.cfg)
        # Warm the identity cache first: the new follower must see the repaired specs.
        self.assertEqual(uqm.movement_specs(cfg)['SC1_E_to_S_SC107']['phase'], 'SC1_p4')
        self.configure(cfg)
        cfg.simulation.control_interval = 10.0  # one real freeway/two urban substeps
        follower = adapter.build_priced_wu_link_controller(cfg, self.tuning).nash_solver
        old_cfg = copy.deepcopy(self.cfg)
        old_cfg.simulation.control_interval = 10.0
        old_follower = adapter.build_priced_wu_link_controller(old_cfg, self.tuning).nash_solver
        control = clock.prepare_control(ControlAction.uncontrolled(cfg), cfg)
        neutral = DemandStep({}, {}, {})
        original_emit = urban_flow_accounting.emit_transfer
        for name, proof in self.document['by_movement'].items():
            signal = proof['expected_spec']['signal']
            model = follower._local_models[signal]
            self.assertEqual(model.specs[name]['phase'], proof['new_phase'])
            self.assertEqual(model.phase_of[name], proof['new_phase'].rpartition('_')[2])
            states = self.state.copy()
            states.urban_movement_queue[name] = 10.0
            get_ledger(states).stocks['movement:' + name] = {'inside': 10.0, 'outside': 0.0}
            before_state = pickle.dumps(states)
            start = int(round(states.time_sec / cfg.simulation.T_u_sec))
            corrected = cfg.network.urban_movements[name]
            old = dict(corrected, phase=proof['expected_spec']['phase'])
            offsets = {}
            for offset in range(int(cfg.network.signal_cycle_length(signal))):
                probe = control.copy()
                probe.offsets[signal] = float(offset)
                newer = [clock.phase_fraction(probe, cfg, corrected, start + i) for i in range(2)]
                older = [clock.phase_fraction(probe, cfg, old, start + i) for i in range(2)]
                if newer == [1.0, 1.0] and older == [0.0, 0.0]: offsets.setdefault('correct', offset)
                if newer == [0.0, 0.0] and older == [1.0, 1.0]: offsets.setdefault('old', offset)
            self.assertEqual(set(offsets), {'correct', 'old'})
            local_costs, old_local_costs, endpoint_release = {}, {}, {}
            for label, offset in offsets.items():
                probe = control.copy()
                probe.offsets[signal] = float(offset)
                greens = {p: probe.green_times[signal + '_' + p] for p in ('p1', 'p2', 'p3', 'p4')}
                fractions = follower._offset_green_fractions_vec(signal, greens, offset, 2, start)
                self.assertEqual(fractions[name], [1.0, 1.0] if label == 'correct' else [0.0, 0.0])
                local_costs[label] = rollout_local_tts_phased(
                    model, {name: 10.0}, {}, fractions,
                    {receiver: 10000.0 for receiver in model.receiving_of.values()}, 2, cfg.simulation.T_u_h)
                old_model = old_follower._local_models[signal]
                old_fractions = old_follower._offset_green_fractions_vec(signal, greens, offset, 2, start)
                old_local_costs[label] = rollout_local_tts_phased(
                    old_model, {name: 10.0}, {}, old_fractions,
                    {receiver: 10000.0 for receiver in old_model.receiving_of.values()}, 2, cfg.simulation.T_u_h)
                released = []
                def emit(state, config, source, target, vehicles, **kwargs):
                    if kwargs.get('route_key') == 'movement:' + name and source == 'movement:' + name:
                        released.append(float(vehicles))
                    return original_emit(state, config, source, target, vehicles, **kwargs)
                with patch.object(urban_flow_accounting, 'emit_transfer', emit):
                    result = endpoint.evaluate_price_point(states, probe, [neutral], (),
                        endpoint.ObjectiveSpec(cfg=cfg, depth_override=1, box_walk=False))
                endpoint_release[label] = sum(released)
                self.assertTrue(hasattr(result, 'control_area'))
                self.assertEqual(pickle.dumps(states), before_state)
            self.assertLess(local_costs['correct'], local_costs['old'])
            self.assertGreater(old_local_costs['correct'], old_local_costs['old'])
            self.assertGreater(endpoint_release['correct'], 0.0)
            self.assertEqual(endpoint_release['old'], 0.0)


class HeadFreeTunnelTests(unittest.TestCase):
    """Source-only proof tests: no model preparation, endpoint or VISSIM run."""

    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((ROOT / EVIDENCE).read_text(encoding='utf-8'))
        cls.plan = json.loads((ROOT / cls.document['selected_plan']['path']).read_text())
        cls.tree = ET.parse(ROOT / cls.document['network']['path'])
        cls.name = 'SC107_N_SC1_to_S'
        config = json.loads((ROOT / 'diagnostics/selected_control_demand/'
                            'codex_selected_fw070_u030_beta0_fast_r01/config.json').read_text())
        cls.surface_name = 'SC107_N_SC1_to_E_SC108'
        cls.surface = config['config_overrides']['network']['urban_movements'][cls.surface_name]

    def cfg(self):
        specs = {name: dict(row['expected_spec'], beta=0.25)
                 for table in ('by_movement', 'unsignalized_movements', 'head_free_movements')
                 for name, row in self.document[table].items()}
        for name in self.document['unsignalized_movements']:
            specs[name]['signal'] = 'SC1004'
        specs[self.surface_name] = copy.deepcopy(self.surface)
        return SimpleNamespace(network=SimpleNamespace(
            urban_movements=specs, movement_capacity_by_movement_veh_h={self.name: 413.0612244897959},
            urban_link_storage_veh={'SC107_S_out': 216.0}))

    def configure(self, cfg, document=None):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'proof.json'
            path.write_text(json.dumps(document or self.document), encoding='utf-8')
            tuning = {'urban': {'movements': {'physical_phase_authority': str(path)}}}
            return physical.configure_phase_authority(cfg, tuning, self.plan)

    def test_exact_native_tunnel_is_head_free_and_surface_sg7_is_separate(self):
        _, routes, _ = physical.load_evidence(EVIDENCE)
        path = self.document['head_free_movements'][self.name]['path']
        self.assertEqual(routes['1063:2']['path'], path)
        heads = self.tree.getroot().findall('./signalHeads/signalHead')
        self.assertFalse([h for h in heads if h.get('lane').split()[0] in path])
        surface_heads = [h for h in heads if h.get('no') in {'1070701', '1070702'}]
        self.assertEqual(len(surface_heads), 2)
        self.assertTrue(all(h.get('sg') == '107 7' and
                            h.get('lane').split()[0] == '1220043200' for h in surface_heads))
        self.assertIn('1220043200', routes['1063:1']['path'])
        self.assertIn('1220043200', routes['1063:3']['path'])
        self.assertNotIn('1220043200', path)

    def test_only_tunnel_authority_changes_against_previous_three_alias_contract(self):
        before_cfg, after_cfg = self.cfg(), self.cfg()
        previous = copy.deepcopy(self.document)
        previous.pop('head_free_movements')
        self.configure(before_cfg, previous)
        meta = self.configure(after_cfg)
        before = copy.deepcopy(vars(before_cfg.network))
        before['urban_movements'][self.name]['unsignalized'] = True
        self.assertEqual(vars(after_cfg.network), before)
        self.assertEqual(after_cfg.network.urban_movements[self.name]['phase'], 'SC107_p2')
        self.assertEqual(after_cfg.network.urban_movements[self.surface_name], self.surface)
        self.assertEqual(self.surface['phase'], 'SC107_p2')
        self.assertFalse(self.surface.get('unsignalized'))
        self.assertEqual(meta['physical_unsignalized_authority_corrected_count'], 4)

    def test_tunnel_service_is_independent_of_surface_p2_red_and_green(self):
        from evaluation.controllers import signal_actuation_contract as clock
        cfg = self.cfg()
        self.configure(cfg)
        cfg.network.signal_actuation_contract = {'nodes': {'SC107': {}}}
        cfg.simulation = SimpleNamespace(T_u_sec=5)
        control = SimpleNamespace(green_times={})
        tunnel = cfg.network.urban_movements[self.name]
        surface = cfg.network.urban_movements[self.surface_name]
        with patch.object(clock, '_validated_clock', return_value=(150.0, 0.0, [('p2', (30.0, 60.0))])):
            self.assertEqual(clock.phase_fraction(control, cfg, surface, 0), 0.0)
            self.assertEqual(clock.phase_fraction(control, cfg, surface, 6), 1.0)
            self.assertEqual(clock.phase_fraction(control, cfg, tunnel, 0), 1.0)
            self.assertEqual(clock.phase_fraction(control, cfg, tunnel, 6), 1.0)

    def test_invalid_tunnel_proof_is_rejected_before_any_change(self):
        for field in ('extra', 'path', 'route', 'connector', 'decision', 'conflict', 'phase'):
            with self.subTest(field=field):
                document = copy.deepcopy(self.document)
                row = document['head_free_movements'][self.name]
                if field == 'extra': document['head_free_movements'][self.surface_name] = copy.deepcopy(row)
                if field == 'path': row['path'][2] = '1220043200'
                if field == 'route': row['native_routes'] = ['1063:1']
                if field == 'connector': row['connectors']['10597']['source_lane'] = 1
                if field == 'decision': row['decision']['pos'] = 500.0
                if field == 'conflict': row['conflicts']['1486']['status'] = 'ONEYIELDSTWO'
                if field == 'phase': row['expected_spec']['phase'] = 'SC107_p1'
                cfg = self.cfg()
                before = pickle.dumps(cfg)
                with self.assertRaises(ValueError): self.configure(cfg, document)
                self.assertEqual(pickle.dumps(cfg), before)

    def test_any_actual_tunnel_head_or_changed_route_is_rejected(self):
        path = self.document['head_free_movements'][self.name]['path']
        for location in path + ['route', 'connector', 'conflict']:
            with self.subTest(location=location):
                tree = copy.deepcopy(self.tree)
                if location in path:
                    ET.SubElement(tree.getroot().find('signalHeads'), 'signalHead', {
                        'no': '99999999', 'lane': location + ' 1', 'sg': '1 1', 'pos': '0.1'})
                elif location == 'route':
                    tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1063']"
                              "/vehRoutSta/vehicleRouteStatic[@no='2']").set('destLink', '1220043200')
                elif location == 'connector':
                    tree.find("./links/link[@no='10597']/fromLinkEndPt").set('lane', '1220006803 1')
                else:
                    tree.find("./conflictAreas/conflictArea[@no='1486']").set('status', 'ONEYIELDSTWO')
                cfg = self.cfg()
                before = pickle.dumps(cfg)
                with patch.object(physical.ET, 'parse', return_value=tree):
                    with self.assertRaises(ValueError): self.configure(cfg)
                self.assertEqual(pickle.dumps(cfg), before)


if __name__ == '__main__':
    unittest.main()
