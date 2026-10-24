"""One bounded three-budget selection; unchanged plant, objective and cap rules."""
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
OUTPUT=I/'closedloop_recorded4500_select_rm235_three_budgets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    (D/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    assert not OUTPUT.exists() and not (D/'protocol.json').exists(), 'Preserve prior attempts'
    os.chdir(ROOT)
    os.environ.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
        NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
        RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    prior=json.loads((D.parent/'select234/protocol.json').read_bytes())
    assert all(sha(ROOT/p)==h for p,h in prior['source_sha256'].items())
    original=D.parent/'config.json'
    config=json.loads(original.read_bytes())
    assert config['adapter']['joint_owner_game']['max_leader_candidates']==1
    config['adapter']['joint_owner_game']['max_leader_candidates']=3
    candidate=D/'config.json'
    save('config.json',config)
    reverted=json.loads(candidate.read_bytes())
    reverted['adapter']['joint_owner_game']['max_leader_candidates']=1
    assert reverted==json.loads(original.read_bytes())
    pins=dict(prior['source_sha256'])
    pins[str(candidate)]=sha(candidate)
    pins[str(Path(__file__))]=sha(Path(__file__))
    argv=[arg.replace('rm234_projection_fix','rm235_three_budgets')
          if not arg.startswith('--tuning-json=') else '--tuning-json='+str(candidate)
          for arg in prior['argv']]
    save('protocol.json',dict(start_sec=4500,seed=29,horizon_sec=450,
        purpose='Activate existing bounded upper-level budget search, not widening the fixed cap of a rejected action',
        sole_configuration_change={'adapter.joint_owner_game.max_leader_candidates':[1,3]},
        unchanged=['plant','forecast','Omega objective','PFO iterations','follower iterations','prices',
                   'cap initialization and margins','cap stencil','physical feasibility','actuator limits'],
        max_optimizer_calls=1,max_leader_candidates=3,follower_iterations_per_candidate=2,
        runtime_model_change=False,native_runs=0,fzp_reads=0,fit=0,source_sha256=pins,
        previous_turn='PROGRESS: saved SDMPC selection recovered, quantity-cap rejection isolated',
        claude_evidence=['f34b8961','docs/HANDOFF_20260922_PFO_CAP_SDMPC.md',
                         'diagnostics/sdmpc_cap_margin_20260923/README.md'],
        argv=argv,output=str(OUTPUT),missing_current_vsl_witness=True))
    sys.path.insert(0,str(ROOT))
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    replay=probe.replay_vsl_history
    probe.replay_vsl_history=lambda *a,**kw:replay(*a,**kw,allow_missing_current_online=True)
    sys.argv=[probe.__file__,*argv]
    save('launch.json',dict(pid=os.getpid(),started_epoch=time.time(),output=str(OUTPUT)))
    started=time.perf_counter()
    probe.main()
    result=json.loads((OUTPUT/'unused_action.joint.json').read_bytes())
    unchanged=all(sha(ROOT/p)==h for p,h in pins.items())
    assert unchanged and result['completed'] and result['selection']['feasible']
    assert len(result['selection']['candidates'])<=3
    save('completion.json',dict(status='saved_selection_complete_not_native_gain_qualified',
        wall_sec=time.perf_counter()-started,output=str(OUTPUT),sources_unchanged=True,
        optimizer_calls=1,leader_candidates=len(result['selection']['candidates']),
        native_runs=0,fzp_reads=0,gain_qualified=False))


if __name__=='__main__':main()
