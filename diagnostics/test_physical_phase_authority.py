"""Three proven phase mappings; no routing, stock, or capacity calibration."""
import copy
import json
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_absent_flag_is_bit_identical_and_does_not_load_evidence(self):
        cfg = copy.deepcopy(self.cfg)
        before = pickle.dumps(cfg)
        self.assertEqual(physical.configure_phase_authority(cfg, {}, None), {})
        self.assertEqual(pickle.dumps(cfg), before)

    def test_exactly_three_phase_fields_change_and_snapshot_stock_is_untouched(self):
        cfg = copy.deepcopy(self.cfg)
        before = copy.deepcopy(vars(cfg.network))
        state_bytes = pickle.dumps(self.state)
        meta = self.configure(cfg)
        for name, row in self.document['by_movement'].items():
            self.assertEqual(cfg.network.urban_movements[name]['phase'], row['new_phase'])
            before['urban_movements'][name]['phase'] = row['new_phase']
        self.assertEqual(vars(cfg.network), before)
        self.assertEqual(pickle.dumps(self.state), state_bytes)
        self.assertEqual(meta['physical_phase_authority_corrected_count'], 3)

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


if __name__ == '__main__':
    unittest.main()
