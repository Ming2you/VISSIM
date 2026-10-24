"""Review the three completed probes; never launch a prediction or native run."""
import hashlib
import importlib.util
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
M = HERE.parent / 'multirate271'
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    receipt = json.loads((HERE/'slope_execution.json').read_bytes())
    assert receipt['status'] in ('complete_pending_review', 'complete_reviewed')
    assert len(receipt['rows']) == 3 and all(x['exit_code'] == 0 for x in receipt['rows'])
    assert receipt['source_pins_unchanged']
    for path, expected in receipt['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    spec = importlib.util.spec_from_file_location('completed_multirate_review', M/'review.py')
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    read = lambda path: pickle.loads(path.read_bytes())
    baseline = read(M/'macro_hold_ad_v3_result.pickle')
    request = read(M/'macro_hold_ad_v3_request.pickle')
    axes = [(i, axis) for i, axis in enumerate(request['axes'])
            if axis['key'] == 'RM_C10681' and axis.get('block', 0) == 0]
    assert len(axes) == 1, axes
    index, axis = axes[0]
    base = review.row(baseline)
    ad = dict(omega_per_green_second=sum(row[index] for row in baseline['cost_jacobian'])/axis['scale'],
              total_nuf_per_green_second=baseline['resource_jacobian'][1][index]/axis['scale'])
    rows = []
    for execution in receipt['rows']:
        result = read(HERE/(execution['label']+'_result.pickle'))
        actual = review.row(result)
        delta = execution['delta_green_sec']
        rows.append(dict(**execution, checks=actual,
            omega_change_veh_h=actual['omega_veh_h']-base['omega_veh_h'],
            omega_slope_per_green_second=(actual['omega_veh_h']-base['omega_veh_h'])/delta,
            total_nuf_slope_per_green_second=(result['resources'][1]-baseline['resources'][1])/delta,
            merge_change_by_ramp={k: actual['merges_veh'][k]-v for k,v in base['merges_veh'].items()}))
    micro = rows[0]
    errors = dict(omega=abs(micro['omega_slope_per_green_second']/ad['omega_per_green_second']-1),
                  nuf=abs(micro['total_nuf_slope_per_green_second']/ad['total_nuf_per_green_second']-1))
    assert max(errors.values()) < .001
    result = dict(status='complete_reviewed_no_production_change', reviewed_utc=datetime.now(timezone.utc).isoformat(),
        state_sec=2400, horizon_sec=450, seed=29, freeway_exchange_sec=5, urban_physical_sec=1,
        axis=axis, baseline=base, ad=ad, rows=rows, micro_relative_errors=errors,
        conclusion='Local AD agrees with a tiny perturbation; executable one-second response is highly nonlinear. No evidence here justifies replacing the derivative or changing the objective.',
        limitations=[
            'Micro and small probes are mathematical continuous-model probes, not executable VISSIM commands.',
            'The one-second RM change is within the green-step bound; no new complete native writer or native execution proof is claimed.',
            'NUF is total actual merging across all ramps, not direct10681 service; other ramp response contributes.',
            'One held state and one coordinate do not establish all-axis differentiation accuracy or a unique cause of the final optimizer miss.',
            'The held-state Jacobian differs from the actual PFO-warm SDMPC anchor.',
            'No gradient clipping, finite-step surrogate, extra optimizer iteration, calibration or native run was introduced.'],
        source_pins=receipt['source_pins'])
    save(HERE/'review.json', result)
    receipt.update(status='complete_reviewed', review='review.json')
    save(HERE/'slope_execution.json', receipt)
    print(json.dumps(dict(status=result['status'], ad=ad, micro_relative_errors=errors,
        legal_omega_change_veh_h=rows[-1]['omega_change_veh_h']), ensure_ascii=False))


if __name__ == '__main__':
    main()
