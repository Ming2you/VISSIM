"""Actual five-second collector with fake COM; never starts VISSIM."""
import unittest
from unittest.mock import patch
from diagnostics import test_signal_observation_window_patch as installed


class FiveSecondCollectorTests(unittest.TestCase):
    def test_heavy_scan_cadence_and_unbroken_signal_exposure(self):
        installed.InstalledConsumerTests.setUpClass()
        template = installed.InstalledConsumerTests(
            'test_actual_collector_native_to_controlled_and_reset_no_duplicate_step')
        captured = []
        with patch.object(installed, 'run_vbs', side_effect=lambda code:
                          captured.append(code) or 'COLLECTOR_CLOCK_PASS'):
            template.test_actual_collector_native_to_controlled_and_reset_no_duplicate_step()
        prefix = captured[0].rsplit('ResetHeadObservation 1\n',1)[0]
        code = ('Dim obsSampleInterval,obsClockSec,obsIntervalGreen\n'
                + prefix
                + installed.procedure(template.sources['scripts/run_real_world_stackelberg_controller.vbs'],
                                      'AccumulateHeadClock') + '''
obsSampleInterval=5: obsClockSec=-1
Set obsIntervalGreen=CreateObject("Scripting.Dictionary")
ResetHeadObservation 1
For t=1 To 10
 Vissim.Simulation.Current=t
 CollectHeadObservation t
 If t=2 Then fakeState="RED"
 If t=3 Then fakeState="GREEN"
 SealHeadSignalStates t
Next
Check scans=3,"heavy scans must only occur at1,5,10"
Check queueSamples=2 And farSamples=3,"sparse vehicle samples"
Check obsTransitions=9 And obsClockSec=10,"exposure clock must retain each second"
Check DictNumber(obsGreen,"h")=8 And DictNumber(obsNativeSec,"h")=9,"one intermediate RED second must remain visible"
Check DictNumber(obsCross,"h")=1 And DictNumber(obsQualified,"h")=0,"crossing spanning RED cannot be qualified"
snapshot=HeadObservationJson(10)
Check InStr(snapshot,"""vehicle_cadence_sec"":5")>0,"sparse provenance required"
CollectHeadObservation 10
Check scans=3 And obsTransitions=9,"same-time observer/logger calls must be idempotent"
ResetHeadObservation 10
fakeState="RED": fakeOwner=True: obsSignalSec=-1
SealHeadSignalStates 10
For t=11 To 15
 Vissim.Simulation.Current=t
 CollectHeadObservation t
 SealHeadSignalStates t
Next
Check scans=4,"next five-second sample"
Check obsTransitions=5 And obsWindowStart=10,"reset must preserve the exposure endpoint"
Check DictNumber(obsControlledSec,"h")=5 And DictNumber(obsNativeSec,"h")=0,"controlled and native exposure must stay separate"
Check DictNumber(obsGreen,"h")=0,"red exposure must not count as green"
Vissim.Simulation.Current=17
On Error Resume Next
CollectHeadObservation 17
failure=Err.Number: Err.Clear
On Error GoTo 0
Check failure<>0 And scans=4,"clock gaps must fail before vehicle capture"
WScript.Echo "FIVE_SECOND_COLLECTOR_PASS"
''')
        self.assertIn('FIVE_SECOND_COLLECTOR_PASS', installed.run_vbs(code))


if __name__ == '__main__':
    unittest.main()
