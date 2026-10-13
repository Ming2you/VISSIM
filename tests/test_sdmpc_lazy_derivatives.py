"""Scalar line search must retain candidates and the selected physical response."""
from unittest.mock import patch
import pytest
from diagnostics.test_sdmpc_pfo_caps import OwnPfoTests
from evaluation.controllers import sdmpc_pfo
from evaluation.controllers.sdmpc import policy_token
from evaluation.controllers.sdmpc_tangent_surrogate import Query, token, check_scalar_upgrade
from tests.test_sdmpc_cap_response_reuse import template, fake, action


def pfo(lazy, initial=1., passive=0.):
    original = sdmpc_pfo.solve
    evaluations = []
    def wrapped(reference, coord, policy, options, evaluate, derivative, quantities, budget, emit):
        def traced(actions, **kwargs):
            evaluations.append((kwargs.get('derivatives', False), [coord.encode(a).tolist() for a in actions]))
            return evaluate(actions, **kwargs)
        return original(reference, coord, dict(policy, lazy_trial_derivatives=lazy), options,
                        traced, derivative, quantities, budget, emit)
    with patch.object(sdmpc_pfo, 'solve', wrapped):
        result, witnesses = OwnPfoTests().run_quadratic(initial=initial, passive=passive)
    return result, witnesses, evaluations


@pytest.mark.parametrize('initial,passive', [(1.,0.), (1.5,-1e6), (0.,0.)])
def test_same_candidates_choice_and_final_jacobian_without_rejected_trial_derivatives(initial, passive):
    eager, _, eager_calls = pfo(False, initial, passive)
    lazy, witnesses, lazy_calls = pfo(True, initial, passive)
    assert eager[0].green_times == lazy[0].green_times
    assert eager[1] == lazy[1]
    assert eager[2]['trial_rows'] == lazy[2]['trial_rows']
    # Same physical trials, with only the derivative timing changed.
    assert [a for _, a in eager_calls] == [a for _, a in lazy_calls[:-1]]
    assert eager_calls[0][0] and lazy_calls[0][0]
    assert all(not derivatives for derivatives, _ in lazy_calls[1:])
    assert witnesses[-1] == tuple(lazy[0].green_times[k] for k in ('A','B'))


def test_lazy_upgrade_rejects_changed_primal_before_caching():
    t = template(lazy_trial_derivatives=True)
    def wrong(request):
        result = fake(request)
        if request['surrogate_evaluation'] == 'ad':
            item = result['surrogate_prediction']
            item.pop('response_token')
            item['objective_veh_h'] += 1.
            item['response_token'] = token(item)
        return result
    query = Query(t, lambda *args:None, lambda *args,**kwargs:None, runner=wrong)
    query.evaluate([action()])
    with pytest.raises(ValueError, match='Scalar/AD trial response'):
        query.derivative(action())
    assert query.ad == 0 and query.entries[query.physical_key(action())][2] is None


def test_lazy_timing_flag_keeps_same_price_policy_identity():
    old = dict(max_iterations=2, budget_caps=True)
    assert policy_token(dict(old,lazy_trial_derivatives=True)) == policy_token(old)
    assert policy_token(dict(old,lazy_trial_derivatives=True,max_iterations=3)) != policy_token(old)


def area_summary(events):
    return dict(control_area=dict(event_count=events,flow_counts={'route':12.},
        ttt_veh_h=5.,ttd_veh=2.,entered_veh=3.),resource_summary=dict(count=17,max_exceedance_veh=0.))


def test_sparse_record_counter_is_not_vehicle_count():
    check_scalar_upgrade(area_summary(197481),area_summary(197478),1e-7)


@pytest.mark.parametrize('field',['ttt_veh_h','ttd_veh','entered_veh'])
def test_record_difference_never_hides_physical_area_change(field):
    other=area_summary(197478);other['control_area'][field]+=1.
    with pytest.raises(ValueError,match='trial response changed'):
        check_scalar_upgrade(area_summary(197481),other,1e-7)


def test_record_difference_never_hides_route_or_coverage_change():
    other=area_summary(197478);other['control_area']['flow_counts']['route']+=1.
    with pytest.raises(ValueError,match='trial response changed'):
        check_scalar_upgrade(area_summary(197481),other,1e-7)
    other=area_summary(197478);other['resource_summary']['count']-=1
    with pytest.raises(ValueError,match='trial response changed'):
        check_scalar_upgrade(area_summary(197481),other,1e-7)


@pytest.mark.parametrize('counter',[-1,1.5,True,None])
def test_invalid_record_counter_rejected(counter):
    with pytest.raises(ValueError,match='record-counter contract'):
        check_scalar_upgrade(area_summary(5),area_summary(counter),1e-7)


def owner_summary(events):
    return dict(quantities=dict(owners=dict(SC1004=dict(accepted_event_count=events,
        by_kind_veh={'arrival': 12., 'departure': 10.}, net_inflow_veh=2.))))


def test_owner_record_counter_does_not_count_vehicles():
    check_scalar_upgrade(owner_summary(2716), owner_summary(2712), 1e-7)


@pytest.mark.parametrize('field', ['flow', 'net'])
def test_owner_record_difference_never_hides_physical_change(field):
    other = owner_summary(2712)
    row = other['quantities']['owners']['SC1004']
    if field == 'flow':
        row['by_kind_veh']['arrival'] += 1.
    else:
        row['net_inflow_veh'] += 1.
    with pytest.raises(ValueError, match='trial response changed'):
        check_scalar_upgrade(owner_summary(2716), other, 1e-7)


@pytest.mark.parametrize('counter', [-1, 1.5, True, None])
def test_invalid_owner_record_counter_rejected(counter):
    with pytest.raises(ValueError, match='owner record-counter contract'):
        check_scalar_upgrade(owner_summary(5), owner_summary(counter), 1e-7)


@pytest.mark.parametrize('field', ['accepted_event_count', 'by_kind_veh', 'net_inflow_veh'])
def test_missing_owner_counter_contract_rejected(field):
    other = owner_summary(5)
    del other['quantities']['owners']['SC1004'][field]
    with pytest.raises(ValueError, match='owner record-counter contract'):
        check_scalar_upgrade(owner_summary(5), other, 1e-7)
