"""Inspect, never waive, a failed scalar/tangent state comparison."""
from pathlib import Path
import collections
import json
import pickle
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_worker import state_error
from evaluation.controllers.sdmpc_dual import primal, derivative


def main():
    data=pickle.loads(Path(sys.argv[1]).read_bytes())
    a,b=data['scalar_states'][0],data['tangent_states'][0]
    fields={}
    for key in vars(a):
        try:fields[key]=state_error(getattr(a,key),getattr(b,key),key)
        except Exception as exc:fields[key]=str(exc)[:300]
    def transfers(s):
        ledger=s._control_area_ledger
        return [r for chunk in ledger._packed_response_records
                for r in pickle.loads(chunk)['transfers']]+ledger._response['transfers']
    left,right=transfers(a),transfers(b)
    key=lambda r:tuple((k,v) for k,v in r.items() if k not in ('vehicles','ttd_veh','entered_veh'))
    l,r=collections.defaultdict(list),collections.defaultdict(list)
    for row in left:l[key(row)].append(primal(row['vehicles']))
    for row in right:r[key(row)].append(primal(row['vehicles']))
    differences=[]
    for k in l.keys()|r.keys():
        delta=sum(l[k])-sum(r[k])
        if len(l[k])!=len(r[k]) or abs(delta)>1e-10:
            differences.append(dict(identity=dict(k),scalar=l[k],tangent=r[k],delta=delta))
    import numpy as np
    request=pickle.loads((Path(sys.argv[1]).parent/'request.pickle').read_bytes())
    jac=np.array([[derivative(v).get(j,0.) for j in range(len(request['axes']))]
                 for v in data['dual_costs']+data['dual_resources']])
    groups={}
    for j,axis in enumerate(request['axes']):
        groups.setdefault(axis['kind'],[]).append(dict(axis=j,key=axis['key'],norm=float(np.linalg.norm(jac[:,j]))))
    result=dict(fields=fields,transfer_differences=differences,
        cost_errors=[x-primal(y) for x,y in zip(data['scalar_costs'],data['dual_costs'])],
        resource_errors=[x-primal(y) for x,y in zip(data['scalar_resources'],data['dual_resources'])],
        gradients=groups)
    output=Path(sys.argv[1]).with_suffix('.audit.json')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='gradients'},indent=2))
    print('nonzero_columns', {k:sum(r['norm']>1e-8 for r in rows) for k,rows in groups.items()})


if __name__=='__main__':main()
