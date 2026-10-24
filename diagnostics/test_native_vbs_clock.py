"""Actual WSH pure-function checks of optional native clocks; never starts VISSIM."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plant/src'))
from vissim_strict.signal_program import parse_sig
from evaluation.controllers import signal_group_plan as plans
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from scripts.derive_signal_group_actuation_plan_mainline_20260825 import render_vbs
from scripts.tests.test_action_csv_vbs_validators import CSCRIPT, run_vbs, vbs_string, parts_literal, harness_source as validator_harness
from scripts.tests.test_signal_group_plan_vbs_behavior import harness_source as state_harness, contract_harness_source, event_harness_source
from scripts.tests.test_b1a_vbs_verified_capture_static import SOURCE, procedure

EVIDENCE = ROOT / 'reports/20260911_decision_runtime/native_writer_pure_v1'
SOURCE_AUDIT = ROOT / 'reports/20260911_decision_runtime/native_clock_basis_source_v1.json'


def source_plan():
    raw = json.loads((ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8'))
    audit = json.loads(SOURCE_AUDIT.read_text(encoding='utf-8'))
    for sc, row in raw['controllers'].items():
        row['native_clock_basis'] = audit['controllers'][sc]['native_clock_basis']
    return raw, audit


def native_harness(raw, body):
    extra = '\n\n'.join(procedure(SOURCE, name) for name in
        ('PhaseGreenSum', 'LivePhaseCount', 'SignalCycleFromPhases', 'SignalCycleForController'))
    return state_harness(body='\n'.join([
        'Dim RW_SIGNAL_SG_PLAN_SOURCE_SHA256', extra, render_vbs(raw),
        'ParseSignalGroupPlanConfig', body]))


@unittest.skipUnless(CSCRIPT, 'Windows Script Host required')
class NativeVbsClockTests(unittest.TestCase):
    def run_recorded(self, name, script, expected=0):
        EVIDENCE.mkdir(exist_ok=True)
        (EVIDENCE / (name + '.vbs')).write_text(script, encoding='utf-8')
        result = run_vbs(script)
        (EVIDENCE / (name + '.json')).write_text(json.dumps({
            'scope': 'extracted actual VBS functions; no VISSIM COM',
            'runner_sha256': hashlib.sha256((ROOT / 'scripts/run_real_world_stackelberg_controller.vbs').read_bytes()).hexdigest(),
            'harness_sha256': hashlib.sha256(script.encode()).hexdigest(),
            'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
        }, indent=2), encoding='utf-8')
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        if expected == 0:
            self.assertIn('PASS', result.stdout)
        return result

    def test_all17_actual_adapter_rows_match_source_initial_and_complete_cycles(self):
        raw, audit = source_plan()
        lines = ['Dim stateIndex, expectedStates, actualState, checks, rowKey', 'checks = 0',
                 'Check "native_controller_count", nativeClockPlans.Count, 17']
        expected_checks = 0
        for sc, node in sorted(raw['controllers'].items(), key=lambda pair: int(pair[0])):
            basis = node['native_clock_basis']
            program = parse_sig(ROOT / audit['controllers'][sc]['program'], 1)
            cycle = program.cycle_length_sec
            offset = basis['reference_offset_sec']
            phase_text = '|'.join(str(node['axis_green_sec'][p]) for p in plans.MODEL_PHASES)
            lines.append(f'Check "cycle_{sc}", SignalCycleForController({sc}, "{phase_text}"), {cycle}')
            rows = adapter.signal_group_action_rows(raw, int(sc), node['axis_green_sec'], offset, 'native source proof')
            windows = {}
            for row in rows:
                self.assertEqual(row['green_sec'], cycle)
                self.assertEqual(row['offset'], offset)
                windows.setdefault(str(row['dsd_no']), []).append(f"{row['p1_green']}|{row['p2_green']};")
            for sg, specs in windows.items():
                lines.append(f'sgPlanWindows("{sc}-{sg}") = "{"".join(specs)}"')
            lines.append(f'sgPlanCycle("{sc}") = {cycle}')
            for sg in audit['controllers'][sc]['owned_signal_groups']:
                expected = ''.join(program.state_at(i / 2, sg)[0] for i in range(int(cycle * 2)))
                self.assertEqual(expected[0], audit['controllers'][sc]['initial_state_at_t0'][sg][0])
                lines.extend([
                    f'expectedStates = "{expected}"',
                    f'For stateIndex = 0 To {int(cycle * 2) - 1}',
                    f'    actualState = Left(SignalGroupStateFromPlan({sc}, {sg}, stateIndex / 2 + {offset}, {cycle}), 1)',
                    '    If actualState <> Mid(expectedStates, stateIndex + 1, 1) Then',
                    f'        Check "source_SC{sc}_SG{sg}_t" & CStr(stateIndex / 2), actualState, Mid(expectedStates, stateIndex + 1, 1)',
                    '    End If', '    checks = checks + 1', 'Next'])
                expected_checks += len(expected)
        self.assertEqual(expected_checks, 40320)
        lines.extend([
            f'Check "all_source_states_including_136_initial", checks, {expected_checks}',
            'Check "SC7_own_amber_over_other_green", SignalGroupStateFromPlan(7, 4, 68, 120), "AMBER"',
            'Check "SC7_concurrent_green", SignalGroupStateFromPlan(7, 7, 68, 120), "GREEN"',
            'Check "SC16_idle", SignalGroupStateFromPlan(16, 4, 40, 150), "RED"'])
        self.run_recorded('all17_source_states', native_harness(raw, '\n'.join(lines)))

    def test_native_cycle_constraints_and_legacy_absence(self):
        raw, _ = source_plan()
        self.run_recorded('native_cycle_constraints', native_harness(raw, '''
Check "SC7_independent_p1", SignalCycleForController(7, "73|90|0|24"), 120
Check "SC7_bad_pair_sum", SignalCycleForController(7, "67|89|0|24"), 0
Check "SC7_conflicting_clearance", SignalCycleForController(7, "88|90|0|24"), 0
Check "SC7_dead_phase", SignalCycleForController(7, "67|90|1|24"), 0
Check "SC16_valid", SignalCycleForController(16, "63|17|27|0"), 150
Check "SC16_bad_sum", SignalCycleForController(16, "64|17|27|0"), 0
nativeClockPlans.RemoveAll
Check "OFF_SC7_legacy_cycle", SignalCycleForController(7, "67|90|0|24"), 190
Check "OFF_SC16_legacy_cycle", SignalCycleForController(16, "63|17|27|0"), 116
sgPlanWindows("7-4") = "0|67;"
sgPlanWindows("7-7") = "0|90;"
Check "OFF_keeps_legacy_amber_suppression", SignalGroupStateFromPlan(7, 4, 68, 120), "RED"
'''))

    def test_all17_actual_csv_rows_pass_atomic_contract_and_stale_cycle_fails(self):
        raw, _ = source_plan()
        lines = ['Dim RW_SIGNAL_SG_PLAN_SOURCE_SHA256', render_vbs(raw),
                 'RW_SIGNAL_SCS = "' + ','.join(raw['controllers']) + '"',
                 'ParseSignalGroupPlanConfig', 'ResetPending']
        for sc, node in raw['controllers'].items():
            basis = node['native_clock_basis']
            lines.extend([f'rowCycle("{sc}") = {basis["cycle_sec"]}',
                          f'rowOffset("{sc}") = {basis["reference_offset_sec"]}'])
            for row in adapter.signal_group_action_rows(raw, int(sc), node['axis_green_sec'],
                                                        basis['reference_offset_sec'], 'source proof'):
                literal = parts_literal([str(row.get(field, '')) for field in ACTION_CSV_FIELDS])
                lines.append(f'Check "accept_{row["id"]}", SignalSgRowValid({literal}, seenSg, pendWindows, pendCounts, pendCycle, pendOffset), True')
        lines.extend([
            'Check "all17_atomic_accept", SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), ""',
            'rowCycle("7") = 190',
            'CheckContains "legacy_cycle_rejected_for_native_rows", SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), "cycle_mismatch"'])
        self.run_recorded('all17_csv_atomic_contract', contract_harness_source(body='\n'.join(lines)))

    def test_native_invalid_config_is_rejected(self):
        for name, token in [('unknown_kind', '7:unknown:120:0:1101'),
                            ('invalid_mask', '7:serial:120:0:110x'),
                            ('duplicate', '7:serial:120:0:1101;7:serial:120:0:1101'),
                            ('partial_cohort', '7:serial:120:0:1101')]:
            body = f'''RW_SIGNAL_SG_PLAN_SCHEMA = 1
RW_SIGNAL_SG_EXPECTED = "7:1:1,16:1:1"
RW_SIGNAL_SG_CONFLICTS = ""
RW_SIGNAL_NATIVE_CLOCKS = {vbs_string(token)}
ParseSignalGroupPlanConfig
Check "must_not_accept", True, False
'''
            self.run_recorded('reject_' + name, state_harness(body=body), expected=2)

    def test_axis_csv_native_cycle_offset_and_physical_bounds(self):
        self.run_recorded('native_axis_csv', validator_harness(body='''
nativeClockPlans.Add "7", "concurrent_p1_p2|120|0|1101"
nativeClockPlans.Add "16", "serial|150|34|1110"
Check "native_SC7_axis", SignalActionValuesValid(Split("signal,SC7,0,7,0,0,0,67,90,0,24,119,0,0,proof", ",")), True
Check "native_SC16_axis", SignalActionValuesValid(Split("signal,SC16,0,16,0,0,0,63,17,27,0,1,0,0,proof", ",")), True
Check "reject_offset_at_cycle", SignalActionValuesValid(Split("signal,SC7,0,7,0,0,0,67,90,0,24,120,0,0,proof", ",")), False
Check "reject_native_pair", SignalActionValuesValid(Split("signal,SC7,0,7,0,0,0,67,89,0,24,119,0,0,proof", ",")), False
Check "reject_under_writer_min", SignalActionValuesValid(Split("signal,SC7,0,7,0,0,0,4,90,0,24,119,0,0,proof", ",")), False
'''))

    def test_native_prestep_alignment_actual_helper_composite_and_event_scheduler(self):
        raw, _ = source_plan()
        lines = ['Dim RW_SIGNAL_SG_PLAN_SOURCE_SHA256', render_vbs(raw), 'ParseSignalGroupPlanConfig']
        for sc in ('7', '16'):
            node = raw['controllers'][sc]
            basis = node['native_clock_basis']
            text = '|'.join(str(node['axis_green_sec'][p]) for p in plans.MODEL_PHASES)
            lines.extend([f'sigPhaseGreen("{sc}") = "{text}"',
                          f'sigOffset("{sc}") = {basis["reference_offset_sec"]}'])
            windows = {}
            for row in adapter.signal_group_action_rows(raw, int(sc), node['axis_green_sec'], basis['reference_offset_sec'], 'frame proof'):
                windows.setdefault(str(row['dsd_no']), []).append(f"{row['p1_green']}|{row['p2_green']};")
            for sg, specs in windows.items():
                lines.append(f'sgPlanWindows("{sc}-{sg}") = "{"".join(specs)}"')
        lines.extend(['''
Check "native_position_for_next_recorded_frame", SignalClockPosition(7, 907, 119, 120), 67
Check "native_amber_at_write907_for_frame908", SignalGroupStateFromPlan(7, 4, SignalClockPosition(7, 907, 119, 120), 120), "AMBER"
Check "native_other_group_still_green", SignalGroupStateFromPlan(7, 7, SignalClockPosition(7, 907, 119, 120), 120), "GREEN"
Check "composite_observes_advanced_transition", SignalCompositeStateAt(906) <> SignalCompositeStateAt(907), True
Check "next_transition_advanced_one_second", NextSignalTransitionAfter(906), 907
Check "own_amber_end_advanced_one_second", NextSignalTransitionAfter(907), 910
Check "max_native_cycle", MaxSignalCycleSec(), 150
nativeClockPlans.RemoveAll
Check "legacy_position_unchanged", SignalClockPosition(7, 907, 119, 120), 66
Check "legacy_still_green_at_same_write", SignalGroupStateFromPlan(7, 4, SignalClockPosition(7, 907, 119, 120), 120), "GREEN"
'''])
        self.run_recorded('native_prestep_frame_alignment_v2', event_harness_source(body='\n'.join(lines)))
        self.assertIn('pos = SignalClockPosition(scKey, simSec, offset, cycle)', procedure(SOURCE, 'ApplyRuntimeSignals'))
        self.assertIn('pos = SignalClockPosition(scKey, simSec, offset, cycle)', procedure(SOURCE, 'SignalCompositeStateAt'))


class NativeAdapterBindingTests(unittest.TestCase):
    def test_optional_native_structure_preserves_capacity_and_sets_explicit_clock(self):
        raw, _ = source_plan()
        net = SimpleNamespace(signals=['SC' + sc for sc in raw['controllers']],
                              movement_capacity_vph={'sentinel': 123.}, meter_capacity_vph=1800.)
        cfg = SimpleNamespace(network=net)
        tuning = {'urban': {'native_signal': {'enabled': True, 'minimum_policy': 'include_source_reference'},
                            'physical_signal_contract': True}}
        with patch.dict(adapter._CFG_STRINGS, {'signal_actuation_plan_json': 'explicit'}), \
             patch.object(adapter, 'load_signal_group_actuation_plan', return_value=raw):
            result = adapter.install_native_signal_structure(cfg, tuning)
        self.assertEqual(net.cycle_length_by_signal['SC7'], 120.)
        self.assertEqual(net.effective_green_total_by_signal['SC7'], 114.)
        self.assertEqual(net.effective_green_total_by_signal['SC16'], 107.)
        self.assertEqual(net.live_phases_by_signal['SC7'], ('p1', 'p2', 'p4'))
        self.assertEqual(net.native_signal_minimum_policy, 'include_source_reference')
        self.assertEqual(result['native_signal_concurrency_movements'], 0.)
        self.assertEqual(result['native_signal_drive_cycle_recompute'], 0.)
        self.assertEqual(net.movement_capacity_vph, {'sentinel': 123.})
        self.assertEqual(net.meter_capacity_vph, 1800.)
        for failure in ('partial', 'minimum_policy', 'physical_contract'):
            changed_raw, changed_tuning = deepcopy(raw), deepcopy(tuning)
            if failure == 'partial': changed_raw['controllers']['16'].pop('native_clock_basis')
            if failure == 'minimum_policy': changed_tuning['urban']['native_signal'].pop('minimum_policy')
            if failure == 'physical_contract': changed_tuning['urban']['physical_signal_contract'] = False
            with patch.dict(adapter._CFG_STRINGS, {'signal_actuation_plan_json': 'explicit'}), \
                 patch.object(adapter, 'load_signal_group_actuation_plan', return_value=changed_raw):
                with self.assertRaises(ValueError): adapter.install_native_signal_structure(cfg, changed_tuning)

    def test_disabled_structure_is_noop_and_explicit_plan_path_is_used(self):
        cfg = SimpleNamespace(network=SimpleNamespace(sentinel=1))
        self.assertEqual(adapter.install_native_signal_structure(cfg, {}), {'native_signal_structure_enabled': 0.})
        self.assertEqual(vars(cfg.network), {'sentinel': 1})
        path = ROOT / 'reports/20260911_decision_runtime/native_clock_plan_v1.json'
        self.assertTrue(path.is_file())
        with patch.dict(adapter._CFG_STRINGS, {'signal_actuation_plan_json': str(path)}):
            self.assertEqual(adapter.signal_group_actuation_plan_path(), path.resolve())
            self.assertEqual(adapter.load_signal_group_actuation_plan(), json.loads(path.read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main()
