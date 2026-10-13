"""Cap-only reuse cannot alias changed actuators, contexts or impure costs."""
import copy
from types import SimpleNamespace as NS
import numpy as np
import pytest
from src.models.state import ControlAction
from evaluation.controllers import sdmpc_sequence as seq
from evaluation.controllers.sdmpc_response_cache import physical_key,validate_binding
from evaluation.controllers.sdmpc_tangent_surrogate import Query,token,MODEL
from evaluation.controllers.sdmpc import GradientCache,policy_token


def action():
    a=ControlAction(N_P_star=50.,N_UF_star=800.,ramp_metering={'R':700.},
                    vsl={'E':90.},green_times={},offsets={})
    return seq.pack([a,a,a])


def template(enabled=True,**policy):
    opts=dict(response_cap_cache=enabled,budget_caps=True,pfo_each_interval=True,
              surrogate_reuse=True,central_multiplier=True,**policy)
    f=NS(cfg=NS(network=NS(sdmpc_options=opts,physical_ramp_branches={'R':{}})))
    return dict(owned=(f,NS(lane_freeway_runtime={}),action(),[]),runtime={},bootstrap={},
                horizon=3,axes=[{'kind':'meter'}])


def fake(request):
    a=request['action'];ad=request['surrogate_evaluation']=='ad'
    item=dict(action_token=token(a),frozen_context_token=request['surrogate_context_sha256'],
              prediction_model=MODEL,execution_model_evaluated=False,
              price_or_quantity_terms_included=False,objective_veh_h=12.,
              quantities={'actual_merge':700.})
    item['response_token']=token(item)
    return dict(surrogate_prediction=item,primal_audit_performed=False,
                scalar_rollouts=int(not ad),tangent_rollouts=int(ad),fallback_reasons={},
                ad_axes=request['axes'],wall_sec_including_spawn=1.,cost_jacobian=[[3.]])


def query(enabled=True):
    return Query(template(enabled),lambda *a:None,lambda *a,**kw:None,runner=fake)


def test_default_keeps_nuf_distinct_but_opt_in_normalizes_all_budget_copies():
    a=action();b=copy.deepcopy(a);b.N_UF_star+=100
    for row in b.diagnostics[seq.KEY]['future']:row['N_UF_star']+=100
    assert physical_key(a)!=physical_key(b)
    assert physical_key(a,nuf_cap=True)==physical_key(b,nuf_cap=True)
    b.diagnostics[seq.KEY]['future'][0]['vsl']['E']=80.
    assert physical_key(a,nuf_cap=True)!=physical_key(b,nuf_cap=True)


def test_cap_alias_keeps_source_identity_and_fresh_target_for_feasibility():
    q=query();a=action();b=copy.deepcopy(a);b.N_UF_star=600.
    x,y=q.evaluate([a,b])
    assert q.scalar==1 and q.hits==1
    validate_binding(b,y)
    assert y['action_token']==token(b) and x['response_token']==y['response_token']
    # Same physical merge is feasible for the first cap and violates the second.
    assert x['quantities']['actual_merge']<=a.N_UF_star
    assert y['quantities']['actual_merge']>b.N_UF_star
    y['sdmpc_physical_response_reuse']['physical_key']='tampered'
    with pytest.raises(ValueError):validate_binding(b,y)


def test_disabled_computes_both_predictions():
    q=query(False);a=action();b=copy.deepcopy(a);b.N_UF_star-=100
    q.evaluate([a,b]);assert q.scalar==2 and q.hits==0


def test_changed_meter_or_future_control_cannot_reuse():
    q=query();a=action();b=copy.deepcopy(a);b.ramp_metering['R']=600.
    c=copy.deepcopy(a);c.diagnostics[seq.KEY]['future'][1]['vsl']['E']=80.
    q.evaluate([a,b,c]);assert q.scalar==3


def test_ad_reuse_and_scalar_upgrade_are_counted_without_mutable_alias():
    q=query();a=action();q.evaluate([a])
    b=copy.deepcopy(a);b.N_UF_star+=100
    q.evaluate([b],derivatives=True)
    first=q.derivative(a);first['cost_jacobian'][0][0]=99.
    second=q.derivative(b)
    assert second['cost_jacobian']==[[3.]]
    assert q.ad==1 and q.scalar==1
    assert second['candidate_prediction_reused']['cap_only_contract']=='lane-central-pfo-cap-continuous/v1'


def test_reuse_rejected_outside_cap_only_lane_mode():
    t=template();t['owned'][0].cfg.network.sdmpc_options['budget_caps']=False
    with pytest.raises(ValueError):Query(t,lambda *a:None,lambda *a,**kw:None,runner=fake)


def test_gradient_cache_requires_same_cost_and_resource_values():
    a=action();b=copy.deepcopy(a);b.N_UF_star+=100
    old=GradientCache();new=GradientCache(nuf_cap=True)
    z=np.array([1.]);cost=np.array([12.]);resource=np.array([4.,700.])
    assert old.key(z,a,cost,resource)!=old.key(z,b,cost,resource)
    assert new.key(z,a,cost,resource)==new.key(z,b,cost,resource)
    assert new.key(z,a,cost,resource)!=new.key(z,b,cost+1,resource)
    assert new.key(z,a,cost,resource)!=new.key(z,b,cost,resource+1)


def test_queries_do_not_share_different_initial_state_contexts():
    q=query();other=template();other['owned'][1].time_sec=100.
    r=Query(other,lambda *a:None,lambda *a,**kw:None,runner=fake)
    x=q.evaluate([action()])[0];y=r.evaluate([action()])[0]
    assert x['frozen_context_token']!=y['frozen_context_token']
    assert q.scalar==r.scalar==1


def test_price_policy_identity_ignores_only_exact_cache_switch():
    old=dict(max_iterations=2,budget_caps=True,fixed_vsl={'E':90.})
    assert policy_token(old)==token(old)
    assert policy_token(dict(old,response_cap_cache=True))==token(old)
    assert policy_token(dict(old,response_cap_cache=False))==token(old)
    changed=dict(old,response_cap_cache=True,max_iterations=3)
    assert policy_token(changed)!=token(old)
