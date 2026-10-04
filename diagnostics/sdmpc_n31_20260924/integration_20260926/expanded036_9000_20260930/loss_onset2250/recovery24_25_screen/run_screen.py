"""Four finite, sequential diagnostic forecasts; no retries or native runtime."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

O=Path(__file__).resolve().parent
L=O.parent
protocol=json.loads((O/'protocol.json').read_bytes())
for name,digest in protocol['source_pins'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
rows=[]
for label in ('fd125','relax200'):
    for start in (2250,3600):
        run_label=label+'r1'
        args=[sys.executable,str(L/'audit_city_arrival.py'),str(start),'--physical-speed',
            '--all-ramp-ledger','--mainline-terms','--audit-label='+run_label,
            '--audit-config='+str(O/label/'candidate_config.json')]
        before=time.perf_counter()
        with (O/f'{run_label}_{start}.log').open('x',encoding='utf-8') as log:
            result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=False)
        row=dict(label=label,start=start,exit_code=result.returncode,wall_sec=time.perf_counter()-before)
        rows.append(row)
        (O/'run_status.json').write_text(json.dumps(dict(rows=rows,status='failed' if result.returncode else 'running'),indent=2)+'\n',encoding='utf-8')
        print(json.dumps(row),flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
(O/'run_status.json').write_text(json.dumps(dict(rows=rows,status='complete',forecasts=4),indent=2)+'\n',encoding='utf-8')
