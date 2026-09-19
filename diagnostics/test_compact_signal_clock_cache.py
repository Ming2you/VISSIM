"""Opt-in native clock signatures: exact command-only tests, no model/COM."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine'), str(ROOT/'plant/src')]
from diagnostics.test_native_signal_contract import Net
from evaluation.controllers import signal_actuation_contract as clock, offset_promotion, plant_cycle


def fixture(native=True):
    raw = json.loads((ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8'))
    source = json.loads((ROOT/'reports/20260911_decision_runtime/native_clock_basis_source_v1.json').read_text(encoding='utf-8'))
    if native:
        for signal, row in raw['controllers'].items():
            row['native_clock_basis'] = deepcopy(source['controllers'][signal]['native_clock_basis'])
            # Recreate local source provenance before configure; all .sig bytes
            # and physical operands are the checked-in original fixture.
            row['native_clock_basis']['source_path'] = str((ROOT/source['controllers'][signal]['program']).resolve())
    cfg = SimpleNamespace(network=Net(raw), simulation=SimpleNamespace(T_u_sec=5.))
    if not native:
        for signal in cfg.network.signals:
            cfg.network.cycle_length_by_signal[signal] = 150.
            cfg.network.effective_green_total_by_signal[signal] = 150.-3*len(cfg.network.signal_live_phases(signal))
    tuning = {'urban': {'physical_signal_contract': True},
              'actuation': {'real_world_signal_control': {'offset_writer': 'experiment'}}}
    with patch.dict('os.environ', {'RW_OFFSET_WRITER': 'experiment'}), patch.object(clock, 'install_candidates'):
        clock.configure(cfg, tuning, raw)
    greens, offsets = {}, {}
    for sc, row in raw['controllers'].items():
        signal = 'SC'+sc
        values = row['axis_green_sec'] if native else clock.project_vector(cfg.network, signal, row['axis_green_sec'])
        greens.update({signal+'_'+p: v for p, v in values.items()})
        offsets[signal] = row.get('native_clock_basis', {}).get('reference_offset_sec', 0.)
    return cfg, SimpleNamespace(green_times=greens, offsets=offsets, diagnostics={})


def outcome(action, cfg, spec, step):
    try:
        value = clock.phase_fraction(action, cfg, spec, step)
        return ('None',) if value is None else ('bits', struct.pack('!d', value).hex())
    except Exception as exc:
        return ('error', type(exc).__name__, str(exc))


class CompactNativeClockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.action = fixture()

    def setUp(self):
        clock.clear_clock_cache()

    def compare(self, cfg, action, signal='SC16', phase='p2', step=13):
        spec = {'phase': signal+'_'+phase}
        cfg.network.control_area_compact_signal_clock_cache = False
        expected = outcome(action, cfg, spec, step)
        cfg.network.control_area_compact_signal_clock_cache = True
        self.assertEqual(outcome(action, cfg, spec, step), expected)
        self.assertEqual(outcome(action, cfg, spec, step), expected)
        return expected

    def test_all_17_source_clocks_float_bits_offsets_steps_and_candidate_vectors(self):
        cfg, action = deepcopy(self.cfg), deepcopy(self.action)
        self.assertEqual(len(cfg.network.signals), 17)
        for signal in cfg.network.signals:
            raw = cfg.network.signal_actuation_contract['nodes'][signal]
            self.assertIsNotNone(clock._compact_native_signature(raw), signal)
            original = {p: action.green_times[signal+'_'+p] for p in clock.PHASES}
            candidates = [original, clock.project_vector(cfg.network, signal,
                          {p: original[p]+(2. if i % 2 else -2.) for i, p in enumerate(clock.PHASES)})]
            for values in candidates:
                action.green_times.update({signal+'_'+p: v for p, v in values.items()})
                for offset in (-150.001, -.0001, 0., 10., 149.999, 150.001):
                    action.offsets[signal] = offset
                    for phase in clock.PHASES:
                        for step in (None, -.1, 0, 13, 29, 30, 179, 180.2, 30000.25):
                            self.compare(cfg, action, signal, phase, step)
        self.assertGreater(clock.clock_cache_info()['clock_hits'], 1000)

    def test_every_basis_field_changes_signature_and_forces_original_miss_validation(self):
        cfg, action = deepcopy(self.cfg), deepcopy(self.action)
        cfg.network.control_area_compact_signal_clock_cache = True
        signal = 'SC16'
        raw = cfg.network.signal_actuation_contract['nodes'][signal]
        original = clock._compact_native_signature(raw)
        self.compare(cfg, action)
        for field in tuple(raw['native_clock_basis']):
            other = deepcopy(cfg)
            row = other.network.signal_actuation_contract['nodes'][signal]
            value = row['native_clock_basis'][field]
            if type(value) is str:
                row['native_clock_basis'][field] += '_changed'
            elif type(value) in (float, int):
                row['native_clock_basis'][field] += 1
            elif type(value) is list:
                value.reverse()
            elif type(value) is dict:
                value[next(iter(value))] += 1.
            else:
                self.fail(field)
            self.assertNotEqual(clock._compact_native_signature(row), original, field)
            # Compare with separately empty caches; then prove a warmed original
            # command does not satisfy the mutated compact lookup.
            clock.clear_clock_cache()
            self.compare(other, action)
            clock.clear_clock_cache()
            self.compare(cfg, action)
            with patch.object(clock, '_uncached_clock', wraps=clock._uncached_clock) as validate:
                outcome(action, other, {'phase': 'SC16_p2'}, 13)
                self.assertEqual(validate.call_count, 1, field)

    def test_unknown_nested_fields_and_custom_types_fall_back(self):
        class FloatAlias(float):
            def __float__(self): return float('nan')
        class KeyAlias(str):
            pass
        mutations = [
            lambda r: r['native_clock_basis'].update(extra='new'),
            lambda r: r['native_clock_basis'].pop('source_path'),
            lambda r: r['native_clock_basis']['native_green_sec'].update(extra=1.),
            lambda r: r['axis_green_sec'].update(extra=1.),
            lambda r: r['native_clock_basis'].__setitem__('cycle_sec', 150),
            lambda r: r['native_clock_basis'].__setitem__('cycle_sec', FloatAlias(150)),
            lambda r: r['native_clock_basis'].__setitem__('cycle_sec', float('nan')),
            lambda r: r['native_clock_basis'].__setitem__('phase_order', [KeyAlias('p1'), 'p2', 'p3']),
            lambda r: r.__setitem__('native_clock_basis', SimpleNamespace()),
        ]
        for mutation in mutations:
            cfg = deepcopy(self.cfg)
            row = cfg.network.signal_actuation_contract['nodes']['SC16']
            mutation(row)
            self.assertIsNone(clock._compact_native_signature(row))
            self.compare(cfg, deepcopy(self.action))

    def test_signed_zero_and_dictionary_reordering_cannot_hide_changes(self):
        cfg = deepcopy(self.cfg)
        row = cfg.network.signal_actuation_contract['nodes']['SC16']
        before = clock._compact_native_signature(row)
        row['native_clock_basis']['controller_offset_sec'] = -0.
        self.assertNotEqual(clock._compact_native_signature(row), before)
        self.compare(cfg, deepcopy(self.action))
        row['native_clock_basis'] = dict(reversed(tuple(row['native_clock_basis'].items())))
        self.assertIsNotNone(clock._compact_native_signature(row))
        self.compare(cfg, deepcopy(self.action))

    def test_mutated_runtime_operands_preserve_values_errors_and_reject_custom_offset(self):
        class BadFloatZero(int):
            def __float__(self): return float('nan')
        for mutation in ('green', 'offset', 'cycle', 'total', 'minimum', 'policy', 'live',
                         'amber', 'all_red', 'segments', 'order', 'writer', 'duration', 'custom_offset'):
            cfg, action = deepcopy(self.cfg), deepcopy(self.action)
            self.compare(cfg, action)
            net = cfg.network; contract = net.signal_actuation_contract; row = contract['nodes']['SC16']
            if mutation == 'green': action.green_times['SC16_p2'] += .001
            if mutation == 'offset': action.offsets['SC16'] += 1.
            if mutation == 'cycle': net.cycle_length_by_signal['SC16'] -= .001
            if mutation == 'total': net.effective_green_total_by_signal['SC16'] += .001
            if mutation == 'minimum': net.green_min = 90.
            if mutation == 'policy': net.native_signal_minimum_policy = 'strict'
            if mutation == 'live': net.live['SC16'] = ('p1', 'p2')
            if mutation == 'amber': contract['amber'] += .001
            if mutation == 'all_red': contract['all_red'] += .001
            if mutation == 'segments': row['_segments'] = tuple((p, ()) if p == 'p2' else (p, s) for p, s in row['_segments'])
            if mutation == 'order': row['_order'] = tuple(reversed(row['_order']))
            if mutation == 'writer': contract['offset_writer'] = 'intent_only'
            if mutation == 'duration': cfg.simulation.T_u_sec = 2.5
            if mutation == 'custom_offset': action.offsets['SC16'] = BadFloatZero(0)
            self.compare(cfg, action)
        for value in (float('nan'), float('inf'), None, 'bad'):
            cfg, action = deepcopy(self.cfg), deepcopy(self.action)
            action.offsets['SC16'] = value
            self.assertEqual(self.compare(cfg, action)[0], 'error')
        with patch.object(plant_cycle, 'SIGNAL_GREEN_WRITE_CLAMP_SEC', (1., 20.)):
            self.assertEqual(self.compare(deepcopy(self.cfg), deepcopy(self.action))[0], 'error')

    def test_raw_source_and_plan_mutations_after_warm_hit(self):
        class EqualInt(int):
            def __float__(self): return float('nan')
        for mutation in ('axis', 'native_cycle', 'mutable_segments', 'custom_segment', 'missing_total'):
            cfg, action = deepcopy(self.cfg), deepcopy(self.action)
            self.compare(cfg, action)
            row = cfg.network.signal_actuation_contract['nodes']['SC16']
            if mutation == 'axis': row['axis_green_sec']['p2'] += 1.
            if mutation == 'native_cycle': row['native_cycle_sec'] += 1.
            if mutation == 'mutable_segments': row['_segments'] = list(row['_segments'])
            if mutation == 'custom_segment':
                row['_segments'] = tuple((p, tuple((sg, name, EqualInt(0), high) for sg, name, low, high in spans))
                                         for p, spans in row['_segments'])
            if mutation == 'missing_total': cfg.network.effective_green_total_by_signal.pop('SC16')
            self.compare(cfg, action)

    def test_test_only_presence_and_mutable_diagnostics_are_still_guarded(self):
        cfg, action = deepcopy(self.cfg), deepcopy(self.action)
        cfg.network.signal_actuation_contract['offset_writer'] = 'test_only'
        first, second = offset_promotion.FORCED_ARM_DIAGNOSTIC_KEYS
        for diagnostics in ({second: 10.}, {first: None, second: 10.},
                            {offset_promotion.FORCED_ARM_TABLE_KEY: '{"SC16":10.}'},
                            {offset_promotion.FORCED_ARM_TABLE_KEY: {}},
                            {offset_promotion.FORCED_ARM_TABLE_KEY: 'bad'}):
            action.diagnostics = diagnostics
            self.compare(cfg, action)

    def test_disabled_and_non_native_never_call_compact_signature(self):
        for native in (True, False):
            cfg, action = fixture(native)
            with patch.object(clock, '_compact_native_signature', side_effect=AssertionError('disabled')):
                outcome(action, cfg, {'phase': 'SC16_p2'}, 13)
                cfg.network.control_area_compact_signal_clock_cache = False
                self.assertEqual(outcome(action, cfg, {'phase': 'SC16_p2'}, 13)[0], 'bits')
            if not native:
                self.compare(cfg, action)

    def test_cache_bounded_no_input_mutation_or_retention(self):
        import gc
        import weakref
        from dataclasses import dataclass
        @dataclass
        class Holder:
            network: object
            simulation: object
        base = deepcopy(self.cfg)
        cfg = Holder(base.network, base.simulation)
        cfg.network.control_area_compact_signal_clock_cache = True
        action = deepcopy(self.action)
        before = pickle.dumps((cfg.network, cfg.simulation, action))
        with patch.object(clock, 'MAX_CLOCKS', 3):
            for step in range(4):
                for signal in cfg.network.signals:
                    outcome(action, cfg, {'phase': signal+'_p2'}, step)
            self.assertEqual(clock.clock_cache_info()['clocks'], 3)
        self.assertEqual(pickle.dumps((cfg.network, cfg.simulation, action)), before)
        ref = weakref.ref(cfg)
        del cfg
        gc.collect()
        self.assertIsNone(ref())


if __name__ == '__main__':
    unittest.main()
