from types import SimpleNamespace as NS
import pytest
from evaluation.controllers.multirate_coupling import plan_coverage,prepare_ramp_admission_windows,ramp_admission_windows
from evaluation.controllers.control_area_objective import ModelAreaLedger
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from evaluation.controllers import known_wout_causal_response as causal


def fixture():
    ledger=ModelAreaLedger({},capture_response=True,indexed_coverage=True)
    control=NS(**dict.fromkeys(('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'),{}))
    state=NS(time_sec=100,freeway_density={},urban_movement_queue={})
    ledger.record_freeway_operands(state,control,initial=True)
    return ledger,state,control


def test_coverage_requires_both5s_frames_and10s_landing_visits():
    ledger,state,control=fixture()
    plan_coverage(ledger,100,10,['urban_allocator'],('off',))
    for scope in ('urban_allocator',):
        ledger.begin_response_step('urban',100,110);ledger.complete_constraint_coverage(scope)
    for sec in (100,105):
        ledger.begin_response_step('freeway',sec,sec+5)
        for scope in ('physical_ramp_release','freeway_allocator'):ledger.complete_constraint_coverage(scope)
        ledger.record_freeway_operands(state,control,{},multirate_exchange=True)
    assert not ledger.response()['model_constraint_coverage']['complete']
    ledger.begin_response_step('landing',100,110)
    for scope in ('offramp_landing','offramp_landing:off'):ledger.complete_constraint_coverage(scope)
    assert ledger.response()['model_constraint_coverage']['complete']
    ledger._response['freeway_frames'].pop()
    assert not ledger.response()['model_constraint_coverage']['complete']


def test_intermediate_frame_cannot_bypass_declared_allocator_or_old_residence():
    ledger,state,control=fixture();ledger.begin_response_step('freeway',100,105)
    with pytest.raises(ValueError,match='declared'):ledger.record_freeway_operands(state,control,{},multirate_exchange=True)
    with pytest.raises(ValueError,match='post-landing'):ledger.record_freeway_operands(state,control,{})


def test_causal_admission_uses_new10s_window_without_borrowing_future_service():
    b=PhysicalRampBoundary(connector_id='test',length_m=72.,head_position_m=60.,lanes=1,
        spacing_m=6.,travel_speed_kmh=36.,time_sec=100.,initial_cohorts=[])
    causal.attach(b,3.);b._causal_receiving_enabled=True
    old=b._spatial_entry
    assert b.current_admission_space()==0.
    windows=prepare_ramp_admission_windows(NS(buffers={'r':b}),100.)
    with ramp_admission_windows(windows):
        available=b.current_admission_space()
        assert available>0.
    assert b._spatial_entry is old and b.time_sec==100.
    for t in (100.,105.):
        b.advance_coarse_interval(start_sec=t,duration_sec=5.,cycle_sec=10.,
            receiving_budget_veh=0.,service_veh=0.,mode='RED',green_sec=0.)
    with ramp_admission_windows(windows):
        b.admit_current(available)
        assert b.current_admission_space()==pytest.approx(0.)
    assert b._spatial_entry is old and old['departure_times']==[0,5.,10.]
    assert b.snapshot()['connector_veh']==pytest.approx(available)
    assert b.snapshot()['conservation_residual_veh']==pytest.approx(0.)
