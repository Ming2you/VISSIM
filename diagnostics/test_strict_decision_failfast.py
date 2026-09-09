"""Imported current watchdog gate -> current VBS decision, fake VISSIM only."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from diagnostics import test_profile_runner_invocation as harness
from diagnostics.review_fixtures import fixture_path
ROOT = harness.ROOT
WRAPPER = ROOT/'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'


def psq(value):
    return "'"+str(value).replace("'","''")+"'"


@unittest.skipUnless(sys.platform=='win32','Requires PowerShell/cscript, never live VISSIM')
class StrictDecisionFailFastTests(unittest.TestCase):
    def run_case(self,tmp,config,failure='missing',controller='wu-link',*,parent=None):
        script=harness.build_harness(tmp,controller,'ramp_profile_config_c10639_g5.json',failure='missing' if failure in {'nonzero','valid'} else failure)
        # Failure comes from a real subprocess, not from replacing RunCapture3.
        if failure=='nonzero':
            (tmp/'invalid_child.py').write_text('raise SystemExit(7)\n',encoding='utf-8')
        elif failure=='valid':
            fixture=fixture_path(ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910/action_000900.csv')
            (tmp/'invalid_child.py').write_text('import shutil,sys\n'+
                f'shutil.copyfile({str(fixture)!r},sys.argv[sys.argv.index("--out-action-csv")+1])\n'+
                f'shutil.copyfile({str(fixture.with_suffix(".json"))!r},sys.argv[sys.argv.index("--out-action-json")+1])\n',encoding='utf-8')
        data=script.read_text(encoding='utf-16')
        data=data.replace('RunControllerDecision 1\n','RunControllerDecision 900\n')
        data=data.replace('WScript.Echo "UNEXPECTED_CONTINUATION"','WScript.Echo "COUNTS=" & decisionsOk & "," & decisionsFailed\nWScript.Echo "UNEXPECTED_CONTINUATION"')
        script.write_text(data,encoding='utf-16')
        tuning=tmp/'case.json'
        tuning.write_text(json.dumps(config),encoding='utf-8')
        if parent is not None:(tmp/'parent.json').write_text(json.dumps(parent),encoding='utf-8')
        current=WRAPPER.read_text(encoding='utf-8')
        gates=re.findall(r'(?ms)^# Strict area accounting must stop.*?^"RW_DECISION_FAIL_FAST=.*?\n',current)
        self.assertEqual(len(gates),1,'Current watchdog must contain exactly one strict gate')
        gate=gates[0]
        driver=tmp/'invoke.ps1'
        driver.write_text('$ErrorActionPreference="Stop"\n$Tuning='+psq(tuning)+'\n'+
            'function Resolve-RepoPath([string]$PathValue) { return $PathValue }\n'+gate+
            '\n& cscript.exe //nologo '+psq(script)+'\nexit $LASTEXITCODE\n',encoding='utf-8-sig')
        env=dict(os.environ,RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',
                 RW_SIGNAL_READBACK_SEC='1',RW_SIGNAL_WRITE_ON_CHANGE='0')
        return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(driver)],
                              env=env,cwd=ROOT,capture_output=True,text=True,errors='replace',timeout=30)

    def test_strict_on_stops_nonzero_missing_and_incomplete_child_output(self):
        for failure,error in [('nonzero','DECISION_EXIT_NONZERO'),('missing','ACTION_CSV_MISSING'),('incomplete','ACTION_CSV_INCOMPLETE')]:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as directory:
                result=self.run_case(Path(directory),{'control_area_objective':{'enabled':True}},failure)
                self.assertEqual(result.returncode,3,result.stdout+result.stderr)
                self.assertIn('RW_DECISION_FAIL_FAST=1',result.stdout)
                self.assertIn('ERROR='+error,result.stdout)
                self.assertIn('ERROR=STRICT_DECISION_FAILED',result.stdout)
                self.assertIn('FAKE_SIM_STOP',result.stdout)
                self.assertNotIn('UNEXPECTED_CONTINUATION',result.stdout)

    def test_off_absent_and_null_preserve_existing_continuation_and_clear_stale_env(self):
        for config in ({},{'control_area_objective':{'enabled':False}},{'control_area_objective':None}):
            with self.subTest(config=config),tempfile.TemporaryDirectory() as directory:
                result=self.run_case(Path(directory),config)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('RW_DECISION_FAIL_FAST=0',result.stdout)
                self.assertIn('UNEXPECTED_CONTINUATION',result.stdout)
                self.assertNotIn('FAKE_SIM_STOP',result.stdout)

    def test_inherited_enabled_and_explicit_disabled_follow_effective_tuning(self):
        for child,expected in [({'extends':'parent.json'},3),({'extends':'parent.json','control_area_objective':{'beta_sec':0}},3),
                               ({'extends':'parent.json','control_area_objective':{'enabled':False}},0)]:
            with self.subTest(child=child),tempfile.TemporaryDirectory() as directory:
                result=self.run_case(Path(directory),child,parent={'control_area_objective':{'enabled':True}})
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr)

    def test_existing_diagnostic_stop_keeps_its_original_error_label(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_case(Path(directory),{},controller='diagnostic-ramp-profile')
            self.assertEqual(result.returncode,3,result.stdout+result.stderr)
            self.assertIn('ERROR=DIAGNOSTIC_DECISION_FAILED',result.stdout)
            self.assertNotIn('ERROR=STRICT_DECISION_FAILED',result.stdout)

    def test_strict_success_applies_the_valid_real_csv_and_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_case(Path(directory),{'control_area_objective':{'enabled':True}},failure='valid')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('COUNTS=1,0',result.stdout)
            self.assertIn('UNEXPECTED_CONTINUATION',result.stdout)
            self.assertNotIn('FAKE_SIM_STOP',result.stdout)

    def test_cyclic_tuning_stops_before_starting_a_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_case(Path(directory),{'extends':'case.json'})
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Cyclic tuning extends',result.stderr)
            self.assertNotIn('CONTROLLER_DECISION',result.stdout)


if __name__=='__main__':unittest.main()
