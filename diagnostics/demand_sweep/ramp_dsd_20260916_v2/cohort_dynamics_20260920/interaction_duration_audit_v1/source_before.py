"""Test elapsed native interaction state before adding another plant state.

Frozen existing NC conditional model is the comparator. Only an elapsed-state
table is fitted; future rows are outcome labels, never duration inputs.
"""
from pathlib import Path
from collections import defaultdict, Counter
import bisect
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_interaction_response as c

K, e = c.d.HERE, c.d.e
OUT = K / 'interaction_duration_audit_v1'
EDGES = (1, 3, 7)
CAP = 8


def ages(frame, previous, history):
    """Current/past frames only; age8 means observed lower bound >=8s."""
    result = {}
    for vid, row in frame.items():
        before = previous.get(vid)
        if before is None:
            result[vid] = (1, False)
        elif before['interaction'] != row['interaction']:
            result[vid] = (1, True)
        else:
            n, known = history[vid]
            n = min(CAP, n + 1)
            result[vid] = (n, known or n == CAP)
    return result


def attach(records, frames):
    by_time = defaultdict(list)
    for r in records:
        by_time[r['time_s']].append(r)
    previous, history = {}, {}
    checks = unknown = 0
    for t in sorted(frames):
        history = ages(frames[t], previous, history)
        for r in by_time[t]:
            n, known = history[r['vehicle']]
            r['elapsed_bin'] = bisect.bisect_left(EDGES, n) if known else -1
            r['elapsed_observed_s'] = n
            unknown += not known
        if t in (2090, 2400, 2550, 2700):
            # Truncation to the last9 current/past frames must give the same
            # capped age. No future frame can change an observed duration.
            short, prev = {}, {}
            for s in range(t-CAP, t+1):
                short = ages(frames[s], prev, short)
                prev = frames[s]
            assert short == history
            checks += 1
        previous = frames[t]
    return dict(age_prefix_checks=checks, unknown_left_censored_records=unknown)


def base_model(doc):
    return [{tuple(row['key']): {int(h): (v['n'], v['mean']) for h, v in row['targets'].items()}
             for row in bank} for bank in doc['models']['target_state']]


def base_predict(r, h, tables, means):
    for table, key in zip(tables, c.keys(r, 'target_state')):
        value = table.get(key, {}).get(h)
        if value and value[0] >= c.g.MIN_SUPPORT:
            return value[1]
    return means[str(h)]


def age_key(r):
    return c.keys(r, 'target_state')[0] + (r['elapsed_bin'],)


def fit(records):
    table = defaultdict(lambda: defaultdict(lambda: [0, 0.]))
    rows = 0
    for r in records:
        if not 900 <= r['time_s'] <= 2090 or r['elapsed_bin'] < 0:
            continue
        rows += 1
        for h, value in r['labels'].items():
            table[age_key(r)][h][0] += 1
            table[age_key(r)][h][1] += value
    return {key: {h: (v[0], v[1]/v[0]) for h, v in entries.items()} for key, entries in table.items()}, rows


def score(records, lo, hi, tables, means, durations):
    selected = [r for r in records if lo <= r['time_s'] and r['time_s']+10 <= hi]
    result = {}
    for h in c.HORIZONS:
        answers = {}
        for mode in ('existing', 'elapsed_state'):
            errors, grouped, supported = [], defaultdict(list), 0
            for r in selected:
                if h not in r['labels']:
                    continue
                value = base_predict(r, h, tables, means)
                extra = durations.get(age_key(r), {}).get(h)
                if mode == 'elapsed_state' and r['elapsed_bin'] >= 0 and extra and extra[0] >= c.g.MIN_SUPPORT:
                    value = extra[1]
                    supported += 1
                error = value-r['labels'][h]
                errors.append(error)
                grouped[r['time_s'], r['cell']].append(error)
            cohort = [sum(v)/len(v) for v in grouped.values()]
            answers[mode] = dict(n=len(errors), rmse_kmh=math.sqrt(sum(v*v for v in errors)/len(errors)),
                bias_kmh=sum(errors)/len(errors), elapsed_supported=supported,
                cohort_rmse_kmh=math.sqrt(sum(v*v for v in cohort)/len(cohort)),
                cohort_bias_kmh=sum(cohort)/len(cohort))
        result[str(h)] = answers
    return result


def main():
    OUT.mkdir(exist_ok=False)
    gp = c.d.H / 'controller_response_s23_v1/none/geometry.json'
    network = c.d.H / 'source_dsd/baseline.inpx'
    oldpath = K / 'current_interaction_response_v1/training_table.json'
    priorpath = K / 'current_interaction_response_v1/result.json'
    doc, prior = e.load(oldpath), e.load(priorpath)
    geometry = e.load(gp)
    params = c.g.restart.native_parameters(network)
    tables, means = base_model(doc), doc['global_mean']
    scores, counts, receipts, age_checks = {}, {}, {}, {}
    prefix = None
    for arm, folder, lo in (('none', 'none_s23/run_retry1', 899),
                            ('rm_ramp', 'rm_ramp_s23/run', 2249),
                            ('vsl', 'vsl_s23/run_retry1', 2249)):
        frames, receipts[arm] = c.g.read(K / 'route_state_native_v1' / folder / 'vissim_eval/baseline_001.fzp', True, lo)
        rs, counts[arm] = c.records(frames, geometry, params, 900 if arm == 'none' else 2250)
        age_checks[arm] = attach(rs, frames)
        if arm == 'none':
            duration, n = fit(rs)
            prefix = {t: frames[t] for t in range(2392, 2401)}
            canary = {**rs[-1], 'labels': {h: 999999. for h in c.HORIZONS}}
            assert fit([r for r in rs if r['time_s'] <= 2090]+[canary]) == (duration, n)
            e.save(OUT / 'training_table.json', dict(age_edges_s=EDGES, cap_s=CAP, min_support=c.g.MIN_SUPPORT,
                rows=n, train_first=900, train_last=2090, label_last=2100,
                table=[dict(key=list(k), targets={str(h): dict(n=v[0], mean=v[1]) for h, v in ys.items()}) for k, ys in duration.items()]))
            scores['nc_time_validation'] = score(rs, 2100, 2400, tables, means, duration)
            scores['focused_cell16'] = score([r for r in rs if r['cell'] == 16], 2550, 2580, tables, means, duration)
        else:
            assert all(frames[t] == prefix[t] for t in prefix)
        label = 'nc_control' if arm == 'none' else arm + '_control'
        scores[label] = score(rs, 2400, 2850, tables, means, duration)
        # Existing published comparator must remain identical on its periods.
        for period in (('nc_time_validation', 'nc_control') if arm == 'none' else ('vsl_control',) if arm == 'vsl' else ()):
            for h, row in scores[period].items():
                saved = prior['scores'][period]['target_state'][h]
                assert row['existing']['n'] == saved['n']
                for name in ('rmse_kmh', 'bias_kmh'):
                    assert abs(row['existing'][name] - saved[name]) < 1e-10
        e.save(OUT / f'scores_{arm}.json', {k:v for k,v in scores.items() if k == label or arm == 'none'})
        print(json.dumps(dict(arm=arm, scores=scores[label], age_checks=age_checks[arm])), flush=True)
        del frames, rs
    sources = [Path(__file__), Path(c.__file__), Path(c.g.__file__), gp, network, oldpath, priorpath, OUT/'training_table.json']
    e.save(OUT / 'result.json', dict(qualified=False, production_adopted=False, new_native_runs=0,
        scores=scores, coverage=counts, source_receipts=receipts, age_checks=age_checks,
        comparator_exact=True, precontrol_prefix_exact_frames=9, future_labels_do_not_change_keys=True,
        future_training_canary_ignored=True, source_pins={p.relative_to(c.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Conditional short-response identification; neither autonomous nor450s gain qualification.',
          'Native interaction is the recorded preceding-step state, not a newly asserted physical regime.',
          'Counts are overlapping samples from inspected seed23; no independent holdout claim.',
          'Same geometric/native observed-target inclusion as previous model; unsupported duration uses exact prior fallback.',
          'Only elapsed-state table is fit, NC900..2090, labels through2100; no controlled outcomes in fitting.',
          'First seen states are left-censored until a change or eight observed seconds; no invented entry age.']))


if __name__ == '__main__':
    main()
