from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import patch
import unittest
from candidate import compile_method, enabled, service, settings


class BranchServiceTest(unittest.TestCase):
    def test_scope_and_rate_are_past_supported(self):
        rates, _ = settings()
        spec = dict(decision='1129', per_lane_capacity_veh_h=206.53061224489795)
        self.assertEqual(service(spec, dict(service_group='bypass', lanes=2), rates), 904)
        self.assertEqual(service(spec, dict(service_group='local', lanes=2), rates), 413.0612244897959)
        spec['decision'] = '1130'
        self.assertEqual(service(spec, dict(service_group='bypass', lanes=2), rates), 413.0612244897959)

    def execute(self, rate=None, room=100.):
        from evaluation.controllers.aggregate_route_corridors import Routes
        from evaluation.controllers import route_choice_corridor as rc
        from src.models import urban_queue_model as uqm
        labels = [('P','prefix_tagged','1','a',None,()),
                  ('P','prefix_tagged','1','b',None,()),
                  ('P','prefix_tagged','2','c',None,())]
        class Bins:
            def __init__(self): self.waiting = [5., 15., 3.]; self.labels = labels
            def total(self, j): return self.waiting[j]
        obj = Routes.__new__(Routes)
        obj.start=0;obj.dt=1;obj.by_decision={'1129':[0,1,2]};obj.by_storage={'P':[0,1,2]};obj.bins=Bins()
        spec=dict(decision='1129',capacity_veh={'P':23.},per_lane_capacity_veh_h=206.53061224489795,
                  branches={'1':dict(service_group='bypass',lanes=2,mode='free_storage',destination='T'),
                            '2':dict(service_group='local',lanes=2,mode='free_storage',destination='L')},local_exits={})
        state=NS(urban_link_storage={'P':0.,'T':room,'L':100.},urban_arrival_buffer={},urban_storage_release_buffer={},
                 route_choice_corridor_state={'aggregate_routes':obj,'departed_veh':0.})
        cfg=NS(simulation=NS(T_u_h=10/3600,T_u_sec=10))
        original=Routes.advance_one
        method=original if rate is None else compile_method(original,rate)[0]
        emitted=[]
        with patch.object(uqm,'_effective_available_space',side_effect=lambda s,c,t:s.urban_link_storage[t]), \
             patch.object(uqm,'_link_delay_steps',return_value=1), \
             patch.object(rc,'get_ledger',return_value=None), \
             patch.object(rc,'emit_transfer',side_effect=lambda s,c,source,target,n,**kw:emitted.append((source,target,n))):
            result=method(obj,state,None,cfg,0,spec)
        self.assertAlmostEqual(sum(obj.bins.waiting)+state.urban_link_storage['P'],23.)
        self.assertAlmostEqual(sum(n for _,_,n in emitted),state.route_choice_corridor_state['departed_veh'])
        return result,deepcopy(state.urban_link_storage),deepcopy(state.urban_arrival_buffer),list(obj.bins.waiting)

    def test_empty_override_preserves_original_allocation_exactly(self):
        self.assertEqual(self.execute(),self.execute({}))

    def test_two_tags_share_one_budget_other_branch_unchanged(self):
        old=self.execute();new=self.execute({'1129:branch:bypass':904.})
        self.assertAlmostEqual(new[0]['branch:bypass'],904*10/3600)
        self.assertEqual(new[0]['branch:local'],old[0]['branch:local'])
        self.assertAlmostEqual((5-new[3][0])/(15-new[3][1]),1/3)

    def test_receiver_still_limits_actual_accepted_flow(self):
        out=self.execute({'1129:branch:bypass':904.},room=.7)
        self.assertAlmostEqual(out[0]['branch:bypass'],.7)
        self.assertAlmostEqual(out[1]['T'],0.)

    def test_scoped_method_restores_even_after_error(self):
        from evaluation.controllers.aggregate_route_corridors import Routes
        old=Routes.advance_one
        with self.assertRaises(RuntimeError):
            with enabled():
                self.assertIsNot(Routes.advance_one,old)
                raise RuntimeError('test')
        self.assertIs(Routes.advance_one,old)


if __name__=='__main__':unittest.main()
