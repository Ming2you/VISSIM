from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_aggregate import TimeBins
from evaluation.controllers import sdmpc_dual as ad
from evaluation.controllers import sdmpc_aggregate as agg


class AggregateTests(unittest.TestCase):
    def test_fractional_arrivals_fixed_shape_no_early_release_and_tail_conserved(self):
        b=TimeBins(['left','through'],900,3);shape=b.future.shape
        b.add('left',899,.2);b.add('left',901,.3);b.add('through',904,.5)
        b.advance(900);self.assertEqual(list(b.waiting),[.2,0])
        b.advance(901);self.assertEqual(list(b.waiting),[.5,0])
        b.advance(902);b.advance(903);b.verify()
        self.assertEqual(b.future.shape,shape);self.assertAlmostEqual(sum(b.waiting)+sum(b.pending),1.)
        with self.assertRaises(ValueError):b.advance(904)

    def test_repeated_fractional_labels_and_direct_tangents_are_summed(self):
        b=TimeBins(['left'],0,5);trace=ad.Trace([1.,1.],track_stencils=False)
        b.add('left',2,ad.Dual(.2,{0:.2},trace));b.add('left',2,ad.Dual(.3,{1:.3},trace))
        for t in range(3):b.advance(t)
        self.assertEqual(ad.primal(b.waiting[0]),.5)
        self.assertEqual(ad.derivative(b.waiting[0]),{0:.2,1:.3});b.verify()

    def test_future_tail_does_not_become_eligible_and_corrupt_inventory_rejected(self):
        b=TimeBins(['ramp'],0,1);b.add('ramp',100,2.);b.advance(0);b.advance(1)
        self.assertEqual(b.waiting[0],0.);self.assertEqual(b.pending[0],2.)
        b.pending[0]=1.
        with self.assertRaises(ValueError):b.verify()

    def test_route_fraction_is_conserved_through_receiving_and_next_stage_delay(self):
        stages=[dict(origin='s0',movement='m0',distance_m=1.),dict(origin='s1',movement='m1',distance_m=1.)]
        cfg=NS(mpc=NS(horizon_steps=1),simulation=NS(T_c_sec=5.,T_u_sec=1.),network=NS(
            native_internal_inputs={'inputs':{'A':{'route_stages':stages}}},urban_avg_speed_km_h=36.,
            urban_link_storage_veh={'s0':100.,'s1':100.},urban_movements={'m0':{'receiving_link':'s1'},'m1':{}}))
        state=NS(time_sec=0.,urban_link_speed_kph={},urban_link_storage={'s0':100.,'s1':100.},
            urban_movement_queue={'m0':4.,'m1':0.},native_input_route_state=dict(last_step=-1,
                cohorts=[dict(input='A',stage=0,queued=True,due=0,vehicles=n) for n in (.25,.75,3.)],
                initial_veh=4.,received_veh=0.,completed_veh=0.))
        with patch('evaluation.controllers.control_area_objective.get_ledger',return_value=None),\
             patch('evaluation.controllers.control_area_objective.emit_transfer'),\
             patch('src.models.urban_queue_model._queue_max',return_value=10.),\
             patch('src.models.urban_queue_model._link_delay_steps',return_value=1):
            agg.route_advance(state,cfg,0)
            state.urban_movement_queue['m0']=3.;state.urban_link_storage['s1']=99.
            self.assertTrue(agg.route_accept(state,cfg,'m0',1.,0))
            self.assertEqual(state.urban_movement_queue['m1'],0.)
            agg.route_advance(state,cfg,1)
            self.assertEqual(state.urban_movement_queue['m1'],1.)
            self.assertEqual(state.urban_link_storage['s1'],100.)
            state.native_input_route_state['aggregate']['bins'].verify()

    def test_first_head_service_cannot_skip_the_second_head_travel_delay(self):
        spec=dict(origin='s',branches={'L':{'movement':'mL','probability':.5},'R':{'movement':'mR','probability':.5}},
            left_movement='mL',capacity_reference_movement='mR',first_phase='SC1_p1',
            physical_head_lanes=1,wn_movements=['mR'],decision_to_head_m=10.,interhead_distance_m=20.)
        cfg=NS(mpc=NS(horizon_steps=1),simulation=NS(T_c_sec=5.,T_u_sec=1.,T_u_h=1/3600.),network=NS(
            native_internal_inputs={'inputs':{'A':{'kind':'native_choice_prehead','prehead_spec':spec}}},
            urban_avg_speed_km_h=36.,urban_link_storage_veh={'s':100.},urban_movements={'mL':{},'mR':{}}))
        state=NS(time_sec=0.,urban_link_speed_kph={},urban_link_storage={'s':100.},urban_movement_queue={'mL':2.,'mR':0.},
            native_input_prehead_state=dict(last_step=-1,finished_step=-1,initial_veh=2.,generated_veh=0.,
                departed_scope_veh=0.,first_head_service_veh=0.,existing_wn_budget_overdraw_veh=0.,wn_actual={},
                cohorts=[dict(input='A',route='L',stage='queue',vehicles=2.,due=0,ready=0,passed_first=False)]))
        with patch('evaluation.controllers.control_area_objective.get_ledger',return_value=None),\
             patch('src.models.urban_queue_model._phase_green_fraction',return_value=1.),\
             patch('src.models.urban_queue_model._movement_capacity_flow',return_value=3600.):
            for t in (0,1):
                agg.prehead_advance(state,cfg,t)
                self.assertEqual(agg.prehead_limit(state,cfg,'mL',2.,2.,t),0.)
                agg.prehead_finish(state,NS(),cfg,t)
            agg.prehead_advance(state,cfg,2)
            self.assertEqual(agg.prehead_limit(state,cfg,'mL',2.,2.,2),1.)
            state.urban_movement_queue['mL']=1.
            agg.prehead_accept(state,cfg,'mL',1.,2)
            self.assertEqual(state.native_input_prehead_state['departed_scope_veh'],1.)
            state.native_input_prehead_state['aggregate']['bins'].verify()


if __name__=='__main__':unittest.main()
