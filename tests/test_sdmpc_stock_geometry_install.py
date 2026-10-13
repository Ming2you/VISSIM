from collections import deque
from types import SimpleNamespace as NS
import copy
import pytest
from evaluation.controllers import sdmpc_stock_geometry as module
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import lane_offramp_runtime as lanes,physical_urban_transport as transport,route_choice_corridor as routes
from evaluation.controllers.sdmpc import policy_token

def test_disabled_is_noop():
    original=lanes.SharedSignalApproach.stock
    module.install(NS(backend='forward'),NS(network=NS(sdmpc_options={})),surrogate_mode=None)
    assert lanes.SharedSignalApproach.stock is original

def test_primal_assertions_keep_every_violation_and_no_derivative_state(monkeypatch):
    cls=lanes.SharedSignalApproach
    for name in ('stock','assert_conserved','assert_network_mirror'):
        monkeypatch.setattr(cls,name,getattr(cls,name))
    monkeypatch.setattr(transport.ReceivingEnvelope,'initial_bound',transport.ReceivingEnvelope.initial_bound)
    monkeypatch.setattr(routes,'_known_total',routes._known_total)
    monkeypatch.setattr(module,'_ORIGINAL_BOUND',None)
    finder=NS(backend='reverse-v1',source_hashes={})
    cfg=NS(network=NS(sdmpc_options=dict(stock_geometry_hotpath=True,prediction_hotpath=True,compact_audit=True),
                      urban_link_storage_veh={'X':200.}))
    module.install(finder,cfg,surrogate_mode='ad')
    obj=object.__new__(cls)
    trace=ad.Trace([1.]);amount=ad.Dual(1.,{0:1.},trace)
    obj.queues={'1':deque([[0,'city','straight',amount] for _ in range(160)])}
    obj.lanes={'1':dict(capacity_veh=200.)};obj.initial=160.;obj.admitted=obj.departed=0.;obj.storage='X'
    before=repr(obj.__dict__);nodes=len(trace.p1)
    obj.assert_conserved();obj.assert_network_mirror(NS(urban_link_storage={'X':40.}),cfg)
    assert repr(obj.__dict__)==before and len(trace.p1)==nodes and ad.PRIMAL_GUARD is False
    assert obj.stock().node!=0  # Physical stock still carries sensitivity.
    obj.initial=159.
    with pytest.raises(ArithmeticError,match='lost or duplicated'):obj.assert_conserved()
    obj.initial=160.;obj.lanes['1']['capacity_veh']=100.
    with pytest.raises(ArithmeticError,match='lane storage'):obj.assert_conserved()
    with pytest.raises(ArithmeticError,match='canonical storage'):obj.assert_network_mirror(NS(urban_link_storage={'X':39.}),cfg)
    assert any(p.endswith('sdmpc_stock_geometry.py') for p in finder.source_hashes)
    assert ad.PRIMAL_GUARD is False

def test_geometry_cache_never_enters_frozen_state(monkeypatch):
    monkeypatch.setattr(module,'_ORIGINAL_BOUND',transport.ReceivingEnvelope.initial_bound)
    env=transport.ReceivingEnvelope(500.,5.,15.,3.,[20.,80.,150.])
    before=copy.deepcopy(vars(env))
    module.initial_bound(env,35.)
    assert vars(env)==before
    fork=copy.deepcopy(env)
    fork.positions[0]+=2.
    assert module.initial_bound(fork,35.)==fork.initial_bound(35.)
    assert vars(env)==before

def test_scalar_keeps_stock_and_assertion_functions(monkeypatch):
    cls=lanes.SharedSignalApproach
    original={name:getattr(cls,name) for name in ('stock','assert_conserved','assert_network_mirror')}
    total=routes._known_total
    monkeypatch.setattr(transport.ReceivingEnvelope,'initial_bound',transport.ReceivingEnvelope.initial_bound)
    monkeypatch.setattr(module,'_ORIGINAL_BOUND',None)
    finder=NS(backend='reverse-v1',source_hashes={})
    cfg=NS(network=NS(sdmpc_options=dict(stock_geometry_hotpath=True,prediction_hotpath=True,compact_audit=True)))
    module.install(finder,cfg,surrogate_mode='scalar')
    assert all(getattr(cls,name) is value for name,value in original.items())
    assert routes._known_total is total
    assert transport.ReceivingEnvelope.initial_bound is module.initial_bound

def test_timing_flag_does_not_reset_physical_price_policy():
    assert policy_token(dict(max_iterations=2))==policy_token(dict(max_iterations=2,stock_geometry_hotpath=True))


def test_geometry_only_keeps_ad_stock_and_conservation_paths(monkeypatch):
    cls=lanes.SharedSignalApproach
    original={name:getattr(cls,name) for name in ('stock','assert_conserved','assert_network_mirror')}
    total=routes._known_total
    monkeypatch.setattr(transport.ReceivingEnvelope,'initial_bound',transport.ReceivingEnvelope.initial_bound)
    monkeypatch.setattr(module,'_ORIGINAL_BOUND',None)
    finder=NS(backend='reverse-v1',source_hashes={})
    cfg=NS(network=NS(sdmpc_options=dict(receiving_geometry_cache=True,prediction_hotpath=True,compact_audit=True)))
    env=transport.ReceivingEnvelope(500.,5.,15.,3.,[20.,80.,150.])
    expected=[env.initial_bound(t) for t in (1.,10.,35.,500.)]
    module.install(finder,cfg,surrogate_mode='ad')
    assert transport.ReceivingEnvelope.initial_bound is module.initial_bound
    assert [env.initial_bound(t) for t in (1.,10.,35.,500.)]==expected
    assert all(getattr(cls,name) is value for name,value in original.items())
    assert routes._known_total is total
    assert policy_token(dict(max_iterations=2))==policy_token(dict(max_iterations=2,receiving_geometry_cache=True))
