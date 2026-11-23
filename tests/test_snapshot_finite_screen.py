import importlib.util
from pathlib import Path
import numpy as np

path=Path(__file__).resolve().parents[1]/'evaluation/controllers/vsl_finite_screen.py'
spec=importlib.util.spec_from_file_location('vsl_finite_screen',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Coord:
    axes=[dict(kind='vsl',key='FW_E__seg13',owner='FW_E',block=0,reference_value=110.,scale=110.,allowed=[90.,100.,110.]),dict(kind='vsl',key='FW_W__seg13',owner='FW_W',block=0,reference_value=100.,scale=110.,allowed=[90.,100.,110.]),dict(kind='green',key='p1',owner='SC1',block=0,scale=100.)]
    def encode(self,a):return np.array(a,float)
    def valid(self,z):return np.all(np.isfinite(z)) and -.2<=z[0]<=0 and -.1<=z[1]<=.1 and z[2]==0
    def decode(self,z,anchor):return np.array(z)
    def validate(self,a):assert self.valid(a)
coord=Coord();anchor=np.zeros(3);base={'objective_veh_h':100.,'physical':True,'q':[10.,5.]}
def evaluate(actions,derivatives=False):
    assert derivatives is False
    out=[]
    for a in actions:
        if a[0]<0:out.append({'objective_veh_h':98.,'physical':True,'q':[12.,5.]})
        elif a[1]<0:out.append({'objective_veh_h':90.,'physical':False,'q':[10.,5.]})
        else:out.append({'objective_veh_h':101.,'physical':True,'q':[10.,5.]})
    return out
scores,detail=m.score_adjacent(coord,anchor,base,evaluate,lambda a,x:x['q'],lambda x:x['physical'],[.5,0.],2.,[10.,1.])
assert abs(scores[('vsl','FW_E__seg13')]-(2.-.1-(10/110)**2))<1e-9
assert scores[('vsl','FW_W__seg13')]==0
assert detail['vsl/FW_E__seg13']['chosen_kmh']==100
assert [x['target_kmh'] for x in detail['vsl/FW_W__seg13']['trials']]==[90.,110.]
assert detail['vsl/FW_W__seg13']['trials'][0]['status']=='physical_model_infeasible'
assert np.array_equal(anchor,np.zeros(3))
try:m.score_adjacent(coord,anchor,{**base,'physical':False},evaluate,lambda a,x:x['q'],lambda x:x['physical'],[.5,0.],2.,[10.,1.])
except ValueError:pass
else:raise AssertionError('unsafe anchor was accepted')
print('PASS: adjacent 10-km/h, scaled dual price, physical rejection, actual delta, anchor preservation')
