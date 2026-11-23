import importlib.util,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
path=Path(__file__).resolve().parents[1]/'evaluation/controllers/adaptive_lever_selection.py'
spec=importlib.util.spec_from_file_location('adjacent_selection',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from evaluation.controllers import sdmpc
class Coord:
    axes=[dict(kind='green',key='p1',owner='SC105',block=0,scale=1.),dict(kind='vsl',key='FW_E__seg10',owner='FW_E',block=0,scale=1.),dict(kind='vsl',key='FW_W__seg10',owner='FW_W',block=0,scale=1.),dict(kind='meter',key='RM_C10484',owner='RM',block=0,scale=1.)]
    owners=['SC105','FW_E','FW_W','RM'];G=np.empty((0,4));glo=np.array([]);ghi=np.array([])
    def __init__(self):self.lower=np.full(4,-1.);self.upper=np.full(4,1.)
    def encode(self,a):return np.asarray(a,float)
    def validate(self,a):assert np.all(self.lower<=a) and np.all(a<=self.upper)
def qp(center,*args):return np.zeros_like(center),{'success':True}
def probe(prices,prox,scale):
    return {('vsl','FW_E__seg10'):.02,('vsl','FW_W__seg10'):0.}, {'vsl/FW_E__seg10':{'chosen_kmh':100},'vsl/FW_W__seg10':{'chosen_kmh':None}}
c=Coord();anchor=np.array([.3,.2,.1,.4])
with patch.object(sdmpc,'solve_qp',qp):
    r=m.select_lagrangian(c,anchor,np.zeros((1,4)),np.zeros((2,4)),.01,residual=np.zeros(2),tolerance=np.zeros(2),dual=np.zeros(2),dual_step=0.,resource_scale=np.ones(2),proximal=1.,qp_options={},mandatory_groups=[('signal','SC105')],vsl_probe=probe)
assert r['selected_groups']==[['meter','RM_C10484'],['vsl','FW_E__seg10']]
assert r['fixed_groups']==[['signal','SC105'],['vsl','FW_W__seg10']]
assert c.lower.tolist()==[.3,-1.,.1,-1.] and c.upper.tolist()==[.3,1.,.1,1.]
assert r['vsl_score_method']=='full_prediction_adjacent_legal_single_block'
assert r['mandatory_protection_groups']==[]
c=Coord()
with patch.object(sdmpc,'solve_qp',qp):
    r0=m.select_lagrangian(c,anchor,np.zeros((1,4)),np.zeros((2,4)),0.,residual=np.zeros(2),tolerance=np.zeros(2),dual=np.zeros(2),dual_step=0.,resource_scale=np.ones(2),proximal=1.,qp_options={},mandatory_groups=[('signal','SC105')],vsl_probe=probe)
assert len(r0['selected_groups'])==4 and r0['fixed_groups']==[]
print('PASS: finite-step score controls VSL selection; protected seed preserved; urban mandatory disabled; RM guard retained')
print('PASS: tau=0 selects all scored groups including zero-score VSL')
