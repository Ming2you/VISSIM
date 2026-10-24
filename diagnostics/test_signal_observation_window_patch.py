"""Test installed Python and exact production VBS/PS functions with fake COM.

No production file is written, no VISSIM object is created, no MPC is invoked.
The historical filename is retained; no proposal builder or patch is loaded.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
OFF_REFERENCE_COMMIT = '109afeef5da0fded77b6b68848d271a68743933e'
OPTIONS = {'enabled': True, 'min_green_sec': 30.0, 'min_crossings': 5.0}


def save_previous(path, metadata):
    action_metadata = {**metadata, 'sim_sec': metadata['head_observation_snapshot_sec']}
    path.write_text(json.dumps({'metadata': action_metadata, 'run_provenance': {'run_id': 'test-run'}}))


def installed_sources():
    names = ('scripts/run_real_world_stackelberg_controller.vbs',
             'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1',
             'evaluation/controllers/vissim_stackelberg_adapter.py',
             'evaluation/controllers/signal_head_observation.py')
    return {name: (ROOT / name).read_text(encoding='utf-8-sig') for name in names}


def procedure(source, name):
    match = re.search(r'(?im)^(Sub|Function) ' + re.escape(name) + r'\b', source)
    assert match, name
    end = re.search(r'(?im)^End ' + match[1] + r'\s*$', source[match.start():])
    return source[match.start():match.start() + end.end()] + '\n'


def run_vbs(source):
    with tempfile.TemporaryDirectory(prefix='signal-head-installed-') as directory:
        path = Path(directory) / 'fake_observation.vbs'
        path.write_bytes(source.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-16'))
        result = subprocess.run(['cscript.exe', '//nologo', str(path)], text=True, encoding='mbcs', errors='replace',
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
        if result.returncode:
            raise AssertionError(result.stdout)
        return result.stdout


class InstalledConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import signal_head_observation
        cls.sources = installed_sources()
        cls.module = signal_head_observation
        if Path(cls.module.__file__).resolve() != (ROOT / 'evaluation/controllers/signal_head_observation.py').resolve():
            raise AssertionError('Installed consumer import resolved outside this checkout')

    def fixture(self, directory, *, green=45, count=10, start=750, end=900):
        network = Path(directory) / 'network.inpx'
        network.write_text('<network><signalHeads><signalHead no="1" lane="66 1" pos="100" sg="1004 8" allVehTypes="true"/></signalHeads></network>', encoding='utf-8')
        cfg = types.SimpleNamespace(network=types.SimpleNamespace(movement_capacity_veh_h=200,
                    movement_capacity_by_movement_veh_h={'through': 200.0}))
        plan = {'controllers': {'1004': {'phase_signal_groups': {'p1': ['8']}}}}
        head = {'head_id': '1', 'link': '66', 'lane': 1, 'position_m': 100.0, 'sc': '1004', 'sg': '8',
                'green_sec': green, 'crossings': count, 'qualified_crossings': count,
                'native_sec': end-start, 'controlled_sec': 0}
        raw = {'network_path': str(network), 'sim_sec': end, 'local_observation': {
            'signal_observation_window': {'schema': 'physical-head-window/v1', 'start_sec': start, 'end_sec': end,
              'cadence_sec': 1, 'transition_count': end-start, 'clock_complete': True,
              'exposure_method': 'actual_left_step_hold', 'heads': [head], 'unknown_links': {}}}}
        tuning = Path(directory)/'tuning.json'
        tuning.write_text(json.dumps({'urban':{'capacity':{'measured':True,'head_observation':OPTIONS}}}))
        def evidence(path):
            return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        source = evidence(tuning)
        manifest = {'run_id': 'test-run', 'files': {'tuning': source, 'network': evidence(network)},
                    'env': {'RW_SIGNAL_OBSERVATION':'1', 'RW_QUEUE_WINDOW':'1'},
                    'signal_observation': {'config_key':'urban.capacity.head_observation',
                                           'options':OPTIONS,'config_chain':[source]}}
        provenance = Path(directory)/'manifest.json'
        provenance.write_text(json.dumps(manifest))
        raw['run_provenance'] = {'run_id':'test-run','manifest_path':str(provenance)}
        raw['local_observation']['signal_observation_window']['config_sha256'] = source['sha256']
        def distribute(cfg, groups, estimates, caps):
            if ('66', 'p1') in estimates:
                caps['through'] = estimates['66', 'p1']; return 1
            return 0
        return cfg, raw, plan, distribute

    def test_two_nonoverlapping_windows_required_and_prior_carried_without_data(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg, raw, plan, distribute = self.fixture(directory)
            untouched = copy.deepcopy(raw)
            first = self.module.install(cfg, raw, None, {'through': 200.0}, plan, distribute, OPTIONS)
            self.assertEqual(raw, untouched)
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'], 200)
            previous = Path(directory)/'previous.json'; save_previous(previous, first)
            raw['sim_sec'] = 1050; window = raw['local_observation']['signal_observation_window']
            window.update(start_sec=900, end_sec=1050)
            window['heads'][0]['crossings'] = window['heads'][0]['qualified_crossings'] = 20
            second = self.module.install(cfg, raw, previous, {'through': 200.0}, plan, distribute, OPTIONS)
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'], 800)
            self.assertEqual(second['head_observation_groups_updated'], 1)
            save_previous(previous, second)
            raw['sim_sec'] = 1200
            raw['local_observation'] = {}
            third = self.module.install(cfg, raw, previous, {'through': 200.0}, plan, distribute, OPTIONS)
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'], 800)
            self.assertEqual(third['head_observation_missing_window'], 1)
            self.assertEqual(untouched['local_observation']['signal_observation_window']['end_sec'], 900)

    def test_no_model_members_is_zero_installation_not_claimed_success(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg, raw, plan, _ = self.fixture(directory)
            def no_members(cfg, groups, estimates, caps):
                return 0
            meta = self.module.install(cfg, raw, None, {'through': 619.59}, plan, no_members, OPTIONS)
            self.assertEqual(meta['head_observation_groups_updated'], 0)
            self.assertEqual(meta['head_observation_no_model_members'], 1)
            self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h, {'through': 200.0})

    def test_prior_foreign_run_future_overlap_and_changed_source_are_discarded(self):
        for change in ('run', 'future', 'equal', 'overlap', 'config', 'geometry'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                cfg, raw, plan, dist = self.fixture(directory)
                prior = Path(directory)/'previous.json'
                first = self.module.install(cfg, raw, None, {'through':200}, plan, dist, OPTIONS)
                save_previous(prior, first)
                raw['sim_sec'] = 1050
                raw['local_observation']['signal_observation_window'].update(start_sec=900,end_sec=1050)
                second = self.module.install(cfg, raw, prior, {'through':200}, plan, dist, OPTIONS)
                self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'],800)
                save_previous(prior, second)
                previous = json.loads(prior.read_text())
                raw['sim_sec'] = 1200
                window = raw['local_observation']['signal_observation_window']
                window.update(start_sec=1050,end_sec=1200)
                if change == 'run': previous['run_provenance']['run_id'] = 'another-run'
                if change in ('future','equal'):
                    invalid_time = 1350 if change == 'future' else 1200
                    previous['metadata']['sim_sec'] = invalid_time
                    previous['metadata']['head_observation_snapshot_sec'] = invalid_time
                    for key in previous['metadata']:
                        if key.startswith('head_candidate_end_'): previous['metadata'][key] = invalid_time
                if change == 'overlap':
                    window.update(start_sec=1000,transition_count=200)
                    window['heads'][0]['native_sec'] = 200
                else:
                    raw['local_observation'] = {}  # Missing data must never bypass prior binding.
                prior.write_text(json.dumps(previous))
                if change in ('config','geometry'):
                    manifest_path = Path(raw['run_provenance']['manifest_path'])
                    manifest = json.loads(manifest_path.read_text())
                    name = 'tuning' if change == 'config' else 'network'
                    source = Path(manifest['files'][name]['path'])
                    source.write_text(source.read_text()+'\n')
                    digest = hashlib.sha256(source.read_bytes()).hexdigest()
                    manifest['files'][name]['sha256'] = digest
                    if change == 'config': manifest['signal_observation']['config_chain'][0]['sha256'] = digest
                    manifest_path.write_text(json.dumps(manifest))
                cfg.network.movement_capacity_by_movement_veh_h = {'through':200}
                meta = self.module.install(cfg, raw, prior, {'through':200}, plan, dist, OPTIONS)
                self.assertEqual(meta['head_observation_prior_discarded'],1)
                self.assertEqual(meta['head_observation_groups_carried'],0)
                self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'],200)

    def test_short_spike_zero_nonfinite_and_ambiguous_data_not_updates(self):
        for green, count in ((1, 2), (0, 10), (45, 0)):
            with self.subTest(green=green, count=count), tempfile.TemporaryDirectory() as directory:
                cfg, raw, plan, dist = self.fixture(directory, green=green, count=count)
                self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)
                self.assertEqual(cfg.network.movement_capacity_by_movement_veh_h['through'], 200)
        for bad in (float('nan'), float('inf'), -1):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                cfg, raw, plan, dist = self.fixture(directory, green=bad)
                with self.assertRaises(ValueError): self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)

    def test_unknown_geometry_duplicate_or_stale_window_cannot_be_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg, raw, plan, dist = self.fixture(directory)
            window = raw['local_observation']['signal_observation_window']
            window['unknown_links'] = {'66': 1}
            meta = self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)
            self.assertEqual(meta['head_observation_unknown_link'], 1)
            window['unknown_links'] = {}; window['heads'][0]['position_m'] = 101
            with self.assertRaises(ValueError): self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)
            window['heads'][0]['position_m'] = 100; window['heads'].append(copy.deepcopy(window['heads'][0]))
            with self.assertRaises(ValueError): self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)
            window['heads'].pop(); window['end_sec'] = 899
            with self.assertRaises(ValueError): self.module.install(cfg, raw, None, {'through': 200.0}, plan, dist, OPTIONS)

    def test_adapter_off_is_original_ast_and_scheduler_closes_before_decision(self):
        fixture = ROOT / 'diagnostics/fixtures/install_measured_movement_capacity_109afee.py'
        proof = json.loads(fixture.with_suffix('.json').read_text(encoding='utf-8'))
        data = fixture.read_bytes()
        self.assertEqual(proof['commit'], OFF_REFERENCE_COMMIT)
        self.assertEqual(hashlib.sha256(data).hexdigest(), proof['fixture_sha256'])
        original = ast.parse(data.decode('utf-8'))
        self.assertEqual(len(original.body), 1)
        self.assertEqual(hashlib.sha256(ast.dump(original.body[0]).encode('utf-8')).hexdigest(), proof['normalized_ast_sha256'])
        patched = ast.parse(self.sources['evaluation/controllers/vissim_stackelberg_adapter.py'])
        before = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == 'install_measured_movement_capacity')
        after = next(n for n in patched.body if isinstance(n, ast.FunctionDef) and n.name == before.name)
        added = [n for n in after.body if isinstance(n, ast.If) and 'head_observation' in ast.unparse(n.test)]
        self.assertEqual(len(added), 2)
        for node in added: after.body.remove(node)
        self.assertEqual(ast.dump(before), ast.dump(after))
        vbs = self.sources['scripts/run_real_world_stackelberg_controller.vbs']
        step = procedure(vbs, 'RunStepwiseMode')
        self.assertLess(step.index('CollectHeadObservation stepNo'), step.index('RunControllerDecision stepNo'))
        self.assertLess(step.index('SealHeadSignalStates stepNo'), step.index('LogStateCsv stepNo'))
        write = procedure(vbs, 'WriteStateJson')
        self.assertLess(write.index('ts.Close'), write.index('ResetHeadObservation simSec'))
        self.assertIn('If obsEnabled And resetWindows Then', write)
        self.assertIn('If scanOk And Not obsEnabled Then', procedure(vbs, 'LogStateCsv'))

    def test_config_provenance_source_changes_and_quality_validation(self):
        for value in (True, None, {}, {'enabled':'true'}, {'enabled':True},
                      {'enabled':True,'min_green_sec':'30','min_crossings':5},
                      {'enabled':True,'min_green_sec':0,'min_crossings':5}):
            with self.subTest(value=value), self.assertRaises((ValueError, KeyError)):
                self.module.settings(value)
        self.assertEqual(self.module.settings({'enabled':False}), {'enabled':False})
        with tempfile.TemporaryDirectory() as directory:
            cfg, raw, plan, dist = self.fixture(directory)
            original = copy.deepcopy(raw)
            raw['local_observation']['signal_observation_window']['config_sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'collector/consumer'):
                self.module.install(cfg, raw, None, {'through':200.0}, plan, dist, OPTIONS)
            raw = original
            path = Path(raw['run_provenance']['manifest_path'])
            manifest = json.loads(path.read_text())
            manifest['signal_observation']['options']['min_green_sec'] = 31
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'configuration mismatch'):
                self.module.install(cfg, raw, None, {'through':200.0}, plan, dist, OPTIONS)
            manifest['signal_observation']['options'] = OPTIONS
            path.write_text(json.dumps(manifest))
            (Path(directory)/'tuning.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                self.module.install(cfg, raw, None, {'through':200.0}, plan, dist, OPTIONS)

    def test_watchdog_config_only_transport_inheritance_and_launch_revalidation(self):
        source = self.sources['scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1']
        start = source.index('function Read-HeadObservationSettings(')
        end = source.index('function Read-ControlAreaObjectiveEnabled(', start)
        # Execute only the two installed pure config functions, never the watchdog body.
        functions = source[start:end]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'base.json').write_text(json.dumps({'urban':{'capacity':{'measured':True,'head_observation':OPTIONS}}}))
            (root/'child.json').write_text(json.dumps({'extends':'base.json','urban':{'capacity':{'head_observation':{'min_crossings':7}}}}))
            (root/'off.json').write_text(json.dumps({'extends':'base.json','urban':{'capacity':{'head_observation':{'enabled':False}}}}))
            (root/'absent.json').write_text('{}')
            (root/'invalid.json').write_text(json.dumps({'urban':{'capacity':{'head_observation':True}}}))
            (root/'missing.json').write_text(json.dumps({'urban':{'capacity':{'measured':True,'head_observation':{'enabled':True}}}}))
            (root/'disabled_measured.json').write_text(json.dumps({'extends':'base.json','urban':{'capacity':{'measured':False}}}))
            code = ('param([string]$Fixture)\n$ErrorActionPreference="Stop"\n'
                    'Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1")\n') + functions + r'''
function Assert($condition,$message) { if (-not $condition) { throw $message } }
$child = Join-Path $Fixture 'child.json'
$settings = Read-HeadObservationSettings $child
Assert ($settings.options.min_green_sec -eq 30 -and $settings.options.min_crossings -eq 7) 'inheritance differs'
Assert ($settings.config_chain.Count -eq 2) 'chain provenance missing'
$env:RW_SIGNAL_OBSERVATION='0'; $env:RW_QUEUE_WINDOW='0'
Set-HeadObservationTransport $child $settings
Assert ($env:RW_SIGNAL_OBSERVATION -eq '1' -and $env:RW_QUEUE_WINDOW -eq '1') 'enabled config did not set transport'
Assert ($env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256 -eq $settings.config_chain[0].sha256) 'collector source hash absent'
foreach ($name in @('absent.json','off.json')) {
  $path=Join-Path $Fixture $name
  $env:RW_SIGNAL_OBSERVATION='1'; $env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256='untrusted'
  Set-HeadObservationTransport $path (Read-HeadObservationSettings $path)
  Assert ($env:RW_SIGNAL_OBSERVATION -eq '0' -and [string]::IsNullOrEmpty($env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256)) 'inherited env activated OFF'
}
foreach ($name in @('invalid.json','missing.json','disabled_measured.json')) {
  $failed=$false
  try { Read-HeadObservationSettings (Join-Path $Fixture $name) | Out-Null } catch { $failed=$true }
  Assert $failed ('invalid config accepted: '+$name)
}
[IO.File]::WriteAllText((Join-Path $Fixture 'base.json'), '{}')
$failed=$false
try { Set-HeadObservationTransport $child $settings } catch { $failed=$true }
Assert $failed 'changed inherited source accepted at launch'
'CONFIG_TRANSPORT_PASS'
'''
            script = root/'config_only.ps1'; script.write_text(code,encoding='utf-8-sig')
            result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(root)],
                                    text=True,encoding='mbcs',errors='replace',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('CONFIG_TRANSPORT_PASS', result.stdout)
        self.assertLess(source.index('Set-HeadObservationTransport $Tuning $headObservation'), source.index('$rwEnv ='))
        launch = source.index('  Set-HeadObservationTransport $Tuning $headObservation')
        self.assertLess(launch, source.index('$proc = Start-Process'))
        self.assertIn('$provenance.signal_observation = $headObservation', source)

    def test_actual_vbs_head_functions_bypass_boundary_duplicate_and_reset(self):
        vbs = self.sources['scripts/run_real_world_stackelberg_controller.vbs']
        names = ('ResetHeadObservation', 'HeadForLane', 'CountHeadCrossing', 'ObserveHeadTransition',
                 'ObservationNumbersJson', 'HeadObservationJson', 'AddDictNumber', 'DictNumber')
        code = '''Dim obsHeads, obsHeadLanes, obsHeadRoads, obsConnectors, obsHeld, obsActual
Dim obsCross, obsQualified, obsGreen, obsUnknown, obsBypass, obsSeenVehicleHead
Dim obsConfigSha256, obsNativeSec, obsControlledSec, obsUnverifiedSec, obsClockComplete, obsWindowStart, obsTransitions, obsFrameSec
'''+ '\n'.join(procedure(vbs, n) for n in names)
        code += '''
Function Num(v): Num=CStr(v): End Function
Function JsonDoubleInvariant(v): JsonDoubleInvariant=CStr(v): End Function
Function JsonEscape(v): JsonEscape=CStr(v): End Function
Sub Check(ok, detail)
 If Not ok Then Err.Raise 513,,detail
End Sub
Set obsHeads=CreateObject("Scripting.Dictionary")
Set obsHeadLanes=CreateObject("Scripting.Dictionary")
Set obsHeadRoads=CreateObject("Scripting.Dictionary")
Set obsConnectors=CreateObject("Scripting.Dictionary")
Set obsHeld=CreateObject("Scripting.Dictionary")
Set obsActual=CreateObject("Scripting.Dictionary")
obsHeads.Add "h1",Array("66",1,100,"1","2")
obsHeads.Add "h2",Array("66",2,101,"1","2")
obsHeadLanes.Add "66|1","h1": obsHeadLanes.Add "66|2","h2"
obsHeadRoads.Add "66",True
obsConnectors.Add "9",Array("66",1,90,"10",1)
obsHeld.Add "1-2",Array("GREEN",False,True)
obsActual.Add "1-2",Array("GREEN",False,True)
ResetHeadObservation 750
ObserveHeadTransition 1,Array("66",1,85),Array("9",1,3),True
Check DictNumber(obsBypass,"66")=1,"pre-head bypass"
Check obsCross.Count=0,"bypass must not count at head"
ObserveHeadTransition 2,Array("66",1,99),Array("66",1,100),True
Check DictNumber(obsCross,"h1")=1,"head bracket"
Check DictNumber(obsQualified,"h1")=1,"stable green bracket"
ObserveHeadTransition 2,Array("66",2,100.5),Array("66",2,102),True
Check DictNumber(obsCross,"h2")=0,"same vehicle must not count at another lane head"
Check DictNumber(obsUnknown,"66")=1,"duplicate head ambiguity"
obsActual("1-2")=Array("RED",False,True)
ObserveHeadTransition 3,Array("66",1,99),Array("66",1,101),True
Check DictNumber(obsCross,"h1")=2,"boundary crossing remains observable"
Check DictNumber(obsQualified,"h1")=1,"boundary bracket excluded from lower bound"
ObserveHeadTransition 4,Array("66",1,99),Empty,False
Check DictNumber(obsUnknown,"66")=2,"missing vehicle is unresolved"
obsFrameSec=900: obsTransitions=150: obsGreen("h1")=45
snapshot=HeadObservationJson(900)
Check obsTransitions=150,"audit read must not reset"
Check DictNumber(obsGreen,"h1")=45,"audit read green unchanged"
ResetHeadObservation 900
Check obsFrameSec=900,"reset preserves endpoint"
Check obsHeld.Count=1,"reset preserves held actual signal"
Check obsTransitions=0,"reset clears only window counters"
WScript.Echo "HEAD_FUNCTIONS_PASS"
'''
        self.assertIn('HEAD_FUNCTIONS_PASS', run_vbs(code))

    def test_actual_vbs_verified_table_cache_one_bulk_capture_per_timestamp(self):
        vbs = self.sources['scripts/run_real_world_stackelberg_controller.vbs']
        code = '''Dim obsEnabled,obsTableValid,obsTableSec,obsTables,obsTableMeta,obsBulkReads,obsCacheHits,bulkCalls,Vissim
obsEnabled=True: obsTableValid=False: bulkCalls=0: obsBulkReads=0: obsCacheHits=0
Class FakeVehicles
 Public FakeCount
 Public Property Get Count(): Count=FakeCount: End Property
 Public Function GetMultiAttValues(name)
  Dim table(0,1)
  bulkCalls=bulkCalls+1
  If FakeCount=0 Then
   GetMultiAttValues=Empty
  Else
   table(0,0)=1: table(0,1)=1
   GetMultiAttValues=table
  End If
 End Function
End Class
Class FakeNet
 Public Vehicles
 Private Sub Class_Initialize(): Set Vehicles=New FakeVehicles: End Sub
End Class
Class FakeSimulation
 Public Current
 Public Function AttValue(name): AttValue=Current: End Function
End Class
Class FakeVissim
 Public Net,Simulation
 Private Sub Class_Initialize()
  Set Net=New FakeNet: Set Simulation=New FakeSimulation
 End Sub
End Class
Function TryNonnegativeLongVariant(v,ByRef result): result=CLng(v): TryNonnegativeLongVariant=True: End Function
Function TryFiniteNonnegativeDouble(v,ByRef result): result=CDbl(v): TryFiniteNonnegativeDouble=True: End Function
Function IsB1aEmptyTableResult(v): IsB1aEmptyTableResult=IsEmpty(v): End Function
Sub PerfCount(name,amount): End Sub
Sub RecordVehicleCaptureFailure(kind,detail): Err.Raise 513,,kind&detail: End Sub
Sub Check(ok,detail): If Not ok Then Err.Raise 513,,detail
End Sub
'''+procedure(vbs, 'TryExact2DTableBounds')+procedure(vbs, 'ReadVerifiedVehicleTables')+'''
Set Vissim=New FakeVissim
Vissim.Net.Vehicles.FakeCount=0: Vissim.Simulation.Current=750
ok=ReadVerifiedVehicleTables(750,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
Check ok And bulkCalls=4,"first capture requires four bulk fields"
ok=ReadVerifiedVehicleTables(750,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
Check ok And bulkCalls=4 And obsCacheHits=1,"decision/log reuse must not scan vehicles again"
Vissim.Simulation.Current=751
ok=ReadVerifiedVehicleTables(751,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
Check ok And bulkCalls=8,"next step must create new physical capture"
Vissim.Net.Vehicles.FakeCount=1
On Error Resume Next
ok=ReadVerifiedVehicleTables(751,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
failure=Err.Number: Err.Clear
On Error GoTo 0
Check failure<>0,"stale same-time cache binding must reject"
Vissim.Simulation.Current=752
ok=ReadVerifiedVehicleTables(752,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
Check ok And bulkCalls=12 And n(0,1)=1,"nonempty 2D bulk capture"
ok=ReadVerifiedVehicleTables(752,n,l,p,s,cb,ca,tb,ta,lo,hi,k,v)
Check ok And bulkCalls=12 And n(0,1)=1,"nested 2D array cache reuse"
WScript.Echo "TABLE_CACHE_PASS"
'''
        self.assertIn('TABLE_CACHE_PASS', run_vbs(code))

    def test_actual_collector_native_to_controlled_and_reset_no_duplicate_step(self):
        vbs = self.sources['scripts/run_real_world_stackelberg_controller.vbs']
        names = ('ResetHeadObservation', 'HeadForLane', 'CountHeadCrossing', 'ObserveHeadTransition',
                 'CollectHeadObservation', 'CaptureHeadSignalStates', 'SealHeadSignalStates',
                 'ObservationSignalReadback', 'ObservationNumbersJson', 'HeadObservationJson', 'AddDictNumber', 'DictNumber',
                 'HeadObservationTime', 'TryFiniteNonnegativeDouble', 'TryB1aFiniteDouble')
        declaration = procedure(vbs, 'ScanVehicleState').splitlines()
        signature = []
        for line in declaration:
            signature.append(line)
            if not line.rstrip().endswith('_'): break
        scan = '\n'.join(signature)+'''
 scans=scans+1: scanOk=True
 recordVehNos=Array(1): recordLinkNos=Array(66): recordLaneNos=Array(1)
 recordPositions=Array(97+2*expectedSimSec)
 Set linkCounts=CreateObject("Scripting.Dictionary"): linkCounts.Add "66",1
 Set linkStopped=CreateObject("Scripting.Dictionary")
End Sub
'''
        code = '''Dim obsEnabled,obsHeads,obsHeadLanes,obsHeadRoads,obsConnectors,obsHeld,obsActual,obsPrevious
Dim obsCross,obsQualified,obsGreen,obsUnknown,obsBypass,obsSeenVehicleHead,obsNativeSec,obsControlledSec,obsUnverifiedSec
Dim obsClockComplete,obsWindowStart,obsTransitions,obsFrameSec,obsSignalSec,obsHeldSec,signalTraceSimSec
Dim RW_SIGNAL_SCS,RW_FW_E_SEG_BOUNDS,RW_FW_W_SEG_BOUNDS,winDepart,scans,queueSamples,farSamples,fakeState,fakeOwner,Vissim
obsEnabled=True: obsFrameSec=-1: obsSignalSec=-1: obsHeldSec=-1: scans=0: queueSamples=0: farSamples=0
RW_SIGNAL_SCS="1": fakeState="GREEN": fakeOwner=False
Class FakeClock
 Public Current,Resolution
 Public Function AttValue(name)
  If name="SimSec" Then AttValue=Current Else AttValue=Resolution
 End Function
End Class
Class FakeVissim
 Public Simulation
 Private Sub Class_Initialize(): Set Simulation=New FakeClock: End Sub
End Class
Class FakeSignal
 Public Property Get AttValue(name)
  If name="SigState" Then AttValue=fakeState Else AttValue=fakeOwner
 End Property
End Class
Function CachedSignalGroup(sc,sg): Set CachedSignalGroup=New FakeSignal: End Function
Function SafeAtt(obj,key): SafeAtt=obj.AttValue(key): End Function
Function InCsvInt(n,csv): InCsvInt=(CStr(n)=CStr(csv)): End Function
Function FwSegCount(csv): FwSegCount=1: End Function
Function Num(v): Num=CStr(v): End Function
Function JsonDoubleInvariant(v): JsonDoubleInvariant=CStr(v): End Function
Function JsonEscape(v): JsonEscape=CStr(v): End Function
Function PerfNow(): PerfNow=0: End Function
Function EnvText(name): EnvText="": End Function
Sub PerfAdd(name,t0): End Sub
Sub PerfCount(name,amount): End Sub
Sub AccumulateQueueWindow(counts,stops): queueSamples=queueSamples+1: End Sub
Sub AccumulateFreewayExits(vehicles,links): farSamples=farSamples+1: End Sub
Sub AbortVehicleObservation(t): Err.Raise 513,,"scan failed": End Sub
Sub Check(ok,detail): If Not ok Then Err.Raise 513,,detail
End Sub
'''+scan+'\n'.join(procedure(vbs, n) for n in names)+'''
Set obsHeads=CreateObject("Scripting.Dictionary")
Set obsHeadLanes=CreateObject("Scripting.Dictionary")
Set obsHeadRoads=CreateObject("Scripting.Dictionary")
Set obsConnectors=CreateObject("Scripting.Dictionary")
Set obsHeld=CreateObject("Scripting.Dictionary")
Set obsActual=CreateObject("Scripting.Dictionary")
Set obsPrevious=CreateObject("Scripting.Dictionary")
Set winDepart=CreateObject("Scripting.Dictionary")
Set Vissim=New FakeVissim: Vissim.Simulation.Resolution=1
obsHeads.Add "h",Array("66",1,100,"1","2")
obsHeadLanes.Add "66|1","h": obsHeadRoads.Add "66",True
ResetHeadObservation 1
Vissim.Simulation.Current=1
CollectHeadObservation 1
SealHeadSignalStates 1
Vissim.Simulation.Current=2
CollectHeadObservation 2
Check obsTransitions=1 And queueSamples=1,"same interval ending at decision"
Check DictNumber(obsCross,"h")=1 And DictNumber(obsQualified,"h")=1,"actual collector crossing"
Check DictNumber(obsGreen,"h")=1 And DictNumber(obsNativeSec,"h")=1,"actual native exposure"
snapshot=HeadObservationJson(2)
CollectHeadObservation 2
Check scans=2 And obsTransitions=1,"decision/logger same-time collection must be idempotent"
ResetHeadObservation 2
fakeState="RED": fakeOwner=True
ObservationSignalReadback 1,2,"RED",True
SealHeadSignalStates 2
CollectHeadObservation 2
Check obsTransitions=0 And scans=2,"post-reset logger must not add endpoint to new window"
Vissim.Simulation.Current=3
CollectHeadObservation 3
Check obsTransitions=1 And obsWindowStart=2,"next window starts from saved endpoint"
Check DictNumber(obsGreen,"h")=0 And DictNumber(obsControlledSec,"h")=1,"actual controlled exposure"
Check DictNumber(obsNativeSec,"h")=0,"native/controlled ownership must not be mixed"
Vissim.Simulation.Current=3.5
On Error Resume Next
CollectHeadObservation 3.5
failure=Err.Number: Err.Clear
On Error GoTo 0
Check failure<>0 And obsTransitions=1 And scans=3,"fractional time must not accumulate or scan"
Vissim.Simulation.Current=4: Vissim.Simulation.Resolution=2
On Error Resume Next
CollectHeadObservation 4
failure=Err.Number: Err.Clear
On Error GoTo 0
Check failure<>0 And obsTransitions=1 And scans=3,"changed actual SimRes must reject before accumulation"
Vissim.Simulation.Resolution=1
On Error Resume Next
CollectHeadObservation 3
failure=Err.Number: Err.Clear
On Error GoTo 0
Check failure<>0 And obsTransitions=1,"mislabeled duplicate must not hide actual time advance"
Vissim.Simulation.Current=3
fakeState="GREEN": fakeOwner="invalid-owner"
ObservationSignalReadback 1,2,"GREEN",True
Check Not obsClockComplete,"invalid owner must mark original window"
ResetHeadObservation 3
SealHeadSignalStates 3
Check Not obsClockComplete,"reset must not turn an invalid held owner into verified state"
fakeOwner=False
Vissim.Simulation.Current=4
CollectHeadObservation 4
Check Not obsClockComplete,"invalid held interval must invalidate the next window too"
Check DictNumber(obsUnverifiedSec,"h")=1,"invalid held interval needs explicit unknown exposure"
Check DictNumber(obsNativeSec,"h")=0 And DictNumber(obsControlledSec,"h")=0,"invalid owner is neither native nor controlled"
Check DictNumber(obsGreen,"h")=0,"unverified held green must not be a valid denominator"
SealHeadSignalStates 4
ResetHeadObservation 4
Vissim.Simulation.Current=5
CollectHeadObservation 5
Check obsClockComplete And DictNumber(obsNativeSec,"h")=1,"a genuinely valid subsequent held interval can recover"
WScript.Echo "COLLECTOR_CLOCK_PASS"
'''
        self.assertIn('COLLECTOR_CLOCK_PASS', run_vbs(code))


if __name__ == '__main__':
    unittest.main()
