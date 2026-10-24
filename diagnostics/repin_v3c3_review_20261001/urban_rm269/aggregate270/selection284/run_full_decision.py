"""One actual saved-state SDMPC decision with unchanged PFO2/SDMPC2 budget."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import ctypes,hashlib,json,runpy,sys,time,traceback
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];M=HERE.parent/'multirate271'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,v:p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def main():
    receipt=HERE/'full_decision_execution.json';out=HERE/'full2400_current'
    assert not receipt.exists() and not out.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    review=read(HERE.parent/'isolated283/review.json')
    assert review['material_directions_pass'] and review['same_np_nuf_caps_feasible']
    pins=dict(read(HERE.parent/'matched280/authority/summary.json')['source_pins'])
    pins.update(review['source_pins'])
    for p in (Path(__file__),HERE/'plan.json'):pins[str(p)]=sha(p)
    assert all(sha(Path(p))==h for p,h in pins.items())
    config=HERE.parent/'flow279/config_10686_free.json'
    tuning=read(config)
    assert tuning['freeway']['multirate_exchange_sec']==5 and tuning['urban']['multirate_exchange_sec']==10
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation import parameters
    policy=parameters.load();assert policy['sdmpc']['max_iterations']==policy['sdmpc_pfo_cap']['max_iterations']==2
    old=read(M/'full2400_fw5/protocol.json');decisions=str(Path(old['state']).parent)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        source_pins=pins,config_sha256=sha(config),native_runs=0,full_decisions=1,retries=0,
        iterations_per_stage=2,output=str(out),decisions=decisions)
    save(receipt,record);t0=time.perf_counter()
    script=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv=[str(script),'--at','2400','--out',str(out),'--full-selection','--tuning',str(config),'--decisions',decisions]
    try:
        runpy.run_path(str(script),run_name='__main__')
        assert read(out/'completion.json')['full_selection']
        assert all(sha(Path(p))==h for p,h in pins.items())
        record['status']='complete_pending_review'
    except BaseException as error:
        record.update(status='failed_preserved',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        record.update(wall_sec=time.perf_counter()-t0,ended_utc=datetime.now(timezone.utc).isoformat())
        save(receipt,record)
    print('FULL_DECISION_COMPLETE',record['wall_sec'],flush=True)
if __name__=='__main__':main()
