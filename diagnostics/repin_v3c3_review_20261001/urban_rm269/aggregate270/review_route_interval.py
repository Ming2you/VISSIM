"""Review completed route aggregation forecasts; never starts a forecast."""
import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade

HERE = Path(__file__).resolve().parent
OUT = HERE / 'route_interval'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
load = lambda p: pickle.loads(p.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    plan = read(OUT/'plan.json')
    for path, digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for mode in ('scalar', 'ad'):
        receipt = read(OUT/(mode+'_execution.json'))
        assert receipt['status'] in ('complete_pending_review', 'complete_reviewed')
        assert all(row['exit_code'] == 0 and not row['error'] for row in receipt['results'])
    scalar = load(OUT/'new_hold.scalar.result.pickle')
    ad = load(OUT/'new_hold.ad.result.pickle')
    check_scalar_upgrade(scalar['surrogate_prediction'], ad['surrogate_prediction'], 1e-7)
    assert len(ad['ad_axes']) == 213 and not ad['fallback_reasons']
    error, shapes = {}, {}
    for key, count in (('costs', 20), ('resources', 2)):
        before, after = np.asarray(scalar[key]), np.asarray(ad[key])
        assert before.shape == after.shape == (count,)
        assert np.isfinite(after).all()
        error[key] = float(np.max(abs(before-after)))
        assert error[key] < 1e-7
    before = scalar['surrogate_prediction']['central_physical']
    after = ad['central_physical']
    assert before['names'] == after['names'] and len(before['values']) == 5112
    error['central_values'] = float(np.max(abs(np.asarray(before['values'])-np.asarray(after['values']))))
    assert error['central_values'] < 1e-7
    for key, array, shape in (
            ('cost_jacobian', ad['cost_jacobian'], (20, 213)),
            ('resource_jacobian', ad['resource_jacobian'], (2, 213)),
            ('central_jacobian', after['jacobian'], (5112, 213))):
        value = np.asarray(array)
        assert value.shape == shape and np.isfinite(value).all(), key
        shapes[key] = list(shape)
    margins = {}
    for name in ('old_release', 'new_hold', 'new_release'):
        request = load(OUT/(name+'.pickle'))
        options = request['owned'][0].cfg.network.sdmpc_options
        assert options['budget_caps'] is True
        action = request['action']
        result = load(OUT/(name+'.scalar.result.pickle'))
        used = result['resources']
        margins[name] = dict(np_cap_veh=action.N_P_star, np_used_veh=used[0],
            np_margin_veh=action.N_P_star-used[0], nuf_cap_veh_h=action.N_UF_star,
            nuf_used_veh_h=used[1], nuf_margin_veh_h=action.N_UF_star-used[1])
    report = dict(status='completed_scalar_ad_consistency_pass',
        reviewed_utc=datetime.now(timezone.utc).isoformat(), max_abs_error=error,
        jacobian_shapes=shapes, source_pins_pass=True, cap_margins=margins,
        scalar_wall_sec=read(OUT/'scalar_execution.json')['results'],
        ad_wall_sec=read(OUT/'ad_execution.json')['results'][0]['wall_sec'],
        tangent_core_sec=ad['tangent_sec'], native_gain_qualified=False,
        whole_decision_600sec_qualified=False,
        limitations=['One saved state only; no native or full SDMPC selection.',
            'Scalar/AD values and finite Jacobians checked; not exhaustive finite differences.',
            'Route aggregation changes FIFO sharing; it is a model approximation.',
            'Receiving/service and freeway remain1s. Not full urban10s or freeway5s.',
            'Cap margins are reported without modifying caps or claiming an optimal selection.'])
    save(OUT/'ad_review.json', report)
    for mode in ('scalar', 'ad'):
        path = OUT/(mode+'_execution.json'); receipt = read(path)
        receipt['status'] = 'complete_reviewed'; receipt['review'] = 'ad_review.json'
        save(path, receipt)
    plan.update(status='completed_single_state_response_and_ad_reviewed',
        review='ad_review.json', next_step='Check one unused state before considering full selection or adoption.')
    save(OUT/'plan.json', plan)
    print(json.dumps(dict(max_abs_error=error, shapes=shapes, cap_margins=margins,
                         ad_wall_sec=report['ad_wall_sec']), ensure_ascii=False))


if __name__ == '__main__':
    main()
