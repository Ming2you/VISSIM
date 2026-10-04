import json
from pathlib import Path
import unittest
from evaluation.controllers.lane_offramp_runtime import _shared_post_head_distribution

D=Path(__file__).resolve().parent
def doc(name):return json.loads((D/(name+'.json')).read_bytes())
def total(s):return sum(s['queue'].values())+sum(s['storage'].values())
def row(decision=None,route=None):return [1,127,1,624.,40.,4.6,decision,route,'STATIC' if decision else None]

class PostHeadTests(unittest.TestCase):
    def test_known_turn_is_preserved(self):
        self.assertEqual(_shared_post_head_distribution(row(1117,1),('E','S'),{1:'S',2:'N',3:'E'},{'E':2,'S':1}),{'S':1.})

    def test_unknown_turn_uses_only_lane_compatible_existing_prior(self):
        self.assertEqual(_shared_post_head_distribution(row(),('E','S'),{1:'S',2:'N',3:'E'},
            {'E':2,'N':100,'S':1}),{'E':2/3,'S':1/3})
        self.assertEqual(_shared_post_head_distribution(row(),('E',),{1:'S',2:'N',3:'E'},
            {'E':2,'N':100,'S':1}),{'E':1.})

    def test_conflicting_known_route_is_not_silently_changed(self):
        with self.assertRaises(ValueError):
            _shared_post_head_distribution(row(1117,2),('E','S'),{1:'S',2:'N',3:'E'},{'E':2,'S':1,'N':1})

    def test_observed_failure_is_reproduced_then_initializes(self):
        old,new=doc('before1650'),doc('after1650')
        self.assertEqual(old['status'],'failed')
        self.assertIn('Post-head or unbound',old['error'])
        self.assertEqual(new['status'],'initialized_no_optimizer')
        self.assertEqual(old['before'],new['before'])
        self.assertEqual(old['inputs'],new['inputs'])

    def test_normal_saved_states_are_numerically_unchanged(self):
        for sec in (900,1500):
            old,new=doc('before'+str(sec)),doc('after'+str(sec))
            self.assertEqual(old['after'],new['after'])
            self.assertEqual(old['shared_stock'],new['shared_stock'])

    def test_post_head_cohorts_have_one_owner_and_one_reservation(self):
        x=doc('after1650');before,after=x['before'],x['after']
        meta=x['shared_metadata']['sc1001_shared_approach']
        self.assertEqual(meta['initial_post_head_veh'],2)
        self.assertEqual(x['shared_stock'],23.)
        self.assertEqual({r['vehicle'] for r in meta['initial_post_head_assignments']},{10504,11034})
        self.assertAlmostEqual(total(before),total(after),places=9)
        projection=after['projection']['127']
        self.assertEqual(projection['storage:lane_shared_SC1001'],23.)
        self.assertAlmostEqual(sum(projection.values()),25.)
        for receiver,n in (('SC1001_to_SC1002',5/3),('SC1001_to_SC1003',1/3)):
            self.assertAlmostEqual(after['storage'][receiver]-before['storage'][receiver],n)
            self.assertAlmostEqual(projection['storage:'+receiver],n)
            for key in ('arrival','release'):
                delta=sum(after[key].get(receiver,{}).values())-sum(before[key].get(receiver,{}).values())
                self.assertAlmostEqual(delta,n)
                self.assertTrue(all(int(t)>1650 for t in after[key][receiver]))

if __name__=='__main__':unittest.main()
