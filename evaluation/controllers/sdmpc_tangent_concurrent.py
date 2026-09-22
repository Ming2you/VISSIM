"""Overlap two independent predictions; compare their complete trajectories.

Only two prediction processes run concurrently. The eight-thread reverse sweep
starts after the scalar process has exited and its hashed witness is checked.
The parent delivers the witness descriptor through stdin; EOF fails closed.
"""
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import time


def read_descriptor(stream):
    line=stream.readline()
    if not line:
        raise ValueError('Scalar producer closed before supplying a witness')
    descriptor=json.loads(line)
    if (not isinstance(descriptor,dict) or set(descriptor)!={'path','sha256','anchor_sha256','bytes'}
            or any(not isinstance(descriptor[k],str) or not descriptor[k]
                   for k in ('path','sha256','anchor_sha256'))
            or type(descriptor['bytes']) is not int or descriptor['bytes']<=0):
        raise ValueError('Malformed concurrent scalar witness descriptor')
    return descriptor


def evaluate(request):
    from evaluation.controllers.sdmpc_tangent import _evaluate_single
    options=request['owned'][0].cfg.network.sdmpc_options
    if (options.get('tangent_backend') != 'reverse-v1'
            or not options.get('tangent_shared_primal')
            or options.get('derivative_workers',1)<2):
        raise ValueError('Concurrent primal requires shared reverse AD and at least two workers')
    started=time.perf_counter()
    root=Path(__file__).resolve().parents[2]
    worker=Path(__file__).with_name('sdmpc_tangent_worker.py')
    common=pickle.dumps(request,protocol=5)
    digest=hashlib.sha256(common).hexdigest()
    with tempfile.TemporaryDirectory(prefix='sdmpc-overlap-') as tmp:
        folder=Path(tmp)
        common_path=folder/'common.pickle'; common_path.write_bytes(common)
        descriptor=dict(path=str(common_path),sha256=digest)
        witness_path=folder/'scalar.pickle'
        envelope=dict(shared_request=descriptor,shared_primal_stdin=True)
        data=pickle.dumps(envelope,protocol=5)
        inp,out=folder/'request.pickle',folder/'result.pickle'
        inp.write_bytes(data); request_digest=hashlib.sha256(data).hexdigest()
        env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        with subprocess.Popen([sys.executable,'-B',str(worker),str(inp),str(out),
                request_digest,'reverse-v1'],cwd=root,env=env,stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8') as child:
            try:
                # The explicit backend is also needed before unpickling the
                # envelope, because the import finder is installed first.
                baseline=_evaluate_single(dict(shared_request=descriptor,
                    scalar_output=str(witness_path),worker_backend='reverse-v1'))
                witness=baseline['shared_primal']
                if witness['anchor_sha256']!=digest or witness['path']!=str(witness_path):
                    raise ValueError('Concurrent scalar used a different anchor')
                stdout,stderr=child.communicate(json.dumps(witness)+'\n')
            except BaseException:
                # Only this parent-owned, offline derivative child is stopped.
                # Do not leave a child waiting for a failed scalar producer.
                child.kill(); child.communicate()
                raise
            if not out.is_file():
                raise RuntimeError('Concurrent tangent worker failed: '+stderr[-6000:])
            result=pickle.loads(out.read_bytes())
            if result.get('request_sha256')!=request_digest:
                raise ValueError('Concurrent tangent response identity mismatch')
            if child.returncode or 'error' in result:
                raise RuntimeError('Concurrent tangent failed:\n'+result.get('error',stderr))
            if result.get('shared_primal')!=witness:
                raise ValueError('Concurrent tangent used a different witness')
        for name,expected in baseline['transformed_source_sha256'].items():
            if result['transformed_source_sha256'].get(name)!=expected:
                raise ValueError('Concurrent predictions used different sources: '+name)
    result.update(scalar_rollouts=1,scalar_sec=baseline['scalar_sec'],
        wall_sec_including_spawn=time.perf_counter()-started)
    result['concurrent_primal']=dict(prediction_processes=2,
        scalar_finished_before_reverse_sweep=True,common_request_sha256=digest,
        scalar_worker={k:baseline[k] for k in ('scalar_sec','scalar_export_sec','wall_sec_including_spawn')},
        scope='Overlapped predictions; full state comparison and eight output sweeps follow')
    if 'spatial_receiving' in baseline:
        result['concurrent_primal']['scalar_worker']['spatial_receiving']=baseline['spatial_receiving']
    return result
