"""Synthetic pinned tuning/source proofs; no simulator or controller model."""
import copy
from pathlib import Path
import tempfile
import unittest

from diagnostics.com_execution_equivalence import verify_pair as v
from diagnostics.com_execution_equivalence.test_verify_pair import save


RUNTIME_SOURCE = '''Const RAMP_CYCLE_SEC = 10
Const RAMP_AMBER_SEC = 1
Const AMBER_SEC = 3
Dim runtimeRampAmberSec
runtimeRampAmberSec = ReadRuntimeRampAmberSec()
Function ReadRuntimeRampAmberSec()
Dim value
value = EnvText("RW_RAMP_AMBER_SEC")
If value = "" Then
ReadRuntimeRampAmberSec = RAMP_AMBER_SEC
ElseIf value = "0" Or value = "1" Then
ReadRuntimeRampAmberSec = CLng(value)
Else
WScript.Echo "ERROR=INVALID_RAMP_AMBER_SEC value=" & value
WScript.Quit 2
End If
End Function
Function RampStateAt(greenSec, simSec)
Dim pos
pos = FMod(CDbl(simSec), RAMP_CYCLE_SEC)
If CDbl(greenSec) <= 0 Then
RampStateAt = "RED"
ElseIf pos < CDbl(greenSec) Then
RampStateAt = "GREEN"
ElseIf pos < CDbl(greenSec) + runtimeRampAmberSec Then
RampStateAt = "AMBER"
Else
RampStateAt = "RED"
End If
End Function
Function ApplyRampMeterSignal(scNo, greenSec, simSec)
Dim state
signalTraceSimSec = CLng(simSec)
state = RampStateAt(greenSec, simSec)
ApplyRampMeterSignal = SetSignalGroupState(scNo, 1, state)
End Function
'''
LEGACY_SOURCE = '\n'.join(RUNTIME_SOURCE.splitlines()[:3]) + '\n'


def entry(p):
    return {'path': str(p), 'sha256': v.sha(p), 'exists': True}


def attach_timing(prov, root, amber=0):
    """Upgrade only a test fixture's native source + canonical timing proof."""
    tuning = root / 'ramp_timing.json'
    save(tuning, {'actuation': {'real_world_ramp_metering': {'amber_sec': amber}}})
    runner = Path(prov['files']['main_vbs_runner']['path']); runner.write_text(RUNTIME_SOURCE)
    prov['files']['main_vbs_runner'] = entry(runner)
    prov['files']['tuning'] = entry(tuning)
    prov['env']['RW_RAMP_AMBER_SEC'] = str(amber)
    prov['ramp_meter_timing'] = {'config_key': 'actuation.real_world_ramp_metering.amber_sec',
        'amber_sec': amber, 'declared': True, 'config_chain': [entry(tuning)]}


class RampAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        runner = self.root / 'runner.vbs'; runner.write_text(LEGACY_SOURCE)
        self.prov = {'files': {'main_vbs_runner': entry(runner)}, 'env': {}}
        attach_timing(self.prov, self.root)
        self.tuning = Path(self.prov['files']['tuning']['path'])

    def authority(self, prov=None, source=RUNTIME_SOURCE):
        return v.ramp_meter_timing_authority(self.prov if prov is None else prov, source)

    def repin(self):
        self.prov['files']['tuning'] = entry(self.tuning)
        self.prov['ramp_meter_timing']['config_chain'][0] = entry(self.tuning)

    def test_explicit_zero_and_actual_canonical_runtime_hook(self):
        self.assertEqual(self.authority()['amber_sec'], 0)
        source = (Path(__file__).resolve().parents[2] / 'scripts/run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8-sig')
        self.assertEqual(self.authority(source=source)['amber_sec'], 0)

    def test_legacy_default_and_new_undeclared_default(self):
        save(self.tuning, {}); self.repin()
        legacy = {'files': {'tuning': entry(self.tuning)}, 'env': {}}
        self.assertEqual(self.authority(legacy, LEGACY_SOURCE)['amber_sec'], 1)
        self.prov['ramp_meter_timing'].update(amber_sec=1, declared=False)
        self.prov['env']['RW_RAMP_AMBER_SEC'] = '1'
        self.assertEqual(self.authority()['amber_sec'], 1)

    def test_complete_inheritance_and_child_override(self):
        parent = self.root / 'parent.json'
        save(parent, {'actuation': {'real_world_ramp_metering': {'amber_sec': 0}}})
        save(self.tuning, {'extends': parent.name}); self.repin()
        self.prov['ramp_meter_timing']['config_chain'].append(entry(parent))
        self.assertEqual(self.authority()['amber_sec'], 0)
        save(self.tuning, {'extends': parent.name, 'actuation': {'real_world_ramp_metering': {'amber_sec': 1}}})
        self.repin(); self.prov['ramp_meter_timing']['amber_sec'] = 1; self.prov['env']['RW_RAMP_AMBER_SEC'] = '1'
        self.assertEqual(self.authority()['amber_sec'], 1)
        parent.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'SHA differs'): self.authority()

    def test_invalid_numeric_and_declaration_types_fail(self):
        for value in (True, False, '0', '1', None, -1, 2, 0.5):
            with self.subTest(value=value):
                bad = copy.deepcopy(self.prov); bad['ramp_meter_timing']['amber_sec'] = value
                with self.assertRaises(ValueError): self.authority(bad)
                save(self.tuning, {'actuation': {'real_world_ramp_metering': {'amber_sec': value}}}); self.repin()
                with self.assertRaises(ValueError): self.authority()
        attach_timing(self.prov, self.root)
        for value in (None, 'true', 1):
            bad = copy.deepcopy(self.prov); bad['ramp_meter_timing']['declared'] = value
            with self.assertRaises(ValueError): self.authority(bad)

    def test_missing_evidence_and_transport_mismatches_fail(self):
        for scope, key in ((None, 'ramp_meter_timing'), ('env', 'RW_RAMP_AMBER_SEC'),
                           ('files', 'tuning'), ('ramp_meter_timing', 'config_chain')):
            bad = copy.deepcopy(self.prov); (bad if scope is None else bad[scope]).pop(key)
            with self.subTest(scope=scope), self.assertRaises(ValueError): self.authority(bad)
        for value in ('1', '', 0, False):
            bad = copy.deepcopy(self.prov); bad['env']['RW_RAMP_AMBER_SEC'] = value
            with self.assertRaises(ValueError): self.authority(bad)
        bad = copy.deepcopy(self.prov); bad['ramp_meter_timing']['declared'] = False
        with self.assertRaisesRegex(ValueError, 'differs from manifest'): self.authority(bad)
        with self.assertRaisesRegex(ValueError, 'lacks manifest'):
            self.authority({'files': self.prov['files'], 'env': {}}, LEGACY_SOURCE)

    def test_chain_order_completeness_cycles_and_sha_are_enforced(self):
        parent = self.root / 'parent.json'; save(parent, {})
        save(self.tuning, {'extends': parent.name, 'actuation': {'real_world_ramp_metering': {'amber_sec': 0}}})
        self.repin()
        with self.assertRaisesRegex(ValueError, 'config pin'): self.authority()
        self.prov['ramp_meter_timing']['config_chain'].append(entry(parent))
        self.assertEqual(self.authority()['amber_sec'], 0)
        for chain in (self.prov['ramp_meter_timing']['config_chain'][::-1],
                      self.prov['ramp_meter_timing']['config_chain'] + [entry(parent)]):
            bad = copy.deepcopy(self.prov); bad['ramp_meter_timing']['config_chain'] = chain
            with self.assertRaises(ValueError): self.authority(bad)
        save(parent, {'extends': self.tuning.name})
        self.prov['ramp_meter_timing']['config_chain'][1] = entry(parent)
        with self.assertRaisesRegex(ValueError, 'Cyclic'): self.authority()

    def test_inert_or_divergent_native_hook_cannot_authorize_zero(self):
        for source in (LEGACY_SOURCE, LEGACY_SOURCE + "' " + RUNTIME_SOURCE.replace('\n', "\n' "),
                       RUNTIME_SOURCE.replace(' + runtimeRampAmberSec', ' + RAMP_AMBER_SEC'),
                       RUNTIME_SOURCE.replace('ReadRuntimeRampAmberSec = CLng(value)', 'ReadRuntimeRampAmberSec = 1'),
                       RUNTIME_SOURCE.replace('SetSignalGroupState(scNo, 1, state)', 'SetSignalGroupState(scNo, 1, "GREEN")'),
                       RUNTIME_SOURCE.replace('runtimeRampAmberSec = ReadRuntimeRampAmberSec()', 'runtimeRampAmberSec = 0'),
                       RUNTIME_SOURCE + 'runtimeRampAmberSec = 1\n'):
            with self.subTest(source=source[-80:]), self.assertRaises(ValueError): self.authority(source=source)


if __name__ == '__main__': unittest.main()
