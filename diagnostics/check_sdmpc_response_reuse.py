"""Eight fresh original-model predictions qualify NP-only response reuse."""
from pathlib import Path
import copy
import hashlib
import json
import pickle
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def main():
    from diagnostics.check_sdmpc_three_blocks import context
    from evaluation.controllers import area_follower_objective as joint, sdmpc
    from evaluation.controllers import sdmpc_response_cache as reuse, sdmpc_sequence as seq
    from evaluation.controllers import area_leader_objective as constraints
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    pins=request['bootstrap']['runtime_sources']
    for path in sorted((ROOT/'evaluation/controllers').glob('*.py')):
        pins[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in pins:pins[name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    follower,state,reference,forecast=request['owned'];cfg=follower.cfg
    cfg.network.sdmpc_options['response_np_cache']=True
    coord,callbacks,ctx,options=context(request)
    prior=pickle.loads((ROOT/'diagnostics/sdmpc_reverse_20260921/full_decision_v2/result.pickle').read_bytes())
    selected=prior['response']['control']
    actions=[]
    for base in (reference,selected):
        for cap in (2400.,743.75,81.25,-250.):
            action=base.copy();action.N_P_star=cap
            if seq.KEY in action.diagnostics:
                for row in action.diagnostics[seq.KEY]['future']:row['N_P_star']=cap
            actions.append(action)
    query=joint.make_decision_shared_query(follower,state,reference,forecast,horizon_steps=3,
        source_fingerprint=sdmpc.token(pins),parallel_workers=8,
        worker_bootstrap=request['bootstrap'],unlimited_time=True)
    report=dict(completed=False,native_applied=False,source_sha256=pins,scope=__doc__)
    started=time.perf_counter()
    try:
        fresh=query(tuple(actions))['results']
        # The reuse cache is empty; the underlying exact-action query now has
        # fresh evidence for every action. No new traffic rollout is required.
        cache=reuse.ResponseCache(query,cfg)
        bound=cache(actions)
        checks=[]
        for action,raw,value in zip(actions,fresh,bound):
            reuse.validate_binding(action,value)
            physical={k:v for k,v in value.items() if k not in
                ('response_token','sdmpc_physical_response_reuse')}
            original={k:v for k,v in raw.items() if k!='response_token'}
            exact=physical==original
            q=lambda item:constraints.shared_quantity_constraints(follower,action,item['quantities'],
                start_sec=state.time_sec,horizon_steps=3,np_mode='cap',target_np_veh=action.N_P_star,
                np_tolerance_veh=options['np_tolerance_veh'],nuf_mode='equality',
                target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=options['nuf_tolerance_veh_h'])
            actual=q(raw)
            checks.append(dict(np_cap=action.N_P_star,physical_response_exact=exact,
                quantity_checks_exact=actual==q(value),feasible=actual['feasible'],
                objective=raw['objective_veh_h']))
        report.update(completed=True,checks=checks,cache=cache.stats(),
            pass_all=all(c['physical_response_exact'] and c['quantity_checks_exact'] for c in checks))
        (out/'witness.pickle').write_bytes(pickle.dumps(dict(actions=actions,fresh=fresh,bound=bound),protocol=5))
    finally:
        query.close();report['query']=query.stats();report['wall_sec']=time.perf_counter()-started
        report['source_changes']=[p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        if report['source_changes']:report['pass_all']=False
        (out/'report.json').write_text(json.dumps(json_records(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','query','cache')}),flush=True)
    return 0 if report.get('pass_all') else 1


if __name__=='__main__':raise SystemExit(main())
