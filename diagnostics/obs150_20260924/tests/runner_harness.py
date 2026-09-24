"""Harness for the WP-A runner tests: real procedures of the runner VBS + the mock COM, run by cscript.

The procedures are cut out of scripts/run_real_world_stackelberg_controller.vbs by name (the
repository's own extractor, scripts/tests/test_b1a_vbs_verified_capture_static.procedure), so a
test always runs the code that ships. The obs150 procedure block and the obs150 globals block
are taken whole. Nothing here starts VISSIM or creates the Vissim COM object.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tests.test_b1a_vbs_verified_capture_static import class_body, procedure  # noqa: E402

VBS_PATH = ROOT / 'scripts' / 'run_real_world_stackelberg_controller.vbs'
# D10 (plan A4/section 9): the ONE value the WP-A tests expect for the runner's OBS150_FRAME_ADVANCE.
# 0 is provisional (open until G1 / the user). When D10 is decided (WP-B1 proposes 1 in
# patches/VBS_B1_D10.patch), change it here together with the VBS constant; the open-D10 runlog
# markers are asserted only while it is 0.
D10_FRAME_ADVANCE = 1
PS1_PATH = ROOT / 'scripts' / 'run_real_world_single_watchdog_distributed_core17legs4b.ps1'
MOCK_PATH = Path(__file__).resolve().parent / 'mock_vissim_runner.vbs'
CSCRIPT = shutil.which('cscript.exe') or shutil.which('cscript')
POWERSHELL = shutil.which('powershell.exe') or shutil.which('powershell')

PROCEDURES = (
    'EnvText', 'ForceStepwiseMode', 'UseSingleDecisionEventMode', 'StateLogMode', 'QueueWindowEnabled',
    'FarMeasurementEnabled', 'ParseB1aPositiveLongText', 'ReadAllText', 'OneLine', 'RunCapture3Timeout',
    'TerminateExecTree', 'ElapsedSec', 'Q', 'Pad6', 'JsonEscape', 'JsonBoolean', 'JsonDoubleInvariant',
    'B1aSignificantDigitCount', 'TryB1aFiniteDouble', 'TryExact2DTableBounds', 'IsB1aEmptyTableResult',
    'ParseB1aLaneId', 'TrimB1aHorizontalWhitespace', 'ComBoolean', 'SafeAtt', 'CachedSignalController',
    'CachedSignalGroup', 'EnsureFolder', 'EnsureParentFolder', 'WriteLanePlantObservation',
    'AbortVehicleObservation', 'PerfNow', 'PerfAdd', 'PerfCount', 'RunContinuousTo', 'TrySetAtt',
    'RecordStartupSimulationProgress', 'IsFiniteNumberInRange', 'Num', 'SignalClockPosition', 'FMod',
    'FarMeasurementJson', 'InitializeComRampMeterControl', 'EnableSignalControllerForRuntime',
    'RecordSignalReadback', 'ObservationSignalReadback', 'SetSignalGroupState', 'SkipUnchangedSignalWrites',
    'IsControlledSignalGroup', 'MainlineSignalGroupsOnly', 'SignalGroupCount', 'NativeVehRecResolution',
    'ValidateRuntimeSignalPersistence', 'SignalReadbackIntervalSec', 'BoolInt',
)


def source():
    return VBS_PATH.read_text(encoding='utf-8')


def obs150_block(text):
    match = re.search(r"(?ms)^' BEGIN OBS150_RUNNER\n.*?^' END OBS150_RUNNER\n", text)
    if match is None:
        raise AssertionError('OBS150_RUNNER block missing')
    return match.group(0)


def obs150_globals(text):
    match = re.search(r"(?ms)^' obs150 \(SDMPC31_OBS150_PLAN_20260924 section 2.*?"
                      r"^obs150SigScList = Empty : obs150LastEventCountValue = 0\n", text)
    if match is None:
        raise AssertionError('obs150 globals block missing')
    return match.group(0)


def vbs_string(value):
    return '"' + str(value).replace('"', '""') + '"'


PRELUDE = '''Option Explicit
Dim fso, shell, Vissim, gMock
Dim gMockPosShift, gMockEvalBad, gMockStopShift, gMockNoVehs, gMockLastShift, gMockStuck, gMockCurrentK
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
gMockPosShift = 0 : gMockEvalBad = "" : gMockStopShift = 0 : gMockNoVehs = "" : gMockLastShift = 0
gMockStuck = "" : gMockCurrentK = 1
Const B1A_ENTRY_TOLERANCE_M = 8.0
Dim JSON_DECIMAL_SEPARATOR
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)
Dim obsEnabled, obsSampleInterval, obsBulkReads, obsCacheHits, decisionDir, netPath, workspaceRoot, pythonExe, runId
Dim simPeriod, controlInterval, stateLogIntervalSec, auditAnchorsSec, incidentEnabled
Dim controllerName, controlStartSec, warmupControllerName, RW_SIGNAL_SCS, RW_RAMP_METER_SCS, nativeClockPlans
Dim signalFailures, observationFailures, comFailures
Dim signalTraceStage, signalTraceSimSec, signalTraceFile, signalWriteAttempts, signalReadbackOk
Dim signalPersistenceChecks, signalPersistenceOk, sigRequestedState, sigPendingPostCheck
Dim signalWriteOnChangeConfigured, signalWriteOnChangeEnabled, signalReadbackIntervalConfigured, signalReadbackIntervalValue
Dim sigScCache, sigSgCache, sigSgCountCache, sigSgNameCache, signalControlled, sgEnableMidblockSkips, signalWriteSkips
Dim RW_PERF_ENABLED, perfSum, perfCnt, startupPerfT0, farMeasLinks, farFwExit
Dim failures
failures = 0
obsEnabled = False : obsSampleInterval = 1 : obsBulkReads = 0 : obsCacheHits = 0
simPeriod = {sim_period} : controlInterval = 150 : stateLogIntervalSec = 150
auditAnchorsSec = "" : incidentEnabled = False
controllerName = "wu-link" : controlStartSec = 900 : warmupControllerName = "no-control"
RW_SIGNAL_SCS = {signal_scs} : RW_RAMP_METER_SCS = {meter_scs}
Set nativeClockPlans = CreateObject("Scripting.Dictionary")
signalFailures = 0 : observationFailures = 0 : comFailures = 0
signalTraceStage = "immediate" : signalTraceSimSec = 0
signalWriteAttempts = 0 : signalReadbackOk = 0 : signalPersistenceChecks = 0 : signalPersistenceOk = 0
Set sigRequestedState = CreateObject("Scripting.Dictionary")
Set sigPendingPostCheck = CreateObject("Scripting.Dictionary")
signalWriteOnChangeConfigured = False : signalReadbackIntervalConfigured = False
Set sigScCache = CreateObject("Scripting.Dictionary")
Set sigSgCache = CreateObject("Scripting.Dictionary")
Set sigSgCountCache = CreateObject("Scripting.Dictionary")
Set sigSgNameCache = CreateObject("Scripting.Dictionary")
Set signalControlled = CreateObject("Scripting.Dictionary")
sgEnableMidblockSkips = 0 : signalWriteSkips = 0
RW_PERF_ENABLED = False
Set perfSum = CreateObject("Scripting.Dictionary")
Set perfCnt = CreateObject("Scripting.Dictionary")
Set farMeasLinks = CreateObject("Scripting.Dictionary")
farFwExit = 0
decisionDir = {decision_dir}
netPath = {net_path}
workspaceRoot = {workspace_root}
pythonExe = {python_exe}
runId = "run-wpa-test"
Set gMock = New MockVissimR
Set Vissim = gMock
Set signalTraceFile = fso.CreateTextFile({trace_path}, True)
'''

CHECKS = '''
Sub Check(label, actual, expected)
    If CStr(actual) <> CStr(expected) Then
        failures = failures + 1
        WScript.Echo "FAIL " & label & " actual=" & CStr(actual) & " expected=" & CStr(expected)
    Else
        WScript.Echo "OK " & label
    End If
End Sub

Sub SaveText(path, text)
    Dim ts
    Set ts = fso.CreateTextFile(path, True, False)
    ts.Write text
    ts.Close
End Sub
'''

EPILOGUE = '''
If failures > 0 Then WScript.Quit 1
WScript.Echo "PASS"
'''


_CUT = {}


def _cut(text):
    """The runner code a harness needs, cut once per source text (the extractor scans every line)."""
    if text not in _CUT:
        _CUT[text] = (obs150_globals(text), '\n\n'.join(procedure(text, name) for name in PROCEDURES),
                      class_body(text, 'Utf8LineWriter'), obs150_block(text))
    return _CUT[text]


def build(body, *, work, sim_period=1350, signal_scs='5', meter_scs='9106', text=None):
    text = source() if text is None else text
    work = Path(work)
    prelude = PRELUDE.format(
        sim_period=sim_period, signal_scs=vbs_string(signal_scs), meter_scs=vbs_string(meter_scs),
        decision_dir=vbs_string(work / 'decisions'), net_path=vbs_string(work / 'network' / 'net.inpx'),
        workspace_root=vbs_string(ROOT), python_exe=vbs_string('"' + sys.executable + '"'),
        trace_path=vbs_string(work / 'signal_readback.csv'))
    globals_block, procedures, writer_class, block = _cut(text)
    parts = [prelude, globals_block, MOCK_PATH.read_text(encoding='utf-8'), procedures, writer_class, block,
             CHECKS, body, EPILOGUE]
    return '\n'.join(parts)


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_')}
    env.update(extra or {})
    env['PYTHONUTF8'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run_vbs(script, *, work, env=None, timeout=240):
    work = Path(work)
    (work / 'decisions').mkdir(parents=True, exist_ok=True)
    (work / 'network').mkdir(parents=True, exist_ok=True)
    path = work / 'harness.vbs'
    path.write_text(script, encoding='utf-8')
    return subprocess.run([CSCRIPT, '//nologo', str(path)], cwd=str(work), env=clean_env(env),
                          capture_output=True, text=True, errors='replace', timeout=timeout)


def obs150_env(csv_path, sha256, **extra):
    env = {'RW_OBSERVATION_CADENCE': 'decision150', 'RW_LANE_PLANT_OBSERVATION': '1',
           'RW_STATE_LOG': 'decision', 'RW_QUEUE_WINDOW': '0', 'RW_VEHICLE_OBSERVATION_INTERVAL_SEC': '1',
           'RW_OBS150_DETECTORS': str(csv_path), 'RW_OBS150_DETECTORS_SHA256': sha256,
           'RW_OBS150_EXPECTED_SIMRES': '10', 'RW_OBS150_VEHREC_SEC': '5'}
    env.update(extra)
    return env


def mock_network_lines(rows, *, sc_groups):
    """VBS lines that create every link/lane of the table and the signal controllers."""
    lanes = {}
    for row in rows:
        lanes[row.link] = max(lanes.get(row.link, 0), row.lane,
                              int(row.geometry_assert.get('lane_count', row.lane)))
    lines = [f'gMock.mNet.mLinks.AddLink {link}, {count}' for link, count in sorted(lanes.items())]
    lines += [f'gMock.mNet.mScs.AddController {sc}, {count}' for sc, count in sorted(sc_groups.items())]
    return '\n'.join(lines)


def mer_header(rows, network_path):
    lines = ['', 'Data Collection (Raw Data)', '', f'File:     {network_path}', 'Comment:  ',
             'Date:     test', 'PTV Vissim 2020.00-14 (64 bit) [95957]', '']
    for row in rows:
        lines.append(f'Data collection point {row.dcp_no:>8}: Link {row.link:>5} lane {row.lane} at {row.pos:>11.3f} m.')
    text = '\r\n'.join(lines) + '\r\n\r\n'
    text += (' Measurem.;  t(Entry);   t(Exit);    VehNo; Vehicle type;    Line; v[km/h]; b[m/s2];   Occ; Pers; '
             'tQueue; VehLength[m];\n')
    return text


def mer_row(dcp, t_entry, t_exit, veh):
    def t(v):
        return '-1.00' if v is None else f'{v:.2f}'
    return (f'  {dcp};  {t(t_entry):>8};  {t(t_exit):>8};  {veh:>7};          100;        0;   50.0;   0.00;   '
            f'0.00;    1;   0.0;     4.50;\n')
