"""Actual source binding and first native anchor; no rollout or VISSIM calls."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from diagnostics.test_native_signal_contract import fixture, ROOT
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import runtime_setup
from evaluation.controllers.fixed_signal_schedule import _signal_program_path

PLAN = ROOT / 'reports/20260911_decision_runtime/native_clock_plan_v1.json'
PHYSICAL_FIELDS = ('N_P_star', 'N_UF_star', 'green_times', 'offsets', 'vsl',
                   'ramp_metering', 'inflow_outflow_allocation')


class Action(SimpleNamespace):
    def copy(self):
        return deepcopy(self)


def nominal_action(cfg):
    return Action(N_P_star=1000., N_UF_star=7200.,
        green_times={s + '_' + p: (0. if p not in cfg.network.signal_live_phases(s) else 30.)
                     for s in cfg.network.signals for p in ('p1', 'p2', 'p3', 'p4')},
        offsets={s: 0. for s in cfg.network.signals},
        vsl={'FW_E': 100., 'FW_W': 80.}, ramp_metering={'D_W': 1800., 'F_E': 1800.},
        inflow_outflow_allocation={'unchanged': .75}, diagnostics={'no_control_active': True})


class NativeRuntimeReferenceTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.raw, self.source, _, _ = fixture()
        self.network = ROOT / self.source['network']
        self.plan_patch = patch.dict(adapter._CFG_STRINGS, {'signal_actuation_plan_json': str(PLAN)})
        self.plan_patch.start()
        self.addCleanup(self.plan_patch.stop)

    def test_actual_network_binds_every_source_and_no_control_is_exact(self):
        metadata = adapter.validate_native_signal_runtime_source(self.cfg, {'network_path': str(self.network)})
        self.assertEqual(metadata, {'native_signal_runtime_sources_verified': 17.})
        proof = self.cfg.network.native_signal_runtime_source_binding
        self.assertEqual(proof['network_sha256'], self.source['network_sha256'])
        self.assertEqual(len(proof['controllers']), 17)
        for signal, row in proof['controllers'].items():
            self.assertEqual(row['program_sha256'], self.source['controllers'][signal[2:]]['program_file_sha256'])
        action = nominal_action(self.cfg)
        untouched = {name: deepcopy(getattr(action, name)) for name in
                     ('N_P_star', 'N_UF_star', 'vsl', 'ramp_metering', 'inflow_outflow_allocation')}
        self.assertIs(adapter.represent_native_no_control_signals(action, self.cfg), action)
        for sc, node in self.raw['controllers'].items():
            basis = node['native_clock_basis']
            self.assertEqual({p: action.green_times[f'SC{sc}_{p}'] for p in ('p1', 'p2', 'p3', 'p4')},
                             basis['native_green_sec'])
            self.assertEqual(action.offsets['SC' + sc], basis['reference_offset_sec'])
        self.assertEqual([action.green_times['SC7_' + p] for p in ('p1', 'p2', 'p3', 'p4')], [67., 90., 0., 24.])
        self.assertEqual([action.green_times['SC16_' + p] for p in ('p1', 'p2', 'p3', 'p4')], [63., 17., 27., 0.])
        self.assertEqual((action.offsets['SC7'], action.offsets['SC16']), (119., 1.))
        for name, value in untouched.items(): self.assertEqual(getattr(action, name), value)
        reference = action.diagnostics['no_control_native_signal_reference']
        self.assertFalse(reference['new_com_command'])
        self.assertEqual(reference['source_plan_sha256'], adapter._file_sha256(PLAN))

    def test_source_program_active_number_controller_offset_and_type_mismatches_fail(self):
        for failure in ('program', 'prog_no', 'offset', 'inactive', 'type', 'missing'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                cfg = deepcopy(self.cfg)
                tree = ET.parse(self.network)
                controllers = tree.find('./signalControllers')
                for node in controllers:
                    supply = node.get('supplyFile2', '')
                    if supply:
                        node.set('supplyFile2', str(_signal_program_path(self.network, supply)))
                node = next(row for row in controllers if row.get('no') == '7')
                if failure == 'program': node.set('supplyFile2', str(ROOT / self.source['controllers']['16']['program']))
                elif failure == 'prog_no': node.set('progNo', '2')
                elif failure == 'offset': node.set('offset', '1')
                elif failure == 'inactive': node.set('active', 'false')
                elif failure == 'type': node.set('type', 'EXTERNAL')
                else: controllers.remove(node)
                path = Path(folder) / 'network.inpx'
                tree.write(path, encoding='utf-8', xml_declaration=True)
                with self.assertRaisesRegex(ValueError, 'SC7: loaded'):
                    adapter.validate_native_signal_runtime_source(cfg, {'network_path': str(path)})
                self.assertFalse(hasattr(cfg.network, 'native_signal_runtime_source_binding'))

    def test_disabled_reference_is_identity_without_source_or_plan_access(self):
        cfg = SimpleNamespace(network=SimpleNamespace())
        action = nominal_action(self.cfg)
        before = deepcopy(vars(action))
        with patch.object(adapter, 'signal_group_actuation_plan_path', side_effect=AssertionError('disabled plan read')):
            self.assertEqual(adapter.validate_native_signal_runtime_source(cfg, {}), {})
            self.assertIs(adapter.represent_native_no_control_signals(action, cfg), action)
            self.assertEqual(vars(action), before)
            factory = SimpleNamespace(uncontrolled=lambda _: action)
            self.assertIs(adapter._make_no_control(factory, cfg), action)

    def test_no_control_factory_uses_source_representation_and_refuses_partial_contract(self):
        action = nominal_action(self.cfg)
        factory = SimpleNamespace(uncontrolled=lambda _: action)
        self.assertIs(adapter._make_no_control(factory, self.cfg), action)
        self.assertEqual(action.offsets['SC7'], 119.)
        cfg = deepcopy(self.cfg)
        cfg.network.signal_actuation_contract['nodes']['SC16'].pop('native_clock_basis')
        with self.assertRaisesRegex(ValueError, 'Incomplete native no-control reference'):
            adapter.represent_native_no_control_signals(nominal_action(cfg), cfg)

    def test_historical_native_reference_accepts_exact_and_rejects_nominal_or_stale_proof(self):
        from evaluation.controllers import area_meter_finalization as meters
        adapter.validate_native_signal_runtime_source(self.cfg, {'network_path': str(self.network)})
        for variant in ('exact', 'nominal', 'stale_plan_proof', 'offset', 'no_proof'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as folder:
                previous = nominal_action(self.cfg)
                if variant != 'nominal': adapter.represent_native_no_control_signals(previous, self.cfg)
                if variant == 'stale_plan_proof': previous.diagnostics['no_control_native_signal_reference']['source_plan_sha256'] = 'stale'
                if variant == 'offset': previous.offsets['SC7'] = 0.
                if variant == 'no_proof': previous.diagnostics.pop('no_control_native_signal_reference')
                raw = {name: getattr(previous, name) for name in (*PHYSICAL_FIELDS, 'diagnostics')}
                raw.update(run_provenance={'run_id': 'native-fixture'},
                           metadata={'sim_sec': 750., 'run_provenance': {'run_id': 'native-fixture'}})
                path = Path(folder) / 'action_000750.json'
                path.write_text(json.dumps(raw), encoding='utf-8')
                with path.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
                    csv.DictWriter(stream, fieldnames=adapter.action_csv_schema.ACTION_CSV_FIELDS).writeheader()
                with patch.object(meters, 'prepare_recorded_historical_meter_reference', return_value={'stage': 'meter'}) as prepare:
                    if variant == 'exact':
                        result, pins = adapter.load_joint_historical_reference(path, previous, self.cfg,
                            expected_run_id='native-fixture', expected_previous_sim_sec=750.)
                        self.assertEqual(result, {'stage': 'meter'})
                        self.assertEqual(len(pins), 2)
                        prepare.assert_called_once()
                    else:
                        with self.assertRaisesRegex(ValueError, 'nominal archived warmup cannot be substituted'):
                            adapter.load_joint_historical_reference(path, previous, self.cfg,
                                expected_run_id='native-fixture', expected_previous_sim_sec=750.)
                        prepare.assert_not_called()

    def test_controlled_serialization_roundtrip_keeps_written_clock_not_inherited_native_claim(self):
        from evaluation.controllers import area_meter_finalization as meters
        previous = adapter.represent_native_no_control_signals(nominal_action(self.cfg), self.cfg)
        previous.green_times['SC1004_p1'] = 40.
        previous.green_times['SC1004_p2'] = 29.
        previous.offsets['SC1004'] = 0.
        previous.diagnostics['retained_context'] = {'nested': [1, 2]}
        before = deepcopy(vars(previous))
        metadata = {'controller_variant': 'wu-link', 'sim_sec': 900.,
                    'run_provenance': {'run_id': 'controlled-fixture'}}
        payload = adapter.control_to_json_dict(previous, metadata)
        self.assertNotIn('no_control_active', payload['diagnostics'])
        self.assertNotIn('no_control_native_signal_reference', payload['diagnostics'])
        self.assertEqual(payload['diagnostics']['retained_context'], {'nested': [1, 2]})
        self.assertEqual(vars(previous), before)
        for key in PHYSICAL_FIELDS:
            self.assertEqual(payload[key], getattr(previous, key))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'action_000900.json'
            path.write_text(json.dumps(payload), encoding='utf-8')
            with path.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=adapter.action_csv_schema.ACTION_CSV_FIELDS)
                writer.writeheader()
                writer.writerows({'kind': 'signal', 'id': sc, 'sc_no': sc[2:],
                    **{p+'_green': previous.green_times[sc+'_'+p] for p in ('p1', 'p2', 'p3', 'p4')},
                    'offset': previous.offsets[sc]} for sc in self.cfg.network.signals)
            restored = adapter.control_from_json(path, self.cfg, Action)
            with patch.object(meters, 'prepare_recorded_historical_meter_reference',
                              side_effect=lambda control, *args, **kwargs: {'previous': control}), \
                 patch.object(adapter, 'represent_native_no_control_signals',
                              side_effect=AssertionError('Controlled history is not a native warmup')):
                result, pins = adapter.load_joint_historical_reference(path, restored, self.cfg,
                    expected_run_id='controlled-fixture', expected_previous_sim_sec=900.)
            self.assertEqual(len(pins), 2)
            for key in PHYSICAL_FIELDS:
                self.assertEqual(getattr(result['previous'], key), getattr(previous, key))
            self.assertEqual(result['previous'].offsets['SC1004'], 0.)

    def test_native_or_unspecified_serialization_preserves_strict_native_proof(self):
        previous = adapter.represent_native_no_control_signals(nominal_action(self.cfg), self.cfg)
        for variant in ('no-control', '', None):
            with self.subTest(variant=variant):
                metadata = {} if variant is None else {'controller_variant': variant}
                payload = adapter.control_to_json_dict(previous, metadata)
                for key in ('no_control_active', 'no_control_native_signal_reference'):
                    self.assertEqual(payload['diagnostics'][key], previous.diagnostics[key])

    def test_runtime_setup_calls_source_binding_only_after_explicit_activation(self):
        class ReachedNextStage(Exception): pass
        class StubAdapter:
            def __getattr__(self, name):
                if name == '_link_counts_from_local_observation': return lambda _: {}
                if name == 'install_merged_movements': return lambda cfg, tuning, detectors: (detectors, {})
                if name == 'load_signal_group_actuation_plan': return lambda: self.raw
                return lambda *args, **kwargs: {}
        for active in (False, True):
            cfg = deepcopy(self.cfg)
            cfg.network.native_signal_minimum_policy = 'include_source_reference' if active else None
            stub = StubAdapter()
            stub.raw = self.raw
            stub.validate_native_signal_runtime_source = Mock(wraps=adapter.validate_native_signal_runtime_source)
            with patch.object(runtime_setup, 'configure_freeway_runtime', return_value={}), \
                 patch.object(runtime_setup.offramp_routing, 'install', return_value={}), \
                 patch.object(runtime_setup.signal_actuation_contract, 'configure', return_value={}), \
                 patch('evaluation.controllers.head_service_resources.configure', side_effect=ReachedNextStage):
                with self.assertRaises(ReachedNextStage):
                    runtime_setup.configure_runtime(stub, cfg, {}, {}, {'network_path': str(self.network)},
                                                    None, {}, {}, None)
            if active:
                stub.validate_native_signal_runtime_source.assert_called_once()
                self.assertEqual(len(cfg.network.native_signal_runtime_source_binding['controllers']), 17)
            else: stub.validate_native_signal_runtime_source.assert_not_called()


if __name__ == '__main__':
    unittest.main()
