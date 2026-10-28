"""GB-7' report-only items (OG_METHOD.md section 2 "보고만" (a)(b) + A-item hit counts), amendment 21 section 8 "보고는
OG_METHOD §2 '보고만'(a)(b)를 그대로".  Not a judgement.  Reads OUTVA gb7/A bundles; writes OUTVA/judge/gb7_report.json.
(a) for each difference on R3-04/05/06: original value with the FRZ_K7 root prefix replaced by FRZ_K92 (case-insensitive,
    separators normalized) == replay value?  Values are printed only for the not-equal ones (paths; none expected).
(b) R3-03 input names (run_provenance/inputs/<name>/sha256, metadata side included); names outside
    {tuning_json, adapter_py, main_vbs_runner} listed apart.
Also: per A item, number of paths / decisions, max |delta| of numeric leaves (timing leaves only in practice), int leaves.
V-A copy of SP/j1/fix/gates/gb7_report.py (e41cb191...): expected values only (OUTVA, FRZ_K92 via gcommon, FRZ_K92 list
via gcommon.load_allowed() defaults; amendment 34 5.0 R4 item 1).  Items are list A items; E_K92 paths count as
'OUTSIDE' here (E1-E4 hits are in judge/gb7_result.json hits_by_item)."""
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gcommon as c  # noqa: E402

G, LREC = c.load_allowed()
R3_RE = re.compile(r'/(?:metadata/)?run_provenance/inputs/([^/]+)/sha256')
R3_EXPECTED = {'tuning_json', 'adapter_py', 'main_vbs_runner'}


def norm(p):
    return os.path.normcase(os.path.normpath(str(p)))


def diff_values(a, b, path='', out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', a.get(key, '<absent>'), b.get(key, '<absent>'), 'presence'))
            else:
                diff_values(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, len(a), len(b), 'list_length'))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff_values(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, a, b, 'value' if type(a) is type(b) else 'type'))
    return out


def int_leaves(doc):
    if isinstance(doc, dict):
        return sum(int_leaves(v) for v in doc.values())
    if isinstance(doc, list):
        return sum(int_leaves(v) for v in doc)
    return 1 if isinstance(doc, int) and not isinstance(doc, bool) else 0


def main():
    times = [1] + [150 * k for k in range(1, 61)]
    agg, r3a_n, r3a_eq, r3a_bad, names, ints = {}, 0, 0, [], set(), 0
    for T in times:
        s6 = '%06d' % T
        d = c.OUTV / 'gb7' / 'A' / ('T%s' % s6)
        a = c.read_json(d / 'original' / ('action_%s.json' % s6))
        b = c.read_json(d / 'replay' / ('action_%s.json' % s6))
        ints += int_leaves(a)
        seen = set()
        for p, va, vb, kind in diff_values(a, b):
            w = G.which(p) or 'OUTSIDE'
            h = agg.setdefault(w, {'paths': 0, 'decisions': 0, 'max_abs_delta': 0.0, 'kinds': {}})
            h['paths'] += 1
            if w not in seen:
                h['decisions'] += 1
                seen.add(w)
            h['kinds'][kind] = h['kinds'].get(kind, 0) + 1
            if kind == 'value' and isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
                h['max_abs_delta'] = max(h['max_abs_delta'], abs(float(vb) - float(va)))
            if w in ('R3-04', 'R3-05', 'R3-06'):
                r3a_n += 1
                ok = None
                if isinstance(va, str) and isinstance(vb, str):
                    na, nb = norm(va), norm(vb)
                    k7, kn = norm(c.FRZ7), norm(c.FRZN)
                    ok = (na.replace(k7, kn, 1) if na.startswith(k7) else na) == nb
                if ok:
                    r3a_eq += 1
                else:
                    r3a_bad.append({'T': T, 'path': p, 'item': w})
            m = R3_RE.fullmatch(p)
            if m and w == 'R3-03':
                names.add(m.group(1))
    rep = {'gate': "GB-7' report-only (OG_METHOD 2 (a)(b))", 'allowed_list': LREC, 'hits_by_item': agg,
           'r3_a': {'n_paths': r3a_n, 'n_prefix_substitution_equal': r3a_eq, 'not_equal': r3a_bad[:50]},
           'r3_b': {'names': sorted(names), 'outside_expected': sorted(names - R3_EXPECTED)},
           'int_leaves_original_total': ints}
    c.write_json(c.OUTV / 'judge' / 'gb7_report.json', rep)
    print('GB7_REPORT r3a=%d/%d r3b=%s outside=%s items=%s' % (
        r3a_eq, r3a_n, rep['r3_b']['names'], rep['r3_b']['outside_expected'],
        {k: (v['paths'], v['decisions']) for k, v in agg.items()}))


if __name__ == '__main__':
    main()
