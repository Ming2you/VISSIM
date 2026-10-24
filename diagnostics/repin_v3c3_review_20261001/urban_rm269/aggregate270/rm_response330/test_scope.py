import copy,unittest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.rm_response330.scope import read,COMMANDS,validate_commands

class Scope(unittest.TestCase):
    def setUp(self):
        self.j=read(COMMANDS['joint']/'action_002400.json');self.c=read(COMMANDS['city']/'action_002400.json')
    def test_executed_three_blocks_only_change_RM(self):
        for t in (2400,2550,2700):
            j=read(COMMANDS['joint']/f'action_{t:06}.json');c=read(COMMANDS['city']/f'action_{t:06}.json')
            expected={2400:{'RM_C10639','RM_C10681','RM_C10490','RM_C10484'},
                      2550:{'RM_C10639','RM_C10681','RM_C10484'},
                      2700:{'RM_C10639','RM_C10681','RM_C10490'}}
            self.assertEqual(set(validate_commands(j,c)),expected[t])
    def test_reject_urban_or_vsl_confounded_contrast(self):
        for field in ('green_times','offsets','vsl'):
            j=copy.deepcopy(self.j);key=next(iter(j[field]));j[field][key]+=1
            with self.assertRaises(ValueError):validate_commands(j,self.c)
    def test_reject_changed_cap_and_no_RM_intervention(self):
        j=copy.deepcopy(self.j);j['N_UF_star']+=1
        with self.assertRaises(ValueError):validate_commands(j,self.c)
        with self.assertRaises(ValueError):validate_commands(self.c,self.c)

if __name__=='__main__':unittest.main()
