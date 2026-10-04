"""Check prepared CSVs using actual VBS validators/writers with fake COM only."""
from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess
import sys
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics import test_profile_runner_invocation as harness

protocol=json.loads((HERE/'protocol.json').read_bytes())
assert protocol['native_authorization_pending'] and not protocol['native_started']
for name,digest in protocol['command_pins'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
assert protocol['arms']==['selected'] and protocol['control_start_sec']==2700
out=HERE/'writer_contract';out.mkdir()
history=Path(protocol['reuse_native_baseline']['run'])/'decisions_sdmpc31_g_2700_hold_s47'
with mock.patch.object(harness,'CONFIG',HERE/'selected/replay.vbs'), mock.patch.object(harness,'RAW',history/'state_002700.json'):
    script_path=harness.build_harness(out,'wu-link','signal_profile_config_sc1004_green10.json')
script=script_path.read_text(encoding='utf-16').replace('RW_OFFSET_WRITER = "test_only"','RW_OFFSET_WRITER = "experiment"')
begin=script.rindex('If UseContinuousStaticMode() Then')
end=script.index('WScript.Echo "LAST_ACTION=" & lastActionJson',begin)+len('WScript.Echo "LAST_ACTION=" & lastActionJson')
body=['Set vslTraceFile = fso.CreateTextFile('+harness.q(out/'vsl_readback.csv')+',True)',
      'controlStartSec=2700', 'RW_RAMP_AMBER_SEC=0']
commands=HERE/'selected/commands'
counts={}
for sec in (1,*range(150,3151,150)):
    path=commands/f'action_{sec:06d}.csv'
    with path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    kinds={k:sum(row['kind']==k for row in rows) for k in ('signal','signal_sg','vsl','ramp_meter')}
    assert kinds['ramp_meter']==8
    if sec<2700:
        assert kinds['signal']==kinds['signal_sg']==0
        assert path.read_bytes()==(history/path.name).read_bytes()
    else:assert kinds['signal']==17 and kinds['signal_sg']>0
    controller='no-control' if sec<2700 else 'wu-link'
    body += [f'If Not ApplyActionCsv({sec}, {harness.q(path)}, "{controller}") Then WScript.Quit 4',
             f'ApplyRuntimeSignals {sec}',
             f'If sigPhaseGreen.Count <> {0 if sec<2700 else 17} Then WScript.Quit 5',
             f'WScript.Echo "PASS_CSV={sec}"']
    counts[sec]=kinds
body+=['vslTraceFile.Close','WScript.Echo "WRITER_CONTRACT_PASS"']
script=script[:begin]+'\n'.join(body)+'\n'+script[end:]
assert 'Set Vissim = New FakeVissim' in script and 'CreateObject("Vissim.' not in script
script_path.write_text(script,encoding='utf-16')
run=subprocess.run(['cscript.exe','//nologo',str(script_path)],capture_output=True,text=True,
    encoding='mbcs',timeout=30,env=dict(os.environ,RW_MAINLINE_SG_ONLY='1',RW_SIGNAL_WRITE_ON_CHANGE='1',RW_RAMP_AMBER_SEC='0'))
(out/'stdout.txt').write_text(run.stdout,encoding='utf-8')
(out/'stderr.txt').write_text(run.stderr,encoding='utf-8')
assert run.returncode==0 and 'WRITER_CONTRACT_PASS' in run.stdout,(run.returncode,run.stderr,run.stdout[-1200:])
assert run.stdout.count('PASS_CSV=')==22
report=dict(commands=22,checks=counts,actual_vbs_apply_contract_passed=True,
    fake_com=True,native_started=False,urban_signal_tables_empty_before2700=True,
    controls_match_verified_prediction=True,simulation_equivalence_not_yet_verified=True,
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(__file__),harness.RUNNER,HERE/'protocol.json',HERE/'selected/replay.vbs',script_path)})
(HERE/'writer_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(commands=22,fake_com_contract='PASS',native_started=False)))
