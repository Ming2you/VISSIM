"""K9-2 V-B record selection (K8_PREDECLARATION_AMENDMENT_32 section 3.4).  Diagnostics only, never committed.
Standard library only.  Runs AFTER a decision process has ended, outside it.

    python -B vb_select.py select --hook-dir H --action-json A --T T --dest D

H = the hook folder of one decision (vbhook/sitecustomize.py wrote loaded_<pid>.json, c_<pid>_<seq>/{cand.json,
k92_record.json, k92_series.npz}, hook_error_<pid>.txt, hook_setup_error_<pid>.txt).  A = the decision's written
action JSON.  D = the record folder of that decision (created; must not hold a k92_select.json yet).

A candidate MATCHES when (all):
  (m1) its signature equals the written action: green_times (every key, value == as float), offsets (same) and the
       future block green_times (metadata path diagnostics.sdmpc_prediction_sequence.future[i].green_times; both
       absent, or the same length with every block equal);
  (m2) first_row_start_sec == T and dt_sec == 150.0 and n_residence_rows > 0;
  (m3) its folder holds k92_record.json (and cand.json).
Status (one, in this order):
  hook_error      a hook_error_*.txt / hook_setup_error_*.txt exists, a c_* folder lacks cand.json or
                  k92_record.json, or a loaded_*.json says recorder_ok false
  no_hook         no loaded_*.json whose argv0 is vissim_stackelberg_adapter.py
  no_candidate    no c_* folder
  no_match        candidates, none matches
  match_conflict  two or more matches whose records differ (blocks and horizon; numbers within relative 1e-9 of
                  max(1, |a|, |b|), everything else exactly)
  selected        the match first in (is_ad, time_ns, pid, seq) order (non-AD first, then earliest) -- its
                  k92_record.json and k92_series.npz are byte-copied into D
D/k92_select.json is written in every case (schema k92vb-select/v1).  Exit 0 when it ran, 2 on a usage error."""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SCHEMA = 'k92vb-select/v1'
ADAPTER = 'vissim_stackelberg_adapter.py'
REL = 1e-9


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def as_float_map(d):
    if not isinstance(d, dict):
        return None
    out = {}
    for k, v in d.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            out[str(k)] = ('<non-number>', repr(v))
        else:
            out[str(k)] = float(v)
    return out


def out_signature(doc):
    diag = doc.get('diagnostics') if isinstance(doc.get('diagnostics'), dict) else {}
    seq = diag.get('sdmpc_prediction_sequence')
    fut = None
    if isinstance(seq, dict) and isinstance(seq.get('future'), list):
        fut = [as_float_map(row.get('green_times')) if isinstance(row, dict) else None for row in seq['future']]
    return {'green_times': as_float_map(doc.get('green_times')), 'offsets': as_float_map(doc.get('offsets')),
            'future_green_times': fut}


def sig_equal(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    for key in ('green_times', 'offsets'):
        x, y = a.get(key), b.get(key)
        if x is None or y is None or set(x) != set(y) or any(x[k] != y[k] for k in x):
            return False
    fa, fb = a.get('future_green_times'), b.get('future_green_times')
    if fa is None or fb is None:
        return fa is None and fb is None
    if len(fa) != len(fb):
        return False
    for x, y in zip(fa, fb):
        if x is None or y is None:
            if not (x is None and y is None):
                return False
            continue
        if set(x) != set(y) or any(x[k] != y[k] for k in x):
            return False
    return True


def close(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        a, b = float(a), float(b)
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return abs(a - b) <= REL * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b


def read_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def select(hook_dir, action_json, T, dest):
    hook_dir, action_json, dest = Path(hook_dir), Path(action_json), Path(dest)
    if (dest / 'k92_select.json').exists():
        raise SystemExit('k92_select.json already exists in %s (never reused)' % dest)
    dest.mkdir(parents=True, exist_ok=True)
    T = float(T)
    res = {'schema': SCHEMA, 'T': T, 'hook_dir': str(hook_dir), 'action_json': str(action_json),
           'tool_sha256': sha256_file(__file__)}
    doc = read_json(action_json)
    res['action_json_sha256'] = sha256_file(action_json)
    md = doc.get('metadata') if isinstance(doc.get('metadata'), dict) else {}
    res['sdmpc_active'] = md.get('sdmpc_active')
    res['keyed'] = {'k92_w': 'k92_w' in md, 'k92_hb': 'k92_hb' in md}
    want = out_signature(doc)
    errors = sorted(p.name for p in hook_dir.glob('hook_error_*.txt')) + \
        sorted(p.name for p in hook_dir.glob('hook_setup_error_*.txt')) if hook_dir.is_dir() else []
    loaded = []
    for p in sorted(hook_dir.glob('loaded_*.json')) if hook_dir.is_dir() else []:
        try:
            j = read_json(p)
        except Exception as exc:  # noqa: BLE001
            errors.append('%s unreadable: %r' % (p.name, exc))
            continue
        loaded.append({'pid': j.get('pid'), 'argv0': j.get('argv0'), 'recorder_ok': j.get('recorder_ok')})
    res['loaded'] = loaded
    if any(x.get('recorder_ok') is not True for x in loaded):
        errors.append('loaded_*.json with recorder_ok not true')
    cands = []
    for folder in sorted(hook_dir.glob('c_*')) if hook_dir.is_dir() else []:
        if not folder.is_dir():
            continue
        cj, rj = folder / 'cand.json', folder / 'k92_record.json'
        if not cj.is_file() or not rj.is_file():
            errors.append('%s lacks cand.json or k92_record.json' % folder.name)
            continue
        m = read_json(cj)
        c = {'folder': folder.name, 'pid': m.get('pid'), 'seq': m.get('seq'), 'argv0': m.get('argv0'),
             'is_ad': bool(m.get('is_ad')), 'time_ns': m.get('time_ns'), 'hook_sec': m.get('hook_sec'),
             'n_states': m.get('n_states'), 'record_errors': len(m.get('record_errors') or [])}
        c['m1_signature'] = sig_equal(m.get('signature'), want)
        c['m2_time'] = (m.get('first_row_start_sec') == T and m.get('dt_sec') == 150.0
                        and isinstance(m.get('n_residence_rows'), int) and m.get('n_residence_rows') > 0)
        c['match'] = c['m1_signature'] and c['m2_time']
        cands.append(c)
    res['candidates'] = cands
    res['n_candidates'] = len(cands)
    res['errors'] = errors
    res['hook_sec_total'] = math.fsum(float(c['hook_sec']) for c in cands if isinstance(c['hook_sec'], (int, float)))
    matches = sorted((c for c in cands if c['match']),
                     key=lambda c: (c['is_ad'], c['time_ns'] or 0, c['pid'] or 0, c['seq'] or 0))
    res['n_match'] = len(matches)
    res['chosen'] = None
    if errors:
        res['status'] = 'hook_error'
    elif not any(x.get('argv0') == ADAPTER for x in loaded):
        res['status'] = 'no_hook'
    elif not cands:
        res['status'] = 'no_candidate'
    elif not matches:
        res['status'] = 'no_match'
    else:
        recs = [read_json(hook_dir / c['folder'] / 'k92_record.json') for c in matches]
        base = recs[0]
        same = all(close(r.get('blocks'), base.get('blocks')) and close(r.get('horizon'), base.get('horizon'))
                   for r in recs[1:])
        if not same:
            res['status'] = 'match_conflict'
        else:
            c = matches[0]
            src = hook_dir / c['folder']
            shutil.copy2(src / 'k92_record.json', dest / 'k92_record.json')
            chosen = {'folder': c['folder'], 'pid': c['pid'], 'seq': c['seq'], 'is_ad': c['is_ad'],
                      'record_sha256': sha256_file(dest / 'k92_record.json')}
            if (src / 'k92_series.npz').is_file():
                shutil.copy2(src / 'k92_series.npz', dest / 'k92_series.npz')
                chosen['series_sha256'] = sha256_file(dest / 'k92_series.npz')
            else:
                chosen['series_sha256'] = None
            if chosen['record_sha256'] != sha256_file(src / 'k92_record.json'):
                raise SystemExit('copied record differs from its source')
            res['chosen'] = chosen
            res['status'] = 'selected'
    with open(dest / 'k92_select.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, sort_keys=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    s = sub.add_parser('select')
    s.add_argument('--hook-dir', required=True)
    s.add_argument('--action-json', required=True)
    s.add_argument('--T', required=True, type=float)
    s.add_argument('--dest', required=True)
    args = ap.parse_args(argv)
    if args.cmd != 'select':
        ap.print_usage()
        return 2
    r = select(args.hook_dir, args.action_json, args.T, args.dest)
    print('K92VB_SELECT T=%s status=%s candidates=%d match=%d' % (r['T'], r['status'], r['n_candidates'],
                                                                  r['n_match']), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
