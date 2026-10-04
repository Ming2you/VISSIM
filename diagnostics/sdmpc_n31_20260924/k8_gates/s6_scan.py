"""S6: decision-call output sizes in past SDMPC/NC runner logs (CONTROLLER_DECISION ... result=exit=.. stdout=.. stderr=..).
Reads runlog_*.txt of the listed run roots only (no seed filter needed: only sizes/exit codes are reported, no results).
    python -B s6_scan.py [--runs-root DIR ...]   (read only; stdout only; paths containing s37/s59/s61/s67 are skipped)"""
import argparse
import glob
import json
import re
from pathlib import Path
ROOTS = [r'D:/VISSIM_runs/20260924_sdmpc31', r'D:/VISSIM_runs/20260925_sdmpc31_v3b', r'D:/VISSIM_runs/20260928_sdmpc31_v3c1',
         r'D:/VISSIM_runs/20261001_sdmpc31_v3c3']
_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument('--runs-root', action='append', help='run root to scan (repeatable; default: the four SDMPC-31 roots)')
roots = _ap.parse_args().runs_root or ROOTS
SEALED = ('s37', 's59', 's61', 's67')
rx = re.compile(r'CONTROLLER_DECISION sim_sec=(\S+) wall_sec=(\S+) result=exit=(-?\d+) stdout=(.*?) stderr=(.*)$')
rows = []
for root in roots:
    for f in glob.glob(root + '/**/runlog_*.txt', recursive=True):
        if any(s in f.lower() for s in SEALED):
            continue
        for line in open(f, encoding='utf-8', errors='replace'):
            m = rx.search(line)
            if m:
                rows.append(dict(run=Path(f).parent.name, sec=m.group(1), wall=float(m.group(2)), exit=int(m.group(3)),
                                 out=len(m.group(4).encode('utf-8')), err=len(m.group(5).encode('utf-8'))))
out = {'decisions': len(rows), 'runs': len({r['run'] for r in rows}),
       'max_stdout_B': max((r['out'] for r in rows), default=None), 'max_stderr_B': max((r['err'] for r in rows), default=None),
       'max_total_B': max((r['out'] + r['err'] for r in rows), default=None),
       'n_total_over_2048': sum(1 for r in rows if r['out'] + r['err'] > 2048),
       'n_total_over_4096': sum(1 for r in rows if r['out'] + r['err'] > 4096),
       'nonzero_exit': [(r['run'], r['sec'], r['exit'], r['err']) for r in rows if r['exit'] != 0][:20],
       'max_wall_sec': max((r['wall'] for r in rows), default=None)}
print(json.dumps(out, indent=1))
