"""WP-A runner (plan A1-A7, A9): the obs150 VBS procedures run by cscript against a mock COM.

Each test cuts the real procedures out of scripts/run_real_world_stackelberg_controller.vbs
(runner_harness.build), runs them with cscript and checks what they wrote with the WP-0
contract validators. The end-to-end bundle test also runs the WP-B1 capture CLI and the
real sha256 helper. No VISSIM, no COM server, no licence seat.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import runner_harness as rh  # noqa: E402
from contract_fixtures import detector_rows  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402

SC_GROUPS = {'1004': 5, '5': 2, '9106': 1}      # the fixture heads: 1004-2/5, 5-2, meter 9106-1


class RunnerCase(unittest.TestCase):
    def setUp(self):
        if not rh.CSCRIPT:
            self.skipTest('Windows Script Host is required')
        self._tmp = tempfile.TemporaryDirectory(prefix='wpa_vbs_')
        self.work = Path(self._tmp.name)
        self.rows = detector_rows()
        self.csv = self.work / 'obs150_detectors_v2.csv'
        self.csv.write_bytes(oc.format_detector_csv(self.rows))
        self.sha = hashlib.sha256(self.csv.read_bytes()).hexdigest()
        self.network = rh.mock_network_lines(self.rows, sc_groups=SC_GROUPS)

    def tearDown(self):
        self._tmp.cleanup()

    def run_body(self, body, *, env_extra=None, sim_period=1350, expect=0, env=None, text=None):
        script = rh.build(self.network + '\n' + body, work=self.work, sim_period=sim_period, text=text)
        environment = rh.obs150_env(self.csv, self.sha) if env is None else env
        environment.update(env_extra or {})
        result = rh.run_vbs(script, work=self.work, env=environment)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, expect, output)
        if expect == 0:
            self.assertIn('PASS', result.stdout, output)
        return result

    def load(self, name):
        return json.loads((self.work / name).read_text(encoding='ascii'))


STARTUP = '''
ValidateObs150Startup
Obs150LoadDetectorCsv
ReadObs150SimRes
'''


class StartupTests(RunnerCase):
    """Plan A1: every combination that would mislabel a window stops with Quit 2."""

    def reject(self, mutation, reason, env_extra=None):
        result = self.run_body(mutation + '\nValidateObs150Startup\nWScript.Echo "NOT_REJECTED"\n',
                               env_extra=env_extra, expect=2)
        self.assertIn('ERROR=OBS150_', result.stdout)
        self.assertIn(reason, result.stdout)
        self.assertNotIn('NOT_REJECTED', result.stdout)

    def test_valid_environment_enters_obs150_mode(self):
        result = self.run_body(STARTUP + '''
Check "mode", obs150Mode, True
Check "simres", simResSteps, 10
Check "vehrec", NativeVehRecResolution(), 50
Check "rows", UBound(obs150Rows) + 1, ''' + str(len(self.rows)) + '''
Check "gt_empty", IsEmpty(obs150GtWindows), True
Check "obs150_dir", obs150Dir, fso.BuildPath(fso.GetAbsolutePathName(decisionDir), "obs150")
''')
        self.assertIn('OBS150_MODE=1 cadence=decision150', result.stdout)
        self.assertIn('SIMRES=10 source=network', result.stdout)
        self.assertIn(f'SIGNAL_FRAME_ADVANCE={rh.D10_FRAME_ADVANCE} ', result.stdout)
        if rh.D10_FRAME_ADVANCE == 0:
            self.assertIn('d10=open_pending_G1', result.stdout)

    def test_ground_truth_windows_parse(self):
        self.run_body(STARTUP + '''
Check "gt_count", UBound(obs150GtWindows) + 1, 2
Check "gt_json", Obs150GtJson(), "[[750,900],[1050,1200]]"
''', env_extra={'RW_OBS150_GT': '750:900,1050:1200'})

    def test_v1_path_is_inert(self):
        env = {k: v for k, v in rh.obs150_env(self.csv, self.sha).items() if k != 'RW_OBSERVATION_CADENCE'}
        self.run_body('''
ValidateObs150Startup
Check "mode", obs150Mode, False
Check "no_frame_advance_field", SignalClockPosition(7, 907, 119, 120), 66
Check "vehrec_v1_default", NativeVehRecResolution(), 5
''', env=env)

    def test_unknown_cadence(self):
        self.reject('', 'RW_OBSERVATION_CADENCE=decision60', {'RW_OBSERVATION_CADENCE': 'decision60'})

    def test_head_observer_exclusive(self):
        self.reject('obsEnabled = True', 'RW_SIGNAL_OBSERVATION=1')

    def test_force_stepwise(self):
        self.reject('', 'RW_FORCE_STEPWISE', {'RW_FORCE_STEPWISE': '1'})

    def test_control_interval(self):
        self.reject('controlInterval = 60 : stateLogIntervalSec = 60', 'control_interval_sec=60')

    def test_state_log_interval(self):
        self.reject('stateLogIntervalSec = 30', 'state_log_interval_sec=30')

    def test_sim_period(self):
        self.reject('simPeriod = 1000', 'sim_period_sec=1000')

    def test_audit_anchors(self):
        self.reject('auditAnchorsSec = "900"', 'RW_AUDIT_ANCHORS_SEC')

    def test_incident(self):
        self.reject('incidentEnabled = True', 'incident closure')

    def test_single_decision_diagnostic(self):
        self.reject('controllerName = "diagnostic-ramp-profile"', 'single-decision diagnostic')

    def test_state_log_mode(self):
        self.reject('', 'RW_STATE_LOG must be decision', {'RW_STATE_LOG': 'full'})

    def test_queue_window(self):
        self.reject('', 'RW_QUEUE_WINDOW=1', {'RW_QUEUE_WINDOW': '1'})

    def test_lane_plant_observation(self):
        self.reject('', 'RW_LANE_PLANT_OBSERVATION must be 1', {'RW_LANE_PLANT_OBSERVATION': '0'})

    def test_native_eval_off(self):
        self.reject('', 'RW_NATIVE_EVAL=0', {'RW_NATIVE_EVAL': '0'})

    def test_vehrec_resolution_conflict(self):
        self.reject('', 'RW_VEHREC_RESOLUTION', {'RW_VEHREC_RESOLUTION': '5'})

    def test_detector_sha_format(self):
        self.reject('', 'RW_OBS150_DETECTORS_SHA256', {'RW_OBS150_DETECTORS_SHA256': 'ABC'})

    def test_ground_truth_from_zero(self):
        self.reject('', 'RW_OBS150_GT', {'RW_OBS150_GT': '0:150'})

    def test_ground_truth_overlap(self):
        self.reject('', 'RW_OBS150_GT windows must be sorted', {'RW_OBS150_GT': '750:900,750:1050'})

    def test_ground_truth_adjacent_windows(self):
        # 900 would be both the last step of the first window and the start row of the second.
        self.reject('', 'separated (merge adjacent ones)', {'RW_OBS150_GT': '750:900,900:1050'})

    def test_stale_obs150_folder(self):
        folder = self.work / 'decisions' / 'obs150'
        folder.mkdir(parents=True)
        (folder / 'mer_000001.jsonl').write_bytes(b'')
        self.reject('', 'stale obs150 folder')

    def test_stale_runtime_error_file(self):
        (self.work / 'network').mkdir(parents=True, exist_ok=True)
        (self.work / 'network' / 'net_001.err').write_bytes(b'old run\r\n')
        self.reject('', 'stale runtime error file')

    def test_simres_mismatch(self):
        result = self.run_body('gMock.mSim.res = 1\n' + STARTUP + 'WScript.Echo "NOT_REJECTED"\n', expect=2)
        self.assertIn('ERROR=OBS150_SIMRES_MISMATCH network=1', result.stdout)

    def test_detector_table_checked_by_the_contract_parser(self):
        self.run_body('ValidateObs150Startup\nObs150VerifyDetectorTable\n')
        # A JSON column only the contract parser reads: lane_count 0 in the first row.
        good = self.csv.read_bytes()
        bad = good.replace(b'""lane_count"":4', b'""lane_count"":0', 1)
        self.assertNotEqual(bad, good)
        self.csv.write_bytes(bad)
        env = rh.obs150_env(self.csv, hashlib.sha256(bad).hexdigest())
        result = self.run_body('ValidateObs150Startup\nObs150VerifyDetectorTable\nWScript.Echo "NOT_REJECTED"\n',
                               env=env, expect=2)
        self.assertIn('ERROR=OBS150_DETECTOR_TABLE exit=1', result.stdout)
        self.assertIn('lane_count', result.stdout)


EVALUATION = '''
Obs150SetEvaluation "DataCollCollectData", True
Obs150SetEvaluation "DataCollFromTime", 0
Obs150SetEvaluation "DataCollToTime", CLng(simPeriod)
Obs150SetEvaluation "DataCollInterval", OBS150_DECISION_SEC
Obs150SetEvaluation "DataCollRawWriteFile", True
Obs150SetEvaluation "DataCollRawFromTime", 0
Obs150SetEvaluation "DataCollRawToTime", CLng(simPeriod)
'''


class InstallTests(RunnerCase):
    """Plan A5/A6: detectors installed 1:1 with readback, evaluation read back, install record."""

    def test_install_record_passes_the_contract(self):
        result = self.run_body(STARTUP + '''
gMock.mNet.mDcms.AddDataCollectionMeasurement 910030
Obs150InstallDetectors
''' + EVALUATION + '''
Obs150WriteInstallRecord
Check "points", gMock.mNet.mDcps.Count, ''' + str(len(self.rows)) + '''
Check "measurements", gMock.mNet.mDcms.Count, ''' + str(len(self.rows) + 1) + '''
Check "link", gMock.mNet.mDcms.ItemByKey(960001).AttValue("DataCollectionPoints"), "960001"
Check "interval", gMock.mEval.AttValue("DataCollInterval"), 150
Check "raw", gMock.mEval.AttValue("DataCollRawWriteFile"), 1
''')
        record_path = self.work / 'decisions' / 'obs150' / 'obs150_install.json'
        record = json.loads(record_path.read_text(encoding='utf-8'))
        oc.validate_install_record(record, self.rows)
        self.assertEqual(record['evaluation']['DataCollToTime'], 1350)
        self.assertEqual(record['detector_config'], {'path': str(self.csv), 'sha256': self.sha, 'rows': len(self.rows)})
        digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
        self.assertIn(f'OBS150_INSTALL_RECORD path={record_path} sha256={digest}', result.stdout)
        self.assertIn(f'OBS150_DETECTORS n={len(self.rows)} sha={self.sha}', result.stdout)

    def test_reused_key_stops(self):
        result = self.run_body(STARTUP + '''
gMock.mNet.mDcms.AddDataCollectionMeasurement 960003
Obs150InstallDetectors
WScript.Echo "NOT_REJECTED"
''', expect=2)
        self.assertIn('ERROR=OBS150_DETECTOR_KEY_REUSED key=960003', result.stdout)

    def test_position_readback_mismatch_stops(self):
        result = self.run_body(STARTUP + 'gMockPosShift = 0.01\nObs150InstallDetectors\nWScript.Echo "NOT_REJECTED"\n',
                               expect=2)
        self.assertIn('ERROR=OBS150_DETECTOR_READBACK key=960001 pos', result.stdout)

    def test_missing_lane_stops_without_key_zero_fallback(self):
        text = self.network.replace('gMock.mNet.mLinks.AddLink 71, 4', 'gMock.mNet.mLinks.AddLink 71, 1')
        self.network = text
        result = self.run_body(STARTUP + 'Obs150InstallDetectors\nWScript.Echo "NOT_REJECTED"\n', expect=2)
        self.assertIn('ERROR=OBS150_DETECTOR_INSTALL key=960002 link=71 lane=4', result.stdout)
        self.assertNotIn('NOT_REJECTED', result.stdout)

    def test_evaluation_readback_mismatch_stops(self):
        result = self.run_body(STARTUP + 'gMockEvalBad = "DataCollInterval"\n' + EVALUATION + 'WScript.Echo "NOT_REJECTED"\n',
                               expect=2)
        self.assertIn('ERROR=OBS150_EVALUATION_READBACK att=DataCollInterval value=150', result.stdout)


SIGNAL_SEQUENCE = STARTUP + '''
obs150StopSec = 1
SaveText {sig1}, Obs150SignalLogJson(1)
InitializeComRampMeterControl
Check "enable5", EnableSignalControllerForRuntime(5), "stored"
Check "w_5_1", SetSignalGroupState(5, 1, "GREEN"), "GREEN"
Check "w_5_2", SetSignalGroupState(5, 2, "RED"), "RED"
Check "skip_same", SetSignalGroupState(5, 2, "RED"), "RED"
obs150StopSec = 37
Check "w_amber", SetSignalGroupState(5, 1, "AMBER"), "AMBER"
obs150StopSec = 62
gMockStuck = "5-2"
Check "fail", Left(SetSignalGroupState(5, 2, "GREEN"), 4), "ERR:"
obs150StopSec = 80
gMockStuck = ""
Check "rewrite", SetSignalGroupState(5, 2, "GREEN"), "GREEN"
obs150StopSec = 150
SaveText {sig150}, Obs150SignalLogJson(150)
Check "event_at_start", SetSignalGroupState(5, 1, "RED"), "RED"
obs150StopSec = 200
Check "w_200", SetSignalGroupState(5, 1, "GREEN"), "GREEN"
obs150StopSec = 300
SaveText {sig300}, Obs150SignalLogJson(300)
'''


class SignalLogTests(RunnerCase):
    """Plan A4, CONTRACT 4.3: the runner's own write/own/fail log, window by window."""

    def paths(self):
        return {name: rh.vbs_string(self.work / f'{name}.json') for name in ('sig1', 'sig150', 'sig300')}

    def test_write_own_fail_sequence(self):
        self.run_body(SIGNAL_SEQUENCE.format(**self.paths()))
        first, second, third = self.load('sig1.json'), self.load('sig150.json'), self.load('sig300.json')
        oc.validate_signal_log(first, 0, 1)
        oc.validate_signal_log(second, 0, 150)
        oc.validate_signal_log(third, 150, 300)
        self.assertEqual(first['scs'], ['5', '1004', '9106'])
        self.assertEqual(first['events'], [])
        self.assertTrue(first['complete'])
        self.assertEqual(set(first['start']), {'5-1', '5-2', '1004-1', '1004-2', '1004-3', '1004-4', '1004-5', '9106-1'})
        self.assertTrue(all(v == {'owner': 'native'} for v in first['start'].values()))
        self.assertEqual(second['start'], first['start'])
        self.assertEqual(second['events'], [
            [1, '9106', '1', 'own', True], [1, '9106', '1', 'write', 'GREEN'],
            [1, '5', '1', 'own', True], [1, '5', '2', 'own', True],
            [1, '5', '1', 'write', 'GREEN'], [1, '5', '2', 'write', 'RED'],
            [37, '5', '1', 'write', 'AMBER'], [62, '5', '2', 'fail', 'GREEN', 'ERR:readback=RED'],
            [80, '5', '2', 'write', 'GREEN']])
        self.assertFalse(second['complete'])
        # CONTRACT 2.2/4.3: the window starts with the state BEFORE the writes at its first stop;
        # they reach the heads one second later (2.3), so they are this window's events.
        self.assertEqual(third['start']['5-1'], {'owner': 'com', 'state': 'AMBER', 'verified': True})
        self.assertEqual(third['start']['5-2'], {'owner': 'com', 'state': 'GREEN', 'verified': True})
        self.assertEqual(third['start']['9106-1'], {'owner': 'com', 'state': 'GREEN', 'verified': True})
        self.assertEqual(third['start']['1004-2'], {'owner': 'native'})
        self.assertEqual(third['events'], [[150, '5', '1', 'write', 'RED'], [200, '5', '1', 'write', 'GREEN']])
        self.assertTrue(third['complete'])

    def test_unverified_ownership_makes_the_window_incomplete(self):
        body = STARTUP + '''
obs150StopSec = 1
SaveText {sig1}, Obs150SignalLogJson(1)
obs150StopSec = 40
Check "enable5", EnableSignalControllerForRuntime(5), "stored"
obs150StopSec = 150
SaveText {sig150}, Obs150SignalLogJson(150)
Check "write_at_start", SetSignalGroupState(5, 1, "GREEN"), "GREEN"
obs150StopSec = 300
SaveText {sig300}, Obs150SignalLogJson(300)
'''
        self.run_body(body.format(**self.paths()))
        second, third = self.load('sig150.json'), self.load('sig300.json')
        oc.validate_signal_log(second, 0, 150)
        oc.validate_signal_log(third, 150, 300)
        self.assertEqual(second['events'], [[40, '5', '1', 'own', True], [40, '5', '2', 'own', True]])
        self.assertFalse(second['complete'])
        # the start is taken before the write at 150: both SGs are still unverified in (150, 151]
        self.assertEqual(third['start']['5-1'], {'owner': 'com', 'state': 'RED', 'verified': False})
        self.assertEqual(third['start']['5-2'], {'owner': 'com', 'state': 'RED', 'verified': False})
        self.assertEqual(third['events'], [[150, '5', '1', 'write', 'GREEN']])
        self.assertFalse(third['complete'])

    def test_post_step_mismatch_marks_the_window(self):
        body = SIGNAL_SEQUENCE.split('obs150StopSec = 300')[0] + '''
obs150StopSec = 240
gMock.mNet.mScs.ItemByKey(5).SGs.ItemByKey(1).state = "AMBER"
ValidateRuntimeSignalPersistence 240
obs150StopSec = 300
SaveText {sig300}, Obs150SignalLogJson(300)
'''
        self.run_body(body.format(**self.paths()))
        third = self.load('sig300.json')
        oc.validate_signal_log(third, 150, 300)
        self.assertEqual(third['events'][-1], [240, '5', '1', 'fail', 'GREEN', 'ERR:post_step readback=AMBER'])
        self.assertFalse(third['complete'])

    def test_an_interrupted_update_stops_the_run(self):
        # SetSignalGroupState calls the hook under On Error Resume Next; a swallowed run-time error
        # leaves obs150SigBusy set, and the next log entry must stop instead of logging on.
        result = self.run_body(STARTUP + '''
obs150StopSec = 1
SaveText {sig1}, Obs150SignalLogJson(1)
obs150SigBusy = True
InitializeComRampMeterControl
WScript.Echo "NOT_REJECTED"
'''.format(**self.paths()), expect=13)
        self.assertIn('ERROR=OBS150_SIGNAL_LOG sim_sec=1 an earlier signal log update was interrupted', result.stdout)

    def test_write_before_the_log_stops(self):
        result = self.run_body(STARTUP + '''
obs150StopSec = 1
Check "enable5", EnableSignalControllerForRuntime(5), "stored"
WScript.Echo "NOT_REJECTED"
''', expect=13)
        self.assertIn('ERROR=OBS150_SIGNAL_LOG sim_sec=1 signal write before the t=1 bundle', result.stdout)

    def test_write_at_a_decision_stop_before_its_bundle_stops(self):
        result = self.run_body(STARTUP + '''
obs150StopSec = 1
SaveText {sig1}, Obs150SignalLogJson(1)
InitializeComRampMeterControl
obs150StopSec = 150
Check "late", SetSignalGroupState(9106, 1, "RED"), "RED"
WScript.Echo "NOT_REJECTED"
'''.format(**self.paths()), expect=13)
        self.assertIn('before the bundle of its window start', result.stdout)


class ClockTests(RunnerCase):
    """Plan A1/A2/A4/A9: exact stops, D10 frame advance, ground-truth stepping."""

    def test_frame_advance_is_the_provisional_d10_constant(self):
        """D10 is open until G1: the runner applies ONE provisional constant and says so in its runlog.

        V0-4 (NATIVE_STEP_RULE) settles the native read-back only. The probe vehicles at the COM meter
        moved 1 s late (test_clock_probe.test_vehicle_start_after_com_green_is_recorded), so nothing
        here claims the value follows from V0-4; the user decides D10 with the G1 evidence.
        """
        advance = rh.D10_FRAME_ADVANCE
        result = self.run_body('''
nativeClockPlans.Add "7", "serial|120.000000|12.000000|1111"
Check "simres1_advance", SignalClockPosition(7, 907, 119, 120), 67
simResSteps = 10
Obs150ApplyNativeFrameAdvance
Check "spec", nativeClockPlans("7"), "serial|120.000000|12.000000|1111|{advance}"
Check "obs150_advance", SignalClockPosition(7, 907, 119, 120), {position}
Check "non_native_sc", SignalClockPosition(8, 907, 119, 120), 66
'''.format(advance=advance, position=(907 + 119 + advance) % 120))
        self.assertEqual(re.findall(r'(?m)^Const OBS150_FRAME_ADVANCE = .*$', rh.source()),
                         [f'Const OBS150_FRAME_ADVANCE = {advance}'])
        lines = [line for line in result.stdout.splitlines() if line.startswith('SIGNAL_FRAME_ADVANCE=')]
        self.assertEqual(len(lines), 1, result.stdout)
        if advance == 0:
            self.assertIn(' source=probe_readback d10=open_pending_G1 ', lines[0])
            self.assertTrue(lines[0].endswith(' g1_check=com_head_lead_departure_t+0.1_or_t+1.1'), lines[0])
            self.assertNotIn('V0-4', lines[0])

    def test_frame_advance_refuses_another_simres(self):
        result = self.run_body('''
nativeClockPlans.Add "7", "serial|120.000000|12.000000|1111"
simResSteps = 1
Obs150ApplyNativeFrameAdvance
WScript.Echo "NOT_REJECTED"
''', expect=2)
        self.assertIn('ERROR=OBS150_FRAME_ADVANCE_SIMRES OBS150_FRAME_ADVANCE is the SimRes 10 value (D10); '
                      'network simres=1', result.stdout)
        self.assertNotIn('NOT_REJECTED', result.stdout)

    def test_stop_off_the_whole_second_stops_the_run(self):
        result = self.run_body(STARTUP + '''
obs150StopSec = 1
gMock.mSim.t10 = 10
gMockStopShift = 1
RunContinuousTo 150
WScript.Echo "NOT_REJECTED"
''', expect=13)
        self.assertIn('ERROR=OBS150_STOP_MISSED sim_sec=150 target=150 actual=150.1', result.stdout)

    def test_first_step_writes_the_empty_start_frame(self):
        self.run_body(STARTUP + '''
Obs150FirstStep
Check "stop", obs150StopSec, 1
Check "sim", gMock.mSim.AttValue("SimSec"), 1
Check "runs", gMock.mSim.runs, 1
''')
        frame = self.work / 'decisions' / 'lane_observations' / 'frame_000000.json'
        text = frame.read_bytes()
        oc.load_frame(frame, hashlib.sha256(text).hexdigest(), 0)

    def test_ground_truth_steps_between_scheduled_stops_only(self):
        self.run_body(STARTUP + '''
gMock.mSim.t10 = 1500
obs150StopSec = 150
gMock.mNet.mVehs.AddVehicle 11, 71, 1, 10.5, 36.0, 4.5, 1126, 1
gMock.mNet.mVehs.AddVehicle 12, 999, 1, 3.0, 36.0, 4.5, Null, Null
Obs150AdvanceTo 150, 180
Check "stop180", obs150StopSec, 180
Obs150AdvanceTo 180, 300
Check "stop300", obs150StopSec, 300
Check "no_continuous_inside", gMock.mSim.runs, 0
Obs150AdvanceTo 300, 450
Check "continuous_outside", gMock.mSim.runs, 1
Check "stop450", obs150StopSec, 450
''', env_extra={'RW_OBS150_GT': '150:300'})
        gt = self.work / 'decisions' / 'obs150_gt'
        meta = (gt / 'gt_meta.csv').read_text().splitlines()
        veh = (gt / 'gt_veh.csv').read_text().splitlines()
        sig = (gt / 'gt_sig.csv').read_text().splitlines()
        self.assertEqual(meta[0], 't10,sim_sec,veh_rows,sig_rows,step_wall_sec')
        self.assertEqual(len(meta), 1 + 1 + 1500)
        self.assertEqual([r.split(',')[0] for r in meta[1:3]], ['1500', '1501'])
        self.assertEqual(meta[-1].split(',')[0], '3000')
        self.assertEqual(veh[0], 't10,veh,link,lane,pos,rout_dec_no,route_no')
        self.assertEqual(len(veh), 1 + 1501)
        self.assertEqual(veh[1], '1500,11,71,1,10.5000000000000,1126,1')
        self.assertEqual(len(sig), 1 + 1500 * 8)
        self.assertEqual(sig[1:9], ['1500,5,1,RED', '1500,5,2,RED'] + [f'1500,1004,{g},RED' for g in range(1, 6)]
                         + ['1500,9106,1,RED'])

    def test_ground_truth_blank_signal_state_stops(self):
        for value, vartype in (('Empty', 0), ('Null', 1), ('" "', 8)):
            with self.subTest(value=value):
                shutil.rmtree(self.work / 'decisions', ignore_errors=True)    # each case starts a fresh run folder
                result = self.run_body(STARTUP + '''
gMock.mSim.t10 = 1500
obs150StopSec = 150
gMock.mNet.mScs.ItemByKey(1004).SGs.ItemByKey(3).state = {value}
Obs150AdvanceTo 150, 180
WScript.Echo "NOT_REJECTED"
'''.format(value=value), env_extra={'RW_OBS150_GT': '150:300'}, expect=13)
                self.assertIn(f'ERROR=OBS150_GT_SIGNAL_STATE sim_sec=150 sc=1004 sg=3 t10=1500 vartype={vartype}',
                              result.stdout)
                self.assertNotIn('NOT_REJECTED', result.stdout)

    def test_far_measurement_is_merged_not_scanned(self):
        self.run_body(STARTUP + '''
farMeasLinks("10643") = "R_F_E"
obs150K = Empty
Check "t1", FarMeasurementJson(), "{""interval_sec"": 150, ""freeway_exit_count"": null, ""link_volume_veh_h"": {""10643"": -1.000000}}"
obs150K = 2
gMock.mNet.mLinks.vol("10643|AVG:LinkEvalSegs\\Volume(Current,2,All)") = 812.5
Check "k2", FarMeasurementJson(), "{""interval_sec"": 150, ""freeway_exit_count"": null, ""link_volume_veh_h"": {""10643"": 812.500000}}"
''')

    def test_far_link_volume_never_reads_a_blank_as_zero(self):
        """CDbl(Empty) = 0 would be read as 'capacity 0'. obs150 writes -1, as the bundle writes null."""
        far = '{""interval_sec"": 150, ""freeway_exit_count"": null, ""link_volume_veh_h"": {""10643"": %s}}'
        cases = [('Empty', '-1.000000', 'null'), ('Null', '-1.000000', 'null'), ('"abc"', '-1.000000', 'null'),
                 ('-5.0', '-1.000000', 'null'), ('0.0', '0.000000', '0.00000000000000'),
                 ('812.5', '812.500000', '812.500000000000')]
        body = STARTUP + '''
farMeasLinks("10643") = "R_F_E"
obs150LinkEvalLinks.RemoveAll
obs150LinkEvalLinks("10643") = True
obs150K = 2
'''
        for n, (value, consumed, audit) in enumerate(cases):
            body += '''gMock.mNet.mLinks.vol("10643|AVG:LinkEvalSegs\\Volume(Current,2,All)") = {value}
Check "far_{n}", FarMeasurementJson(), "{far}"
Check "audit_{n}", Obs150LinkEvalJson(300), "{{""10643"":{audit}}}"
'''.format(value=value, n=n, far=far % consumed, audit=audit)
        # v1 (no obs150 mode) still reads the last completed interval exactly as before.
        body += '''obs150Mode = False
gMock.mNet.mLinks.vol("10643|AVG:LinkEvalSegs\\Volume(Current,Last,All)") = 700
Check "v1", FarMeasurementJson(), "{""interval_sec"": 150, ""freeway_exit_count"": 0, ""link_volume_veh_h"": {""10643"": 700.000000}}"
'''
        self.run_body(body)


BUNDLE = STARTUP + '''
Obs150VerifyDetectorTable
gMock.mNet.mDcms.AddDataCollectionMeasurement 910030
Obs150InstallDetectors
obs150EvalOutDir = fso.GetAbsolutePathName({eval_dir})
''' + EVALUATION + '''
Obs150WriteInstallRecord
Obs150FirstStep
Dim vehs, links, lanes, positions, speeds
gMock.mNet.mVehs.AddVehicle 21, 74, 1, 0.8, 80.0, 4.5, Null, Null
vehs = Array(21) : links = Array(74) : lanes = Array(1) : positions = Array(0.8) : speeds = Array(80.0)
{counts_t1}
Obs150BeginBundle 1
SaveText {out1}, Obs150Bundle(1, 1, vehs, links, lanes, positions, speeds)
InitializeComRampMeterControl
Check "meter_under_com", gMock.mNet.mScs.ItemByKey(9106).SGs.ItemByKey(1).com, True
RunContinuousTo 150
Dim mer
Set mer = fso.OpenTextFile({mer_path}, 8, False)
mer.Write {mer_rows}
mer.Close
gMockCurrentK = 1
{counts_k1}
gMock.mNet.mLinks.vol("10643|AVG:LinkEvalSegs\\Volume(Current,1,All)") = 812.4
gMock.mNet.mVehs.list.RemoveAll
gMock.mNet.mVehs.AddVehicle 31, 71, 1, 60.0, 30.0, 4.5, 1126, 2
gMock.mNet.mVehs.AddVehicle 32, 2, 3, 900.0, 90.0, 4.5, Null, Null
vehs = Array(31, 32) : links = Array(71, 2) : lanes = Array(1, 3) : positions = Array(60.0, 900.0) : speeds = Array(30.0, 90.0)
Obs150BeginBundle 150
SaveText {out150}, Obs150Bundle(150, 2, vehs, links, lanes, positions, speeds)
'''


class BundleTests(RunnerCase):
    """Plan A7: the whole obs150 bundle at t=1 and t=150, with the WP-B1 capture CLI."""

    def body(self, counts_k1=None):
        eval_dir = self.work / 'vissim_eval'
        eval_dir.mkdir()
        mer_path = eval_dir / 'net_001.mer'
        mer_path.write_bytes(rh.mer_header(self.rows, self.work / 'network' / 'net.inpx').encode('ascii'))
        # Window 1: 960001 twice (both in .mer), 960002 three times (the last one still in the
        # VISSIM buffer: a tail of 1), 960026 (source FW_E lane 1) once, and a network point.
        rows_text = ''.join([rh.mer_row(910030, 12.34, None, 5), rh.mer_row(960001, 100.10, None, 7),
                             rh.mer_row(960001, None, 100.95, 7), rh.mer_row(960002, 120.55, None, 8),
                             rh.mer_row(960001, 130.00, None, 9), rh.mer_row(960002, 140.00, 140.20, 10)])
        self.source_key = next(r.dcp_no for r in self.rows if r.role == 'source' and r.ref == 'FW_E')
        counts = counts_k1 or {960001: 2, 960002: 3, self.source_key: 1, 910030: 1}
        return BUNDLE.format(
            eval_dir=rh.vbs_string(eval_dir), mer_path=rh.vbs_string(mer_path), mer_rows=rh.vbs_string(rows_text)
            .replace('\n', '" & vbLf & "'),
            counts_t1='gMock.mNet.mDcms.SetCount 910030, 1, 0',
            counts_k1='\n'.join(f'gMock.mNet.mDcms.SetCount {k}, 1, {v}' for k, v in counts.items()),
            out1=rh.vbs_string(self.work / 'obs_1.json'), out150=rh.vbs_string(self.work / 'obs_150.json'))

    def test_bundles_pass_the_raw_contract(self):
        result = self.run_body(self.body())
        first, second = self.load('obs_1.json'), self.load('obs_150.json')
        for obs in (first, second):
            oc.validate_raw(obs, self.rows, expected_simres=10)
            bundle = oc.load_bundle({oc.RAW_STATE_KEY: obs})
            self.assertEqual(bundle.frame_end['time_s'], obs['sim_sec'])
        self.assertEqual(first['k'], None)
        self.assertEqual(first['open_interval'], {'k': 1, 'end_s': 1})
        self.assertEqual(first['frames']['previous']['path'], 'lane_observations/frame_000000.json')
        self.assertEqual(first['linkeval_volume_veh_h'], {'10481': None, '10483': None, '10643': None, '10682': None,
                                                          '10479': None, '10485': None, '10648': None, '10650': None,
                                                          '10565': None, '10570': None})
        self.assertEqual(second['k'], 1)
        self.assertEqual(second['window'], {'start_s': 0, 'end_s': 150})
        self.assertEqual(second['frames']['previous'], first['frames']['previous'])
        self.assertEqual(second['frames']['current']['vehicles'], 2)
        self.assertEqual(second['detectors']['960001'], 2)
        self.assertEqual(second['detectors']['960002'], 3)
        self.assertEqual(second['detectors_cum']['960002'], 3)
        self.assertEqual(second['mer']['records_cum_by_dcp']['960001'], 2)
        self.assertEqual(second['mer']['records_cum_by_dcp']['960002'], 2)
        self.assertEqual(second['mer']['max_t_any'], 140.2)
        self.assertEqual(second['rule_crosscheck'], {'910030': 1})
        self.assertEqual(second['linkeval_volume_veh_h']['10643'], 812.4)
        self.assertIsNone(second['linkeval_volume_veh_h']['10565'])
        self.assertEqual(second['source_cumulative_vehs'], {'FW_E': 1, 'FW_W': 0})
        self.assertIs(second['detectors_last_equal'], True)
        self.assertEqual(second['ground_truth_windows'], [])
        self.assertEqual(second['directory'], str(self.work / 'decisions'))
        self.assertEqual(second['signal_log']['events'][:2], [[1, '9106', '1', 'own', True],
                                                               [1, '9106', '1', 'write', 'GREEN']])
        install = self.work / 'decisions' / 'obs150' / 'obs150_install.json'
        self.assertEqual(second['install_record']['sha256'], hashlib.sha256(install.read_bytes()).hexdigest())
        self.assertIn('OBS150_BUNDLE sim_sec=150 vehicles=2 signal_events=2', result.stdout)

    def test_last_interval_mismatch_stops(self):
        body = self.body().replace('Obs150BeginBundle 150', 'gMockLastShift = 1\nObs150BeginBundle 150')
        result = self.run_body(body + 'WScript.Echo "NOT_REJECTED"\n', expect=13)
        self.assertIn('ERROR=OBS150_DETECTORS_LAST_MISMATCH sim_sec=150', result.stdout)

    def test_empty_count_stops(self):
        body = self.body().replace('Obs150BeginBundle 150', 'gMockNoVehs = "960003"\nObs150BeginBundle 150')
        result = self.run_body(body + 'WScript.Echo "NOT_REJECTED"\n', expect=13)
        self.assertIn('ERROR=OBS150_DETECTOR_VALUE sim_sec=150 measurement 960003 vartype=0', result.stdout)

    def test_second_bundle_at_the_same_second_is_refused(self):
        body = self.body() + 'Obs150BeginBundle 150\nWScript.Echo "NOT_REJECTED"\n'
        script = rh.build(self.network + '\n' + body, work=self.work)
        result = rh.run_vbs(script, work=self.work, env=rh.obs150_env(self.csv, self.sha))
        self.assertIn('obs150 bundle already written', result.stderr)
        self.assertNotIn('NOT_REJECTED', result.stdout)


class RealTableTests(RunnerCase):
    """The WP-B2 table in N31D parses the same in VBS and in the contract parser."""

    def test_real_detector_table(self):
        table = rh.ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'obs150' / 'obs150_detectors_v2.csv'
        if not table.is_file():
            self.skipTest('WP-B2 detector table not generated yet')
        try:
            rows, sha = oc.read_detector_csv(table)
        except oc.ObsContractError as error:
            self.skipTest(f'WP-B2 table does not parse yet: {error}')
        heads = sorted({int(oc.parse_head_ref(r.ref)[1]) for r in rows if r.role in ('head', 'meter_head')})
        linkeval = list(dict.fromkeys(r.ref for r in rows if r.role in ('off_entry', 'headfree')))
        links = sorted({r.link for r in rows})
        self.run_body(f'''
obs150DetectorsPath = {rh.vbs_string(table)}
Obs150LoadDetectorCsv
Check "rows", UBound(obs150Rows) + 1, {len(rows)}
Check "heads", Join(Obs150SortedKeys(obs150HeadScs), ","), "{','.join(map(str, heads))}"
Check "linkeval", Join(obs150LinkEvalLinks.Keys, ","), "{','.join(linkeval)}"
Check "links", Join(Obs150SortedKeys(obs150GtLinks), ","), "{','.join(map(str, links))}"
Check "last_key", obs150Rows(UBound(obs150Rows))(0), {rows[-1].dcp_no}
Check "last_pos", obs150Rows(UBound(obs150Rows))(5), "{format(rows[-1].pos, '.6f')}"
''', env=rh.obs150_env(table, sha))


if __name__ == '__main__':
    unittest.main()
