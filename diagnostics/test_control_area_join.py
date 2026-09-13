from pathlib import Path
import copy
import sys
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.control_area_join import build_movement_join,route_contract,turn_membership


class JoinTests(unittest.TestCase):
    def setUp(self):
        self.cfg=NS(network=NS(urban_movements={'M':{'signal':'SC','approach':'W','exit':'E','receiving_link':'dest',
                                                    'origin':'origin','kind':'internal'}},off_ramp_storage_link={}))
        self.det={'link_to_movements':{'a':[{'movement':'M'}]},'link_to_origins':{'b':['dest']}}
        self.membership={'schema':'control-area-membership/v1','inside_links':['a','c','b','bridge','link2'],
                         'outside_links':['x'],'unresolved':[],'connector_transitions':[]}
        self.turn={'sc':'SC','legs':['SC·W'],'heading':'E','from_link':'a','connector':'c','to_link':'b','class':'internal'}

    def join(self,turns=None,**kwargs):
        return build_movement_join(self.cfg,self.det,{'turns':turns or [self.turn]},self.membership,**kwargs)

    def test_internal_transfer_and_external_connector_excursion_differ(self):
        row=self.join()['by_movement']['M']
        self.assertEqual(row['status'],'unique')
        self.assertEqual(row['outward_crossings_per_accepted_vehicle'],0)
        excursion=dict(self.turn,connector='x')
        row=self.join([excursion])['by_movement']['M']
        self.assertTrue(row['source_inside'] and row['target_inside'])
        self.assertEqual(row['outward_crossings_per_accepted_vehicle'],1)
        self.assertEqual(row['inward_crossings_per_accepted_vehicle'],1)

    def test_mixed_routes_do_not_receive_equal_weights(self):
        join=self.join([self.turn,dict(self.turn,connector='x')])
        row=join['by_movement']['M']
        self.assertEqual(row['status'],'mixed_transition')
        self.assertTrue(all(r['weight'] is None for r in row['physical_turns']))
        self.assertIsNone(route_contract(join)['movement:M']['inside_to_inside'])

    def test_same_transition_remains_safe_without_branch_weights(self):
        row=self.join([self.turn,dict(self.turn,connector='link2')])['by_movement']['M']
        self.assertEqual(row['status'],'same_transition')

    def test_curved_exit_uses_actual_destination_support(self):
        row=self.join([dict(self.turn,heading='N')])['by_movement']['M']
        self.assertEqual(row['status'],'unique')
        self.assertFalse(row['physical_turns'][0]['exit_evidence']['canonical_heading_matches_exit_compass'])

    def test_unowned_bridge_walk_stops_at_first_model_storage(self):
        turn=dict(self.turn,to_link='bridge',heading='N')
        row=self.join([turn],physical_successors={'bridge':[('link2','b')]})['by_movement']['M']
        self.assertEqual(row['status'],'unique')
        self.assertEqual(row['physical_turns'][0]['destination_support_paths'],[['bridge','link2','b']])

    def test_incompatible_receiver_and_missing_physical_id_remain_errors(self):
        self.det['link_to_origins']['b']=['different']
        row=self.join()['by_movement']['M']
        self.assertEqual(row['status'],'no_match')
        self.assertIsNone(row['outward_crossings_per_accepted_vehicle'])
        with self.assertRaises(ValueError):turn_membership(dict(self.turn,to_link='missing'),{'a':True,'c':True})

    def test_arrival_contract_uses_canonical_stopline_side(self):
        contract=route_contract(self.join())
        self.assertTrue(contract['arrival:M']['target_inside'])
        self.assertIn('approximation',contract['arrival:M']['timing_assumption'])


if __name__=='__main__':unittest.main()
