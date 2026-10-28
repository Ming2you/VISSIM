"""Gates A30 poll (read-only): process presence, OUTK stage / STOP file names, steps.jsonl name / rc / sec / VISSIM
fields after line 59.  Never opens a log file or any data file."""
import json
import subprocess
import sys
import time
from pathlib import Path

OUTK = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/k92t')
OUT30 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/a30')
TAIL = int(sys.argv[1]) if len(sys.argv) > 1 else 6


def procs():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|VISSIM|cscript|wscript)' }"
                          " | ForEach-Object { '{0} {1} {2}' -f $_.ProcessId, $_.ParentProcessId, $_.Name }"],
                         capture_output=True, text=True).stdout.split('\n')
    return [ln.strip() for ln in out if ln.strip()]


def main():
    print('now', time.strftime('%Y-%m-%d %H:%M:%S'))
    print('procs', procs())
    print('stages', sorted(p.name for p in (OUTK / 'stages').iterdir()))
    print('stops', sorted(p.name for p in OUTK.glob('STOP_*.json')))
    print('judge', sorted(p.name for p in (OUTK / 'judge').iterdir()))
    print('out30', sorted(p.name for p in OUT30.iterdir()) if OUT30.is_dir() else None)
    rows = [json.loads(ln) for ln in (OUTK / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if ln.strip()]
    new = rows[59:]
    print('steps total', len(rows), 'new', len(new), 'rc!=0 new', [r['name'] for r in new if r.get('rc') != 0])
    for r in new[-TAIL:]:
        print('  ', r.get('name'), 'rc=%s' % r.get('rc'), 'sec=%s' % r.get('sec'),
              'vissim=%s/%s' % (r.get('vissim_pre'), r.get('vissim_post')),
              time.strftime('%H:%M:%S', time.localtime(r.get('start', 0))))


if __name__ == '__main__':
    main()
