"""An exhausted shared budget cannot replenish until the next urban step."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.sdmpc import policy_token
from src.models import urban_queue_model as uqm


@pytest.mark.parametrize('green',[None,0.,.5])
@pytest.mark.parametrize('larger_shared_branch',[False,True])
def test_same_flows_and_stock_without_rechecking_zero_requests(monkeypatch,green,larger_shared_branch):
    spec=dict(prefix_storage='source',capacity_veh={'source':100.},decision='x',
        per_lane_capacity_veh_h=3600.,local_exits={},branches={
            'A':dict(destination='a',service_group='shared',lanes=1,mode='free_storage'),
            'B':dict(destination='b',service_group='other',lanes=1,mode='free_storage')})
    if larger_shared_branch:
        spec['branches']['B'].update(service_group='shared',lanes=2)
    if green is not None:
        spec['native_fixed_service']=dict(signal_group=1,controller=1,controller_offset_sec=0.,lanes=1)
    rows=[rc._cohort('source','prefix_tagged','A',1.,0,source=str(i)) for i in range(12)]
    rows.append(rc._cohort('source','prefix_tagged','B',1.,0,source='other'))
    # A head-passed cohort must bypass a red native head, but never a spent connector.
    rows[-1]['native_service_passed']=True
    initial=NS(route_choice_corridor_state=dict(cohorts=rows,departed_veh=0.),
        urban_link_storage={'source':87.,'a':100.,'b':100.},
        urban_arrival_buffer={},urban_storage_release_buffer={})
    results=[]
    for enabled in (False,True):
        state=deepcopy(initial);calls=[];transfers=[];checks=[]
        cfg=NS(network=NS(sdmpc_options=dict(route_service_saturation=enabled)),simulation=NS(T_u_sec=1,T_u_h=1/3600))
        def space(state,cfg,target):
            calls.append(target);return state.urban_link_storage[target]
        monkeypatch.setattr(uqm,'_effective_available_space',space)
        monkeypatch.setattr(uqm,'_link_delay_steps',lambda *args:2)
        monkeypatch.setattr(rc,'emit_transfer',lambda *a,**k:transfers.append((a[2],a[3],a[4])))
        ledger=NS(captures_response=True,_sdmpc_stream_summary_installed=True,
            record_resource_allocation=lambda *a:checks.append(a))
        monkeypatch.setattr(rc,'get_ledger',lambda s:ledger)
        monkeypatch.setattr(rc,'_native_program',lambda *args:None)
        from evaluation.controllers import fixed_signal_schedule
        monkeypatch.setattr(fixed_signal_schedule,'_union_green_overlap',lambda *args:green)
        outcome=rc._advance_one(state,None,cfg,0,spec)
        results.append((state,outcome,transfers,calls,checks,getattr(ledger,'_route_zero_service_checks',{})))
    a,b=results
    assert vars(a[0])==vars(b[0]) and a[1]==b[1] and a[2]==b[2]
    assert len(b[3])<len(a[3])/2
    assert any(check[0]=='route_choice_branch_service' for check in b[4])
    assert all(sum(check[3].values())<=check[2]+1e-9 for check in b[4])
    assert b[0].urban_link_storage['b']==99.  # Independent budget/head-passed path survives.
    from collections import Counter
    actual=Counter(row[0] for row in b[4]);actual.update(b[5])
    assert actual==Counter(row[0] for row in a[4])


def test_saturation_does_not_change_price_policy():
    assert policy_token({})==policy_token(dict(route_service_saturation=True))


def test_zero_service_summary_preserves_logical_checks_and_labels_reuse():
    from collections import Counter
    from evaluation.controllers.sdmpc_tangent_summary import model_check_summary,validate_streamed_checks
    class Records(list):pass
    records=Records([1,2]);records.kinds=Counter(route_choice_receiving=1,route_choice_branch_service=1)
    records.max_exceedance=0.
    kinds=dict(route_choice_receiving=10,route_choice_branch_service=10,native_fixed_head_service=3)
    result=model_check_summary(records,[1,2,3],kinds)
    assert result['original_checks_performed'] is False
    assert result['allocation_summary']['count']==25 and result['executed_allocation_summary']['count']==2
    assert result['state_bound_count']==3
    for mutation in ('missing_kind','different_count','nonzero_transfer','no_step_proof'):
        broken=deepcopy(result)
        if mutation=='missing_kind':broken['zero_service_reuse']['allocation_kinds'].pop('route_choice_receiving')
        elif mutation=='different_count':broken['allocation_summary']['count']+=1
        elif mutation=='nonzero_transfer':broken['zero_service_reuse']['accepted_veh']=.1
        else:broken['zero_service_reuse']['step_local_exhaustion']=False
        with pytest.raises(ValueError):validate_streamed_checks(broken)
    original=model_check_summary(records,[],{})
    assert original['schema']=='sdmpc-streamed-model-checks/v1' and original['original_checks_performed'] is True
