"""One fresh full selection after the finite meter/budget stage repair."""
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
OUTPUT=I/'closedloop_recorded4500_select_rm236_budget_meter_fix'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not OUTPUT.exists() and not (D/'protocol.json').exists(), 'Preserve prior attempts'
    os.chdir(ROOT)
    pins=dict(json.loads((D.parent/'budget235/postsearch/protocol.json').read_bytes())['source_sha256'])
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    pins[str(Path(__file__))]=sha(Path(__file__))
    original=json.loads((D.parent/'budget235/protocol.json').read_bytes())
    argv=[x.replace('rm235_three_budgets','rm236_budget_meter_fix') for x in original['argv']]
    save('protocol.json',dict(start_sec=4500,seed=29,horizon_sec=450,
        purpose='Fresh complete PFO/three-budget SDMPC/finite-meter selection and canonical writer after235 code repair',
        source_sha256=pins,argv=argv,output=str(OUTPUT),
        max_optimizer_calls=1,max_leader_candidates=3,pfo_iterations=2,follower_iterations_per_candidate=2,
        coefficients_changed=False,native_runs=0,fzp_reads=0,fit=0,
        expected_saved_stage_objective=529.0745387551341,
        previous_turn='PROGRESS: ordering defect fixed,43 tests,28 scalar replays and one actuator-model check passed',
        qualification='Not an independent plant response or native traffic gain certificate'))
    os.environ.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
        NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    sys.path.insert(0,str(ROOT))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    replay=probe.replay_vsl_history
    probe.replay_vsl_history=lambda *a,**kw:replay(*a,**kw,allow_missing_current_online=True)
    sys.argv=[probe.__file__,*argv]
    save('launch.json',dict(pid=os.getpid(),started_epoch=time.time(),output=str(OUTPUT)))
    started=time.perf_counter()
    probe.main()
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    j=json.loads((OUTPUT/'unused_action.joint.json').read_bytes())
    assert j['completed'] and j['selection']['feasible'] and len(j['selection']['candidates'])==3
    save('completion.json',dict(status='full_reselection_complete_not_native_qualified',wall_sec=time.perf_counter()-started,
        source_unchanged=True,objective=j['selection']['selected_objective'],
        difference_from_saved_stage=j['selection']['selected_objective']-529.0745387551341,
        native_runs=0,optimizer_calls=1))


if __name__=='__main__':main()
