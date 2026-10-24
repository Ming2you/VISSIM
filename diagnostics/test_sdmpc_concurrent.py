from pathlib import Path
import copy
import hashlib
import io
import json
import pickle
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_concurrent import read_descriptor
from evaluation.controllers.sdmpc_tangent_worker import expand_shared_request


class ConcurrentTests(unittest.TestCase):
    def test_missing_or_invalid_producer_witness_fails_closed(self):
        for text in ('','{}','null','false','{"path":"x"}'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                read_descriptor(io.StringIO(text))
        value=dict(path='x',sha256='digest',anchor_sha256='anchor',bytes=3)
        self.assertEqual(read_descriptor(io.StringIO(json.dumps(value)+'\n')),value)

    def test_deferred_request_still_binds_the_full_anchor(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'request.pickle'
            data=pickle.dumps({'action':3,'owned':['anchor']})
            path.write_bytes(data)
            desc=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest())
            envelope=dict(shared_request=desc,shared_primal_stdin=True)
            result=expand_shared_request(envelope)
            self.assertEqual(result['action'],3)
            self.assertEqual(result['shared_anchor_sha256'],desc['sha256'])
            for changes in (dict(shared_primal_stdin=False),dict(shared_primal={}),
                            dict(scalar_output='x'),dict(action=4)):
                with self.assertRaises(ValueError): expand_shared_request(dict(envelope,**changes))
            path.write_bytes(data+b'tampered')
            with self.assertRaises(ValueError):expand_shared_request(envelope)

    def test_config_requires_matching_backend_and_worker_limit(self):
        from evaluation.controllers import sdmpc
        cfg=pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        opts=dict(sdmpc='proxlinear-v1',sdmpc_derivatives='tangent-v1',sdmpc_tangent_backend='reverse-v1',
                  sdmpc_tangent_shared_primal=True,sdmpc_derivative_workers=8)
        self.assertNotIn('tangent_concurrent_primal',sdmpc.configure({'adapter':opts},copy.deepcopy(cfg)))
        opts['sdmpc_tangent_concurrent_primal']=True
        self.assertTrue(sdmpc.configure({'adapter':opts},copy.deepcopy(cfg))['tangent_concurrent_primal'])
        for changes in (dict(sdmpc_tangent_backend=None),dict(sdmpc_tangent_shared_primal=False),
                        dict(sdmpc_derivative_workers=1),dict(sdmpc_tangent_concurrent_primal=1)):
            with self.assertRaises(ValueError):sdmpc.configure({'adapter':dict(opts,**changes)},copy.deepcopy(cfg))


if __name__=='__main__':unittest.main()
