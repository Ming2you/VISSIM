"""VerifyGates 2 — G-K4 plant rows recomputed from the raw files (amendment 29 section 5, D-K9-55; amendment 30
section 4.5: after the J / F values are fixed and after the post30 LOG line).  No harness / judge import.

Rows: K9-2-1 W and K9-2-2 B1 x {TL3_1500_SAF_OBS_H3, TL3_1050_s43_SAF_OBS_H3} (v3c3-s31 1500, v3c3-s43 1050 only; no
v3c3-s47 file is opened).  Old = OK2/probe_a25/plant/sa/jobs/k92p{W,B1}/<job>, new = OK2/sealed_s47/K9-2-{1,2}/plant/
new/sa/jobs/k92{1,2}g4{W,B1}/<job>; files summary.json and k92_record.json.
Rule (G-K0 plant G5 rule written from the text): numeric leaves bit-equal (NaN = NaN), string leaves equal except
sha / hash keys and strings holding one of the four roots (TK/a25/k92b1_probe, TK/k92{1,2}_pl, OK2/probe_a25/plant,
OK2/sealed_s47/K9-2-{1,2}/plant/new), no one-sided leaf (timing words and G5 exclusion words left out everywhere) ->
PASS; only numeric differences, all within relative 1e-9 -> EXPLAIN; otherwise FAIL.  A row: FAIL if a file FAILs,
else EXPLAIN if a file EXPLAINs, else PASS.  Pass = every recomputed row and file verdict equals the recorded one
(OK2/a27/judge/rjg4.json plant rows: verdict, parts.<file>.verdict).  Blind output (verdicts, counts, paths)."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

OK2A = V.OK2 / 'probe_a25'
ROWS = []
for commit, arm, n in (('K9-2-1', 'W', '1'), ('K9-2-2', 'B1', '2')):
    for job in ('TL3_1500_SAF_OBS_H3', 'TL3_1050_s43_SAF_OBS_H3'):
        ROWS.append(('plant_%s_%s' % (commit, job),
                     OK2A / 'plant' / 'sa' / 'jobs' / ('k92p%s' % arm) / job,
                     V.SEALED / commit / 'plant' / 'new' / 'sa' / 'jobs' / ('k92%sg4%s' % (n, arm)) / job,
                     [V.TK / 'a25' / 'k92b1_probe', V.TK / ('k92%s_pl' % n), OK2A / 'plant',
                      V.SEALED / commit / 'plant' / 'new']))


def main():
    fixed, which = V.jf_fixed()
    if not fixed:
        raise SystemExit('J / F values are not fixed in the LOG (%s)' % which)
    log = V.LOG_MD.read_text(encoding='utf-8')
    if 'k92t30 구동기: J·F 판정 값 고정 확인' not in log:
        raise SystemExit('no post30 LOG line (amendment 30 section 4.5)')
    rec = V.rjson(V.OK2 / 'a27' / 'judge' / 'rjg4.json') or {}
    rrows = rec.get('rows') or {}
    out = {'schema': 'vg3-gk4-plant/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)),
           'recorded_sha256': V.sha_file(V.OK2 / 'a27' / 'judge' / 'rjg4.json'), 'rows': {}}
    agree = True
    for name, old, new, roots in ROWS:
        parts, vs = {}, []
        for fn in ('summary.json', 'k92_record.json'):
            a, b = V.rjson(old / fn), V.rjson(new / fn)
            if not isinstance(a, dict) or not isinstance(b, dict):
                parts[fn] = {'verdict': 'INCOMPLETE'}
                vs.append('INCOMPLETE')
                continue
            c = V.g5_compare(a, b, roots, tol_rel=1e-9)
            if c['numeric_differ'] == 0 and c['string_differ'] == 0 and c['one_sided'] == 0 and c['depth_cut'] == 0:
                v = 'PASS'
            elif c['string_differ'] == 0 and c['one_sided'] == 0 and c['numeric_above_tol'] == 0:
                v = 'EXPLAIN'
            else:
                v = 'FAIL'
            c['verdict'] = v
            parts[fn] = c
            vs.append(v)
        row_v = ('INCOMPLETE' if 'INCOMPLETE' in vs else 'FAIL' if 'FAIL' in vs else 'EXPLAIN' if 'EXPLAIN' in vs
                 else 'PASS')
        r = rrows.get(name) or {}
        same = (r.get('verdict') == row_v and all(((r.get('parts') or {}).get(fn) or {}).get('verdict') ==
                                                   parts[fn]['verdict'] for fn in parts))
        agree &= same
        out['rows'][name] = {'verdict': row_v, 'parts': parts, 'recorded_verdict': r.get('verdict'),
                             'recorded_parts': {fn: ((r.get('parts') or {}).get(fn) or {}).get('verdict') for fn in parts},
                             'same_as_recorded': same, 'old': str(old), 'new': str(new)}
    out['agree_all'] = bool(agree) and len(out['rows']) == 4
    V.wjson(V.OUTV / 'gk4_plant.json', out)
    print('VG3_GK4 rows=%s agree=%s' % ({k: v['verdict'] for k, v in out['rows'].items()}, out['agree_all']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
