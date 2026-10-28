"""VerifyGates: commit-gate records (K9-2-0..3, K9-2-4 a27, K9-2-5 a29) re-read, G-K5 medians recomputed from the raw
per-replay summaries, git state, and the VerifyImpl r3 independent re-comparison record re-read (sha + verdict counts).
Own code, no harness import, reads only.  G-K5 (a) (amendment 24 section 4.3 + amendment 26 D-K9-47): pairs (A0, B1)
and (A2, B3) per state S1-S4; clean = census vissim_any 0, vissim_count_pre 0, vissim_count_post 0, launch exit 0,
replay_run exit_code 0; ratio = replay_run.wall_sec B / A; PASS iff median <= 1.05 / 1.033718118959995 (IQR reported).

    python -B vg_commit.py --dest <json>
"""
import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
KB = HERE.parent
GWT8 = r'D:/VISSIM-merge/sim3-n31-k8'
LIMIT = 1.05 / 1.033718118959995
RECORDED = {
    'commit/K9-2-0/gates.json': '04a5f3161a9a77c44ccc8860e96d3c414f9e6909a80428353fa415f0b6374a16',
    'commit/K9-2-1/gates.json': 'dbf644937010c510a7a2de7336246ae0c1b78219192033e3d548d0a20c98aa24',
    'commit/K9-2-2/gates.json': '176dd263eb38b132e0b25ac18b86aa9ad73c5c65aa04c7f4f709f4a72f73420e',
    'commit/K9-2-3/gates.json': '064d1b4b62748d648e2379ace9cf89e5a0f210281724b77c01b59eb957906d71',
    'a27/gates.json': 'e57f1b3655b1f046820944cf0e55680a83d2f93b9f7f960f7d9e1acd3b8d2db6',
    'a29/gates.json': '129b642d4a53be61f520b26ac9a07f9d29a4de6ae74bdfc6b92eb498d9083f49',
}
WANT_STAGES = {
    'commit/K9-2-0/gates.json': ['pre', 'trees', 'diff0', 'pycompile', 'selftest', 'jb', 'U', 'gk0_plant', 'after'],
    'commit/K9-2-1/gates.json': ['pre', 'trees', 'U', 'B', 'gk0_dec', 'gk0_plant', 'gk1_static', 'gk1_dyn', 'gk2',
                                 'gk4', 'gk5', 'after'],
    'commit/K9-2-2/gates.json': ['pre', 'trees', 'U', 'B', 'gk0_dec', 'gk0_plant', 'gk1_static', 'gk1_dyn', 'gk2',
                                 'gk3', 'gk4', 'gk5', 'after'],
    'commit/K9-2-3/gates.json': ['pre', 'trees', 'gk0_dec', 'gk0_plant', 'gk3', 'after'],
}
COMMITS = [('K9-2-0', '1868b37c'), ('K9-2-1', '7ed49cdf'), ('K9-2-2', '2d5d95f0'), ('K9-2-3', 'b887f99f'),
           ('K9-2-4', 'bfd609c0'), ('K9-2-5', 'e27ceac8')]
R3_ITEMS = KB / 'vimpl_r3' / 'out' / 'items.jsonl'
R3_ITEMS_SHA = '5d400482f305d45336e1d4951ae4128ad4fbb5becd44de5a0070631bfc8f20b3'


def git(*a):
    return subprocess.run(['git', '--no-optional-locks', '-C', GWT8] + list(a), capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout.strip()


def gk5(commit):
    d = OK2 / 'commit' / commit / 'gk5'
    rows = []
    for s in ('S1', 'S2', 'S3', 'S4'):
        for a, b in (('A0', 'B1'), ('A2', 'B3')):
            ra = V.rjson(d / ('%s_%s.summary.json' % (s, a))) or {}
            rb = V.rjson(d / ('%s_%s.summary.json' % (s, b))) or {}

            def clean(r):
                return ((r.get('census_at_start') or {}).get('vissim_any') == 0 and r.get('vissim_count_pre') == 0
                        and r.get('vissim_count_post') == 0 and (r.get('launch') or {}).get('exit') == 0
                        and (r.get('replay_run') or {}).get('exit_code') == 0)
            wa, wb = (ra.get('replay_run') or {}).get('wall_sec'), (rb.get('replay_run') or {}).get('wall_sec')
            rows.append({'state': s, 'pair': [a, b], 'wall': [wa, wb], 'clean': clean(ra) and clean(rb),
                         'order': [ra.get('started'), rb.get('started')],
                         'ratio': wb / wa if (wa and wb) else None})
    r = [x['ratio'] for x in rows if x['clean'] and x['ratio'] is not None]
    q = statistics.quantiles(r, n=4, method='inclusive') if len(r) > 1 else None
    med = statistics.median(r) if r else None
    rec = V.rjson(OK2 / 'commit' / commit / 'gates' / 'gk5.json') or {}
    return {'n_clean': len(r), 'median': med, 'iqr_inclusive': (q[2] - q[0]) if q else None, 'limit': LIMIT,
            'verdict': 'PASS' if (len(r) == 8 and med <= LIMIT) else 'FAIL',
            'record_median_equal': rec.get('median') == med, 'record_iqr_equal': rec.get('iqr') == ((q[2] - q[0]) if q else None),
            'record_verdict': rec.get('verdict'), 'rows': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    res = {'schema': 'vgates-commit/v1', 'files': {}, 'stages': {}}
    for rel, want in RECORDED.items():
        res['files'][rel] = V.sha_file(OK2 / rel) == want
        d = V.rjson(OK2 / rel) or {}
        st = {k: (v or {}).get('verdict') for k, v in d.items() if isinstance(v, dict)}
        res['stages'][rel] = {'all_pass': bool(st) and all(x == 'PASS' for x in st.values()), 'stages': st,
                              'stage_list_as_declared': (list(st) == WANT_STAGES[rel]) if rel in WANT_STAGES else None}
    res['gk5'] = {c: gk5(c) for c in ('K9-2-1', 'K9-2-2')}
    res['git'] = {'head': git('rev-parse', 'HEAD'), 'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
                  'k8': git('rev-parse', 'claude/k8-sc1001eb-defects-20261004'),
                  'log': git('log', '--format=%h %an <%ae> | %cn | %s', 'b9734abe..HEAD').splitlines(),
                  'status_lines': len([x for x in git('status', '--porcelain').splitlines() if x.strip()]),
                  'remote_refs_k92': [x for x in git('for-each-ref', '--format=%(refname)', 'refs/remotes').splitlines()
                                      if 'k92' in x],
                  'trailer_ok': all('Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' in git('log', '-1',
                                                                                                    '--format=%B', h)
                                    for _, h in COMMITS)}
    res['git']['commit_order_ok'] = [x.split()[0] for x in reversed(res['git']['log'])] == [h for _, h in COMMITS]
    items = [json.loads(x) for x in open(R3_ITEMS, encoding='utf-8') if x.strip()]
    kinds = {}
    for it in items:
        k = it.get('kind')
        kinds.setdefault(k, {})
        v = it.get('mine_verdict') or it.get('r5_verdict') or (it.get('r5') or {}).get('verdict') or it.get('verdict')
        kinds[k][str(v)] = kinds[k].get(str(v), 0) + 1
    res['r3'] = {'items_sha_ok': V.sha_file(R3_ITEMS) == R3_ITEMS_SHA, 'n_items': len(items), 'by_kind_verdict': kinds}
    V.wjson(args.dest, res)
    print('VG_COMMIT files_ok=%s stages_ok=%s gk5=%s' % (all(res['files'].values()),
                                                        all(x['all_pass'] for x in res['stages'].values()),
                                                        {c: (g['verdict'], g['median']) for c, g in res['gk5'].items()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
