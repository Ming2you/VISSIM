"""Bounded actual canonical1350 replay of two finite route corridors; no optimizer."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,pickle,subprocess,sys,tempfile
from diagnostics.test_route_choice_1128 import ROOT,base
from diagnostics.probe_route_choice_integration import evaluate,direct


def main():
    if len(sys.argv)==4 and sys.argv[1] in ('--worker','--worker-off'):
        payload=pickle.loads(Path(sys.argv[2]).read_bytes())
        result=evaluate(payload) if sys.argv[1]=='--worker' else direct(payload,False)
        Path(sys.argv[3]).write_bytes(pickle.dumps(result));return
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,route_choice_corridor as rc
    from src.models.demand import DemandStep
    sources=[ROOT/'evaluation/controllers'/name for name in ('route_choice_corridor.py','runtime_setup.py','urban_flow_accounting.py','shared_approach.py','area_runtime.py','area_dynamic_routes.py','projection_support.py')]
    sources += [ROOT/'diagnostics'/name for name in ('route_choice_corridor_ver2.json','route_choice_corridor_1128_ver2.json','physical_projection_support_635_proposal.json')]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (cfg,state,detectors,tuning,raw,mapping,metadata),action=deepcopy(base())
    payload={'cfg':cfg,'state':state,'detectors':detectors,'tuning':tuning,'raw':raw,'action':action,
             'forecast':adapter.demand_from_state(raw,cfg,DemandStep,3)}
    frozen=pickle.dumps(payload)
    result=evaluate(deepcopy(payload));repeat=evaluate(deepcopy(payload));assert result==repeat
    on=direct(deepcopy(payload),True);off=direct(deepcopy(payload),False);assert on==off
    with tempfile.TemporaryDirectory(prefix='route1128_worker_',dir=ROOT/'diagnostics') as directory:
        folder=Path(directory);src=folder/'input.pkl';dst=folder/'output.pkl';src.write_bytes(frozen)
        for mode,expected in [('--worker',result),('--worker-off',off)]:
            child=subprocess.run([sys.executable,'-X','utf8','-m','diagnostics.probe_route_choice_1128_integration',mode,str(src),str(dst)],cwd=ROOT,timeout=55,capture_output=True)
            assert child.returncode==0,child.stderr.decode('utf-8',errors='replace')
            assert pickle.loads(dst.read_bytes())==expected
    assert pickle.dumps(payload)==frozen
    changed=[k for k,v in hashes.items() if hashlib.sha256((ROOT/k).read_bytes()).hexdigest()!=v]
    output={'kind':'historical1350 holding diagnostic; unknown past route is not live-complete',
            'sim_sec':1350,'horizon_sec':450,'source_sha256':hashes,'source_changes':changed,
            'main_repeated_fresh_worker_equal':True,'physical_omega_on_off_equal':True,'omega_off_fresh_worker_equal':True,
            'result':result,'merge_audits':{s['decision']:s['merge_audit'] for s in rc._specs(cfg)}}
    path=ROOT/'diagnostics/route_choice_1128_canonical_1350_450.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ('source_sha256','result','merge_audits')}|{'initial':result['initial_choice'],'final':result['final_choice'],'area':{k:v for k,v in result['area'].items() if k!='flow_counts'},'objective':result['objective']},indent=2))


if __name__=='__main__':main()
