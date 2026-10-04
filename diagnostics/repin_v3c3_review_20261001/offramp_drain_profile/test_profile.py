import copy
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from evaluation.controllers import lane_plant_runtime as init
from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort


class ProfileTests(unittest.TestCase):
    def rows(self):
        return {'10682':dict(direct=True,lanes=1),'10481':dict(direct=False,lanes=2),
                '10645':dict(direct=True,lanes=1)}

    def test_install_declared_and_default(self):
        rows=self.rows()
        init.install_direct_drain_services(rows,{'drain_service_vph':{'10682':2250}},1400.)
        self.assertEqual(rows['10682']['drain_service_veh_h'],2250)
        self.assertEqual(rows['10645']['drain_service_veh_h'],1400)
        self.assertNotIn('drain_service_veh_h',rows['10481'])

    def test_invalid_declarations_rejected_atomically(self):
        for table in ({'unknown':2250},{'10481':2250},{'10682':0},{'10682':-1},
                      {'10682':float('nan')},{'10682':True}):
            with self.subTest(table=table):
                rows=self.rows();before=copy.deepcopy(rows)
                with self.assertRaises(ValueError):
                    init.install_direct_drain_services(rows,{'drain_service_vph':table},1400.)
                self.assertEqual(rows,before)

    def drain(self,room,service):
        port=DelayedPort(10,10,36,[[10,0,1]]*4,0,interval_service=True)
        row=dict(storage='P',target='T',group='G',connector=10682,to_link=121,
                 direct=True,lanes=1,drain_service_veh_h=service)
        runtime=LaneOfframpRuntime({'10682':port},{'10682':row},None,{'10682':True,'121':True})
        state=NS(urban_link_storage={'P':6.,'T':room},urban_arrival_buffer={},urban_storage_release_buffer={})
        cfg=NS(network=NS(urban_link_storage_veh={'P':10.,'T':10.},movement_capacity_veh_h=1400.))
        records=[]
        ledger=NS(captures_response=True,record_resource_allocation=lambda *x:records.append(x),
                  complete_constraint_coverage=lambda *x:None)
        with patch('evaluation.controllers.control_area_objective.get_ledger',return_value=ledger), \
             patch('evaluation.controllers.control_area_objective.emit_transfer'), \
             patch('src.models.urban_queue_model._effective_available_space',side_effect=lambda s,c,t:s.urban_link_storage[t]), \
             patch('src.models.urban_queue_model._link_delay_steps',return_value=1), \
             patch('evaluation.controllers.route_choice_corridor.direct_exit_receive',return_value=False):
            actual=runtime.drain(state,None,cfg,0,{})['G']
        self.assertAlmostEqual(port.stock+actual,4.)
        self.assertAlmostEqual(state.urban_link_storage['P'],6.+actual)
        self.assertAlmostEqual(state.urban_link_storage['T'],room-actual)
        return actual,records

    def test_profile_is_used_in_actual_drain(self):
        actual,records=self.drain(10.,2250.)
        self.assertAlmostEqual(actual,2250/3600)
        row=next(r for r in records if r[0]=='physical_offramp_target_service')
        self.assertAlmostEqual(row[2],2250/3600)

    def test_dynamic_receiving_still_limits_service(self):
        actual,_=self.drain(.1,2250.)
        self.assertAlmostEqual(actual,.1)

    def test_old_default_unchanged(self):
        actual,_=self.drain(10.,1400.)
        self.assertAlmostEqual(actual,1400/3600)


if __name__=='__main__':unittest.main()
