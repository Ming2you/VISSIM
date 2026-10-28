"""Harness-copy check for amendment 34 section 5.0 R4 (closed list of differences between the V-A judge copies and
the K8b gate tools) and S-A34-4 / S-A34-11 (judge fixed before data, not changed after).
python -B v_copydiff.py <outdir>
  1. the K8b originals SP/j1/fix/gates/<f> have the K8b pinned sha (gates_files_before_run.sha256 /
     gates_files_later.sha256), and VA/gates/k8b_orig/<f> are byte copies of them;
  2. a unified diff (difflib, my own) original -> V-A copy for the nine copies, written to <outdir>/<f>.diff for reading;
     the review against R4 items 1-7 is done by reading these files (report section);
  3. VA/gates/va_gates_pins.sha256 lines == sha of the files now; the pinned E_K92 judge sha == d15e9cc0...;
  4. no other file in VA/gates newer than the pin file except the declared later outputs (*.out.txt / *.err.txt /
     wmi_launch_lines.txt) - listed for the report.
Reads source text only (nothing is imported or executed).  Prints counts and sha."""
import difflib
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v_lib as L  # noqa: E402

VA = Path(__file__).resolve().parents[1]
GATES = VA / 'gates'
K8B = VA.parents[1] / 'j1' / 'fix' / 'gates'
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
NINE = ('gcommon.py', 'gprep.py', 'greplay.py', 'gjudge.py', 'g_driver.py', 'launch.ps1', 'gh5_check.py', 'gb7_report.py',
        'gh5_launch.ps1')
pins = {}
for f in ('gates_files_before_run.sha256', 'gates_files_later.sha256'):
    for line in L.read_text(K8B / f).splitlines():
        if line.strip():
            h, n = line.split(' ', 1)
            pins[n.lstrip('*')] = h
res = {'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'files': {}}
for n in NINE:
    o = K8B / n
    c = GATES / 'k8b_orig' / n
    v = GATES / n
    ob, cb, vb = o.read_bytes(), c.read_bytes(), v.read_bytes()
    r = {'k8b_pinned': pins.get(n), 'k8b_now': L.sha256_bytes(ob), 'k8b_orig_copy': L.sha256_bytes(cb),
         'va_copy': L.sha256_bytes(vb)}
    r['orig_ok'] = r['k8b_pinned'] == r['k8b_now'] == r['k8b_orig_copy']
    ud = list(difflib.unified_diff(ob.decode('utf-8').splitlines(True), vb.decode('utf-8').splitlines(True),
                                   fromfile='k8b/' + n, tofile='va/' + n, n=1))
    (OUT / (n + '.diff')).write_text(''.join(ud), encoding='utf-8', newline='\n')
    r['diff_lines'] = len(ud)
    r['plus'] = sum(1 for x in ud if x.startswith('+') and not x.startswith('+++'))
    r['minus'] = sum(1 for x in ud if x.startswith('-') and not x.startswith('---'))
    res['files'][n] = r
pl = {}
for line in L.read_text(GATES / 'va_gates_pins.sha256').splitlines():
    if line.strip():
        h, n = line.split(' ', 1)
        pl[n.lstrip('*')] = h
res['pins_lines'] = len(pl)
res['pins_bad'] = [n for n, h in pl.items() if not (GATES / n).is_file() or L.sha256_file(GATES / n) != h]
res['pins_cover_nine'] = all(n in pl and pl[n] == res['files'][n]['va_copy'] for n in NINE)
res['ek92_pinned'] = pl.get('gb7_k92decl.py') == L.EK92_JUDGE_SHA
pm = os.stat(GATES / 'va_gates_pins.sha256').st_mtime
newer = []
for p in sorted(GATES.rglob('*')):
    if p.is_file() and p.stat().st_mtime > pm:
        newer.append(str(p.relative_to(GATES)).replace('\\', '/'))
res['newer_than_pins'] = newer
res['newer_than_pins_are_outputs_only'] = all(x.endswith(('.out.txt', '.err.txt')) or x == 'wmi_launch_lines.txt'
                                              for x in newer)
res['ok'] = (all(r['orig_ok'] for r in res['files'].values()) and not res['pins_bad'] and res['pins_cover_nine']
             and res['ek92_pinned'] and res['newer_than_pins_are_outputs_only'])
L.write_json(OUT / 'v_copydiff.json', res)
print('V_COPYDIFF ok=%s files=%s pins=%d bad=%s newer=%s' % (
    res['ok'], {n: [r['orig_ok'], r['plus'], r['minus']] for n, r in res['files'].items()}, res['pins_lines'],
    res['pins_bad'], newer))
