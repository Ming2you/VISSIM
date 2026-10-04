"""Run the previously budgeted two forecasts, using the explicit recording proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')

def main():
    plan=json.loads((HERE/'postprocess_plan74.json').read_bytes())
    suffix='_actuator_equivalent' if '--local-cache-correction' in sys.argv else ''
    if suffix:
        failed=json.loads((HERE/'prediction_run76.json').read_bytes())
        assert failed['stage']=='failed' and failed['exit_code']==1
        assert 'PermissionError' in (HERE/'prediction76.log').read_text(encoding='utf-8')
        plan['prediction_output'] += suffix
        plan['prediction_argv']=[x+suffix if x.startswith('--probe-label=') else x for x in plan['prediction_argv']]
    assert not Path(plan['prediction_output']).exists()
    receipt_path=HERE/f'prediction_run76{suffix}.json'
    assert not receipt_path.exists()
    assert json.loads((HERE/'alignment_checks76.json').read_bytes())['passed']
    oldpins=plan['source_pins']
    for path,digest in oldpins.items():
        if Path(path).name not in ('analyze_pair.py','probe_selected_arrival_path.py'):
            assert sha(path)==digest
    argv=[sys.executable,*plan['prediction_argv'][1:],
          '--recording-start-alignment='+str(HERE/'recording_start_alignment76.json')]
    receipt=dict(stage='running',started_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),pid=os.getpid(),
                 argv=argv,source_pins={p:sha(p) for p in oldpins},
                 original_failed_summary_sha256=sha(HERE/'analysis/summary.json'),
                 native_reruns=0,optimizer_budget=0,forecast_budget=2,calibration_candidates=0,
                 scope='New pair observed2700 state; common old/new recorded interval verified, raw-prefix failure preserved')
    save(receipt_path,receipt)
    t=time.monotonic()
    with (HERE/f'prediction76{suffix}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        receipt['child_pid']=process.pid;save(receipt_path,receipt)
        code=process.wait()
    receipt.update(stage='complete' if code==0 else 'failed',exit_code=code,elapsed_sec=time.monotonic()-t)
    save(receipt_path,receipt)
    print(json.dumps(receipt))
    raise SystemExit(code)

if __name__=='__main__':main()
