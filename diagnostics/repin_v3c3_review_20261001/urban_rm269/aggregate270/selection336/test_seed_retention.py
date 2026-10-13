"""Exercise the production retention call site without rerunning SDMPC."""
from pathlib import Path
from types import SimpleNamespace
import copy,textwrap,unittest
from evaluation.controllers import sdmpc


class Action(SimpleNamespace):
    def copy(self): return copy.deepcopy(self)


class SeedRetention(unittest.TestCase):
    def replay(self, *, valid=True, improved=True, feasible=True):
        # The old actual reference violates storage protection. Its projected
        # seed is legal and is the action whose cost PFO initially evaluated.
        raw=Action(kind='raw',N_P_star=20.,N_UF_star=30.)
        seed=Action(kind='protected',N_P_star=20.,N_UF_star=30.)
        winner=Action(kind='winner',N_P_star=80.,N_UF_star=90.)
        calls=[]
        def evaluate(actions):
            calls.extend(actions)
            self.assertEqual([(a.N_P_star,a.N_UF_star) for a in actions],[(80.,90.)])
            return [dict(objective_veh_h=10.,source=a.kind) for a in actions]
        coord=SimpleNamespace(encode=lambda a:a.kind,valid=lambda z:valid and z!='raw')
        env=dict(sdmpc.__dict__,cap_mode=True,coord=coord,reference=raw,operating_seed=seed,
            pfo_initial=dict(objective_veh_h=10.),best=(winner,dict(objective_veh_h=12. if improved else 9.),None),
            anchor=winner,policy=dict(objective_tolerance=1e-7),evaluate=evaluate,
            feasible=lambda a,r:feasible)
        source=Path(sdmpc.__file__).read_text(encoding='utf8')
        start=source.index('        held_candidate = None',source.index('def solve(controller'))
        end=source.index('        if best is None:',start)
        exec(compile(textwrap.dedent(source[start:end]),str(sdmpc.__file__)+':retention','exec'),env)
        return env,calls

    def test_legal_protected_seed_survives_illegal_old_reference(self):
        env,calls=self.replay()
        self.assertEqual([a.kind for a in calls],['protected'])
        self.assertEqual(env['best'][0].kind,'protected')
        self.assertTrue(env['held_candidate']['selected'])

    def test_same_caps_still_reject_physical_or_quantity_violation(self):
        env,calls=self.replay(feasible=False)
        self.assertEqual(len(calls),1)
        self.assertEqual(env['best'][0].kind,'winner')
        self.assertFalse(env['held_candidate']['feasible'])

    def test_better_winner_needs_no_extra_prediction(self):
        env,calls=self.replay(improved=False)
        self.assertEqual(calls,[])
        self.assertEqual(env['best'][0].kind,'winner')

    def test_invalid_seed_is_never_admitted(self):
        env,calls=self.replay(valid=False)
        self.assertEqual(calls,[])
        self.assertEqual(env['held_candidate']['reason'],'outside_current_operating_bounds')


if __name__=='__main__':unittest.main()
