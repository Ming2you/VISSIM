"""Reuse REVIEW255 matched snapshot integration at the current4200 cutoff."""
import os
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import importlib.util
import json
import numpy as np

HERE=Path(__file__).resolve().parent
OLD=HERE.parents[1]/'interim255'
spec=importlib.util.spec_from_file_location('interim255_ttt',OLD/'analyze.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.HERE=HERE
module.END=4200
module.RUNS['sdmpc']=Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc')
module.draw=lambda *_:None
module.main()

p=HERE/'summary.json'
d=json.loads(p.read_bytes())
d['method']=d['method'].replace('6600','4200')
d['limitations']=[s.replace('6600','4200') for s in d['limitations']]
parts=['FW_E','FW_W','Omega_other','outside_Omega']
old=np.load(OLD/'sdmpc_snapshots.npz')
nc=np.load(HERE/'nc_snapshots.npz')
current=np.load(HERE/'sdmpc_snapshots.npz')
for z in (old,nc,current): assert all(t in z['times'] for t in (3600,4200))
def values(z,t):
    row=z['cumulative_ttt'][np.flatnonzero(z['times']==t)[0]]
    return {'Omega':float(row[:3].sum()),**{k:float(v) for k,v in zip(parts,row)}}
old4200=values(old,4200)
new4200=values(current,4200)
d['old_run_same_cutoff_veh_h']=old4200
d['current_minus_old_veh_h']={k:new4200[k]-old4200[k] for k in old4200}
d['intervals_veh_h']={}
for a,b in ((0,3600),(3600,4200)):
    interval={}
    for name,z in (('nc',nc),('old_control',old),('current',current)):
        va,vb=values(z,a),values(z,b)
        interval[name]={k:vb[k]-va[k] for k in vb}
    d['intervals_veh_h'][f'{a}-{b}']=interval
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:d[k] for k in ['old_run_same_cutoff_veh_h','current_minus_old_veh_h','intervals_veh_h']},ensure_ascii=False))
