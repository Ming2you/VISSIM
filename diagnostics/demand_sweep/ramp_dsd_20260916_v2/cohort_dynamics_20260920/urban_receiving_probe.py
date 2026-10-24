"""Small causal one-step feature screen for10643 receiving, not a450s model.

NC seed13 only selects coefficients/regularization. No control benefit labels,
future traffic features, source modifications, or production defaults are used.
"""
from pathlib import Path
import sys
import csv
import json
import argparse
import xml.etree.ElementTree as ET
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from plant.src.vissim_strict.signal_program import parse_sig

OUT = HERE / 'urban_receiving_probe_v1'
HISTORY = 150
STEP = 10


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dataset(path, proof_path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = {int(r['time_s']): {k: (v if k in ('sg2_state', 'sg5_state') else float(v)) for k, v in r.items()}
                for r in csv.DictReader(stream)}
    run = ROOT / load(proof_path)['source']
    root = ET.parse(load(run / 'run.json')['network']).getroot()
    network = Path(load(run / 'run.json')['network'])
    sc = next(n for n in root.findall('./signalControllers/signalController') if n.get('no') == '1004')
    name = sc.get('supplyFile2')
    program = parse_sig(network.parent / name[6:] if name.startswith('#data#') else Path(name), int(sc.get('progNo')))
    return rows, program, float(sc.get('offset'))


NAMES = ['intercept', 'past_lane1_vps', 'past_lane2_vps', 'green2_next_fraction', 'green5_next_fraction',
         'tail1_n_div6', 'tail2_n_div6', 'tail1_speed_div50', 'tail2_speed_div50',
         'link126_n_div20', 'lane2_n_div12', 'lane3_n_div12', 'sg5_n_div20']


def features(rows, program, offset, t, lag=0):
    r = rows[t]
    past = [sum(rows[s][f'off_lane{lane}_departures'] for s in range(t-HISTORY, t)) / HISTORY for lane in (1, 2)]
    # Future fixed signal states are known commands, never future traffic.
    greens = [sum(program.state_at(s, sg, controller_offset_sec=offset) == 'GREEN'
                  for s in range(t-lag+1, t-lag+STEP+1)) / STEP for sg in (2, 5)]
    ns = [r[f'off_lane{lane}_tail30_n'] / 6 for lane in (1, 2)]
    vs = [r[f'off_lane{lane}_tail30_speed_sum'] / max(1., r[f'off_lane{lane}_tail30_n']) / 50 for lane in (1, 2)]
    return np.array([1., *past, *greens, *ns, *vs, r['link126_n']/20, r['urban_lane2_n']/12,
                     r['urban_lane3_n']/12, r['urban_sg5_n']/20])


def samples(data, after=0, lag=0):
    rows, program, offset = data
    lo = max(after, min(rows)+HISTORY)
    times = list(range(10*((lo+9)//10), max(rows)-STEP+2, STEP))
    x = np.array([features(rows, program, offset, t, lag) for t in times])
    y = np.array([[sum(rows[s][f'off_lane{lane}_departures'] for s in range(t,t+STEP)) / STEP
                   for lane in (1,2)] for t in times])
    clean = np.array([not any(rows[s][f'urban_sg{g}_removals'] for s in range(t,t+STEP) for g in (2,5)) for t in times])
    return np.array(times), x, y, clean


def fit(x, y, penalty):
    regularizer = np.eye(x.shape[1]) * np.sqrt(penalty)
    regularizer[0, 0] = 0
    return np.linalg.lstsq(np.vstack([x, regularizer]), np.vstack([y, np.zeros((x.shape[1], 2))]), rcond=None)[0]


def fit_green_nonnegative(x, y, penalty):
    # Exact active-set enumeration for just two constrained coefficients.
    # This tests a plausible signal timing relation; it is not a flow solver.
    result = np.zeros((x.shape[1], 2))
    for lane in (0, 1):
        candidates = []
        for active in ((), (3,), (4,), (3, 4)):
            use = [i for i in range(x.shape[1]) if i not in active]
            coef = np.zeros(x.shape[1])
            regularizer = np.eye(len(use)) * np.sqrt(penalty)
            regularizer[use.index(0), use.index(0)] = 0
            coef[use] = np.linalg.lstsq(np.vstack([x[:, use], regularizer]),
                                      np.r_[y[:, lane], np.zeros(len(use))], rcond=None)[0]
            if min(coef[3:5]) < -1e-9:
                continue
            loss = float(np.sum((x@coef-y[:, lane])**2)+penalty*np.sum(coef[1:]**2))
            candidates.append((loss, coef))
        result[:, lane] = min(candidates, key=lambda v: v[0])[1]
    assert np.min(result[3:5]) >= -1e-9
    return result


def score(predicted, actual):
    error = (predicted-actual) * STEP
    return {'total_count_rmse': float(np.sqrt(np.mean(error.sum(axis=1)**2))),
            'lane_count_rmse': [float(v) for v in np.sqrt(np.mean(error**2, axis=0))],
            'total_count_mae': float(np.mean(abs(error.sum(axis=1)))),
            'mean_count_bias': float(np.mean(error.sum(axis=1))),
            'predicted_exits': float(predicted.sum()*STEP), 'actual_exits': float(actual.sum()*STEP)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lagged-nonnegative-green', action='store_true')
    args = parser.parse_args()
    result_dir = HERE/'urban_receiving_lag_probe_v1' if args.lagged_nonnegative_green else OUT
    if args.lagged_nonnegative_green:
        result_dir.mkdir(exist_ok=False)
    train_data = dataset(OUT/'s13_none.csv', OUT/'s13_none_evidence.json')
    times, x, y, clean = samples(train_data)
    train, tune = (times < 3300) & clean, (times >= 3300) & clean
    models, choices = {}, []
    for name, count in [('history_signal', 5), ('history_signal_state', len(NAMES))]:
        candidates = []
        for lag in ((0, 10, 20, 30, 40, 60) if args.lagged_nonnegative_green else (0,)):
            _, lag_x, _, _ = samples(train_data, lag=lag)
            for penalty in (.01, .1, 1., 10.):
                fitter = fit_green_nonnegative if args.lagged_nonnegative_green else fit
                coef = fitter(lag_x[train, :count], y[train], penalty)
                metric = score(np.maximum(0., lag_x[tune, :count] @ coef), y[tune])
                candidates.append((metric['total_count_rmse'], penalty, coef, metric, lag))
        best = min(candidates, key=lambda v: v[0])
        models[name] = (best[2], best[4])
        choices.append({'name': name, 'regularization': best[1], 'validation': best[3],
                        'signal_lag_s': best[4], 'features': NAMES[:count], 'coefficients_by_lane': best[2].tolist(),
                        'trials': [{'regularization': p, 'validation': m, 'signal_lag_s': lag} for _, p, _, m, lag in candidates]})
    datafiles = {'s13_tune': (OUT/'s13_none.csv', OUT/'s13_none_evidence.json', 3300)}
    for case in ('s23_none', 's23_vsl', 's33_none', 's33_spread'):
        folder = HERE/'urban_drain_observations_v5'
        datafiles[case] = (folder/(case+'.csv'), folder/(case+'_evidence.json'), 2400)
    for case in ('p90', 'p80'):
        folder = HERE/'input1101_sweep_v1/analysis'
        datafiles[case] = (folder/(case+'.csv'), folder/(case+'_evidence.json'), 2400)
    results, causal_checks = {}, []
    for case, (path, proof, after) in datafiles.items():
        data = dataset(path, proof)
        ts, fx, target, clean = samples(data, after)
        case_result = {'samples': len(ts), 'first_t': int(ts[0]), 'last_t': int(ts[-1]),
                       'past150': score(fx[:, 1:3], target), 'no_loss_samples': int(clean.sum()),
                       'no_loss_windows': {'past150': score(fx[clean, 1:3], target[clean])}}
        for name, (coef, lag) in models.items():
            _, lag_x, _, _ = samples(data, after, lag)
            predicted = np.maximum(0., lag_x[:, :len(coef)] @ coef)
            case_result[name] = score(predicted, target)
            case_result['no_loss_windows'][name] = score(predicted[clean], target[clean])
        results[case] = case_result
        rows, program, offset = data
        for t in (int(ts[0]), int(ts[-1])):
            cut = {s: r for s, r in rows.items() if s <= t}
            for _, lag in models.values():
                assert np.array_equal(features(rows, program, offset, t, lag), features(cut, program, offset, t, lag))
            causal_checks.append([case, t])
        print(case, {k: round(v['total_count_rmse'], 3) for k, v in case_result.items() if isinstance(v, dict) and 'total_count_rmse' in v}, flush=True)
    output = {'status': 'DIAGNOSTIC_ONLY_NOT_A_CONSERVED_ROLLOUT_OR_GAIN_QUALIFICATION',
              'training': 'NC seed13,1050-3290s; regularization selected at3300-4490s; exclude10s windows containing71 abnormal loss; no refit on test data',
              'claim': 'One-step future normal discharge, reinitialized from current state every10s. Not450s forecasting.',
              'known_signal_policy': 'Saved SC1004 program/offset only; no future traffic used',
              'models': choices, 'results': results, 'future_row_truncation_checks': causal_checks,
              'limits': 'All original seeds were seen during earlier development. Input sweep scenarios are new validation conditions, not independent seeds. Linear coefficients are a feature screen, not physical causal coefficients.'}
    (result_dir/'result.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
