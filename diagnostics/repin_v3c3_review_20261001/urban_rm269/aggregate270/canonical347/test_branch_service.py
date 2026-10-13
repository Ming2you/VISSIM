"""Physical allocation equivalence for the explicit aggregate service setting."""
import copy
import pickle
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from evaluation.controllers import aggregate_route_corridors as model
from evaluation.controllers import route_choice_corridor as rc
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315 import candidate as legacy


def config():
    spec = dict(decision='1129', capacity_veh={'P': 23.}, per_lane_capacity_veh_h=206.53061224489795,
        branches={'1': dict(service_group='bypass', lanes=2, mode='free_storage', destination='T'),
                  '2': dict(service_group='local', lanes=2, mode='free_storage', destination='L')}, local_exits={})
    return NS(network=NS(route_choice_corridor=spec), simulation=NS(T_u_h=10/3600, T_u_sec=10)), spec


def execute(mode, room=100., native_cap=None):
    from src.models import urban_queue_model as uqm
    cfg, spec = config()
    rates = {'1129:branch:bypass': 904.}
    if mode == 'static':
        model.configure_branch_service(cfg, rates)
        # The child worker receives values, not a mutated function or source text.
        cfg = pickle.loads(pickle.dumps(cfg)); spec = cfg.network.route_choice_corridor
    if native_cap is not None:
        spec['native_fixed_service'] = dict(calibrated_service_veh_h=native_cap, lanes=2,
            signal_group=1, controller_offset_sec=0, controller=7)
    obj = model.Routes.__new__(model.Routes)
    labels = [('P','prefix_tagged','1','a',None,()), ('P','prefix_tagged','1','b',None,()),
              ('P','prefix_tagged','2','c',None,())]
    obj.start=0; obj.dt=1; obj.by_decision={'1129':[0,1,2]}; obj.by_storage={'P':[0,1,2]}
    obj.bins=NS(waiting=[5.,15.,3.], labels=labels)
    obj.bins.total=lambda j: obj.bins.waiting[j]
    state=NS(urban_link_storage={'P':0.,'T':room,'L':100.}, urban_arrival_buffer={},
        urban_storage_release_buffer={}, route_choice_corridor_state={'aggregate_routes':obj,'departed_veh':0.})
    method = legacy.compile_method(model.Routes.advance_one, rates)[0] if mode=='legacy' else model.Routes.advance_one
    emitted=[]
    with patch.object(uqm,'_effective_available_space',side_effect=lambda s,c,t:s.urban_link_storage[t]), \
         patch.object(uqm,'_link_delay_steps',return_value=1), \
         patch.object(rc,'get_ledger',return_value=None), patch.object(rc,'_native_program',return_value={}), \
         patch('evaluation.controllers.fixed_signal_schedule._union_green_overlap',return_value=3.), \
         patch.object(rc,'emit_transfer',side_effect=lambda s,c,a,b,n,**kw:emitted.append((a,b,n))):
        result=method(obj,state,None,cfg,0,spec)
    assert abs(sum(obj.bins.waiting)+state.urban_link_storage['P']-23)<1e-10
    assert abs(sum(n for _,_,n in emitted)-state.route_choice_corridor_state['departed_veh'])<1e-10
    return result, copy.deepcopy(state.urban_link_storage), copy.deepcopy(state.urban_arrival_buffer), obj.bins.waiting


class BranchServiceTests(unittest.TestCase):
    def test_pickle_restores_same_tagged_shared_budget(self):
        self.assertEqual(execute('static'),execute('legacy'))
        old=execute('default'); new=execute('static')
        self.assertEqual(new[0]['branch:local'],old[0]['branch:local'])
        self.assertAlmostEqual(new[0]['branch:bypass'],904*10/3600)
        self.assertAlmostEqual((5-new[3][0])/(15-new[3][1]),1/3)

    def test_actual_downstream_room_still_binds(self):
        self.assertEqual(execute('static',.7),execute('legacy',.7))
        self.assertAlmostEqual(execute('static',.7)[0]['branch:bypass'],.7)

    def test_native_shared_head_still_binds(self):
        self.assertEqual(execute('static',100.,100.),execute('legacy',100.,100.))
        self.assertLessEqual(sum(execute('static',100.,100.)[0].values()),100*3/3600+1e-12)

    def test_unknown_or_invalid_rates_fail_atomically(self):
        for rates in ({'1129:branch:missing':904}, {'1129:branch:bypass':-1},
                      {'1129:branch:bypass':True}, {'1129:branch:bypass':float('nan')},
                      {'1129:branch:bypass':float('inf')}, None):
            with self.subTest(rates=rates):
                cfg,spec=config(); old=copy.deepcopy(spec)
                with self.assertRaises(ValueError):model.configure_branch_service(cfg,rates)
                self.assertEqual(spec,old)

    def test_empty_setting_does_not_modify_default_spec(self):
        cfg,spec=config(); old=copy.deepcopy(spec)
        self.assertEqual(model.configure_branch_service(cfg,{}),{})
        self.assertEqual(spec,old)

    def test_missing_aggregate_clock_cannot_silently_ignore_setting(self):
        cfg,_=config()
        with self.assertRaises(ValueError):
            model.configure(cfg,{'urban':{'route_corridor_branch_service_veh_h':{'1129:branch:bypass':904}}},None)


if __name__=='__main__':unittest.main()
