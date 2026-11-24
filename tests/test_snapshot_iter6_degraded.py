import importlib.util,json,math,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
here=Path(__file__).resolve().parents[1]
root=here
sys.path[:0]=[str(root),str(root/'vendor/NumSim-mine')]
def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
sd=load('candidate_sdmpc',here/'evaluation/controllers/sdmpc.py')
assert abs(sd.relative_iteration_improvement(1000,999)-.001)<1e-12
assert sd.relative_iteration_improvement(1000,998.9)>.001
assert sd.relative_iteration_improvement(1000,999.1)<.001
assert sd.relative_iteration_improvement(1000,1001)<0
try:sd.relative_iteration_improvement(float('nan'),1.)
except ValueError:pass
else:raise AssertionError('non-finite objective accepted')
params=json.loads((here/'evaluation/parameters.json').read_bytes());assert params['sdmpc']['max_iterations']==6
from evaluation.controllers import sdmpc
sel=load('candidate_selector',here/'evaluation/controllers/adaptive_lever_selection.py')
class Coord:
    axes=[dict(kind='green',key='p1',owner='SC105',block=0,scale=1.),dict(kind='vsl',key='FW_E__seg10',owner='FW_E',block=0,scale=1.)]
    owners=['SC105','FW_E'];G=np.empty((0,2));glo=np.array([]);ghi=np.array([])
    def __init__(self):self.lower=np.full(2,-1.);self.upper=np.full(2,1.)
    def encode(self,a):return np.asarray(a,float)
    def validate(self,a):assert np.all(self.lower<=a) and np.all(a<=self.upper)
calls=[]
def qp(center,*args):
    calls.append(1)
    return np.zeros_like(center),{'success':len(calls)!=3,'message':'injected group scoring failure'}
def probe(*a):return {('vsl','FW_E__seg10'):0.},{'vsl/FW_E__seg10':{}}
c=Coord()
with patch.object(sdmpc,'solve_qp',qp):
    r=sel.select_lagrangian(c,np.array([.3,.2]),np.zeros((1,2)),np.zeros((2,2)),.01,residual=np.zeros(2),tolerance=np.zeros(2),dual=np.zeros(2),dual_step=0.,resource_scale=np.ones(2),proximal=1.,qp_options={},vsl_probe=probe)
assert r['selected_groups']==[['signal','SC105']] and 'signal/SC105' in r['failed_group_qps']
assert r['fixed_groups']==[['vsl','FW_E__seg10']]
print('PASS: relative objective values, six-iteration configuration, conservative failed-QP group selection with receipt')
