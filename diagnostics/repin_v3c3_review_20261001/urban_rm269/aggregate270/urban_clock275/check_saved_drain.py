"""One finite saved-state drainage comparison; shared head held RED explicitly."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import copy,hashlib,importlib.util,json,pickle,sys,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    output=HERE/'saved_drain_batched.json'
    assert not output.exists(),'Inspect completed evidence before another attempt'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    started=time.perf_counter()
    previous=json.loads((HERE.parent/'urban_clock274/plan.json').read_bytes())
    pins=dict(previous['source_pins'])
    changed=['evaluation/controllers/'+x for x in
        ('lane_offramp_runtime.py','lane_urban_runtime.py','multirate_urban_boundary.py')]
    for rel,expected in pins.items():
        if rel not in changed:assert sha(ROOT/rel)==expected,rel
    assert sha(HERE/'lane_offramp_before.py')==previous['source_pins'][changed[0]]
    for rel in changed:pins[rel]=sha(ROOT/rel)
    source=HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle'
    request=pickle.loads(source.read_bytes())
    cfg=request['owned'][0].cfg;initial=request['owned'][1]
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers.multirate_urban_clock import rebase_projection
    from evaluation.controllers.multirate_urban_boundary import advance_shared_interval
    from evaluation.controllers.sdmpc_tangent_worker import state_error
    from evaluation.controllers.area_runtime import model_inventory
    from src.models import urban_queue_model as uqm
    install_worker_runtime(adapter,cfg,request['bootstrap']['state_json'],request['bootstrap']['detector_mapping'])
    spec=importlib.util.spec_from_file_location('offramp_before275',HERE/'lane_offramp_before.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    start=int(initial.time_sec);routing=uqm.approach_routing(cfg)
    def red_and_room(s):
        head=s.sc1001_approach
        return {g:0. for g in head.lanes},{t:0. for t in head.city_movements}
    def run_fine(old):
        state=copy.deepcopy(initial);totals={}
        for sec in range(start,start+10):
            state.time_sec=sec;runtime=state.lane_offramp_runtime
            ledger=state._control_area_ledger
            if ledger.captures_response:ledger.begin_response_step('urban',sec,sec+1)
            method=legacy.LaneOfframpRuntime.drain if old else type(runtime).drain
            out=method(runtime,state,None,cfg,sec,routing)
            for k,n in out.items():totals[k]=totals.get(k,0.)+n
            green,room=red_and_room(state)
            assert state.sc1001_approach.advance(sec,green,room)==[]
        state.lane_offramp_runtime.assert_mirrors(state,cfg)
        state._control_area_ledger.assert_stocks(model_inventory(state,cfg))
        return state,totals
    old,old_flows=run_fine(True);fine,fine_flows=run_fine(False)
    default_error=state_error(old,fine)
    assert default_error<1e-9 and old_flows==fine_flows
    coarse_cfg,coarse=copy.deepcopy((cfg,initial))
    rebase_projection(coarse_cfg,coarse)
    green,room=red_and_room(coarse)
    assert advance_shared_interval(coarse.sc1001_approach,start,10,lambda a,b:green,room)==[]
    ledger=coarse._control_area_ledger
    if ledger.captures_response:ledger.begin_response_step('urban',start,start+10)
    before_stock={off:p.stock for off,p in coarse.lane_offramp_runtime.ports.items()}
    coarse_flows=coarse.lane_offramp_runtime.drain(coarse,None,coarse_cfg,start//10,routing)
    coarse.lane_offramp_runtime.assert_mirrors(coarse,coarse_cfg)
    coarse.sc1001_approach.assert_network_mirror(coarse,coarse_cfg)
    ledger.assert_stocks(model_inventory(coarse,coarse_cfg))
    after_stock={off:p.stock for off,p in coarse.lane_offramp_runtime.ports.items()}
    out=sum(coarse_flows.values());mass_error=abs(sum(before_stock.values())-sum(after_stock.values())-out)
    assert mass_error<1e-7
    ports={off:dict(initial=before_stock[off],fine_departed=before_stock[off]-fine.lane_offramp_runtime.ports[off].stock,
        coarse_departed=before_stock[off]-p.stock,remaining=p.stock,
        coarse_segments=p.last_coarse_drain_segments,physical_time=p.last_time_s)
        for off,p in coarse.lane_offramp_runtime.ports.items()}
    new_rows=[row for rows in coarse.sc1001_approach.queues.values() for row in rows
              if row[1] in coarse.sc1001_approach.entries]
    assert all(row[0]>start+10 for row in new_rows)
    result=dict(status='complete_reviewed',updated_utc=datetime.now(timezone.utc).isoformat(),
        source=str(source),source_sha256=sha(source),source_pins=pins,
        experiment='One10s saved2400 boundary interval; shared head RED, no incoming freeway/city traffic, downstream queues do not advance',
        prior_one_second_whole_state_max_error=default_error,ports=ports,
        fine_total_departed=sum(fine_flows.values()),coarse_total_departed=out,
        max_port_departure_difference=max(abs(r['fine_departed']-r['coarse_departed']) for r in ports.values()),
        mass_error_veh=mass_error,canonical_stock_ledger_pass=True,
        new_shared_packets_after_interval=True,full_rollouts=0,full_sdmpc_selections=0,native_runs=0,
        whole_urban10_qualified=False,wall_sec=time.perf_counter()-started)
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    save(output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','source')},ensure_ascii=False))


if __name__=='__main__':main()
