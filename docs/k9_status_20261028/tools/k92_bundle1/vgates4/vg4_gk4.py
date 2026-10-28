"""VerifyGates 3 -- V1: G-K4 plant rows recomputed from raw data (amendment 31 section 4.3 V1 = amendment 29 section 5;
rule text: amendment 24 section 4.3 G-K0 plant, amendment 27 section 2.3 end and section 5.2, amendment 18 section 3.3
G5).  Written from the text; imports no harness / driver / judge / earlier verification tool.

Rows: K9-2-1 W and K9-2-2 B1 x {TL3_1500_SAF_OBS_H3, TL3_1050_s43_SAF_OBS_H3}.
Old side: OK2/probe_a25/plant/sa/jobs/k92p{W,B1}/<job>; new side: OK2/sealed_s47/K9-2-{1,2}/plant/new/sa/jobs/
k92{1,2}g4{W,B1}/<job>; files summary.json and k92_record.json.  Roots (path strings): TK/a25/k92b1_probe,
TK/k92{1,2}_pl, OK2/probe_a25/plant, OK2/sealed_s47/K9-2-{1,2}/plant/new.

Leaves: a JSON document is flattened into path -> value with paths '/key/key[i]/key' (dict keys, list indices).
  numeric leaf = int / float (not bool); string leaf = str; bool / null leaves are 'other' (reported, not judged).
Excluded leaves (the G5 declared exclusions, amendment 18 section 3.3 and the constants amendment 27 section 2.3 names
  by line): a leaf whose lower-cased path contains a timing word (wall, sec, time, rss, elapsed) or a G5 exclusion
  token (template_sha256, /tree, /label, /template, /forecast_long, /coord, /job_path, /eo_dir, /replay, /robs, /root,
  path, python_hash_seed, capture_spec).  /k8b0 and signal_queue leaves ARE compared (G5).
Per file:
  * numeric leaves on both sides: equal (int == int exactly, else float ==; NaN == NaN) -- bit-equal in value;
  * string leaves on both sides: equal, except (i) a sha / hash key (lower-cased path with 'hash', or 'sha' not
    touching a letter a-z on either side) -- listed; (ii) a path string: either value contains one of the four roots
    ('/' form, lower case) -- listed (and, report only, whether the two values are equal after the roots are replaced
    by '<root>');
  * a judged leaf on one side only, or a numeric leaf facing a string leaf: not allowed;
  * PASS = no numeric difference, no non-exempt string difference, nothing one-sided, no kind clash;
    EXPLAIN = only numeric differences, each with |x-y| / max(|x|, |y|) <= 1e-9;  FAIL otherwise.
Row = FAIL if a file FAILs, else EXPLAIN if a file EXPLAINs, else PASS; INCOMPLETE when a file is missing/unreadable.
Output is blind: verdicts, counts, leaf paths only (values stay in memory).
"""
import math
import re
from pathlib import Path

import vg4lib as V

SKIP = ('wall', 'sec', 'time', 'rss', 'elapsed')
G5_EXCLUDE = ('template_sha256', '/tree', '/label', '/template', '/forecast_long', '/coord', '/job_path', '/eo_dir',
              '/replay', '/robs', '/root', 'path', 'python_hash_seed', 'capture_spec')
GENERAL_ONLY = ('/k8b0', 'signal_queue', '/k8b/')     # in the general EXCLUDE but compared by G5 (report only)
TOL = 1e-9
ROWS = (('K9-2-1', 'W', 'k921'), ('K9-2-2', 'B1', 'k922'))
JOBS = ('TL3_1500_SAF_OBS_H3', 'TL3_1050_s43_SAF_OBS_H3')
FILES = ('summary.json', 'k92_record.json')


def flatten(doc, path='', out=None):
    out = {} if out is None else out
    if isinstance(doc, dict):
        for k in doc:
            flatten(doc[k], '%s/%s' % (path, k), out)
    elif isinstance(doc, list):
        for i, x in enumerate(doc):
            flatten(x, '%s[%d]' % (path, i), out)
    else:
        out[path] = doc
    return out


def kind(v):
    if isinstance(v, bool) or v is None:
        return 'other'
    if isinstance(v, (int, float)):
        return 'num'
    if isinstance(v, str):
        return 'str'
    return 'other'


def excluded(key):
    k = key.lower()
    return any(s in k for s in SKIP) or any(e in k for e in G5_EXCLUDE)


def hash_key(key):
    k = key.lower()
    return 'hash' in k or re.search(r'(?<![a-z])sha(?![a-z])', k) is not None


def num_equal(x, y):
    if isinstance(x, int) and isinstance(y, int):
        return x == y
    fx, fy = float(x), float(y)
    return fx == fy or (math.isnan(fx) and math.isnan(fy))


def rel_diff(x, y):
    fx, fy = float(x), float(y)
    if math.isnan(fx) or math.isnan(fy) or math.isinf(fx) or math.isinf(fy):
        return float('inf')
    d = max(abs(fx), abs(fy))
    return abs(fx - fy) / d if d > 0 else 0.0


def norm_roots(roots):
    return [str(r).replace('\\', '/').rstrip('/').lower() for r in roots if str(r).strip()]


def compare(a, b, roots):
    fa, fb = flatten(a), flatten(b)
    nroots = norm_roots(roots)
    r = {'leaves_a': len(fa), 'leaves_b': len(fb), 'excluded': 0, 'numeric_common': 0, 'string_common': 0,
         'numeric_differ': [], 'numeric_near': [], 'string_differ': [], 'hash_differ': [], 'hash_equal': 0,
         'path_differ': [], 'path_differ_beyond_root': [], 'one_sided': [], 'kind_clash': [],
         'other_differ': [], 'other_one_sided': [], 'general_only_compared': 0}
    for k in sorted(set(fa) | set(fb)):
        if excluded(k):
            r['excluded'] += 1
            continue
        if any(t in k.lower() for t in GENERAL_ONLY):
            r['general_only_compared'] += 1
        ina, inb = k in fa, k in fb
        ka = kind(fa[k]) if ina else None
        kb = kind(fb[k]) if inb else None
        if not (ina and inb):
            (r['other_one_sided'] if (ka or kb) == 'other' else r['one_sided']).append(k)
            continue
        if ka != kb:
            r['kind_clash'].append(k)
            continue
        x, y = fa[k], fb[k]
        if ka == 'other':
            if x != y:
                r['other_differ'].append(k)
            continue
        if ka == 'num':
            r['numeric_common'] += 1
            if not num_equal(x, y):
                (r['numeric_near'] if rel_diff(x, y) <= TOL else r['numeric_differ']).append(k)
            continue
        r['string_common'] += 1
        if hash_key(k):
            if x != y:
                r['hash_differ'].append(k)
            else:
                r['hash_equal'] += 1
            continue
        if x == y:
            continue
        nx, ny = x.replace('\\', '/').lower(), y.replace('\\', '/').lower()
        if any(rt and (rt in nx or rt in ny) for rt in nroots):
            r['path_differ'].append(k)
            sx, sy = nx, ny
            for rt in sorted(nroots, key=len, reverse=True):
                sx, sy = sx.replace(rt, '<root>'), sy.replace(rt, '<root>')
            if sx != sy:
                r['path_differ_beyond_root'].append(k)
            continue
        r['string_differ'].append(k)
    hard = r['string_differ'] or r['one_sided'] or r['kind_clash'] or r['numeric_differ']
    if hard:
        v = 'FAIL'
    elif r['numeric_near']:
        v = 'EXPLAIN'
    else:
        v = 'PASS'
    r['verdict'] = v
    blind = {k: (len(x) if isinstance(x, list) else x) for k, x in r.items()}
    blind['paths'] = {k: x[:50] for k, x in r.items() if isinstance(x, list) and x}
    blind['verdict'] = v
    return blind


def row_plan(P):
    plan = []
    for commit, arm, lab in ROWS:
        roots = [P['TKA'] / 'k92b1_probe', P['TK'] / (lab + '_pl'), P['OK2A'] / 'plant',
                 P['SEALED'] / commit / 'plant' / 'new']
        for job in JOBS:
            plan.append({'tag': 'plant_%s_%s' % (commit, job), 'commit': commit, 'arm': arm, 'job': job,
                         'old': P['OK2A'] / 'plant' / 'sa' / 'jobs' / ('k92p' + arm) / job,
                         'new': P['SEALED'] / commit / 'plant' / 'new' / 'sa' / 'jobs' / (lab + 'g4' + arm) / job,
                         'roots': roots})
    return plan


def s47_in(path):
    return any(p.lower() == 's47' or p.lower().endswith('_s47') or '_s47_' in p.lower() or p.lower().startswith('s47_')
               for p in re.split(r'[\\/]', str(path)))


def run_rows(P):
    out = {}
    for row in row_plan(P):
        rec = {'commit': row['commit'], 'arm': row['arm'], 'job': row['job'], 'parts': {}}
        if s47_in(row['job']):
            rec['verdict'] = 'INCOMPLETE'
            rec['why'] = 's47 job refused'
            out[row['tag']] = rec
            continue
        verdicts = []
        for name in FILES:
            a = V.read_json_or(Path(row['old']) / name, None)
            b = V.read_json_or(Path(row['new']) / name, None)
            if a is None or b is None:
                rec['parts'][name] = {'verdict': 'INCOMPLETE', 'old_read': a is not None, 'new_read': b is not None}
                verdicts.append('INCOMPLETE')
                continue
            c = compare(a, b, row['roots'])
            c['old_sha256'] = V.sha256_or_none(Path(row['old']) / name)
            c['new_sha256'] = V.sha256_or_none(Path(row['new']) / name)
            rec['parts'][name] = c
            verdicts.append(c['verdict'])
        rec['verdict'] = ('INCOMPLETE' if 'INCOMPLETE' in verdicts else 'FAIL' if 'FAIL' in verdicts
                          else 'EXPLAIN' if 'EXPLAIN' in verdicts else 'PASS')
        out[row['tag']] = rec
    return out


def compare_record(mine, rjg4):
    """Recorded rjg4.json plant rows: row verdict PASS and parts.<file>.verdict PASS, equal to mine."""
    rows = (rjg4 or {}).get('rows') or {}
    table = {}
    for tag, m in mine.items():
        r = rows.get(tag) or {}
        parts = r.get('parts') or {}
        t = {'record_row_verdict': r.get('verdict'), 'mine_row_verdict': m.get('verdict'),
             'record_parts': {f: (parts.get(f) or {}).get('verdict') for f in FILES},
             'mine_parts': {f: (m['parts'].get(f) or {}).get('verdict') for f in FILES}}
        t['same'] = (t['record_row_verdict'] == 'PASS' == t['mine_row_verdict']
                     and all(t['record_parts'][f] == 'PASS' == t['mine_parts'][f] for f in FILES))
        table[tag] = t
    plant_tags = sorted(k for k in rows if str(k).startswith('plant_'))
    return {'rows': table, 'record_plant_tags': plant_tags,
            'record_plant_tags_equal_plan': plant_tags == sorted(mine),
            'all_same': bool(table) and all(t['same'] for t in table.values()) and plant_tags == sorted(mine)}
