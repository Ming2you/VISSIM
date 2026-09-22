from pathlib import Path
import copy
import pickle
import sys
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_response_cache as cache, sdmpc_sequence as seq


class ResponseCacheTests(unittest.TestCase):
    def setUp(self):
        request=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())
        self.a=request['action']
        self.cfg=request['owned'][0].cfg
        self.cfg.network.sdmpc_options['response_np_cache']=True
        self.calls=[]
        def query(actions):
            self.calls.append(actions)
            return {'results':[dict(action_token=cache.token(a), response_token='original-physical-response',
                frozen_context_token='fixed-context',price_or_quantity_terms_included=False,
                quantities={'actual':572.},sdmpc_omega_partition={'costs':[123.]}) for a in actions]}
        self.c=cache.ResponseCache(query,self.cfg)

    def plan(self,cap):
        rows=seq.actions(self.a,3)
        for row in rows:row.N_P_star=cap
        return seq.pack(rows)

    def test_caps_share_only_physics_and_keep_explicit_original_identity(self):
        a,b=self.plan(2400.),self.plan(743.75)
        before=pickle.dumps((a,b),protocol=5)
        x,y=self.c((a,b))
        self.assertEqual([len(v) for v in self.calls],[1])
        self.assertEqual(x['response_token'],y['response_token'])
        self.assertNotEqual(x['action_token'],y['action_token'])
        self.assertNotIn('sdmpc_physical_response_reuse',x)
        cache.validate_binding(b,y)
        self.assertEqual(self.c.stats()['reused_predictions'],1)
        self.assertEqual(pickle.dumps((a,b),protocol=5),before)
        y['quantities']['actual']=0
        self.assertEqual(self.c((b,))[0]['quantities']['actual'],572.)

    def test_nuf_future_and_metadata_changes_are_not_aliased(self):
        a=self.plan(2400.)
        variants=[]
        for field in ('N_UF_star','future','diagnostics'):
            b=copy.deepcopy(a)
            if field=='N_UF_star':b.N_UF_star+=1.
            elif field=='future':
                row=b.diagnostics[seq.KEY]['future'][1]['vsl'];key=next(iter(row));row[key]-=1.
            else:b.diagnostics['new_physics_input']=1
            variants.append(b)
        self.c((a,*variants))
        self.assertEqual([len(v) for v in self.calls],[4])

    def test_tampered_binding_and_cross_context_fail(self):
        a,b=self.plan(2400.),self.plan(743.75)
        x,y=self.c((a,b))
        for field in ('response_token','action_token','frozen_context_token'):
            bad=copy.deepcopy(y);bad[field]='wrong'
            with self.assertRaises(ValueError):cache.validate_binding(b,bad)
        bad=copy.deepcopy(b);bad.N_UF_star+=1
        with self.assertRaises(ValueError):cache.validate_binding(bad,y)
        old=self.c.query
        def different(actions):
            result=old(actions)
            result['results'][0]['frozen_context_token']='other'
            return result
        self.c.query=different
        with self.assertRaises(ValueError):self.c((bad,))

    def test_invalid_future_plan_and_disabled_context_fail(self):
        a=self.plan(1.);a.diagnostics[seq.KEY]['future'].pop()
        with self.assertRaises(ValueError):self.c((a,))
        self.cfg.network.sdmpc_options.pop('response_np_cache')
        with self.assertRaises(ValueError):cache.ResponseCache(self.c.query,self.cfg)


if __name__=='__main__':unittest.main()
