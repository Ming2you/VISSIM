"""Independent small-perturbation audit; never used by the SDMPC solver."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import copy,hashlib,json,pickle,subprocess,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_dual import derivative,primal


def main():
    source=ROOT/'diagnostics/tangent_900_h1'
    request=pickle.loads((source/'request.pickle').read_bytes())
    checkpoint=pickle.loads((source/'prediction_attempt05.pickle').read_bytes())
    values=checkpoint['dual_costs']+checkpoint['dual_resources']
    baseline=np.array([primal(v) for v in values])
    out=ROOT/'diagnostics'/sys.argv[1]
    out.mkdir(exist_ok=False)
    tasks=[];cases=[]
    h=1e-5
    for j in (57,58,67,71):
        axis=request['axes'][j]
        control=request['action']
        if axis['kind']=='meter':
            value=control.diagnostics['rw_meter_green_'+axis['key']]
            offsets=(0.,-h) if value==max(axis['allowed']) else (0.,h)
        elif axis['kind']=='vsl':
            offsets=(0.,-h) if control.vsl[axis['key']]==max(axis['allowed']) else (0.,h)
        else:offsets=(-h,h)
        case=dict(axis=j,kind=axis['kind'],owner=axis['owner'],offsets=offsets,
                  analytic=[derivative(v).get(j,0.) for v in values])
        case['tasks']=[]
        for delta in offsets:
            if delta==0.:
                case['tasks'].append(None);continue
            r=copy.deepcopy(request);action=r['action'];change=delta*axis['scale']
            if axis['kind']=='green':
                for phase,factor in r['green_vectors'][j].items():
                    action.green_times[axis['owner']+'_'+phase]+=change*factor
            elif axis['kind']=='offset':action.offsets[axis['key']]+=change
            elif axis['kind']=='meter':action.diagnostics['rw_meter_green_'+axis['key']]+=change
            else:
                for cell,head in enumerate(r['owned'][0].cfg.network.freeway_vsl_zone_head_of_cell[axis['owner']]):
                    if head==axis['head']:action.vsl[f"{axis['owner']}__seg{cell}"]+=change
                action.vsl[axis['owner']]=min(v for k,v in action.vsl.items() if k.startswith(axis['owner']+'__seg'))
            r['scalar_only']=True;r.pop('diagnostic_checkpoint',None)
            index=len(tasks);input_path=out/f'request_{index}.pickle';result_path=out/f'result_{index}.pickle'
            data=pickle.dumps(r,protocol=5);input_path.write_bytes(data)
            tasks.append((input_path,result_path,hashlib.sha256(data).hexdigest()))
            case['tasks'].append(index)
        cases.append(case)
    def run(task):
        inp,result,digest=task
        p=subprocess.run([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
            str(inp),str(result),digest],capture_output=True,text=True)
        if not result.is_file():raise RuntimeError(p.stderr)
        r=pickle.loads(result.read_bytes())
        if p.returncode:raise RuntimeError(r.get('error',p.stderr))
        return r
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(run,tasks))
    for case in cases:
        ends=[baseline if index is None else np.array(results[index]['costs']+results[index]['resources'])
              for index in case['tasks']]
        fd=(ends[1]-ends[0])/(case['offsets'][1]-case['offsets'][0])
        analytic=np.array(case['analytic'])
        case.update(finite_difference=fd.tolist(),max_abs_error=float(max(abs(fd-analytic))),
                    relative_l2_error=float(np.linalg.norm(fd-analytic)/max(1.,np.linalg.norm(fd))))
    report=dict(purpose='verification_only_not_solver_finite_differences',workers=8,
        scalar_rollouts=len(tasks),wall_sec=time.perf_counter()-started,cases=cases)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({**report,'cases':[{k:v for k,v in c.items() if k not in ('analytic','finite_difference')} for c in cases]},indent=2))


if __name__=='__main__':main()
