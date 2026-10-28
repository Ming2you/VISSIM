"""Gates A31 poll / wait (read-only; not a judge).  Looks only at: the process table (python / VISSIM / cscript /
wscript / cmd PIDs and names), the file NAMES in OUT31/stages and OUT31/STOP_a31_*.json, OUT31/chain31.json presence,
and the name / rc / sec / VISSIM fields of OUT31/steps31.jsonl.  Never opens a log file or any other data file.

    python -B poll31.py poll
    python -B poll31.py wait <cmd PID> [max_sec<=540]   (ends when the stage / STOP / chain31 set changes, the PID is
                                                          gone, or max_sec pass; prints a poll at the end)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
OUT31 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/a31')


def procs():
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|VISSIM|cscript|wscript)' }"
                          " | ForEach-Object { '{0} {1} {2}' -f $_.ProcessId, $_.ParentProcessId, $_.Name }"],
                         capture_output=True, text=True).stdout.split('\n')
    return [ln.strip() for ln in out if ln.strip()]


def pid_alive(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %s' % pid, '/NH'], capture_output=True, text=True).stdout
    return str(pid) in out


def names():
    if not OUT31.is_dir():
        return {'out31': False}
    st = OUT31 / 'stages'
    return {'out31': True,
            'stages': sorted(p.name for p in st.iterdir()) if st.is_dir() else [],
            'stops': sorted(p.name for p in OUT31.glob('STOP_*.json')),
            'chain31': (OUT31 / 'chain31.json').is_file()}


def steps():
    p = OUT31 / 'steps31.jsonl'
    if not p.is_file():
        return []
    rows = [json.loads(ln) for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip()]
    return [{'name': r.get('name'), 'rc': r.get('rc'), 'sec': r.get('sec'),
             'vissim': '%s/%s' % (r.get('vissim_before'), r.get('vissim_after')),
             'start': time.strftime('%H:%M:%S', time.localtime(r.get('start', 0)))} for r in rows]


def poll():
    print('now', time.strftime('%Y-%m-%d %H:%M:%S'))
    print('procs', procs())
    print('names', json.dumps(names()))
    for r in steps():
        print('  step', json.dumps(r))


def wait(pid, max_sec):
    s0 = json.dumps(names())
    t = 0
    while t < max_sec:
        time.sleep(15)
        t += 15
        s1 = json.dumps(names())
        if s1 != s0:
            print('CHANGE after %ss' % t)
            break
        if not pid_alive(pid):
            print('PROCESS_GONE after %ss' % t)
            break
    else:
        print('TIMEOUT %ss' % max_sec)
    poll()


if __name__ == '__main__':
    if sys.argv[1] == 'poll':
        poll()
    elif sys.argv[1] == 'wait':
        wait(int(sys.argv[2]), min(540, int(sys.argv[3]) if len(sys.argv) > 3 else 540))
