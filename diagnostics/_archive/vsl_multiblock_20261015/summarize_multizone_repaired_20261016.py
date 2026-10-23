"""Summarize completed native/model caches; no FZP, simulation or model calls."""
import csv
import gzip
import importlib.util
import math
from pathlib import Path
import analyze_multizone_repaired_20261016 as task


def model_horizons(response, snapshots, expected_ttt):
    assert [s['time_sec'] for s in snapshots] == [2250, 2400, 2550, 2700]
    residence = response['residence']
    assert [(r['start_sec'], r['end_sec']) for r in residence] == [(t, t + 10) for t in range(2250, 2700, 10)]
    assert all(abs(r['dt_h'] - 10 / 3600) < 1e-12 for r in residence)
    assert [(r['start_sec'], r['end_sec']) for r in response['freeway_frames']] == [(t, t + 5) for t in range(2250, 2700, 5)]
    cases = {}
    for end in (2400, 2550, 2700):
        rows = [r for r in residence if r['end_sec'] <= end]
        transfers = [r for r in response['transfers'] if r['end_sec'] <= end]
        assert all(2250 <= r['start_sec'] <= r['end_sec'] <= end for r in transfers)
        cost = {key: math.fsum(r['inside_veh'][key] * r['dt_h'] for r in rows) for key in rows[0]['inside_veh']}
        outside = math.fsum(math.fsum(r['model_stock_veh'][k] - v for k, v in r['inside_veh'].items()) * r['dt_h'] for r in rows)
        flow = lambda pred: math.fsum(r['vehicles'] for r in transfers if pred(r))
        incoming = flow(lambda r: r['source'] == 'origin:FW_E' and r['target'] == 'freeway:FW_E')
        merge = flow(lambda r: str(r['source']).startswith('merge_pending:') and r['target'] == 'freeway:FW_E')
        terminal = flow(lambda r: r['source'] == 'freeway:FW_E' and r['target'] == 'external:terminal:FW_E')
        off = flow(lambda r: r['source'] == 'freeway:FW_E' and str(r['target']).startswith('transit:exchange:off:'))
        snapshot = next(s for s in snapshots if s['time_sec'] == end)
        stock = math.fsum(snapshot['stocks']['freeway:FW_E'].values())
        initial = math.fsum(snapshots[0]['stocks']['freeway:FW_E'].values())
        residual = stock - initial - incoming - merge + terminal + off
        assert abs(residual) < 1e-7
        cases[str(end - 2250)] = dict(omega_ttt=math.fsum(cost.values()), component_ttt=cost,
            outside_residence=outside, source_accepted=incoming, accepted_merge=merge,
            terminal_outflow=terminal, offramp_outflow=off, end_east_inventory=stock,
            mainline_balance_residual=residual)
    assert abs(cases['450']['omega_ttt'] - expected_ttt) < 1e-7
    return cases


def main():
    output = task.OUT / 'horizon_summary.json'
    assert not output.exists(), 'Preserve completed horizon analysis'
    closure = task.read(task.OUT / 'runtime_closure.json')
    assert closure['all_owned_processes_closed'] and closure['wrapper_closed']
    summary = task.read(task.OUT / 'summary.json')
    assert summary['counterfactual_valid'] and summary['existing_forecast_comparison_qualified']
    prepared = task.read(task.HERE / 'analysis_preparation_repaired_20261016.json')
    for path, digest in prepared['source_pins'].items():
        assert task.sha(path) == digest, path
    helper = Path('E:/VISSIM_analysis/20261011_vsl_response349/native_horizon_cache_v2/summarize.py')
    spec = importlib.util.spec_from_file_location('existing_native_horizon_methods', helper)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    old = task.read(task.BASE / 'horizon_summary.json')
    for path, digest in old['source_pins'].items():
        assert task.sha(path) == digest, path
    cases = {'hold': old['cases']['hold'], 'single90': old['cases']['vsl90']}
    with (task.OUT / 'selected/area_timeseries.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    cases['selected'] = native.horizons(rows)
    assert abs(native.at(rows, 2700)['ttt'] - summary['arms']['selected']['TTT_0_2700_veh_h']) < 1e-7
    model, comparisons = {}, {}
    predictions = task.read(task.MODEL)['results']
    for row in predictions:
        path = task.MODEL.parent / (row['name'] + '_response.json.gz')
        with gzip.open(path, 'rt', encoding='utf8') as stream:
            response = task.json.load(stream)
        model[row['name']] = model_horizons(response, row['snapshots'], row['ttt_veh_h'])
        del response
    for arm in ('single90', 'selected'):
        comparisons[arm] = {}
        for h in ('150', '300', '450'):
            actual = cases[arm][h]['omega_ttt_veh_h'] - cases['hold'][h]['omega_ttt_veh_h']
            predicted = model[arm][h]['omega_ttt'] - model['hold'][h]['omega_ttt']
            comparisons[arm][h] = dict(native_delta_omega_veh_h=actual, model_delta_omega_veh_h=predicted,
                model_minus_native_veh_h=predicted - actual)
    task.save(output, dict(scope='Conditional VSL single/two-zone90 versus110,2250..2700; same city/RM',
        native=cases, model=model, comparisons=comparisons, new_forecasts=0, new_fzp_scans=0,
        source_pins=prepared['source_pins'], prior_native_horizon_sha256=task.sha(task.BASE / 'horizon_summary.json'),
        limitations=['Native TTT integrates5s sampled stock; arbitrary-time boundaries interpolate stock.',
            'Final tail is stock hold, never a normal exit. Mainline flow fields here are model transfers, not native counts.',
            'Outside model residence is distinct from native uninserted delay.',
            'No autonomous8100s policy benefit or independent-state generalization is established.']))
    print(task.json.dumps(comparisons), flush=True)


if __name__ == '__main__':
    main()
