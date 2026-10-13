"""Tiny positive cohorts must survive receiving and AD without a mass cutoff."""
import math
from types import SimpleNamespace as NS

import pytest

from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers import sdmpc_dual as forward
from evaluation.controllers import sdmpc_tangent_reverse as reverse
from evaluation.controllers import sdmpc_tangent_summary as fused


@pytest.fixture(params=['forward', 'reverse', 'fused'])
def backend(request, monkeypatch):
    module = forward if request.param == 'forward' else reverse
    if request.param == 'fused':
        names = ('__add__', '__radd__', '__sub__', '__rsub__', '__mul__', '__rmul__',
                 '__truediv__', '__lt__', '__le__', '__gt__', '__ge__')
        for name in names:
            monkeypatch.setattr(reverse.Dual, name, getattr(reverse.Dual, name))
        fused.install_fused_operations()
    monkeypatch.setattr(rc, 'math', forward.MathProxy())
    return module


def gradient(module, value, trace):
    if module is forward:
        return forward.derivative(value).get(0, 0.)
    if not isinstance(value, reverse.Dual):
        return 0.
    weights = [0.] * len(trace.p1)
    weights[value.node] = 1.
    for i in range(len(weights)-1, 0, -1):
        if weights[i]:
            weights[trace.p1[i]] += weights[i] * trace.w1[i]
            weights[trace.p2[i]] += weights[i] * trace.w2[i]
    return sum(weights[n]*w for n, w in zip(trace.seed_nodes, trace.seed_weights))


@pytest.mark.parametrize('scale', [1., 1e-200])
def test_normalized_tiny_share_has_finite_derivative(backend, scale):
    trace = backend.Trace([.01])
    denominator = backend.Dual(2*scale, {0: scale}, trace)
    numerator = backend.Dual(scale, {0: 0.}, trace)
    for share in (numerator/denominator, scale/denominator):
        assert forward.primal(share) == .5
        assert gradient(backend, share, trace) == pytest.approx(-.25)
    if backend is reverse:
        assert all(math.isfinite(x) for x in (*trace.w1, *trace.w2))


@pytest.mark.parametrize('occupied,amount,expected', [(0., 1e-200, 1e-200),
    (10., 1e-200, 0.), (9., 4., 1.), (0., 10., 10.)])
def test_connector_to_road_preserves_tiny_mass_and_real_cap(backend, occupied, amount, expected):
    trace = backend.Trace([.01])
    n = backend.Dual(amount, {0: 1.}, trace)
    stock = dict(target='unknown', vehicles=occupied, speed_kph=36., due=0,
                 lane68={'shares': {'1': 1.}, 'exit_step': 0})
    moving = dict(target='unknown', vehicles=n, speed_kph=36., due=0,
                  connector68={'link': 'C', 'shares': {'1': 1.}, 'ready_step': 0})
    local = dict(physical_link='68', ramp='R', road_length_m=100.,
                 road_capacity_veh={'1': 10.},
                 connector_entries={'C': {'position_m': 0., 'lanes': [1]}})
    spec = dict(storage='W', connector_queue_gate=True, entry_lane_receiving=local)
    cfg = NS(network=NS(known_legsplit_routes=spec, urban_link_storage_veh={'W': 100.}),
             simulation=NS(T_u_sec=1.))
    state = NS(known_legsplit_route_state={'cohorts': [stock, moving]},
               urban_link_storage={'W': 100.-occupied-n}, urban_storage_release_buffer={})
    rc.known_connector_advance(state, cfg, 0)
    passed = sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts']
                 if c is not stock and 'lane68' in c)
    assert math.isclose(forward.primal(passed), expected, rel_tol=1e-12, abs_tol=0.)
    total = sum(c['vehicles'] for c in state.known_legsplit_route_state['cohorts'])
    assert forward.primal(total) == occupied+amount
    assert gradient(backend, total, trace) == pytest.approx(1.)
    if amount < 1e-100:
        assert gradient(backend, passed, trace) == (1. if occupied == 0 else 0.)
    if backend is reverse:
        assert all(math.isfinite(x) for x in (*trace.w1, *trace.w2))
