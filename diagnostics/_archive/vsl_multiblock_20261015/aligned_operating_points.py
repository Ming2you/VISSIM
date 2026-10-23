"""Reuse completed native endpoint and accepted-flow caches; no new forecasts."""
import hashlib, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE = Path('E:/VISSIM_analysis/20261012_ramp_plant355/route_state431')
paths = [BASE/'assessment.json', BASE/'regional_ledger432.json']
raw = [p.read_bytes() for p in paths]
audit, ledger = [json.loads(data) for data in raw]
out = HERE/'aligned_operating_points.json'
assert not out.exists()
rows = []
for item in ledger['rows']:
    seed, arm, elapsed = item['seed'], item['arm'], item['end_elapsed']
    observed = [r for r in audit['rows'] if r['seed'] == seed and r['arm'] == arm
                and r['elapsed'] == elapsed and 19 <= r['cell'] <= 23]
    initial = [r for r in audit['rows'] if r['seed'] == seed and r['arm'] == arm
               and r['elapsed'] == 0 and 19 <= r['cell'] <= 23]
    assert len(observed) == len(initial) == 5
    native_n = sum(r['native']['n'] for r in observed)
    model_n = math.fsum(r['model_n'] for r in observed)
    assert abs(model_n-item['after']) < 1e-8
    initial_native = sum(r['native']['n'] for r in initial)
    initial_model = math.fsum(r['model_n'] for r in initial)
    assert abs(initial_native-initial_model) < 1e-8
    rows.append(dict(seed=seed, arm=arm, elapsed=elapsed, initial_native_n=initial_native,
        initial_model_n=initial_model, native_n=native_n, model_n=model_n,
        stock_error_veh=model_n-native_n,
        native_mean_speed=sum(r['native']['speed_sum'] for r in observed)/native_n,
        model_mean_speed=sum(r['model_n']*r['model_speed'] for r in observed)/model_n,
        model_interval_flow={k:item[k] for k in ('incoming18','outgoing23','off','merges')},
        model_balance_error=item['balance_error'],
        native_internal_incoming18=None, native_internal_outgoing23=None,
        missing_reason='These exact native cut flows are not present in the reused cache; endpoints alone do not identify either flow.'))
report = dict(schema='aligned-absolute-operating-points/v1', rows=rows,
    source_pins={str(p):hashlib.sha256(data).hexdigest() for p,data in zip(paths,raw)},
    new_forecasts=0,new_native_runs=0,new_fzp_scans=0,fitted_coefficients=0,
    interpretation='Separate absolute base loading/recovery error from intervention response. Closed model balance is not evidence that native inflow and release are correct.')
out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
for r in rows:
    print(r['seed'], r['arm'], r['elapsed'], r['native_n'], round(r['model_n'],2),
          round(r['stock_error_veh'],2), round(r['native_mean_speed'],2),round(r['model_mean_speed'],2))
