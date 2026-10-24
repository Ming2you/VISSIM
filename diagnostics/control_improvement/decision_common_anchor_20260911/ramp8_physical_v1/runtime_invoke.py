"""One canonical decision on a preserved native80/50 state; config owns its wall policy."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('label')
parser.add_argument('config',nargs='?',default='joint_config_v1.json')
parser.add_argument('controller',nargs='?',default='wu-link',choices=('wu-link','diagnostic-signal-profile'))
parser.add_argument('--run',default='codex_native_clock_fw080_u050_open_v2')
parser.add_argument('--sim-sec',type=int,default=900)
cli=parser.parse_args()
label=cli.label
if not label.replace('_','').isalnum():raise ValueError('Fresh result label required')
out=D/label
out.mkdir(exist_ok=False)
if not cli.run.replace('_','').isalnum() or cli.sim_sec<150 or cli.sim_sec%150:
    raise ValueError('Explicit preserved run name and 150-second decision boundary required')
record=ROOT/'evaluation/runs'/cli.run/('decisions_'+cli.run)
stamp=f'{cli.sim_sec:06d}'
previous_stamp=f'{cli.sim_sec-150:06d}'
config=D/cli.config
controller=cli.controller
if controller not in ('wu-link','diagnostic-signal-profile'):raise ValueError('Unsupported bounded replay controller')
args=['-B','-X','utf8','evaluation/controllers/vissim_stackelberg_adapter.py',
    '--state-json',str(record/f'state_{stamp}.json'),'--previous-action-json',str(record/f'action_{previous_stamp}.json'),
    '--out-action-json',str(out/f'action_{stamp}.json'),'--out-action-csv',str(out/f'action_{stamp}.csv'),
    '--mapping-json','evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
    '--detector-mapping-json','evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json',
    '--calibration-json','evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
    '--tuning-json',str(config),'--controller',controller,'--mode','fast-smoke']
paths=list((ROOT/'evaluation/controllers').glob('*.py'))+[Path(__file__),config]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins={str(p.relative_to(ROOT)):sha(p) for p in paths}
env=dict(os.environ);env['RW_OFFSET_WRITER']='experiment';env['PYTHONUTF8']='1'
if controller=='diagnostic-signal-profile':env['RW_OFFSET_WRITER']='test_only'
receipt={'arguments':args,'source_sha256':pins,'native_run':False,
    'scope':'Canonical whole decision including model setup, common prices, leader/follower and final writer; eight-ramp structural model change, not a legacy numerical-equivalence speed benchmark.'}
if controller=='diagnostic-signal-profile':receipt['scope']='Canonical fixed-command preflight only; no price/leader/game calculation or native execution.'
start=time.perf_counter()
unlimited=json.loads(config.read_text(encoding='utf-8-sig')).get('adapter',{}).get('joint_owner_game',{}).get('ignore_wall_time_limits',False)
if type(unlimited) is not bool:raise ValueError('Explicit boolean wall policy required')
receipt['outer_timeout_sec']=None if unlimited else 180
try:
    with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=receipt['outer_timeout_sec'])
    receipt.update(completed=result.returncode==0,exit_code=result.returncode)
except subprocess.TimeoutExpired:
    receipt.update(completed=False,error='Outer180s diagnostic guard exceeded')
finally:
    receipt.update(elapsed_sec=time.perf_counter()-start,source_changes=[p for p,h in pins.items() if sha(ROOT/p)!=h])
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('arguments','source_sha256')}))
sys.exit(0 if receipt.get('completed') else 1)
