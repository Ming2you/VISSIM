import copy
import pytest
from diagnostics.test_shared_signal_approach import fixture, packet
from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
from diagnostics.repin_v3c3_review_20261001.urban_rm269.runtime600.shared_stock_cache_candidate import build


@pytest.mark.parametrize('green', [0., .2, 1.])
@pytest.mark.parametrize('room', [.1, 20.])
def test_uninstalled_cache_keeps_lane_changes_receiving_wait_and_service(green, room):
    initial = [packet('1', 'city', 'N', 1.), packet('2', 'city', 'E', 2.),
               packet('3', 'initial_off', 'N', 1.)]
    before = fixture(initial, cls=SharedSignalApproach)
    after = fixture(initial, cls=build())
    for step in range(8):
        for obj in (before, after):
            admitted = min(.2, obj.receiving('city'))
            obj.accept('city', admitted, step)
        args = (step, dict.fromkeys(before.lanes, green), dict(E=room, S=room, N=room))
        assert before.advance(*args) == after.advance(*args)
        for lane in (None, '1', '2', '3'):
            assert before.stock(lane) == after.stock(lane)
            assert after.stock(lane) == after.stock(lane)
        assert before.queues == after.queues
        assert before.receiving('10491') == after.receiving('10491')
        assert before.residence_veh_h == after.residence_veh_h


def test_cache_does_not_cross_copied_state_mutations():
    a = fixture([packet('1', 'city', 'E', 1.)], cls=build())
    a.stock()
    b = copy.deepcopy(a)
    b.accept('city', .5, 0)
    assert a.stock() == 1. and b.stock() == 1.5


def test_each_city_movement_sees_space_used_by_previous_capture():
    from types import SimpleNamespace as NS
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    outputs = []
    for cls in (SharedSignalApproach, build()):
        obj = fixture(cls=cls, capacity=1.)
        obj.storage = 'shared'
        obj.city_movements = {'E':'city_E', 'S':'city_S', 'N':'city_N'}
        cfg = NS(network=NS(urban_link_storage_veh={'shared':3.}))
        queues = {'city_E':1.5, 'city_S':.5, 'city_N':1.}
        state = NS(urban_link_storage={'shared':3.}, urban_movement_queue=queues.copy())
        stocks = {'movement:'+m:dict(inside=n,outside=0.) for m,n in queues.items()}
        stocks['storage:shared'] = dict(inside=0.,outside=0.)
        state._control_area_ledger = ModelAreaLedger(stocks)
        obj.capture_ready_city(state,cfg,0)
        outputs.append((obj.stock(), state.urban_movement_queue, state.urban_link_storage))
    assert outputs[0] == outputs[1]
    assert outputs[1][1]['city_S'] == .25


@pytest.mark.parametrize('reverse', [False, True])
def test_cache_keeps_control_derivatives_and_guarded_queries(reverse):
    from evaluation.controllers import sdmpc_dual, sdmpc_tangent_reverse
    from diagnostics.test_shared_signal_approach import SharedApproachDerivativeMassTests as AD
    b = sdmpc_tangent_reverse if reverse else sdmpc_dual
    outputs = []
    for cls in (AD.instrument(b), build(b)):
        trace = b.Trace([.0005], track_stencils=False)
        obj = fixture([packet('1','city','N',1.),packet('2','city','E',2.)], cls=cls)
        for step in range(8):
            obj.accept('10481', b.Dual(.2,{0:1.},trace), step)
            if reverse:
                b.PRIMAL_GUARD = True
                try:
                    obj.stock()
                finally:
                    b.PRIMAL_GUARD = False
            obj.advance(step, dict.fromkeys(obj.lanes,.4),dict(E=.5,S=.5,N=.5))
        values = [obj.stock(), obj.departed, obj.residence_veh_h]
        outputs.append([(b.primal(v), AD.gradient(b,trace,v)) for v in values])
    for a, c in zip(*outputs):
        assert a == pytest.approx(c, abs=1e-10)
