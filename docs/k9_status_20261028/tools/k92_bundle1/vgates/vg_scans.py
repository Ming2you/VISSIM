"""VerifyGates: the k92t start scans recomputed with own code (no harness import), plus the section 5.4 file-time check.
Run after the k92t start, so it shows the state now; files added since (k92t outputs are excluded by definition)
are listed by name.
  sealed   amendment 25 section 6.5-3/5: every file under OK2/sealed_s47/<K9-2-0..3> re-hashed (sha256 of the whole
           bytes, nothing parsed) = the inventory of OK2/commit/<c>/sealed_s47_index.json (set, size, sha); n_runs =
           runs listed; every run stdout file in the inventory; a27: the files = the runs' stdout files, sizes equal.
  leak     amendment 25 section 6.5-4: declared roots OK2/commit/** (*.txt *.log *.jsonl *.md *.json), OK2/probe/**,
           OK2/probe_a25/**, OK2/logs/**, KB/** (*.txt *.log *.jsonl *.md); a line counts when the job-name form and
           (value form or job-line form) match (the three regexes of the amendment, verbatim); report-only: OK2/a27,
           OK2/a29 (same extensions + .json).  File names and line counts only.
  blind    amendment 24 section 3.1-3b + amendment 25 section 8.2 (non-sealed part): JSON under OK2/probe, OK2/commit,
           KB/k92_probe, OK2/probe_a25, KB/k92_probe_a25: k92_vissim_ref.json s47 entry = states only, every state
           {value: null, reason: k92_blind_s47}; k92_record.json of seed 47 (field or path) VISSIM side null with that
           reason; any other JSON holding a VR key name and an s47 context = bad.  Names and counts only.
  primary  S-K10: no name (folder or file) of an F primary-sample state (capture folder <T:06d>_s47..., job label
           <H>_<T>_s47_...) under OK2 (OK2/k92t excluded) and D:/VISSIM-merge/k8_gate_trees/k92b1.
  ftime    amendment 24 section 5.4: the F primary-sample folders under OK2/k92t/f_* (names only) all have mtime
           after the k92t start record (2026-10-20 21:45:53) and OK2/k92t/f_* roots were created after it.

    python -B vg_scans.py --dest <json>
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
SEALED = OK2 / 'sealed_s47'
KB = HERE.parent
TK = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1')
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
NAME = re.compile(r'_s47_|s47_|_s47(?![0-9A-Za-z])')
VALUE = re.compile(r'objective=[^\s`<]*\d|continuous_scalar\w*[\s=:]+[^\s`<]*\d')
JOBL = re.compile(r'SA_JOB [^\s`<]*(?:_s47_|s47_|_s47(?![0-9A-Za-z]))')
TEXT = ('.txt', '.log', '.jsonl', '.md')
VR_KEYS = (b'"m1_T150"', b'"m1_T450"', b'"m2_T150"', b'"m2_T450"', b'"m3_T150"', b'"m3_T450"', b'"m1_by_link_T',
           b'"m2_by_head_T', b'"m3_by_head_T')
START = time.mktime(time.strptime('2026-10-20 21:45:53', '%Y-%m-%d %H:%M:%S'))


def walk_files(root):
    out = {}
    if not Path(root).exists():
        return out
    for base, dirs, names in os.walk(V.lp(root)):
        for n in names:
            full = os.path.join(base, n)
            out[os.path.relpath(full, V.lp(root)).replace('\\', '/')] = full
    return out


def sealed():
    res, ok = {'top': sorted(os.listdir(V.lp(SEALED)))}, True
    ok &= res['top'] == ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27']
    total = 0
    for c in ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3'):
        idx = V.rjson(OK2 / 'commit' / c / 'sealed_s47_index.json') or {}
        inv = idx.get('inventory') or {}
        have = walk_files(SEALED / c)
        total += len(have)
        changed = []
        for rel in sorted(set(inv) & set(have)):
            size, sha = inv[rel][0], inv[rel][-1]
            if os.stat(have[rel]).st_size != size or V.sha_file(have[rel]) != sha:
                changed.append(rel)
        runs = idx.get('runs') or []
        run_file_bad = [r.get('name') for r in runs
                        if any(rel not in inv or inv[rel][0] != v[0] or inv[rel][-1] != v[-1]
                               for rel, v in (r.get('files') or {}).items())]
        row = {'n_inventory': len(inv), 'n_files': len(have), 'missing': sorted(set(inv) - set(have))[:10],
               'extra': sorted(set(have) - set(inv))[:10], 'n_changed': len(changed), 'changed': changed[:10],
               'n_runs': idx.get('n_runs'), 'runs_listed': len(runs),
               'stdout_not_in_inventory': [r.get('stdout_file') for r in runs if r.get('stdout_file') not in inv],
               'runs_files_not_matching_inventory': run_file_bad, 'runs_rc': [r.get('rc') for r in runs],
               'index_sha256': V.sha_file(OK2 / 'commit' / c / 'sealed_s47_index.json')}
        ok &= (not row['missing'] and not row['extra'] and not changed and row['n_runs'] == len(runs)
               and not row['stdout_not_in_inventory'] and not run_file_bad and len(inv) > 0)
        res[c] = row
    idx = V.rjson(OK2 / 'a27' / 'sealed_index.json') or {}
    runs = idx.get('runs') or []
    have = walk_files(SEALED / 'a27')
    want = {'logs/' + r.get('stdout_file', ''): r.get('size') for r in runs}
    res['a27'] = {'runs': len(runs), 'files': sorted(have), 'set_equal': set(want) == set(have),
                  'sizes_equal': all(rel in have and os.stat(have[rel]).st_size == s for rel, s in want.items()),
                  'sha256': {rel: V.sha_file(p) for rel, p in have.items()}}
    ok &= bool(runs) and res['a27']['set_equal'] and res['a27']['sizes_equal']
    res['n_files_hashed'] = total + len(have)
    res['ok'] = bool(ok)
    return res


def leak_file(full):
    n = 0
    with open(V.lp(full), 'rb') as f:
        for raw in f:
            s = raw.decode('utf-8', 'replace')
            if NAME.search(s) and (VALUE.search(s) or JOBL.search(s)):
                n += 1
    return n


def leak():
    decl = [(OK2 / 'commit', TEXT + ('.json',)), (OK2 / 'probe', TEXT), (OK2 / 'probe_a25', TEXT),
            (OK2 / 'logs', TEXT), (KB, TEXT)]
    rep = [(OK2 / 'a27', TEXT + ('.json',)), (OK2 / 'a29', TEXT + ('.json',))]
    out = {}
    for key, roots in (('declared', decl), ('report_only', rep)):
        nfiles, hits, newer = 0, {}, 0
        for root, exts in roots:
            for rel, full in walk_files(root).items():
                if os.path.splitext(rel)[1].lower() not in exts:
                    continue
                nfiles += 1
                if os.stat(full).st_mtime > START:
                    newer += 1
                k = leak_file(full)
                if k:
                    hits[full.replace('\\\\?\\', '')] = k
        out[key] = {'files': nfiles, 'files_modified_after_k92t_start': newer, 'leak_files': len(hits),
                    'leak_lines': sum(hits.values()), 'hit_files': sorted(hits)[:30]}
    ctrl = {'SA_JOB TL3_2400_s47 exit=0 wall=12.0 ok=True objective=4711.25': True,
            'continuous_scalar_done 4711.2 job_s47_x': True,
            'rule text: `_s47_` with `objective=` / `continuous_scalar` / `SA_JOB `': False,
            'SA_JOB TL3_2400_s47 exit=1 wall=3.0 ok=False objective=None': True,
            'SA_JOB TL3_2400_s43_SAF_OBS_H3 exit=0 ok=True objective=1.5': False}
    out['controls_ok'] = all(bool(NAME.search(s) and (VALUE.search(s) or JOBL.search(s))) == w for s, w in ctrl.items())
    out['ok'] = out['declared']['leak_lines'] == 0 and out['controls_ok']
    return out


def s47_path(p):
    for part in re.split(r'[\\/]', str(p).lower()):
        if part == 's47' or part.endswith('_s47') or '_s47_' in part or part.startswith('s47_'):
            return True
    return False


def blind():
    roots = [OK2 / 'probe', OK2 / 'commit', KB / 'k92_probe', OK2 / 'probe_a25', KB / 'k92_probe_a25']
    bad, n = [], {'json': 0, 'vissim_ref': 0, 'record': 0, 'record_s47': 0, 'vr_key_json': 0}
    for root in roots:
        for rel, full in walk_files(root).items():
            if not rel.lower().endswith('.json'):
                continue
            n['json'] += 1
            name = rel.rsplit('/', 1)[-1]
            shown = full.replace('\\\\?\\', '')
            if name == 'k92_vissim_ref.json':
                n['vissim_ref'] += 1
                d = V.rjson(full) or {}
                e = (d.get('seeds') or {}).get('s47')
                if e is not None:
                    other = sorted(k for k in e if k != 'states')
                    nonnull = [T for T, v in (e.get('states') or {}).items()
                               if not (isinstance(v, dict) and set(v) == {'value', 'reason'} and v['value'] is None
                                       and v['reason'] == 'k92_blind_s47')]
                    if other or nonnull:
                        bad.append([shown, 'vissim_ref s47 not blind'])
                continue
            if name == 'k92_record.json':
                n['record'] += 1
                d = V.rjson(full) or {}
                if str(d.get('seed')) == '47' or s47_path(full):
                    n['record_s47'] += 1
                    if d.get('vissim') is not None or d.get('vissim_reason') != 'k92_blind_s47':
                        bad.append([shown, 'record s47 VISSIM side not blind'])
                continue
            data = open(V.lp(full), 'rb').read()
            if any(t in data for t in VR_KEYS):
                n['vr_key_json'] += 1
                if s47_path(full) or b'"s47"' in data:
                    bad.append([shown, 'VR key names with s47 context'])
    return {'ok': not bad, 'n_bad': len(bad), 'bad': bad[:20], 'counts': n}


def primary():
    comps = [re.compile(r'^0*%d_s47(?:_|$)' % T) for T in F_PRIMARY]
    labs = [re.compile(r'^[A-Z0-9]+_%d_s47_' % T) for T in F_PRIMARY]
    hits, n = [], 0
    outk = os.path.normcase(os.path.abspath(str(OUTK)))
    for root in (OK2, TK):
        for base, dirs, names in os.walk(V.lp(root)):
            plain = base.replace('\\\\?\\', '')
            if os.path.normcase(os.path.abspath(plain)) == outk:
                dirs[:] = []
                continue
            for d in dirs + names:
                n += 1
                if any(r.search(d) for r in comps) or any(r.search(d) for r in labs):
                    hits.append(os.path.join(plain, d))
    return {'ok': not hits, 'n_names': n, 'n_hits': len(hits), 'hits': hits[:30]}


def ftime():
    rows, ok = {}, True
    for arm in ('f_off', 'f_w', 'f_b1'):
        root = OUTK / arm
        st = os.stat(V.lp(root))
        cap = [root / 'sa' / 'cap' / 'k92t' / 'TL3' / ('%06d_s47' % T) for T in F_PRIMARY]
        job = [root / 'sa' / 'jobs' / 'k92t' / ('TL3_%d_s47_SAF_OBS_H3' % T) for T in F_PRIMARY]
        rep = [root / 'replays' / 's47' / ('%06d' % T) for T in F_PRIMARY]
        present = {k: sum(1 for p in v if p.exists()) for k, v in (('cap', cap), ('job', job), ('replay', rep))}
        mt = [os.stat(V.lp(p)).st_mtime for v in (cap, job, rep) for p in v if p.exists()]
        rows[arm] = {'root_ctime_after_start': st.st_ctime > START, 'present': present,
                     'min_mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(min(mt))) if mt else None,
                     'all_after_start': all(t > START for t in mt) and bool(mt)}
        ok &= rows[arm]['all_after_start'] and rows[arm]['root_ctime_after_start']
    return {'ok': bool(ok), 'rows': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    t0 = time.time()
    res = {'schema': 'vgates-scans/v1', 'when': time.strftime('%Y-%m-%dT%H:%M:%S')}
    for k, fn in (('ftime', ftime), ('primary', primary), ('blind', blind), ('leak', leak), ('sealed', sealed)):
        t = time.time()
        res[k] = fn()
        res[k]['sec'] = round(time.time() - t, 1)
        print('VG_SCAN %s ok=%s sec=%s' % (k, res[k]['ok'], res[k]['sec']), flush=True)
    res['ok'] = all(res[k]['ok'] for k in ('sealed', 'leak', 'blind', 'primary', 'ftime'))
    res['sec'] = round(time.time() - t0, 1)
    V.wjson(args.dest, res)
    print('VG_SCANS ok=%s' % res['ok'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
