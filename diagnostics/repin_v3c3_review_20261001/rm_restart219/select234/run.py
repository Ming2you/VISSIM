"""One real SDMPC selection after the saved4500 observation repair; no native run."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUTPUT=I/'closedloop_recorded4500_select_rm234_projection_fix'
CONFIG=D.parent/'config.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not OUTPUT.exists() and not (D/'protocol.json').exists(), 'Preserve existing attempt'
    os.chdir(ROOT)
    settings={'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1',
              'NUMSIM_REPO_ROOT':str(ROOT/'vendor/NumSim-mine'),
              'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','RW_DECISION_FAIL_FAST':'1',
              'RW_MAINLINE_SG_ONLY':'1','RW_OFFSET_WRITER':'experiment','RW_RAMP_AMBER_SEC':'0'}
    os.environ.update(settings)
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    prior=json.loads((D.parent/'link52_225/protocol.json').read_bytes())
    pins={p:sha(ROOT/p) for p in prior['source_sha256']}
    pins[str(CONFIG)]=sha(CONFIG)
    pins[str(Path(__file__))]=sha(Path(__file__))
    argv=['--at=4500','--closedloop-recorded','--select','--warm-head-history','--replay-vsl-history',
          '--recording-dir=D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29',
          '--tuning-json='+str(CONFIG),'--probe-label=rm234_projection_fix']
    save('protocol.json',dict(purpose='Actual controller selection after233 initialization repair',
         start_sec=4500,seed=29,horizon_sec=450,max_optimizer_calls=1,
         optimizer_policy='Unchanged native219 tuning: fixed90 VSL, green/offset/eight RM selected',
         candidate225_enabled=False,coefficients_changed=False,future_observation_inputs=False,
         new_native_runs=0,fzp_reads=0,priority='BelowNormal',source_sha256=pins,argv=argv,
         output=str(OUTPUT),missing_current_vsl_witness=True,
         previous_turn='PROGRESS: native219 completed/analyzed; observation repair and held forecast verified.'))
    sys.path.insert(0,str(ROOT))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    replay=probe.replay_vsl_history
    def reconstruct_failed_current(*args,**kwargs):
        return replay(*args,**kwargs,allow_missing_current_online=True)
    probe.replay_vsl_history=reconstruct_failed_current
    sys.argv=[probe.__file__,*argv]
    save('launch.json',dict(pid=os.getpid(),started_epoch=time.time(),output=str(OUTPUT)))
    started=time.perf_counter()
    probe.main()
    result=json.loads((OUTPUT/'summary.json').read_bytes())
    assert result['native_started'] is False
    unchanged=all(sha(ROOT/p)==h for p,h in pins.items())
    assert unchanged
    save('completion.json',dict(status='saved_selection_complete_not_native_gain_qualified',
        wall_sec=time.perf_counter()-started,output=str(OUTPUT),sources_unchanged=True,
        optimizer_calls=1,new_native_runs=0,fzp_reads=0,gain_qualified=False))


if __name__=='__main__':main()
