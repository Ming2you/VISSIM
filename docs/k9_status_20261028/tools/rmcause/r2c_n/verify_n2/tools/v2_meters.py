r"""VERIFY_N2: meter command check of R1 (10681-only) and RM arms from run folders (read only), fresh code."""
import csv
import glob
import io
import json
import os
import collections

ROOT = r'D:\VISSIM_runs\20261001_v3c3'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')


def code(g):
    return 'A' if g >= 10 else str(int(g))


def main():
    res = {}
    for arm, sub in (('r1', 'rm10681'), ('rm', 'rm')):
        for s in (31, 41):
            rd = os.path.join(ROOT, 's%d_v3c3%s' % (s, sub), 'run')
            decs = sorted(glob.glob(os.path.join(rd, 'decision_*.json')), key=lambda p: int(p.rsplit('_', 1)[1][:-5]))
            secs, meters_sets, greens, ev_sc, ev_kinds = [], collections.Counter(), collections.defaultdict(dict), collections.Counter(), collections.Counter()
            for p in decs:
                d = json.load(io.open(p, encoding='utf-8-sig'))
                T = int(d['sec'])
                secs.append(T)
                meters_sets[tuple(sorted(d.get('meters', {})))] += 1
                for m, v in d.get('meters', {}).items():
                    greens[m][T] = v['green_sec']
                for e in d.get('events', []):
                    ev_kinds[e[1]] += 1
                    ev_sc[(e[1], e[2], e[4])] += 1
            fe = list(csv.DictReader(io.open(os.path.join(rd, 'fixed_events.csv'), encoding='utf-8')))
            fe_c = collections.Counter((r['kind'], r['no'], r['value']) for r in fe)
            run = json.load(io.open(os.path.join(rd, 'run.json'), encoding='utf-8-sig'))
            val = json.load(io.open(os.path.join(rd, 'fixed_validation.json'), encoding='utf-8-sig'))
            pol = json.load(io.open(os.path.join(os.path.dirname(rd), 'prepared', 'rule_policy.json'), encoding='utf-8-sig'))
            g = greens.get('RM_C10681', {})
            string = ''.join(code(g[T]) for T in secs) if g else ''
            res['%s_s%d' % (arm, s)] = {
                'n_decisions': len(secs), 'first': secs[0], 'last': secs[-1],
                'gaps': [b - a for a, b in zip(secs, secs[1:]) if b - a != 150],
                'meters_sets': {','.join(k): v for k, v in meters_sets.items()},
                'events_by_kind_sc_value': {'%s|%s|%s' % k: v for k, v in ev_sc.items()},
                'fixed_events': {'%s|%s|%s' % k: v for k, v in fe_c.items()},
                'policy_meters': sorted(pol.get('meters', {})) if isinstance(pol.get('meters'), dict) else pol.get('meters'),
                'run_completed': run.get('completed'), 'exit_code': run.get('exit_code'), 'error': run.get('error'),
                'validation_keys': sorted(val)[:20], 'validation_status': val.get('passed'), 'event_readbacks': val.get('event_readbacks'), 'snap_same': val.get('untargeted_snapshot_sha256_before') == val.get('untargeted_snapshot_sha256_after'), 'n_green_windows': len(val.get('actual_green_windows') or []),
                'g10681': string,
                'tight_decisions_10681': [T for T in secs if g.get(T, 10) < 10],
                'min_g10681': min(g.values()) if g else None,
                'greens_all': {m: ''.join(code(v[T]) for T in secs if T in v) for m, v in greens.items()},
            }
    with io.open(os.path.join(OUT, 'v2_meters.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    for k, v in res.items():
        print(k, v['n_decisions'], v['first'], v['last'], v['gaps'], v['meters_sets'], v['fixed_events'], v['policy_meters'],
              v['run_completed'], v['exit_code'], v['error'], v['validation_status'], v['min_g10681'],
              (v['tight_decisions_10681'][0], v['tight_decisions_10681'][-1], len(v['tight_decisions_10681'])) if v['tight_decisions_10681'] else None)
        print('   ', v['g10681'])
        if k.startswith('rm'):
            for m, sstr in v['greens_all'].items():
                print('     ', m, sstr)


if __name__ == '__main__':
    main()
