"""ReviewDeclare A30 (RV30 = KB/a30review): leak scan of the k92t outputs outside the sealed root.
Names and counts only: no line text is printed or written.

Rules
  full   = amendment 25 section 6.5-4 (a v3c3-s47 job-name form + a value form or the SA_JOB job-line form, one line).
  fprim  = a line with an F primary-sample label TL3_<T>_s47_SAF_OBS_H3 (T in the 22 primary states, amendment 24
           section 5.3) together with a value form, or the SA_JOB job-line form of such a label.
  jobok  = a line 'K92T_JOB <root> TL3_<T>_s47_SAF_OBS_H3 ok=...' (job-success line of the base driver child; ok only).
  synth  = full-rule lines holding the judge's synthetic control value 4711 (k92t_judge.py scan_leak controls).
Excluded (never opened, amendment 30 section 4.2): OUTK/logs/f_f_{off,w,b1}_jobs.log, the s47 primary F job and
capture folders of f_off / f_w / f_b1, OUTK/f_vref.  The sealed root is not walked.
Transcript roots (report only): the JSON lines are decoded and every string is split into lines before the rules.

    python -B rv_leak30.py <dest.json>
"""
import json
import os
import re
import sys
import time
from pathlib import Path

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
SEALED = OK2 / 'sealed_s47'
HERE = Path(__file__).resolve().parent
KB = HERE.parent
SP = KB.parent.parent
PROJ = Path(r'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----')
SESSION = '491ef689-f002-4605-9dc5-e6d363495788'
OWN_AGENT = 'agent-a5719a536a3462aa8.jsonl'
SINCE = time.mktime(time.strptime('2026-10-21 03:30:00', '%Y-%m-%d %H:%M:%S'))

F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
NAME_RE = re.compile(r'_s47_|s47_|_s47(?![0-9A-Za-z])')
VALUE_RE = re.compile(r'objective=[^\s`<]*\d|continuous_scalar\w*[\s=:]+[^\s`<]*\d')
SAJOB_RE = re.compile(r'SA_JOB [^\s`<]*(?:_s47_|s47_|_s47(?![0-9A-Za-z]))')
ALT = '|'.join(str(t) for t in F_PRIMARY)
FLAB_RE = re.compile(r'TL3_(?:%s)_s47_SAF_OBS_H3' % ALT)
FJOB_RE = re.compile(r'SA_JOB TL3_(?:%s)_s47_SAF_OBS_H3' % ALT)
JOBOK_RE = re.compile(r'K92T_JOB \S+ TL3_(?:%s)_s47_SAF_OBS_H3 ok=' % ALT)
EXT = ('.txt', '.log', '.jsonl', '.md', '.json', '.csv')
EXCL_LOGS = {'logs/f_f_off_jobs.log', 'logs/f_f_w_jobs.log', 'logs/f_f_b1_jobs.log'}
EXCL_RE = re.compile(r'^(?:f_(?:off|w|b1)/sa/jobs/k92t/TL3_\d+_s47_SAF_OBS_H3/|f_(?:off|w|b1)/sa/cap/k92t/TL3/\d{6}_s47/'
                     r'|f_vref/)')
PATH_FP_RE = re.compile(r'(?:TL3_(?:%s)_s47_|(?<![0-9])0*(?:%s)_s47(?![0-9A-Za-z]))' % (ALT, ALT))


def classify_line(line, acc):
    if 's47' not in line:
        if 'K92T_JOB' in line and JOBOK_RE.search(line):
            acc['jobok'] += 1
        return
    full = bool(NAME_RE.search(line) and (VALUE_RE.search(line) or SAJOB_RE.search(line)))
    if full:
        acc['full'] += 1
        if '4711' in line:
            acc['synth'] += 1
    if FLAB_RE.search(line) and (VALUE_RE.search(line) or FJOB_RE.search(line)):
        acc['fprim'] += 1
    if JOBOK_RE.search(line):
        acc['jobok'] += 1


def scan_bytes(data, acc):
    if b's47' not in data and b'K92T_JOB' not in data:
        return
    if not (b'objective=' in data or b'continuous_scalar' in data or b'SA_JOB ' in data or b'K92T_JOB' in data):
        return
    for raw in data.splitlines():
        classify_line(raw.decode('utf-8', 'replace'), acc)


def strings_of(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings_of(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings_of(v)


def new_acc():
    return {'full': 0, 'fprim': 0, 'jobok': 0, 'synth': 0}


def scan_file(full, acc_root, hits, shown, transcript=False):
    acc = new_acc()
    recs = []
    with open(full, 'rb') as f:
        data = f.read()
    acc_root['bytes'] += len(data)
    if transcript:
        for i, raw in enumerate(data.splitlines()):
            if b's47' not in raw and b'K92T_JOB' not in raw:
                continue
            try:
                doc = json.loads(raw.decode('utf-8', 'replace'))
            except ValueError:
                doc = raw.decode('utf-8', 'replace')
            a = new_acc()
            for s in strings_of(doc):
                for ln in s.splitlines():
                    classify_line(ln, a)
            if any(a.values()):
                ts = doc.get('timestamp') if isinstance(doc, dict) else None
                recs.append({'record': i, 'timestamp': ts, 'type': doc.get('type') if isinstance(doc, dict) else None,
                             **a})
                for k in acc:
                    acc[k] += a[k]
    else:
        scan_bytes(data, acc)
    if any(acc.values()):
        hits[shown] = dict(acc, records=recs[:200]) if transcript else acc
    for k in acc:
        acc_root[k] += acc[k]


def walk(root, rel_base, res_key, res, excl=False, exts=EXT):
    acc_root = {'files': 0, 'bytes': 0, 'excluded_files': 0, 'excluded_bytes': 0, **new_acc()}
    hits, excluded_kinds, path_fp = {}, {}, []
    for base, dirs, names in os.walk(root):
        dirs.sort()
        if Path(base).resolve() == SEALED.resolve():
            dirs[:] = []
            continue
        for n in sorted(names):
            full = os.path.join(base, n)
            rel = os.path.relpath(full, rel_base).replace('\\', '/')
            if excl and (rel in EXCL_LOGS or EXCL_RE.match(rel)):
                acc_root['excluded_files'] += 1
                acc_root['excluded_bytes'] += os.path.getsize(full)
                kind = 'job_logs' if rel in EXCL_LOGS else rel.split('/')[0] + '/' + (
                    'jobs' if '/jobs/' in rel else 'cap' if '/cap/' in rel else 'vref')
                excluded_kinds[kind] = excluded_kinds.get(kind, 0) + 1
                continue
            if excl and PATH_FP_RE.search(rel):
                path_fp.append(rel)
            if os.path.splitext(n)[1].lower() not in exts:
                continue
            acc_root['files'] += 1
            scan_file(full, acc_root, hits, rel)
    res[res_key] = dict(acc_root, hit_files=hits, excluded_kinds=excluded_kinds, path_names_with_primary=path_fp[:50],
                        n_path_names_with_primary=len(path_fp))


def main():
    dest = Path(sys.argv[1])
    t0 = time.time()
    res = {'schema': 'rv30-leak/v1', 'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'rules': {
        'NAME_RE': NAME_RE.pattern, 'VALUE_RE': VALUE_RE.pattern, 'SAJOB_RE': SAJOB_RE.pattern,
        'FLAB_RE': FLAB_RE.pattern, 'FJOB_RE': FJOB_RE.pattern, 'JOBOK_RE': JOBOK_RE.pattern}}
    # controls (synthetic strings built here, no real value)
    ctrl = {}
    for name, line, want in (
            ('prim_value', 'SA_JOB TL3_2400_s47_SAF_OBS_H3 exit=0 wall=1.0 ok=True objective=' + '9' * 3, (1, 1, 0)),
            ('prim_none', 'SA_JOB TL3_2400_s47_SAF_OBS_H3 exit=1 wall=1.0 ok=False objective=None', (1, 1, 0)),
            ('j_state', 'SA_JOB TL3_900_s47_SAF_OBS_H3 exit=0 wall=1.0 ok=True objective=' + '9' * 3, (1, 0, 0)),
            ('jobok', 'K92T_JOB f_off TL3_2400_s47_SAF_OBS_H3 ok=True', (0, 0, 1)),
            ('doc', 'the `SA_JOB ... objective=` line of `TL3_<T>_s47_SAF_OBS_H3`', (0, 0, 0))):
        a = new_acc()
        classify_line(line, a)
        ctrl[name] = (a['full'], a['fprim'], a['jobok']) == want
    res['controls'] = ctrl
    res['controls_ok'] = all(ctrl.values())
    walk(str(OUTK), str(OUTK), 'outk', res, excl=True)
    for key, root in (('ok2_logs', OK2 / 'logs'), ('ok2_vg2t', OK2 / 'vg2t')):
        walk(str(root), str(root), key, res)
    top = {'files': 0, 'bytes': 0, **new_acc()}
    hits = {}
    for p in sorted(OK2.glob('*.md')):
        top['files'] += 1
        scan_file(str(p), top, hits, p.name)
    res['ok2_top_md'] = dict(top, hit_files=hits)
    walk(str(KB), str(KB), 'kb', res)
    top = {'files': 0, 'bytes': 0, **new_acc()}
    hits = {}
    for p in sorted(SP.glob('*.md')):
        top['files'] += 1
        scan_file(str(p), top, hits, p.name)
    res['sp_top_md'] = dict(top, hit_files=hits)
    # transcripts written after the F jobs began (report only; own transcript excluded: it is being written)
    tr = {'files': 0, 'bytes': 0, **new_acc()}
    hits = {}
    cands = [PROJ / (SESSION + '.jsonl')]
    sub = PROJ / SESSION / 'subagents'
    for base, dirs, names in os.walk(sub):
        for n in names:
            if n.endswith('.jsonl') and n != OWN_AGENT:
                cands.append(Path(base) / n)
    for n in os.listdir(PROJ / SESSION / 'tool-results'):
        cands.append(PROJ / SESSION / 'tool-results' / n)
    for p in sorted(set(cands)):
        if not p.is_file() or os.path.getmtime(p) < SINCE:
            continue
        tr['files'] += 1
        scan_file(str(p), tr, hits, str(p.relative_to(PROJ)).replace('\\', '/'), transcript=p.suffix == '.jsonl')
    res['transcripts_report_only'] = dict(tr, hit_files=hits)
    res['sec'] = round(time.time() - t0, 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(res, indent=1, sort_keys=True) + '\n')
    summ = {k: {m: res[k][m] for m in ('files', 'full', 'fprim', 'jobok', 'synth')} for k in
            ('outk', 'ok2_logs', 'ok2_vg2t', 'ok2_top_md', 'kb', 'sp_top_md', 'transcripts_report_only')}
    print('RV30_LEAK controls_ok=%s sec=%s %s' % (res['controls_ok'], res['sec'], json.dumps(summ, sort_keys=True)),
          flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
