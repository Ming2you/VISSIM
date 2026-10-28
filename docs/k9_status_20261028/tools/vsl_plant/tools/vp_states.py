"""Declared state lists for PRE_VP (light; reads only run provenance + per-run action CSV `kind=vsl` rows).

    python -B vp_states.py <out.json>

Rules (PRE_VP section 2; fixed before any probe data):
  V-A runs = the three declared run names below; seed = run_provenance `seed` (never the name).
  T_low(seed) = sorted decision times whose written FW_E VSL rows (RW_FW_E_*) carry any speed < 110.
  Probe A (and B) states per seed:  A1 = min(T_low) - 150,  A2 = min(T_low),  A3 = lower median of T_low,
                                    A4 = max(T_low) + 150.
  P1 states per seed: T in (1800, 5400, 7200); eligible when the written FW_E rows of decisions T, T+150, T+300 are
  all 110; else T+150, T+300, T+450 are tried in that order; none eligible -> recorded as not available.
  Smoke state (pipeline test only, never a result): v3c3-s31 T = 2400 (must not be in any list).
Every listed decision must have state_T.json, action_T.json/.csv, action_{T-150}.json(.applied) and decisions
T+150, T+300 (executed-plan rollout).  Output: one JSON (no plant or VISSIM value)."""
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

RUNS = ['sdmpc31_v3c3_k92va_s31', 'sdmpc31_v3c3_k92va_s41', 'sdmpc31_v3c3_k92va_s43']
P1_T = (1800, 5400, 7200)
SMOKE = (31, 2400)


def written_fwe(csv_path):
    rows = {}
    with open(csv_path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            if r['kind'] != 'vsl' or not r['id'].startswith('RW_FW_E'):
                continue
            t = int(round(float(r['sim_sec'])))
            rows.setdefault(t, {}).setdefault(r['id'], set()).add(float(r['speed_kph']))
    return {t: {k: sorted(v) for k, v in d.items()} for t, d in rows.items()}


def files_ok(dec, T):
    need = [dec / ('state_%06d.json' % T), dec / ('action_%06d.json' % T), dec / ('action_%06d.csv' % T),
            dec / ('action_%06d.json' % (T - 150)), dec / ('action_%06d.json.applied' % (T - 150))]
    for k in (1, 2):
        need += [dec / ('action_%06d.json' % (T + 150 * k)), dec / ('action_%06d.csv' % (T + 150 * k))]
    return [str(p.name) for p in need if not p.is_file()]


def main():
    out = {'schema': 'vp-states/1', 'made_kst': C.kst(), 'rules': __doc__, 'runs': [], 'probe_A': [], 'probe_B': [],
           'p1': [], 'p1_unavailable': [], 'smoke': None}
    for name in RUNS:
        C.blind_guard(name)
        run_dir = C.RUN_ROOTS['va'] / name
        seed, prov, prov_sha = C.provenance_seed(run_dir)
        label = 'v3c3-s%d' % seed
        dec = run_dir / ('decisions_' + name)
        csv_path = run_dir / ('action_%s.csv' % name)
        w = written_fwe(csv_path)
        low = sorted(t for t, d in w.items() if any(v < 110.0 for vs in d.values() for v in vs))
        if not low:
            raise SystemExit('no FW_E VSL below 110 in ' + label)
        mid = low[(len(low) - 1) // 2]
        picks = [('A1', low[0] - 150), ('A2', low[0]), ('A3', mid), ('A4', low[-1] + 150)]
        out['runs'].append({'run': name, 'label': label, 'seed_from_provenance': seed,
                            'provenance_sha256': prov_sha, 'action_csv_sha256': C.sha256_file(csv_path),
                            'T_low': low, 'n_low': len(low)})
        for tag, T in picks:
            miss = files_ok(dec, T)
            if miss:
                raise SystemExit('missing decision files %s T=%d: %s' % (label, T, miss))
            row = {'run': name, 'label': label, 'seed': seed, 'T': T, 'tag': tag,
                   'kind': '101' if T in low else '110',
                   'written_fwe_T': w.get(T), 'written_fwe_T150': w.get(T + 150), 'written_fwe_T300': w.get(T + 300)}
            out['probe_A'].append(row)
            out['probe_B'].append(dict(row))
        for T0 in P1_T:
            got = None
            for T in (T0, T0 + 150, T0 + 300, T0 + 450):
                ok = all(all(v == 110.0 for vs in (w.get(T + 150 * k) or {'x': [0.0]}).values() for v in vs)
                         for k in (0, 1, 2))
                if ok and not files_ok(dec, T):
                    got = T
                    break
            if got is None:
                out['p1_unavailable'].append({'label': label, 'T0': T0})
            else:
                out['p1'].append({'run': name, 'label': label, 'seed': seed, 'T': got, 'T0': T0,
                                  'written_fwe_T': w.get(got), 'written_fwe_T150': w.get(got + 150),
                                  'written_fwe_T300': w.get(got + 300)})
    s_seed, s_T = SMOKE
    listed = {(r['seed'], r['T']) for r in out['probe_A'] + out['p1']}
    if (s_seed, s_T) in listed:
        raise SystemExit('smoke state is in a declared list')
    smoke_run = [r for r in out['runs'] if r['seed_from_provenance'] == s_seed][0]['run']
    out['smoke'] = {'run': smoke_run, 'label': 'v3c3-s%d' % s_seed, 'seed': s_seed, 'T': s_T,
                    'note': 'pipeline test only; its numbers are never results'}
    C.write_json(sys.argv[1], out)
    print('VP_STATES probe_A=%d p1=%d p1_unavailable=%d smoke=%s' % (len(out['probe_A']), len(out['p1']),
                                                                       len(out['p1_unavailable']), (s_seed, s_T)))


if __name__ == '__main__':
    main()
