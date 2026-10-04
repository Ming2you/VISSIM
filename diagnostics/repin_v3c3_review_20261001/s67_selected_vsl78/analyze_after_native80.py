"""One postprocess invocation of the prepared REVIEW78 plan."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUNS=Path('D:/VISSIM_runs/20261003_s67_selected_vsl78')
plan=json.loads((HERE/'postprocess_plan.json').read_bytes())
status=json.loads((ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/closedloop_recorded2700_native_selected_s67_selected_vsl78/status.json').read_text(encoding='utf-8-sig'))
assert status['stage']=='both_native_complete_unanalyzed'
assert not (RUNS/'STOP').exists()
assert not (HERE/'analysis/summary.json').exists()
assert not (HERE/'analysis_run80_cli.json').exists()
failed=json.loads((HERE/'analysis_run80.json').read_bytes())
assert failed['stage']=='failed' and failed['exit_code']==2
assert '--recording-start-alignment requires the cached replay audit only' in (HERE/'analysis80.log').read_text(encoding='utf-8')
for name,digest in plan['source_pins'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
receipt=dict(stage='running',started=datetime.datetime.now().astimezone().isoformat(),
    owned_pids_absent=[19764,41908,4992,27424,48704,43540],source_pins=plan['source_pins'],
    prior_guard_failure='Inline terminal-label error and analyzer argument rejection preserved in analysis_run80/analysis80; no FZP scan ran. Existing selected/VSL pair now admitted by CLI; full evidence checks unchanged.')
def save():
    (HERE/'analysis_run80_cli.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
save()
with (HERE/'analysis80_cli.log').open('w',encoding='utf-8') as log:
    child=subprocess.Popen([plan['python'],*plan['args']],cwd=plan['cwd'],stdout=log,stderr=subprocess.STDOUT)
    receipt['analyzer_pid']=child.pid;save()
    code=child.wait()
receipt.update(stage='complete' if code==0 else 'failed',exit_code=code,ended=datetime.datetime.now().astimezone().isoformat());save()
print(json.dumps(receipt))
raise SystemExit(code)
