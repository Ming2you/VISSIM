"""State-driven entry receiving: conservation, causal release, and opt-in scope."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary

from evaluation.controllers import ramp_entry_receiving as module


def make(positions=(6.,12.,18.,24.,30.,36.,42.,48.,54.,60.)):
    return PhysicalRampBoundary(connector_id='target', length_m=72., head_position_m=60.,
        lanes=1, spacing_m=6., travel_speed_kmh=36., time_sec=100.,
        initial_cohorts=[(p,0.,1) for p in positions])


def configure(buffers, names=None, wave=3.):
    cfg = NS(simulation=NS(T_f_sec=5., T_u_sec=10.))
    state = NS(time_sec=100., lane_ramp_runtime=NS(buffers=buffers))
    return module.configure(cfg, {'urban': {'single_lane_causal_receiving':
        {'ramps': list(buffers) if names is None else names, 'wave_m_s':wave}}}, state)


def step(b, arrivals=0., service=0.):
    return b.advance_coarse_interval(start_sec=b.time_sec,duration_sec=5.,cycle_sec=10.,
        receiving_budget_veh=100.,service_veh=service,mode='OFF',green_sec=None,
        request_arrivals_veh=arrivals)


def test_disabled_requires_no_runtime():
    assert module.configure(None, {}, None)=={}


def test_mass_and_time_unchanged_and_only_named_target_installed():
    target, untouched = make(), make(())
    before = target.snapshot()
    configure({'A':target,'B':untouched},['A'])
    assert target.snapshot()==before and not hasattr(untouched,'_spatial_entry')
    assert target._spatial_entry['envelope'].initial==10


def test_unknown_second_target_does_not_partly_install_first():
    b=make()
    with pytest.raises(ValueError,match='Unknown'):
        configure({'A':b},['A','B'])
    assert not hasattr(b,'_spatial_entry')


def test_duplicate_and_double_install_rejected():
    b=make()
    with pytest.raises(ValueError,match='distinct'):
        configure({'A':b},['A','A'])
    configure({'A':b})
    with pytest.raises(ValueError,match='fresh'):
        configure({'A':b})


def test_too_short_wave_lag_rejected_before_mutation():
    b=make()
    with pytest.raises(ValueError,match='wave lag'):
        configure({'A':b},wave=20.)
    assert not hasattr(b,'_spatial_entry')


def test_head_release_cannot_immediately_reopen_upstream_entry():
    b=make();configure({'A':b})
    first=step(b,service=4.)
    assert first['head_service_veh']==2.
    # Backward-wave delay is20s, even though aggregate prehead room exists now.
    for _ in range(3):
        r=step(b,arrivals=1.)
        assert r['admitted_arrivals_veh']==pytest.approx(0.,abs=1e-12)
        assert abs(r['conservation_residual_veh'])<1e-9
    r=step(b,arrivals=1.)
    assert r['admitted_arrivals_veh']>0.
    assert abs(r['conservation_residual_veh'])<1e-9


def test_uncongested_entry_and_head_dynamics_unchanged():
    old=make(());new=deepcopy(old);configure({'A':new})
    for _ in range(8):
        a,b=step(old,arrivals=.2,service=4.),step(new,arrivals=.2,service=4.)
        for field in ('admitted_arrivals_veh','head_service_veh','accepted_merge_veh','end'):
            assert a[field]==b[field]


def test_cloned_candidate_has_independent_history():
    b=make();configure({'A':b});other=deepcopy(b)
    step(b,service=4.)
    assert other.time_sec==100. and 'departure_times' not in other._spatial_entry
    assert b._spatial_entry['departure_times']==[0.,5.]
