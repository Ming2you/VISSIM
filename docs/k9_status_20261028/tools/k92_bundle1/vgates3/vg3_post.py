"""VerifyGates 2 — post steps recomputed (amendment 30 section 4.5; the sealed-root rules of section 10-15 declared
here before the first run).  No harness / driver / judge import.  Runs only when the J / F values are fixed.

  sealed tops   OK2/sealed_s47 holds exactly K9-2-0, K9-2-1, K9-2-2, K9-2-3, a27, k92t.
  sealed index  K9-2-0..3: every file of OK2/commit/<c>/sealed_s47_index.json 'inventory' re-hashed (size, sha) and the
                file set equal; a27: OK2/a27/sealed_index.json runs -> logs/<stdout_file> sizes and set equal;
                k92t: OK2/a30/sealed_k92t_index.json files -> 'to' present with size / sha, 'from' absent, n = 3.
  record scan   every k92_record.json under OK2/sealed_s47.  Declared s47 rule (this verification): a record is a
                v3c3-s47 record iff its 'seed' field is 47 or a path component BELOW the sealed root (relative path)
                is 's47', ends with '_s47', holds '_s47_' or starts with 's47_'.  Each s47 record must have vissim null
                and vissim_reason 'k92_blind_s47' (amendment 24 section 3.1-3b).  The literal base rule (the same test
                on the full path, sealed root name included) is recomputed beside it (report / diagnosis).
                Counts only (no value): files, by seed field, s47 (declared / literal), bad (declared / literal).
  base records  the 11 inherited OUTK records of amendment 30 section 0 byte-equal.
  stops         OUTK STOP files, stage records present (seal30 / f / jb with driver k92t30 and the amendment-30 sha;
                post absent), steps.jsonl rc != 0 after line 59.
Output OUTV/post.json."""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

TOPS = ['K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3', 'a27', 'k92t']
A30 = 'ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a'
RECORDED = {'STOP_f.json': 'ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17',
            'k92_judging_stage.json': '34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5',
            'start/scans.json': '410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8',
            'stages/start.json': 'f3ed1dcea6f86b6c750368e9b5b2082331a9c85f18d435b9eac6af46744eef13',
            'stages/prep.json': '9ef3a7edd7e5a7c1d5938161c27c1f1bde5394da84d7cc61181876d78cfbc533',
            'stages/j0.json': '3845def6bbc0d95935fac27f36a24b13a5938d111aa11f1f7d93548f3f216631',
            'stages/ja.json': 'b40593bb34f45074546d58c808912ee4cffa6ff95dd0b5d3ac3543c89368b03c',
            'judge/j0.json': '24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1',
            'judge/ja.json': '74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c',
            'judge/jwall.json': '1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a',
            'f_vref/sa/k92_vissim_ref.json': '09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a'}


def s47_part(p):
    return p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_')


def walk_files(root):
    out = {}
    for base, dirs, names in os.walk(V.lp(root)):
        for n in names:
            full = os.path.join(base, n)
            out[os.path.relpath(full, V.lp(root)).replace('\\', '/')] = full
    return out


def sealed_index():
    res, ok = {}, True
    tops = sorted(p.name for p in V.SEALED.iterdir())
    res['tops'] = tops
    ok &= tops == TOPS
    for c in ('K9-2-0', 'K9-2-1', 'K9-2-2', 'K9-2-3'):
        idx = V.rjson(V.OK2 / 'commit' / c / 'sealed_s47_index.json') or {}
        inv = idx.get('inventory') or {}
        have = walk_files(V.SEALED / c)
        bad = [r for r in sorted(set(inv) & set(have))
               if os.stat(have[r]).st_size != inv[r][0] or V.sha_file(have[r]) != inv[r][-1]]
        row = {'n_inventory': len(inv), 'n_files': len(have), 'missing': len(set(inv) - set(have)),
               'extra': len(set(have) - set(inv)), 'changed': len(bad), 'changed_paths': bad[:10]}
        row['ok'] = bool(inv) and not row['missing'] and not row['extra'] and not bad
        ok &= row['ok']
        res[c] = row
    idx = V.rjson(V.OK2 / 'a27' / 'sealed_index.json') or {}
    runs = idx.get('runs') or []
    have = walk_files(V.SEALED / 'a27')
    want = {'logs/' + r.get('stdout_file', ''): r.get('size') for r in runs}
    row = {'runs': len(runs), 'set_equal': set(want) == set(have),
           'sizes_equal': all(k in have and os.stat(have[k]).st_size == v for k, v in want.items())}
    row['ok'] = bool(runs) and row['set_equal'] and row['sizes_equal']
    ok &= row['ok']
    res['a27'] = row
    idx = V.rjson(V.OUT30 / 'sealed_k92t_index.json') or {}
    files = idx.get('files') or []
    have = walk_files(V.SEALED / 'k92t')
    rows = []
    for r in files:
        to = Path(r['to'])
        rows.append(to.is_file() and os.path.getsize(to) == r['size'] and V.sha_file(to) == r['sha256']
                    and not Path(r['from']).exists())
    row = {'n': idx.get('n'), 'files': len(files), 'all_ok': all(rows) and len(rows) == 3,
           'set_equal': sorted(have) == sorted('logs/' + Path(r['to']).name for r in files),
           'amendment30_sha256_ok': idx.get('amendment30_sha256') == A30,
           'index_sha256': V.sha_file(V.OUT30 / 'sealed_k92t_index.json')}
    row['ok'] = row['n'] == 3 and row['all_ok'] and row['set_equal'] and row['amendment30_sha256_ok']
    ok &= row['ok']
    res['k92t'] = row
    res['ok'] = bool(ok)
    return res


def record_scan():
    out = {'files': 0, 'by_seed_field': {}, 's47_declared': 0, 's47_literal': 0, 'bad_declared': 0, 'bad_literal': 0,
           'seed_field_vs_path': 0, 'bad_literal_by_seed_field': {}, 'by_top': {}}
    root = V.lp(V.SEALED)
    for base, dirs, names in os.walk(root):
        for n in names:
            if n != 'k92_record.json':
                continue
            full = os.path.join(base, n)
            rel = os.path.relpath(full, root).replace('\\', '/')
            d = V.rjson(full) or {}
            out['files'] += 1
            sf = str(d.get('seed'))
            out['by_seed_field'][sf] = out['by_seed_field'].get(sf, 0) + 1
            top = rel.split('/')[0]
            out['by_top'][top] = out['by_top'].get(top, 0) + 1
            rel_parts = [p.lower() for p in rel.split('/')]
            full_parts = [p.lower() for p in full.replace('\\\\?\\', '').replace('\\', '/').split('/')]
            path_s47 = any(s47_part(p) for p in rel_parts)
            declared = sf == '47' or path_s47
            literal = sf == '47' or any(s47_part(p) for p in full_parts)
            if (sf == '47') != path_s47:
                out['seed_field_vs_path'] += 1
            blind = d.get('vissim') is None and d.get('vissim_reason') == 'k92_blind_s47'
            if declared:
                out['s47_declared'] += 1
                out['bad_declared'] += not blind
            if literal:
                out['s47_literal'] += 1
                if not blind:
                    out['bad_literal'] += 1
                    out['bad_literal_by_seed_field'][sf] = out['bad_literal_by_seed_field'].get(sf, 0) + 1
    out['ok_declared'] = out['bad_declared'] == 0 and out['seed_field_vs_path'] == 0
    out['ok_literal'] = out['bad_literal'] == 0
    return out


def main():
    fixed, which = V.jf_fixed()
    if not fixed:
        raise SystemExit('J / F values are not fixed in the LOG (%s): the sealed root is not opened' % which)
    out = {'schema': 'vg3-post/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)), 'jf_fixed': which}
    out['sealed_index'] = sealed_index()
    out['record_scan'] = record_scan()
    out['base_records'] = {k: (V.OUTK / k).is_file() and V.sha_file(V.OUTK / k) == v for k, v in RECORDED.items()}
    out['base_records_ok'] = all(out['base_records'].values())
    out['stop_files'] = sorted(p.name for p in V.OUTK.glob('STOP_*.json'))
    out['stop_post'] = V.rjson(V.OUTK / 'STOP_a30_post.json')
    st = {}
    for s in ('seal30', 'f', 'jb', 'post'):
        r = V.rjson(V.OUTK / 'stages' / ('%s.json' % s))
        st[s] = None if r is None else {'ok': r.get('ok'), 'driver': r.get('driver'),
                                        'a30': r.get('amendment30_sha256') == A30}
    out['stages'] = st
    rows = [json.loads(x) for x in (V.OUTK / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    out['steps_after_59'] = {'n': len(rows) - 59, 'rc_nonzero': [[i + 1, r['name'], r.get('rc')] for i, r in
                                                                enumerate(rows) if i >= 59 and r.get('rc') != 0],
                             'vissim_nonzero': [r['name'] for r in rows[59:] if r.get('vissim_pre') not in (0, None)
                                                or r.get('vissim_post') not in (0, None)]}
    sr = V.rjson(V.OUTK / 'judge' / 'sealed_records.json') or {}
    out['recorded_sealed_records'] = {'sha256': V.sha_file(V.OUTK / 'judge' / 'sealed_records.json') if (
                                          V.OUTK / 'judge' / 'sealed_records.json').is_file() else None,
                                      'ok': sr.get('ok'), 'sealed_records': sr.get('sealed_records'),
                                      'n_bad': sr.get('n_bad')}
    rs = out['record_scan']
    out['literal_rule_reproduces_recorded'] = ((sr.get('sealed_records') or {}).get('files') == rs['files']
                                               and (sr.get('sealed_records') or {}).get('s47') == rs['s47_literal']
                                               and (sr.get('sealed_records') or {}).get('bad') == rs['bad_literal'])
    V.wjson(V.OUTV / 'post.json', out)
    print('VG3_POST sealed_index=%s files=%s s47_declared=%s bad_declared=%s s47_literal=%s bad_literal=%s by_seed=%s '
          'base=%s literal_reproduces=%s' % (out['sealed_index']['ok'], rs['files'], rs['s47_declared'],
                                            rs['bad_declared'], rs['s47_literal'], rs['bad_literal'],
                                            rs['by_seed_field'], out['base_records_ok'],
                                            out['literal_rule_reproduces_recorded']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
