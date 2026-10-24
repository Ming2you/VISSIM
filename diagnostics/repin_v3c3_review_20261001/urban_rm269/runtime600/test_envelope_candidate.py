import importlib.util
from pathlib import Path
import random
import struct
import pytest
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope

spec=importlib.util.spec_from_file_location('envelope_candidate',Path(__file__).with_name('envelope_candidate.py'))
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)

@pytest.fixture(autouse=True,params=['prototype','production'])
def implementation(request,monkeypatch):
    if request.param=='production':
        from evaluation.controllers import sdmpc_stock_geometry
        monkeypatch.setattr(sdmpc_stock_geometry,'_ORIGINAL_BOUND',ReceivingEnvelope.initial_bound)
        monkeypatch.setitem(globals(),'candidate',sdmpc_stock_geometry)

def bits(x): return struct.pack('d',x)

@pytest.mark.parametrize('count',[0,1,12,50,80])
def test_bound_at_wave_and_position_breakpoints_is_bitwise_equal(count):
    rng=random.Random(81+count)
    env=ReceivingEnvelope(500.,5.,13.89,3.2557309454394003,
                          [rng.uniform(0.,500.) for _ in range(count)])
    times=[0.,-1.,1.,15.,150.,450.,500./env.wave]
    times += [x/env.wave for x in env.points]
    times += [t+1e-12 for t in times]
    for elapsed in times:
        expected=bits(env.initial_bound(elapsed))
        assert bits(candidate.initial_bound(env,elapsed))==expected
        assert bits(candidate.initial_bound(env,elapsed))==expected

def test_geometry_mutation_rebuilds_and_no_departure_history_is_cached():
    import copy
    env=ReceivingEnvelope(300.,6.,15.,3.,[20.,40.,180.])
    candidate.initial_bound(env,20.)
    for update in [dict(wave=4.), dict(critical=.1),dict(qmax=1.),
                   dict(positions=[35.,70.,190.]),dict(points=[0.,35.,70.,190.,300.])]:
        for k,v in update.items(): setattr(env,k,v)
        assert bits(candidate.initial_bound(env,20.))==bits(env.initial_bound(20.))
    fork=copy.deepcopy(env)
    fork.positions[1]=80.
    assert bits(candidate.initial_bound(fork,21.))==bits(fork.initial_bound(21.))
    assert env.positions[1]==70.

def test_runtime_wave_dual_keeps_original_path():
    from evaluation.controllers import sdmpc_tangent_reverse as ad
    def evaluate(fn):
        env=ReceivingEnvelope(300.,6.,15.,3.,[20.,40.,180.])
        trace=ad.Trace([1.]);env.wave=ad.Dual(3.,{0:1.},trace)
        out=fn(env,20.)
        return (ad.primal(out),getattr(out,'node',0),getattr(out,'support',0),
                tuple(v.tobytes() for v in (trace.p1,trace.p2,trace.w1,trace.w2)),dict(trace.counts))
    assert evaluate(ReceivingEnvelope.initial_bound)==evaluate(candidate.initial_bound)
