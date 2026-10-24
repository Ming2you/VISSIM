"""Three scalar450s probes of an already captured RM Jacobian; no search/run."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from datetime import datetime,timezone
import copy,hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,v:p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    from evaluation.controllers import sdmpc_sequence as seq,sdmpc_continuous as continuous
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    receipt=HERE/'slope_execution.json'
    assert not receipt.exists(),'No automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    plan=json.loads((M/'plan.json').read_bytes())
    for p,h in plan['source_pins'].items():assert sha(ROOT/p)==h,p
    source=M/'macro_hold_ad_v3_request.pickle'
    template=pickle.loads(source.read_bytes())
    for path,expected in template['bootstrap']['runtime_sources'].items():
        p=Path(path);now=sha(p)
        if now!=expected:
            assert now==plan['source_pins'][p.relative_to(ROOT).as_posix()],path
            template['bootstrap']['runtime_sources'][path]=now
    template['surrogate_evaluation']='scalar'
    template['surrogate_context_sha256']=token((template['owned'],template['runtime'],template['bootstrap'],template['horizon']))
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        deltas_green_seconds=[1e-6,.001,1.],changed_axis='RM_C10681 block0 only',
        scope='Two mathematical local derivative probes and one executable+1s probe; not new native commands.',
        reference_request_sha256=sha(source),source_pins=template['bootstrap']['runtime_sources'],max_predictions=3,rows=[])
    save(receipt,record)
    for label,delta in (('micro',1e-6),('small',.001),('legal',1.)):
        request=copy.deepcopy(template);cfg=request['owned'][0].cfg
        blocks=seq.actions(request['action'],3)
        key='rw_meter_green_RM_C10681'
        assert blocks[0].diagnostics[key]==2.
        blocks[0].diagnostics[key]+=delta
        blocks[0].ramp_metering['RM_C10681']=continuous.meter_rate(blocks[0].diagnostics[key],cfg.network.physical_ramp_branches['ramps']['RM_C10681'])
        request['action']=seq.pack(blocks)
        src=HERE/(label+'_request.pickle');dst=HERE/(label+'_result.pickle')
        src.write_bytes(pickle.dumps(request,protocol=5))
        start=time.perf_counter()
        with (HERE/(label+'_stdout.log')).open('w') as out,(HERE/(label+'_stderr.log')).open('w') as err:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1'],
                cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            record.update(current=label,child_pid=child.pid);save(receipt,record)
            code=child.wait()
        record['rows'].append(dict(label=label,delta_green_sec=delta,exit_code=code,wall_sec=time.perf_counter()-start))
        if code:
            record['status']='failed_preserved';save(receipt,record);return code
        save(receipt,record)
    record.update(status='complete_pending_review',source_pins_unchanged=all(sha(Path(p))==h for p,h in record['source_pins'].items()),
        ended_utc=datetime.now(timezone.utc).isoformat())
    save(receipt,record)
    return 0


if __name__=='__main__':raise SystemExit(main())
