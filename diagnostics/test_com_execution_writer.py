"""Exercise installed writer procedures with fake devices, never VISSIM."""
import unittest

from diagnostics.test_signal_observation_window_patch import ROOT, procedure, run_vbs


COMMON = r'''
Option Explicit
Dim shell, devices, sigRequestedState, sigPendingPostCheck
Dim signalWriteOnChangeConfigured, signalWriteOnChangeEnabled
Dim signalReadbackIntervalConfigured, signalReadbackIntervalValue
Dim signalFailures, signalWriteSkips, signalTraceSimSec, signalTraceStage
Dim controlInterval, controlStartSec, simPeriod, records, result, dev, other
Dim vslTraceFile, actual, success
Set shell = CreateObject("WScript.Shell")
Set devices = CreateObject("Scripting.Dictionary")
Set sigRequestedState = CreateObject("Scripting.Dictionary")
Set sigPendingPostCheck = CreateObject("Scripting.Dictionary")
Set dev = New FakeDevice
Set other = New FakeDevice
devices.Add "1-1", dev
devices.Add "1-2", other
signalWriteOnChangeConfigured = True: signalWriteOnChangeEnabled = True
signalReadbackIntervalConfigured = True: signalReadbackIntervalValue = 0
controlInterval = 150: controlStartSec = 975: simPeriod = 1200
signalFailures = 0: signalWriteSkips = 0: records = 0

Class FakeDevice
    Public writes, reads, failWrite, failRead, wrongRead, values
    Private Sub Class_Initialize
        writes = 0: reads = 0: failWrite = False: failRead = False: wrongRead = False
        Set values = CreateObject("Scripting.Dictionary")
        values("SigState") = "RED"
    End Sub
    Public Property Let AttValue(key, value)
        writes = writes + 1
        If failWrite Then Err.Raise 6001, , "setter failed"
        values(key) = value
    End Property
    Public Property Get AttValue(key)
        reads = reads + 1
        If failRead Then Err.Raise 6002, , "read failed"
        If wrongRead Then
            AttValue = "RED"
        Else
            AttValue = values(key)
        End If
    End Property
End Class
Class FakeStream
    Public row
    Public Sub WriteLine(value)
        row = value
    End Sub
End Class
Function CachedSignalGroup(sc, sg)
    Set CachedSignalGroup = devices(CStr(sc) & "-" & CStr(sg))
End Function
Function SafeAtt(obj, attribute)
    SafeAtt = obj.AttValue(attribute)
End Function
Function PerfNow()
    PerfNow = 0
End Function
Sub PerfAdd(name, t0)
End Sub
Sub PerfCount(name, count)
End Sub
Sub RecordSignalReadback(sc, sg, requested, actual, ok)
    records = records + 1
End Sub
Function IsFiniteNumberInRange(value, minimum, maximum)
    IsFiniteNumberInRange = False
    If Not IsNumeric(value) Then Exit Function
    IsFiniteNumberInRange = (CDbl(value) >= minimum And CDbl(value) <= maximum)
End Function
Function Num(value)
    Num = CStr(value)
End Function
Sub Check(label, actual, expected)
    If CStr(actual) <> CStr(expected) Then Err.Raise 6003, , label & ": " & CStr(actual) & " <> " & CStr(expected)
End Sub
'''


class InstalledComWriterTests(unittest.TestCase):
    def execute(self, body, names):
        source = (ROOT / 'scripts/run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8-sig')
        helpers = '\n'.join(procedure(source, name) for name in names)
        return run_vbs(COMMON + helpers + '\n' + body + '\nWScript.Echo "PASS"\n')

    def signal(self, body):
        return self.execute(body, ['SkipUnchangedSignalWrites', 'SetSignalGroupState',
                                  'SignalReadbackIntervalSec', 'ValidateRuntimeSignalPersistence'])

    def test_changed_only_writes_and_next_callback_actual_check(self):
        self.signal(r'''
result = SetSignalGroupState(1, 1, "GREEN")
result = SetSignalGroupState(1, 1, "GREEN")
Check "one write", dev.writes, 1
Check "one skip", signalWriteSkips, 1
Check "pending", sigPendingPostCheck.Count, 1
ValidateRuntimeSignalPersistence 2
Check "actual read after next step", dev.reads, 2
Check "pending cleared", sigPendingPostCheck.Count, 0
ValidateRuntimeSignalPersistence 3
Check "no pure read without change", dev.reads, 2
result = SetSignalGroupState(1, 1, "AMBER")
Check "amber written", dev.writes, 2
ValidateRuntimeSignalPersistence 4
Check "amber actual post read", dev.reads, 4
signalWriteOnChangeEnabled = False
result = SetSignalGroupState(1, 1, "AMBER")
Check "diagnostic repeated write", dev.writes, 3
''')

    def test_failed_write_or_readback_never_cached_as_success(self):
        self.signal(r'''
dev.failWrite = True
result = SetSignalGroupState(1, 1, "GREEN")
Check "write failure reported", signalFailures, 1
Check "failed state not cached", sigRequestedState.Count, 0
Check "failed state not pending", sigPendingPostCheck.Count, 0
dev.failWrite = False: dev.wrongRead = True
result = SetSignalGroupState(1, 1, "GREEN")
Check "mismatch reported", signalFailures, 2
Check "mismatch not cached", sigRequestedState.Count, 0
dev.wrongRead = False
result = SetSignalGroupState(1, 1, "GREEN")
Check "retry written", dev.writes, 3
Check "retry now cached", sigRequestedState.Count, 1
''')

    def test_control_start_periodic_terminal_and_diagnostic_full_checks(self):
        self.signal(r'''
result = SetSignalGroupState(1, 1, "GREEN")
result = SetSignalGroupState(1, 2, "GREEN")
ValidateRuntimeSignalPersistence 2
signalReadbackIntervalValue = 60
ValidateRuntimeSignalPersistence 150
Check "nonaligned periodic still control check", dev.reads, 3
Check "other owned group included", other.reads, 3
ValidateRuntimeSignalPersistence 975
Check "control start check", dev.reads, 4
ValidateRuntimeSignalPersistence 1200
Check "terminal check", dev.reads, 5
signalReadbackIntervalValue = 1
ValidateRuntimeSignalPersistence 151
Check "diagnostic full step check", dev.reads, 6
''')

    def test_vsl_records_actual_distribution_reference_and_failures(self):
        self.execute(r'''
Set vslTraceFile = New FakeStream
success = SetClassSpeedChecked(dev, 10, 80, actual)
Check "checked success", success, True
Check "actual distribution", actual, 80
Check "one setter", dev.writes, 1
Check "one checked read", dev.reads, 1
RecordVslReadback 900, 123, 10, 80, actual, success
Check "actual sidecar", vslTraceFile.row, "900,123,10,80,80,1,immediate"
dev.failRead = True
success = SetClassSpeedChecked(dev, 20, 80, actual)
Check "read failure", success, False
Check "read error retained", actual, "ERR:READ:6002"
RecordVslReadback 900, 123, 20, 80, actual, success
Check "failed sidecar", vslTraceFile.row, "900,123,20,80,ERR:READ:6002,0,immediate"
dev.failRead = False: dev.failWrite = True
success = SetClassSpeedChecked(dev, 30, 80, actual)
Check "setter error retained", actual, "ERR:WRITE:6001"
Check "failed setter no read", dev.reads, 2
''', ['SetClassSpeedChecked', 'RecordVslReadback'])


if __name__ == '__main__':
    unittest.main()
