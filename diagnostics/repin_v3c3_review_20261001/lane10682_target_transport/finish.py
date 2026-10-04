"""Archive and restore only this rejected candidate after all owned jobs exit."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    target=HERE/'completion.json';assert not target.exists()
    assessment=json.loads((HERE/'assessment.json').read_bytes())
    post=json.loads((HERE/'postmortem.json').read_bytes())
    tests=json.loads((HERE/'tests.json').read_bytes())
    assert tests['passed'] and tests['tests']==22
    assert assessment['forecasts']==6 and post['inaccessible10643_final_zero']
    # Native recovery regression and persistent control sign error are material.
    recovery=assessment['cases']['47']['hold']['speeds'][-4:]
    assert recovery[0]['after']<recovery[0]['before']-30
    assert assessment['cases']['43']['vsl']['costs']['native_delta']>0
    assert assessment['cases']['43']['vsl']['costs']['after_delta']<0
    executed=json.loads((HERE/'executed_sources.json').read_bytes())
    before=json.loads((HERE/'before.json').read_bytes())
    for p,h in executed.items():
        assert sha(ROOT/p)==h,p
        assert sha(HERE/'executed_sources'/Path(p).name)==h,p
        assert sha(HERE/(Path(p).name+'.before'))==before[p],p
    for p in before:(ROOT/p).write_bytes((HERE/(Path(p).name+'.before')).read_bytes())
    for p,h in before.items():assert sha(ROOT/p)==h,p
    previous=json.loads((HERE.parent/'lane10682_route_access/completion.json').read_bytes())
    for p,h in previous['production_exact'].items():assert sha(Path(p))==h,p
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop)==previous['stop_sha256']
    result=dict(status='rejected_candidate_restored',goal_status='ACTIVE/NOT_QUALIFIED',
        forecasts=6,forecast_compute_sec=assessment['wall_sec'],tests=22,
        first_test_import_failure_preserved=True,precalculation_label_failure_preserved=True,
        owned_sessions={'5370':'EXIT0','81658':'EXIT0','initial47':'EXIT1_before_calculation'},
        restored_exact=before,previous_production_exact=previous['production_exact'],stop_sha256=sha(stop),
        new_native=0,new_fzp=0,push=0,optimizer_iterations=0,
        mass_residual=assessment['mass_residual'],route_residual=assessment['route_residual'],
        resource_exceedance=assessment['resource_exceedance'],
        evidence=['Wrong-lane10643 terminal stock29veh removed in both states.',
            'Seed47cell9lane2 still falsely accumulates24.39veh versus2native; most are not10643targets.',
            'Seed43cell10lane2 congestion missed:4.89veh/83.2kmh versus19veh/10.0kmh.',
            'Single frozen inlet/lateral approximation not qualified; avoid tuningFD to this candidate.',
            'Need separate downstream off receiving blockage from lane-local speed/through transport using conditional diagnostics, not more uniform rate grids.'])
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','forecasts','forecast_compute_sec','tests','new_native','new_fzp')},ensure_ascii=False))

if __name__=='__main__':main()
