from copy import deepcopy
import unittest
from diagnostics.verify_signal_observation_pair import check


class PairTests(unittest.TestCase):
    def test_only_boolean_leaf_changes_without_mutating_original(self):
        on={'urban':{'capacity':{'head_observation':{'enabled':True,'min_green_sec':30,'min_crossings':5}}},'x':[1,2]}
        original=deepcopy(on)
        overlay={'urban':{'capacity':{'head_observation':{'enabled':False}}}}
        self.assertEqual(len(check(on,overlay)),1);self.assertEqual(on,original)
        off=deepcopy(on);off['urban']['capacity']['head_observation']['enabled']=False
        self.assertEqual(len(check(on,overlay,off)),1)
        for key,value in [('x',[2,1]),('name','different')]:
            bad=deepcopy(off);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check(on,overlay,bad)

    def test_no_hidden_quality_or_nonboolean_changes(self):
        on={'urban':{'capacity':{'head_observation':{'enabled':True,'min_green_sec':30}}}}
        for value in (0,'false',None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                check(on,{'urban':{'capacity':{'head_observation':{'enabled':value}}}})
            bad=deepcopy(on);bad['urban']['capacity']['head_observation']['enabled']=value
            with self.subTest(off_value=value),self.assertRaises(ValueError):
                check(on,{'urban':{'capacity':{'head_observation':{'enabled':False}}}},bad)
        with self.assertRaises(ValueError):
            check(on,{'urban':{'capacity':{'head_observation':{'enabled':False,'min_green_sec':1}}}})


if __name__=='__main__':unittest.main()
