import pytest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.reservoir import LaneTurnReservoir
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.interval_service import green_seconds, meter_service_vehicles


def make(dt):
    return LaneTurnReservoir({'1':2000.},[('1','ramp')],2400,450,dt)


@pytest.mark.parametrize('dt',[1,5,10])
def test_constant_flow_conservation_time_cost_and_update_count(dt):
    r=make(dt);r.seed('1','ramp',1000.,2400)
    for _ in range(450//dt):r.step({'1':dt*.4},{'ramp':dt*.3})
    assert r.exited==pytest.approx(135.)
    assert r.stock()==pytest.approx(865.)
    assert r.residence_veh_h==pytest.approx((1000+865)/2*450/3600)
    assert r.time==2850
    assert r.bins.future.shape==(1,450//dt+2)


def test_ten_second_arrivals_do_not_become_eligible_early():
    r=make(10);r.seed('1','ramp',2.,2401)
    assert r.step({'1':10.},{'ramp':10.})[('1','ramp')]==0.
    assert r.time==2410
    assert r.step({'1':10.},{'ramp':10.})[('1','ramp')]==2.


def test_fractional_eta_rounds_later_not_before_arrival():
    r=make(10);r.seed('1','ramp',2.,2410.1)
    for _ in range(2):assert r.step({'1':10.},{'ramp':10.})[('1','ramp')]==0.
    assert r.step({'1':10.},{'ramp':10.})[('1','ramp')]==2.


def test_control_at_150s_boundary_is_not_shifted_by_coarse_clock():
    r=make(10);r.seed('1','ramp',1000.,2400)
    for _ in range(45):
        rate=.2 if r.time<2550 else .4
        r.step({'1':rate*10},{'ramp':10.})
    assert r.exited==pytest.approx(150*.2+300*.4)


def test_lateral_step_probability_uses_elapsed_seconds():
    # Identical constant hazard, unrestricted receiving: 10 x 1s equals 1 x 10s.
    import math
    results=[]
    for dt in (1,10):
        r=LaneTurnReservoir({'1':20.,'2':20.},[('1','ramp'),('2','ramp')],0,10,dt)
        r.seed('2','ramp',10.,0)
        for _ in range(10//dt):
            r.step({'1':0.,'2':0.},{'ramp':0.})
            ready=r.bins.waiting[r.bins.index[('2','ramp')]]
            r.transfer_ready({(('2','ramp'),('1','ramp')):ready*(-math.expm1(-.08*dt))})
        results.append(r.stock('1'))
    assert results[0]==pytest.approx(results[1])


@pytest.mark.parametrize('start,duration,cycle,green,offset,expected',[
    (0,10,10,2,0,2),(2,10,10,2,0,2),(8,5,10,2,0,2),
    (0,1,10,2,2.5,0),(2,2,10,2,2.5,1.5),(0,450,150,32.5,15,97.5),
    (-5,10,10,4,0,4),(0,10,10,0,0,0),(0,10,10,10,0,10)])
def test_analytic_green_overlap(start,duration,cycle,green,offset,expected):
    assert green_seconds(start,duration,cycle,green,offset)==pytest.approx(expected)
    assert sum(green_seconds(start+i,1,cycle,green,offset) for i in range(duration))==pytest.approx(expected)


@pytest.mark.parametrize('g,rate',[(0,0.),(2,255.6),(4,518.4),(8,1166.4),(10,1512.)])
def test_ten_second_meter_cycle_uses_calibrated_mean_once(g,rate):
    result=meter_service_vehicles(rate,2400,10,10,g)
    assert result==pytest.approx(rate*10/3600)
    assert sum(meter_service_vehicles(rate,2400+i,1,10,g) for i in range(10))==pytest.approx(result)


def test_green_and_flow_derivatives_survive_interval_integration():
    from evaluation.controllers import sdmpc_dual as ad
    trace=ad.Trace([.001]);g=ad.Dual(3.2,{0:1.},trace)
    assert ad.derivative(green_seconds(0,10,10,g))[0]==pytest.approx(1.)
    q=ad.Dual(500.,{0:1.},trace)
    assert ad.derivative(meter_service_vehicles(q,0,10,10,3.2))[0]==pytest.approx(10/3600)
    r=make(10);r.seed('1','ramp',1000.,2400)
    out=r.step({'1':q*10/3600},{'ramp':10.})[('1','ramp')]
    assert ad.derivative(out)[0]==pytest.approx(10/3600)
    assert ad.derivative(r.residence_veh_h)[0]==pytest.approx(-.5*10/3600*10/3600)


@pytest.mark.parametrize('dt',[0,-1,2.5,7])
def test_invalid_clock_cannot_change_horizon(dt):
    with pytest.raises(ValueError):make(dt)
