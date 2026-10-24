"""Two scalar responses and one AD response for the10686 authority correction."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
R=HERE.parent/'urban_clock277'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
M='SC1002_W_SC1001_to_S_SC105'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    diagnosis=json.loads((HERE/'diagnosis.json').read_bytes())
    assert diagnosis['physical10686']['exclusive_source_lane']
    for label,source,mode in [('hold2400','hold_v5','scalar'),('release2400','release_v3','scalar'),('hold2400_ad','hold_ad_v1','ad')]:
        receipt=HERE/(label+'_execution.json');assert not receipt.exists()
        inp=R/(source+'_request.pickle');request=pickle.loads(inp.read_bytes())
        cfg=request['owned'][0].cfg
        assert request['owned'][1].time_sec==2400 and cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
        old_owned=pickle.dumps(request['owned'],protocol=5)
        assert not cfg.network.urban_movements[M].get('unsignalized')
        cfg.network.urban_movements[M]['unsignalized']=True
        # No changes to rates, state, histories, forecast, objective or actions.
        del cfg.network.urban_movements[M]['unsignalized']
        assert old_owned==pickle.dumps(request['owned'],protocol=5)
        cfg.network.urban_movements[M]['unsignalized']=True
        pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')}
        for p,h in request['bootstrap']['runtime_sources'].items():assert sha(p)==h,p
        from evaluation.controllers.sdmpc_tangent_surrogate import token
        request['surrogate_evaluation']=mode
        request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
        src=HERE/(label+'_request.pickle');dst=HERE/(label+'_result.pickle')
        src.write_bytes(pickle.dumps(request,protocol=5))
        record=dict(status='running',mode=mode,input=str(inp),input_sha256=sha(inp),source_pins=pins,
            predictions=1,full_selections=0,native_runs=0,coefficient_fits=0)
        save(receipt,record);start=time.perf_counter()
        with (HERE/(label+'_stdout.log')).open('w') as out,(HERE/(label+'_stderr.log')).open('w') as err:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
                str(src),str(dst),sha(src),'reverse-v1'],cwd=ROOT,stdout=out,stderr=err,
                creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
            record['child_pid']=child.pid;save(receipt,record);code=child.wait()
        record.update(status='complete_unreviewed' if code==0 else 'failed_preserved',exit_code=code,
            wall_sec=time.perf_counter()-start,source_pins_unchanged=all(sha(p)==h for p,h in pins.items()))
        save(receipt,record);print(label,record['status'],record['wall_sec'],flush=True)
        if code:raise SystemExit(code)

if __name__=='__main__':main()
