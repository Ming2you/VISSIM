"""Independent checks of completed246 cached-data diagnostics; no rollout."""
import ctypes
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    protocol = h.read(HERE/'flux_selection/protocol.json')
    spatial = h.read(HERE/'spatial.json')
    profile = h.read(HERE/'recovery_profile.json')
    rows = h.read(HERE/'flux_selection/rows.json')
    summary = h.read(HERE/'flux_selection/summary.json')
    frozen = h.read(HERE/'flux_selection/frozen_coefficient.json')
    pins = {**spatial['pins'], **protocol['input_pins'], **protocol['protected_sha256'],
            protocol['STOP']['path']: protocol['STOP']['sha256']}
    assert all(h.sha(p) == value for p, value in pins.items())
    assert h.sha(HERE/'recovery_profile.py') == profile['source_sha256']
    assert len(profile['profiles']) == 360 and len(profile['moments']) == 10800
    assert spatial['partition_checks'] == 728 and len(spatial['groups']) == 144
    assert len(rows) == 10693
    assert not summary['operational_adopted']
    row_index = {(r['case'], r['time'], r['cell'], r['lane']): r for r in rows}
    assert len(row_index) == len(rows)
    maximum = 0.
    checked = 0
    missing = 0
    nonexit = 0
    for case in summary['bycase']:
        seed, arm = case.split('_', 1)
        start = 2220.1 if seed == '43' else 2670.1
        if seed == '67':
            path = h.R/f'blocking176/{arm}_frames.json.gz'
        elif seed == '29':
            path = h.F/f'vsl_native_exposure/s29_late_{arm}_frames.json.gz'
        else:
            path = h.F/f'cohort_early/s43_{arm}_frames.json.gz'
        data = h.read(path)
        fields = data['fields']
        speed_key = 'speed' if 'speed' in fields else 'speed_kmh'
        frames = {}
        for t, raw in data['frames'].items():
            if isinstance(raw, dict):
                frames[round(float(t), 1)] = {str(k): dict(zip(fields, v)) for k, v in raw.items()}
            else:
                frames[round(float(t), 1)] = {str(int(v[fields.index('vehicle')])): dict(zip(fields, v)) for v in raw}
        for step in range(90):
            t = round(start+step*5, 1)
            now, later = frames[t], frames[round(t+5, 1)]
            groups = {}
            for vehicle, r in now.items():
                if 21 <= r['cell'] <= 25:
                    groups.setdefault((r['cell'], r['lane']), []).append((vehicle, r[speed_key]))
            for (cell, lane), stock in groups.items():
                speeds = [v for _, v in stock]
                observed = [(vehicle, v) for vehicle, v in stock if vehicle in later]
                departures = [v for vehicle, v in observed if later[vehicle]['cell'] > cell]
                missing += len(stock)-len(observed)
                nonexit += len(observed)-len(departures)
                key = (case, t, cell, lane)
                if not departures:
                    assert key not in row_index
                    continue
                saved = row_index[key]
                mean = math.fsum(speeds)/len(speeds)
                variance = math.fsum((v-mean)**2 for v in speeds)/len(speeds)
                feature = variance/mean if mean > 0 else 0.
                expected = dict(n=len(stock), exit_count=len(departures), mean_speed=mean,
                                speed_second_moment=variance+mean**2, selection_feature=feature,
                                exit_pre_speed=math.fsum(departures)/len(departures))
                for name, value in expected.items():
                    error = abs(saved[name]-value)
                    maximum = max(maximum, error)
                    assert error < 1e-8, (key, name, error)
                checked += 1
    assert checked == len(rows)
    assert missing == summary['missing_next'] and nonexit == summary['observed_nonexit']
    train = [r for r in rows if r['case'] == '29_hold']
    numerator = math.fsum(r['exit_count']*r['selection_feature']*(r['exit_pre_speed']-r['mean_speed']) for r in train)
    denominator = math.fsum(r['exit_count']*r['selection_feature']**2 for r in train)
    c = min(1., max(0., numerator/denominator))
    assert c == frozen['c'] == summary['coefficient']
    assert len(train) == frozen['train_groups']
    assert abs(denominator*c-numerator) < 1e-8
    checks = 0
    def verify_metrics(selected, reported):
        nonlocal checks
        weights = math.fsum(r['exit_count'] for r in selected)
        assert len(selected) == reported['groups'] and weights == reported['exits']
        for value, key in [(0., 'group_rmse_base'), (1., 'group_rmse_full_moment'), (c, 'group_rmse_fit')]:
            rmse = math.sqrt(math.fsum(r['exit_count']*(r['exit_pre_speed']-(r['mean_speed']+value*r['selection_feature']))**2 for r in selected)/weights)
            assert abs(rmse-reported[key]) < 1e-10
            checks += 1
    for case, reported in summary['bycase'].items():
        verify_metrics([r for r in rows if r['case'] == case], reported)
    for seed, reported in summary['byseed'].items():
        verify_metrics([r for r in rows if r['case'].startswith(seed+'_')], reported)
    for reported in summary['bycell']:
        verify_metrics([r for r in rows if r['case'] == reported['case'] and r['cell'] == reported['cell']], reported)
    passed = c > 0 and all(r['group_rmse_fit'] <= .9*r['group_rmse_base'] for r in summary['byseed'].values()) and all(r['group_rmse_fit'] <= 1.1*r['group_rmse_base'] for r in summary['bycase'].values())
    assert passed == summary['passed_information_gate'] == False
    for m in profile['moments']:
        for side in ('before', 'after'):
            assert (m[side+'_n'] == 0) == (m[side+'_v'] is None)
    for old in spatial['groups']:
        current = next(p for p in profile['profiles'] if (p['case'], p['cell'], p['lane'], p['block']) == (old['case'], 21, old['lane'], old['block']))
        part = old['part']
        assert current['n'][part] == old['mean_n'] and current['slow'][part] == old['mean_slow']
        a, b = current['v'][part], old['vehicle_sample_speed']
        assert (a is None and b is None) or abs(a-b) < 1e-10
    assert all(h.sha(p) == value for p, value in pins.items())
    result = dict(status='PASS', raw_exit_groups_checked=checked, independently_recomputed_rmse=checks,
                  max_raw_feature_error=maximum, coefficient=c, information_gate='FAIL', adopted=False,
                  missing_next_excluded=missing, observed_nonexit=nonexit, partition_checks=728,
                  empty_half_not_assigned_speed=True, protected_sources_inputs_STOP_unchanged=True,
                  native_runs=0, forecasts=0, FZP_scans=0,
                  qualification='Conditional observed speed-selection diagnostic only; no autonomous variance or benefit validation.')
    h.save(HERE/'verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
