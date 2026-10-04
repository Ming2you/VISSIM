"""Destination ownership must survive different travel and receiving delays."""
import copy
from types import SimpleNamespace as NS
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from evaluation.controllers import route_choice_corridor as rc


class DestinationTravelTests(unittest.TestCase):
    def fixture(self):
        storage='SC1001_W_out'
        paths={'E':[dict(link='31',start=0.,stop=412.)],
               'W':[dict(link='31',start=0.,stop=412.),dict(link='124',start=0.,stop=322.)],
               'free':[dict(link='31',start=0.,stop=412.),dict(link='124',start=0.,stop=323.)]}
        travel=dict(paths=paths,weights={'E':.5,'W':1/3,'free':1/6},
                    incoming={'m':dict(link='31',position=0.,distance=10.,origin='origin',connector='10119')},
                    direct_entry=dict(link='124',position=201.))
        cfg=NS(network=NS(direct_exit_legsplit=dict(storage=storage,connector='10483',travel=travel),
              urban_link_storage_veh={storage:100.},urban_avg_speed_km_h=60.),
              simulation=NS(T_u_sec=1.))
        state=NS(urban_link_storage={storage:94.},urban_storage_release_buffer={storage:{}},
                 urban_link_speed_kph={'origin':60.,storage:60.},
                 direct_exit_route_state=dict(initial=6.,received=0.,departed=0.,plan=None,
                   cohorts=[dict(target='E',due=10,vehicles=3.),dict(target='W',due=20,vehicles=2.),
                            dict(target='free',due=20,vehicles=1.)]))
        return state,cfg,storage

    def test_destination_does_not_redraw_when_one_receiver_blocks(self):
        s,c,k=self.fixture()
        request=rc.direct_exit_requests(s,c,k,.01,6.,20)
        self.assertEqual(request,{'E':3.,'W':2.,'free':1.})
        s.urban_link_storage[k]+=3.
        rc.direct_exit_commit(s,c,[(k,'W',2.),(k,None,1.)],20)
        self.assertEqual(rc.direct_exit_requests(s,c,k,.01,3.,21),{'E':3.})

    def test_no_second_exponential_delay_and_no_early_long_path_release(self):
        s,c,k=self.fixture()
        self.assertEqual(rc.direct_exit_requests(s,c,k,.0001,3.,10),{'E':3.})

    def test_direct_offramp_stays_free_and_uses_remaining_distance(self):
        s,c,k=self.fixture();s.urban_link_storage[k]-=4.
        self.assertTrue(rc.direct_exit_receive(s,c,'10483',k,4.,999,entry_step=20))
        row=s.direct_exit_route_state['cohorts'][-1]
        self.assertEqual((row['target'],row['vehicles'],row['due']),('free',4.,28))
        self.assertEqual(s.urban_storage_release_buffer[k],{28:4.})

    def test_new_urban_mass_is_split_once_and_reserved_by_destination(self):
        s,c,k=self.fixture();s.urban_link_storage[k]-=6.
        self.assertTrue(rc.direct_exit_movement_receive(s,c,'m',6.,20))
        new=s.direct_exit_route_state['cohorts'][3:]
        self.assertEqual({r['target']:r['vehicles'] for r in new},{'E':3.,'W':2.,'free':1.})
        self.assertLess(new[0]['due'],new[1]['due'])
        self.assertAlmostEqual(sum(s.urban_storage_release_buffer[k].values()),6.)

    def test_initial_position_beyond_first_branch_excludes_east(self):
        s,c,k=self.fixture()
        weights=rc._direct_reachable_weights(c.network.direct_exit_legsplit['travel'],'124',250.)
        self.assertEqual(set(weights),{'W','free'})
        self.assertAlmostEqual(weights['W'],2/3)
        with self.assertRaises(ValueError):rc._direct_reachable_weights(c.network.direct_exit_legsplit['travel'],'124',324.)

    def test_physical_path_does_not_use_lane_inflated_speed(self):
        s,c,k=self.fixture()
        travel=c.network.direct_exit_legsplit['travel']
        travel['speed_source']='physical_observation'
        travel['incoming']['m']['distance']=540.6832337034456-412.
        s.urban_link_speed_kph['origin']=139.09846481720706
        s.local_observation_summary={'urban_link_speed_kph':{'origin':40.780464436792734}}
        s.urban_link_storage[k]-=6.
        before=copy.deepcopy(s.urban_link_speed_kph)
        rc.direct_exit_movement_receive(s,c,'m',6.,2250)
        self.assertEqual(s.direct_exit_route_state['cohorts'][3]['due'],2298)
        self.assertEqual(s.urban_link_speed_kph,before)  # Legacy delay still uses effective speed.

    def test_physical_direct_exit_uses_unscaled_storage_speed(self):
        s,c,k=self.fixture()
        c.network.direct_exit_legsplit['travel']['speed_source']='physical_observation'
        s.urban_link_speed_kph[k]=180.
        s.local_observation_summary={'urban_link_speed_kph':{k:60.}}
        s.urban_link_storage[k]-=4.
        rc.direct_exit_receive(s,c,'10483',k,4.,999,entry_step=20)
        self.assertEqual(s.direct_exit_route_state['cohorts'][-1]['due'],28)

    def test_physical_speed_missing_sample_uses_nominal_not_effective(self):
        s,c,k=self.fixture()
        c.network.direct_exit_legsplit['travel']['speed_source']='physical_observation'
        s.urban_link_speed_kph['origin']=180.
        s.local_observation_summary={'urban_link_speed_kph':{}}
        s.urban_link_storage[k]-=6.
        rc.direct_exit_movement_receive(s,c,'m',6.,20)
        self.assertEqual(s.direct_exit_route_state['cohorts'][3]['due'],46)

    def test_physical_speed_requires_observation_provenance(self):
        s,c,k=self.fixture()
        c.network.direct_exit_legsplit['travel']['speed_source']='physical_observation'
        s.urban_link_storage[k]-=6.
        with self.assertRaisesRegex(ValueError,'physical speed observation'):
            rc.direct_exit_movement_receive(s,c,'m',6.,20)

    def test_no_other_movement_is_swallowed(self):
        s,c,k=self.fixture();before=copy.deepcopy(vars(s))
        self.assertFalse(rc.direct_exit_movement_receive(s,c,'other',5.,20))
        self.assertEqual(vars(s),before)

    def test_option_cannot_silently_run_without_direct_destination_ownership(self):
        s,c,k=self.fixture()
        with self.assertRaisesRegex(ValueError,'requires preserved'):
            rc.configure_direct_exit_legsplit(c,{'urban':{'sc1001_destination_travel':{
                'initial_unknown':'reachable_native_prior'}}},s,{})

    def configuration_fixture(self):
        s,c,k=self.fixture()
        del c.network.direct_exit_legsplit['travel']
        c.network.urban_movements={'m':dict(receiving_link=k,origin='origin',beta=1.)}
        c.network.control_area_routes={'movement:m':dict(physical_turns=[dict(to_link='31',connector='10119')])}
        s.time_sec=0.;s.urban_arrival_buffer={}
        s.lane_offramp_runtime=NS(membership={'31':True,'10774':True,'124':True,'10775':False})
        records=[dict(veh_no=i,link_no=31 if i<4 else 124,position_m=100.,speed_kph=60.) for i in range(6)]
        s.local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{
            '31':{'storage:'+k:4.},'124':{'storage:'+k:2.}}}}
        p=Path(__file__).resolve().parents[1]/'integration_20260926/selected/network/native_seed29.inpx'
        return s,c,k,records,ET.parse(p).getroot()

    def test_selected_geometry_preserves_observed_stock_and_native_weights(self):
        s,c,k,records,tree=self.configuration_fixture()
        with patch.object(rc,'complete_records',return_value=records):
            rc._configure_direct_transport(c,s,{},tree)
        travel=c.network.direct_exit_legsplit['travel']
        self.assertEqual(travel['weights'],{'RM_C10484':.5,'free':1/6,'RM_C10480':1/3})
        self.assertAlmostEqual(travel['paths']['RM_C10484'][0]['stop'],412.08696861958236)
        self.assertEqual(s.urban_link_storage[k],94.)
        self.assertAlmostEqual(sum(x['vehicles'] for x in s.direct_exit_route_state['cohorts']),6.)
        self.assertAlmostEqual(sum(x['vehicles'] for x in s.direct_exit_route_state['cohorts'] if x['target']=='RM_C10484'),2.)

    def test_future_route_overwrite_or_signal_or_foreign_owner_is_rejected(self):
        for bad in ('decision','signal','owner'):
            with self.subTest(bad=bad):
                s,c,k,records,tree=self.configuration_fixture()
                if bad=='decision':ET.SubElement(tree.find('./vehicleRoutingDecisionsStatic'),'vehicleRoutingDecisionStatic',no='99999',link='124')
                elif bad=='signal':ET.SubElement(tree.find('./signalHeads'),'signalHead',lane='31 1',pos='300')
                else:s.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['99999']={'storage:'+k:1.}
                with patch.object(rc,'complete_records',return_value=records):
                    with self.assertRaises(ValueError):rc._configure_direct_transport(c,s,{},tree)

    def test_initial_incoming_connector_retains_stock_and_remaining_travel(self):
        due = []
        for position in (10., 130.):
            s,c,k,records,tree=self.configuration_fixture()
            records[0].update(link_no=10119,position_m=position)
            owners=s.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            owners['31']['storage:'+k]-=1.
            owners['10119']={'storage:'+k:1.}
            with patch.object(rc,'complete_records',return_value=records):
                metadata=rc._configure_direct_transport(c,s,{},tree)
            self.assertEqual(metadata['sc1001_initial_connector_stock'],{'10119':1.})
            self.assertEqual(s.urban_link_storage[k],94.)
            self.assertAlmostEqual(sum(x['vehicles'] for x in s.direct_exit_route_state['cohorts']),6.)
            self.assertAlmostEqual(sum(s.urban_storage_release_buffer[k].values()),6.)
            # First observed vehicle: east ramp is 130.627-pos +410.056m away;
            # at60km/h and1s resolution it must not be released immediately.
            first=s.direct_exit_route_state['cohorts'][0]
            self.assertEqual((first['target'],first['vehicles']),('RM_C10484',.5))
            due.append(first['due'])
        self.assertEqual(due,[32,25])

    def test_initial_connector_outside_geometry_or_mixed_owner_is_rejected(self):
        for problem in ('position','ownership'):
            s,c,k,records,tree=self.configuration_fixture()
            records[0].update(link_no=10119,position_m=999. if problem=='position' else 100.)
            owners=s.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            owners['31']['storage:'+k]-=1.
            owners['10119']={'storage:'+k:1. if problem=='position' else .5}
            with patch.object(rc,'complete_records',return_value=records):
                with self.assertRaises(ValueError):rc._configure_direct_transport(c,s,{},tree)

    def test_forward_sensitivity_is_preserved_by_travel_and_partial_receiving(self):
        # The production AD worker instruments numeric primitives before any
        # predictor imports. A Dual passed to an uninstrumented vendor schedule
        # deliberately fails instead of discarding its derivative.
        import subprocess
        import sys
        root=Path(__file__).resolve().parents[3]
        script=Path(__file__).resolve().parents[1]/'integration_20260926/check_transport_ad.py'
        result=subprocess.run([sys.executable,str(script),'forward','--sc1001'],cwd=root,
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
