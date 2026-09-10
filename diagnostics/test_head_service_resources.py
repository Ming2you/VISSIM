"""Installed head resources through actual runtime/main/local/worker calls.

Every warm window uses configure_runtime. The baseline observer spy only saves
its unmodified arguments for independent raw-evidence/OFF unit comparisons.
No proposal imports, generated method bodies, endpoint, search or VISSIM.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter
from evaluation.controllers import head_service_resources as resources
from evaluation.controllers import signal_head_observation as observer
from evaluation.controllers import local_signal_service as pool
from evaluation.controllers import runtime_setup, urban_flow_accounting as urban
from src.models import urban_queue_model as uqm

from diagnostics.head_service_resource_fixtures import input_path, fixture_path, CONFIG as CONFIG_RELATIVE
CONFIG = fixture_path(CONFIG_RELATIVE)
CONTRACT = 'diagnostics/head_service_resource_contract.json'
TARGETS = ('SC1004_E_SC1005_to_W', 'SC1004_E_SC107_to_W')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fingerprints(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def configured(tuning, state_path, previous):
    """Use main's public setup inputs; keep empty/None previous unchanged."""
    tuning = deepcopy(tuning)
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
    raw = read(state_path)
    mapping = adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
    detectors = adapter.load_optional_json(str(ROOT/tuning['detector_mapping_json']))
    detectors, _ = adapter.filter_midblock_links_from_detector_mapping(detectors, tuning)
    _, _, _, _, TrafficState, _ = adapter.repo_imports(ROOT/'vendor/NumSim-mine')
    cfg = adapter.build_config(ROOT/'vendor/NumSim-mine', float(raw['control_interval_sec']),
        float(raw['sim_period_sec']), 'fast-smoke', calibration, tuning,
        local_observation=bool(adapter._link_counts_from_local_observation(raw) and detectors), flagship=True)
    adapter.install_adapter_calibration_fingerprints(cfg, tuning)
    writer = tuning.get('actuation', {}).get('real_world_signal_control', {}).get('offset_writer', 'intent_only')
    with patch.dict(os.environ, {'RW_OFFSET_WRITER': writer}):
        state, detectors, metadata = runtime_setup.configure_runtime(
            adapter, cfg, tuning, mapping, raw, previous, detectors, calibration,
            TrafficState, physical_projection_input=None)
    return cfg, state, detectors, tuning, raw, mapping, metadata


class HeadResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = list((ROOT/'evaluation/controllers').glob('*.py')) + [CONFIG]
        cls.paths += [ROOT/'diagnostics'/name for name in (
            'head_service_resource_contract.json', 'test_head_service_resources.py',
            'test_shared_service_main_stack.py', 'test_shared_service_pool.py')]
        cls.paths += [input_path('state_000001.json'),input_path('action_000001.json')] + [input_path(f'{kind}_{sec:06d}.json')
            for sec in range(150, 1051, 150) for kind in ('state', 'action')]
        cls.before_hash = fingerprints(cls.paths)
        cls.temporary = tempfile.TemporaryDirectory(prefix='head_resource_canonical_')
        cls.temp = Path(cls.temporary.name)
        cls.real_observer = observer.install
        cls.off_tuning = read(CONFIG)
        cls.tuning = deepcopy(cls.off_tuning)
        cls.tuning['urban']['capacity']['head_resource_contract'] = CONTRACT
        captured = {}

        def capture(cfg, raw, previous, caps, plan, distribute, options):
            captured.update(cfg=deepcopy(cfg), caps=deepcopy(caps), plan=deepcopy(plan),
                            distribute=distribute, options=deepcopy(options))
            return cls.real_observer(cfg, raw, previous, caps, plan, distribute, options)

        with patch.object(observer, 'install', capture):
            cls.baseline = configured(cls.off_tuning, input_path('state_001050.json'),
                input_path('action_000900.json'))
        cls.captured = captured
        previous = input_path('action_000001.json')
        cls.history = []
        for sec in range(150, 1051, 150):
            current = configured(cls.tuning, input_path(f'state_{sec:06d}.json'), previous)
            cfg = current[0]; metadata = current[6]
            candidates = {row['group']: {k:v for k,v in metadata.items()
                if k.startswith('head_candidate_rate_'+row['group'].replace('|','_')+'_')}
                for row in resources.view(cfg)['resources'].values()}
            cls.history.append({'sec': sec, 'candidates': candidates,
                                'observations': deepcopy(resources.view(cfg)['observations']),
                                'final_groups': deepcopy(pool.view(cfg)['groups']),
                                'final_rates': {m: cfg.network.movement_capacity_by_movement_veh_h[m] for m in TARGETS}})
            document = read(input_path(f'action_{sec:06d}.json'))
            for section in ('diagnostics', 'metadata'):
                if section in document:
                    document[section] = {k: v for k,v in document[section].items() if not k.startswith('head_')}
            document.setdefault('metadata', {}).update(metadata)
            destination = cls.temp/f'action_{sec:06d}.json'
            destination.write_text(json.dumps(document), encoding='utf-8')
            previous = destination

        cls.final = current
        _, Demand, Control, _, _, _ = adapter.repo_imports(ROOT/'vendor/NumSim-mine')
        cls.action = adapter.control_from_json(input_path('action_001050.json'), cls.final[0], Control)
        calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(dict(calibration), cls.final[3].get('calibration_override', {}))
        cls.demand = adapter.demand_from_state(cls.final[4], cls.final[0], Demand, 1, calibration, cls.final[2])[0]
        cls.main_evidence = {}
        cls.startup_evidence = []

    @classmethod
    def tearDownClass(cls):
        after = fingerprints(cls.paths)
        result = {'schema': 'head-resource-canonical-validation/v1',
                  'scope': 'Installed runtime on all 7 saved windows, actual state1 cold starts, canonical 5sec urban/local/main builder and fresh worker; no endpoint/search/VISSIM',
                  'contract_sha256': hashlib.sha256((ROOT/CONTRACT).read_bytes()).hexdigest(),
                  'history': cls.history, 'final_observations': resources.view(cls.final[0])['observations'],
                  'cold_start': cls.startup_evidence, 'actual_main_local': cls.main_evidence,
                  'final_groups': pool.view(cls.final[0])['groups'], 'source_sha256': cls.before_hash,
                  'source_changes': [p for p,h in cls.before_hash.items() if after[p] != h]}
        (ROOT/'diagnostics/head_service_resources_canonical_validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        cls.temporary.cleanup()
        if result['source_changes']:
            raise AssertionError(result['source_changes'])

    def test_observed_only_history_1050_never_inherits_seed_max(self):
        rows = resources.view(self.final[0])['observations']
        self.assertAlmostEqual(rows['10619']['observed_only_floor_veh_h'], 784.6153846153845)
        self.assertAlmostEqual(rows['10629']['observed_only_floor_veh_h'], 1040.)
        self.assertEqual(rows['10629']['current_pair_support_veh_h'], 0.)
        self.assertAlmostEqual(rows['10619']['current_pair_support_veh_h'], 0.)
        self.assertEqual(self.history[0]['observations']['10629']['observed_only_floor_veh_h'], 0.)

    def test_final_members_and_phantom_removal_single_resource(self):
        cfg = self.final[0]; caps = cfg.network.movement_capacity_by_movement_veh_h
        self.assertEqual({caps[m] for m in TARGETS}, {1040.})
        self.assertAlmostEqual(caps['SC107_E_SC108_to_W_SC1005'], 826.1224489795918)
        self.assertAlmostEqual(caps['SC1004_E_SC1005_to_N_SC1003'], self.captured['caps']['SC1004_E_SC1005_to_N_SC1003'])
        self.assertAlmostEqual(caps['SC107_E_SC108_to_N_SC1'], self.captured['caps']['SC107_E_SC108_to_N_SC1'])
        for name in ('SC1004_E_SC1005_to_E_SC107', 'SC1004_E_SC107_to_E_SC1005'):
            self.assertNotIn(name, cfg.network.urban_movements)
            self.assertNotIn(name, caps)
        self.assertEqual(pool.view(cfg)['groups']['10634'], pool.view(self.baseline[0])['groups']['10634'])
        self.assertEqual(set(pool.view(cfg)['groups']), {'10634', '10629'})

    def test_cold_install_does_not_adopt_legacy_1050_floor(self):
        captured = self.captured; cfg = deepcopy(captured['cfg']); raw = self.final[4]
        resources.configure(cfg, self.tuning, raw, captured['plan'])
        resources.observe(type(self).real_observer, cfg, raw, input_path('action_000900.json'),
            deepcopy(captured['caps']), captured['plan'], captured['distribute'], captured['options'])
        self.assertEqual({r['observed_only_floor_veh_h'] for r in resources.view(cfg)['observations'].values()}, {0.})

    def test_actual_startup_without_previous_action_empty(self):
        raw = read(input_path('state_000001.json'))
        self.assertEqual(raw['sim_sec'], 1.)
        for previous in ('',):
            current = configured(self.tuning, input_path('state_000001.json'), previous)
            cfg = current[0]; metadata = current[6]
            self.assertEqual(metadata['head_observation_snapshot_sec'], 1.)
            self.assertEqual({r['observed_only_floor_veh_h'] for r in resources.view(cfg)['observations'].values()}, {0.})
            self.assertEqual(set(pool.view(cfg)['groups']), {'10634'})
            self.startup_evidence.append({'previous': previous, 'snapshot_sec': 1.,
                'observations': deepcopy(resources.view(cfg)['observations']),
                'groups': sorted(pool.view(cfg)['groups'])})

    def test_runtime_none_is_existing_unsupported_input_but_head_observer_accepts_none(self):
        # argparse's actual main default is ''. The outer adapter has never
        # normalized None: both feature states fail before the observer.
        errors = []
        for tuning in (self.off_tuning, self.tuning):
            with self.assertRaises(TypeError) as caught:
                configured(tuning, input_path('state_000001.json'), None)
            errors.append(str(caught.exception))
        self.assertEqual(errors[0], errors[1])
        captured = self.captured; cfg = deepcopy(captured['cfg'])
        raw = read(input_path('state_000001.json'))
        resources.configure(cfg, self.tuning, raw, captured['plan'])
        metadata = resources.observe(type(self).real_observer, cfg, raw, None,
            deepcopy(captured['caps']), captured['plan'], captured['distribute'], captured['options'])
        self.assertEqual(metadata['head_observation_snapshot_sec'], 1.)
        self.assertEqual({r['observed_only_floor_veh_h'] for r in resources.view(cfg)['observations'].values()}, {0.})
        self.startup_evidence.append({'previous': None, 'outer_runtime_supported': False,
            'off_on_same_TypeError': errors[0], 'head_observer_direct_supported': True})

    def test_new_namespace_only_prior_still_requires_full_action_provenance(self):
        template = read(self.temp/'action_000900.json')
        for section in ('diagnostics','metadata'):
            if section in template:
                template[section] = {k:v for k,v in template[section].items()
                    if not k.startswith(('head_discharge_floor_', 'head_candidate_'))}
        context = next(k for k in template['metadata'] if k.startswith('head_provenance_'))
        for corruption in ('none','run','context','time'):
            previous = deepcopy(template)
            if corruption == 'run': previous['run_provenance']['run_id'] = 'another-run'
            if corruption == 'context': previous['metadata'][context] = 0.
            if corruption == 'time': previous['metadata']['sim_sec'] = 750.
            path = self.temp/('prior_'+corruption+'.json')
            path.write_text(json.dumps(previous),encoding='utf-8')
            captured = self.captured; cfg = deepcopy(captured['cfg']); raw = self.final[4]
            resources.configure(cfg, self.tuning, raw, captured['plan'])
            resources.observe(type(self).real_observer, cfg, raw, path, deepcopy(captured['caps']),
                captured['plan'], captured['distribute'], captured['options'])
            floor = resources.view(cfg)['observations']['10629']['observed_only_floor_veh_h']
            self.assertEqual(floor, 1040. if corruption == 'none' else 0., corruption)

    def test_boolean_carried_support_is_not_a_measurement(self):
        previous = read(self.temp/'action_000900.json')
        key = next(k for k in previous['metadata'] if k.startswith('head_resource_observed_floor_10629_'))
        previous['metadata'][key] = True
        path = self.temp/'boolean_prior.json'; path.write_text(json.dumps(previous),encoding='utf-8')
        captured = self.captured; cfg = deepcopy(captured['cfg']); raw = self.final[4]
        resources.configure(cfg, self.tuning, raw, captured['plan'])
        with self.assertRaisesRegex(ValueError, 'Boolean'):
            resources.observe(type(self).real_observer, cfg, raw, path, deepcopy(captured['caps']),
                captured['plan'], captured['distribute'], captured['options'])

    def test_off_observer_and_config_exact(self):
        captured = self.captured; raw = self.final[4]; previous = input_path('action_000900.json')
        a = deepcopy(captured['cfg']); b = deepcopy(a)
        args = (raw, previous, captured['caps'], captured['plan'], captured['distribute'], captured['options'])
        expected = type(self).real_observer(a, *args)
        actual = resources.observe(type(self).real_observer, b, *args)
        self.assertEqual(actual, expected)
        self.assertEqual(pickle.dumps(a), pickle.dumps(b))
        before = pickle.dumps(b)
        self.assertEqual(resources.configure(b, self.off_tuning, raw, captured['plan']), {})
        self.assertEqual(resources.finalize(b), {})
        resources.extend_local_pool(b)
        self.assertEqual(before, pickle.dumps(b))

    def test_single_budget_partial_green_receiver_rejection_and_reset(self):
        cfg = self.final[0]
        for fraction in (0., .2, 1.):
            with patch.object(uqm, '_phase_green_fraction', return_value=fraction):
                context = resources.regular_context(cfg, self.action, 210)
            amount = 1040. * cfg.simulation.T_u_h * fraction
            requests = resources.regular_batch(cfg, dict.fromkeys(TARGETS, 10.), context)
            reversed_requests = resources.regular_batch(cfg, dict.fromkeys(reversed(TARGETS), 10.), context)
            self.assertEqual(requests, reversed_requests)
            self.assertAlmostEqual(sum(requests.values()), amount)
            self.assertEqual(context[1], {})
            for name, value in requests.items():
                resources.regular_accepted(name, value*.5, context)
            self.assertAlmostEqual(sum(context[1].values()), amount*.5)
            with patch.object(uqm, '_phase_green_fraction', return_value=fraction):
                next_context = resources.regular_context(cfg, self.action, 211)
            self.assertEqual(next_context[1], {})
            self.assertAlmostEqual(sum(resources.regular_batch(cfg, dict.fromkeys(TARGETS, 10.), next_context).values()), amount)

    def test_existing_local_consumer_uses_one_budget(self):
        from src.controllers import local_signal_plant as local
        from diagnostics.test_shared_service_pool import local_args, accepted_trace
        cfg, state = self.final[:2]; specs = uqm.movement_specs(cfg)
        phases = {p: [m for m,s in specs.items() if s['signal']=='SC1004' and s['phase'].endswith('_'+p)]
                  for p in ('p1','p2','p3','p4')}
        model = local.build_local_model(cfg, 'SC1004', specs, {'SC1004': phases})
        for m in TARGETS:
            self.assertEqual(model.cap_flow_of[m], 1040.)
        args, kwargs = local_args(cfg, state, self.action, model, fraction=1.)
        args = list(args); args[1] = dict.fromkeys(model.movements, 0.)
        for m in TARGETS:
            args[1][m] = 10.
        args[3] = dict(args[3]); args[3]['SC1004_W_out'] = 100.
        _, trace = accepted_trace(pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kwargs))
        self.assertAlmostEqual(sum(v for m,v in trace if m in TARGETS), 1040.*cfg.simulation.T_u_h)
        args[3]['SC1004_W_out'] = 0.
        _, trace = accepted_trace(pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kwargs))
        self.assertEqual(sum(v for m,v in trace if m in TARGETS), 0.)

    def test_worker_installer_keeps_final_groups(self):
        cfg = pickle.loads(pickle.dumps(self.final[0]))
        before = deepcopy(pool.view(cfg))
        runtime_setup.install_worker_runtime(adapter, cfg, self.final[4], self.final[2])
        self.assertEqual(pool.view(cfg), before)
        self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h, self.final[0].network.movement_capacity_by_movement_veh_h)

    def test_fresh_worker_uses_serialized_two_resource_view(self):
        packet = self.temp/'worker.pickle'
        packet.write_bytes(pickle.dumps((self.final[0], self.final[1], self.action, self.final[4], self.final[2])))
        source = '''
import json,pickle,sys
from diagnostics.probe_model_area_integration import adapter
from evaluation.controllers import runtime_setup,local_signal_service as pool
from src.controllers import local_signal_plant as local
from src.models import urban_queue_model as uqm
from diagnostics.test_shared_service_pool import local_args,accepted_trace
cfg,state,action,raw,detectors=pickle.load(open(sys.argv[1],'rb'))
runtime_setup.install_worker_runtime(adapter,cfg,raw,detectors)
specs=uqm.movement_specs(cfg)
phases={p:[m for m,s in specs.items() if s['signal']=='SC1004' and s['phase'].endswith('_'+p)] for p in ('p1','p2','p3','p4')}
model=local.build_local_model(cfg,'SC1004',specs,{'SC1004':phases})
targets=('SC1004_E_SC1005_to_W','SC1004_E_SC107_to_W')
args,kwargs=local_args(cfg,state,action,model,fraction=1.)
args=list(args);args[1]=dict.fromkeys(model.movements,0.)
for m in targets:args[1][m]=10.
args[3]=dict(args[3]);args[3]['SC1004_W_out']=100.
result,trace=accepted_trace(pool,lambda:local.rollout_local_tts_ramp_aware(*args,**kwargs))
print(json.dumps({'groups':sorted(pool.view(cfg)['groups']),'accepted':sum(v for m,v in trace if m in targets),'caps':[model.cap_flow_of[m] for m in targets]}))
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', source, str(packet)],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence['groups'], ['10629','10634'])
        self.assertEqual(evidence['caps'], [1040.,1040.])
        self.assertAlmostEqual(evidence['accepted'], 1040.*self.final[0].simulation.T_u_h)

    def test_contract_gate_and_owned_off_lifecycle(self):
        cfg = deepcopy(self.captured['cfg']); raw = self.final[4]
        tuning = deepcopy(self.tuning)
        tuning['urban']['shared_local_service_pool'] = False
        with self.assertRaisesRegex(ValueError, 'requires the shared'):
            resources.configure(cfg, tuning, raw, self.captured['plan'])
        resources.configure(cfg, self.tuning, raw, self.captured['plan'])
        self.assertIsNotNone(resources.view(cfg))
        resources.configure(cfg, self.off_tuning, raw, self.captured['plan'])
        self.assertIsNone(resources.view(cfg))

    def test_invalid_receiving_join_does_not_increase_capacity(self):
        cfg = deepcopy(self.final[0]); before = dict(cfg.network.movement_capacity_by_movement_veh_h)
        cfg.network.urban_movements[TARGETS[0]]['receiving_link'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'semantics changed'):
            resources.finalize(cfg)
        self.assertEqual(before, cfg.network.movement_capacity_by_movement_veh_h)

    def test_actual_urban_method_off_exact_and_on_single_accepted(self):
        from diagnostics.test_shared_service_pool import accepted_trace
        # OFF resource operations leave the canonical baseline entirely alone.
        cfg, state = self.baseline[:2]
        a = state.copy(); b = state.copy()
        expected = urban.urban_substep_accounted(a, self.action, self.demand, cfg)
        context = resources.regular_context(cfg, self.action, 210)
        requests = {m: 1. for m in TARGETS}
        self.assertEqual(resources.regular_batch(cfg, requests, context), requests)
        for name in TARGETS:
            resources.regular_accepted(name, 1., context)
        actual = urban.urban_substep_accounted(b, self.action, self.demand, cfg)
        self.assertEqual(pickle.dumps(a), pickle.dumps(b))
        self.assertEqual(expected, actual)
        cfg, state = self.final[:2]; untouched = pickle.dumps(state)
        a = state.copy(); b = state.copy()
        result, trace = accepted_trace(pool, lambda: urban.urban_substep_accounted(a, self.action, self.demand, cfg))
        repeat = urban.urban_substep_accounted(b, self.action, self.demand, cfg)
        self.assertEqual(result, repeat)
        self.assertEqual(pickle.dumps(a), pickle.dumps(b))
        fraction = uqm._phase_green_fraction(self.action, cfg, cfg.network.urban_movements[TARGETS[0]], urban_step_index=210)
        self.assertLessEqual(sum(v for m,v in trace if m in TARGETS), 1040.*cfg.simulation.T_u_h*fraction+1e-8)
        self.assertEqual(pickle.dumps(state), untouched)

    def test_actual_main_builder_local_cost_and_fresh_worker(self):
        from diagnostics.test_shared_service_main_stack import local_result
        cfg, state, detectors, tuning, raw = self.final[:5]
        with patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'}):
            controller = adapter.build_priced_wu_link_controller(cfg, tuning)
            adapter.install_vissim_terminal_cost_objective(controller, cfg, tuning)
            adapter.install_price_worker_bootstrap(controller, raw, detectors)
            before = pickle.dumps((state, self.action, self.demand))
            expected = local_result(controller, state, self.action, self.demand)
            repeat = local_result(controller, state, self.action, self.demand)
        self.assertEqual(expected, repeat)
        self.assertEqual(expected['seed']['start_step'], 210)
        self.assertEqual(set(pool.view(cfg)['groups']), {'10629', '10634'})
        self.assertEqual(before, pickle.dumps((state, self.action, self.demand)))
        source = '''import pickle,sys,json
from diagnostics.test_shared_service_main_stack import local_result
from evaluation.controllers import local_signal_service as pool
controller,state,action,demand=pickle.loads(sys.stdin.buffer.read())
result=local_result(controller,state,action,demand)
print(json.dumps({'result':result,'groups':sorted(pool.view(controller.cfg)['groups'])},sort_keys=True))
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', source],
            input=pickle.dumps((controller, state, self.action, self.demand)),
            capture_output=True, cwd=ROOT, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
        worker = json.loads(result.stdout)
        self.assertEqual(worker['result'], json.loads(json.dumps(expected)))
        self.assertEqual(worker['groups'], ['10629','10634'])
        type(self).main_evidence = {'parent': expected, 'worker': worker,
            'repeat_exact': True, 'input_pickle_unchanged': True}


if __name__ == '__main__':
    unittest.main()
