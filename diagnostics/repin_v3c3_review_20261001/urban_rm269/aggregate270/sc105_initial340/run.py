"""Three fixed commands on one current-position candidate; no optimizer."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import gzip,hashlib,json,os,pickle,sys,time,traceback
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc105_initial340 import candidate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.tail337 import prepare
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import load
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.response332.commands import pair
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4];OUT=HERE/'forecast3300_v2'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists(),'Preserve existing attempt'
    assert not any((p/'STOP').exists() for p in (ROOT,A.parent,A,HERE))
    check=read(HERE/'check.json');assert check['status']=='passed_three_states'
    pins=dict(check['source_pins']);assert all(sha(p)==h for p,h in pins.items())
    oldpins=read(A/'tail337/source_compatibility.json')['source_pins']
    assert all(sha(p)==h for p,h in oldpins.items());pins.update(oldpins)
    OUT.mkdir();record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),forecasts=0,native=0)
    write('execution.json',record);results={}
    try:
        # Reconstruct the canonical worker/runtime without rewriting337 evidence.
        original_save=prepare.save;prepare.save=lambda name,value:write('bootstrap_'+name,value)
        try:request,coord,plan=prepare.inputs()
        finally:prepare.save=original_save
        follower,state,reference,forecast=request['owned'];cfg=follower.cfg
        cfg0,state0,forecast0=pickle.loads((A/'transfer331/build3300_v2/initial.pickle').read_bytes())
        assert equal(cfg,cfg0) and equal(state,state0) and equal(forecast,forecast0)
        proof=read(A/'transfer331/build3300_v2/summary.json');source=Path(proof['source'])
        raw,frame,ipins=load(source,3300);pins.update(ipins)
        from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
        from evaluation.controllers import signal_actuation_contract as signals,physical_ramp_branches as ramps
        from evaluation.controllers import area_leader_objective as constraints
        from evaluation.controllers.control_area_objective import get_ledger
        from evaluation.controllers.area_runtime import model_inventory
        from src.controllers import rollout_endpoint as endpoint
        from src.models.state import ControlAction
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,verify_pending
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339.runtime import source_hooks,enabled
        np=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
        state,projection=candidate.install(cfg,state,raw,frame,np.read_bytes(),adapter._contiguous_stopline_queue(raw,per_lane=True))
        write('projection.json',projection)
        (OUT/'initial.pickle').write_bytes(pickle.dumps((cfg,state,forecast),protocol=5))
        oldout=Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
        archived_commands=read(oldout/'commands.json')
        # The later336 worker captured a different protected city reference.
        # Restore the exact332 experiment controls; do not mix policy changes
        # into the current-state projection comparison.
        reference=seq.first_action(reference).copy()
        assert equal(reference.offsets,archived_commands['hold'][0]['offsets'])
        assert equal(reference.vsl,archived_commands['hold'][0]['vsl'])
        reference.green_times=deepcopy(archived_commands['hold'][0]['green_times'])
        cap_path=A/'decision285/full3300_current/unused.json';pins[str(cap_path)]=sha(cap_path)
        arms=pair(reference,cfg,adapter.control_from_json(cap_path,cfg,ControlAction));arms['recorded']=[]
        for sec in (3300,3450,3600):
            p=source/f'action_{sec:06}.json';assert p.with_suffix('.json.applied').exists();pins[str(p)]=sha(p)
            arms['recorded'].append(seq.first_action(adapter.control_from_json(p,cfg,ControlAction)))
        commands={}
        for arm,blocks in arms.items():
            prev=seq.first_action(reference);commands[arm]=[]
            for j,b in enumerate(blocks):
                signals.validate_writer(b,cfg,plan,'experiment')
                realized=ramps.candidate_from_greens(b,prev,cfg,{r:b.diagnostics['rw_meter_green_'+r] for r in b.ramp_metering})
                assert ramps.physical_commands(realized,cfg)==ramps.physical_commands(b,cfg)
                prev=b;commands[arm].append(dict(sec=3300+150*j,commands=ramps.physical_commands(b,cfg),
                    NP=b.N_P_star,NUF=b.N_UF_star,green_times=b.green_times,offsets=b.offsets,vsl=b.vsl))
        assert equal(commands,archived_commands)
        write('commands.json',commands)
        pins[str(oldout/'commands.json')]=sha(oldout/'commands.json')
        frozen=pickle.dumps(state,protocol=5)
        with source_hooks() as hooks,hook('source_path_current_physical_speed'):
            for module in tuple(sys.modules.values()):
                path=getattr(module,'__file__',None)
                if path and Path(path).suffix=='.py' and Path(path).is_relative_to(ROOT):pins[str(Path(path))]=sha(path)
            for arm,blocks in arms.items():
                action=seq.pack(blocks);tick=time.perf_counter()
                with enabled(cfg,hooks) as calls,seq.prediction_scope(action,cfg,3300,3) as visits:
                    point=endpoint.evaluate_price_point(state,action,deepcopy(forecast[:3]),(),
                        endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
                elapsed=time.perf_counter()-tick
                assert not point.aborted and len(point.states)==3 and visits==[0,1,2]
                assert pickle.dumps(state,protocol=5)==frozen
                response=point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.);assert exceed<1e-7
                stocks=[]
                for s in (state,*point.states):
                    get_ledger(s).assert_stocks(model_inventory(s,cfg));verify_pending(s)
                    stocks.append(dict(time_sec=s.time_sec,stocks=deepcopy(get_ledger(s).stocks)))
                inside={};outside={}
                for row in response['residence']:
                    for k,n in row['inside_veh'].items():inside[k]=inside.get(k,0.)+n*row['dt_h']
                    for k,n in row['model_stock_veh'].items():outside[k]=outside.get(k,0.)+(n-row['inside_veh'].get(k,0.))*row['dt_h']
                assert abs(sum(inside.values())-point.ttt)<1e-7
                q=constraints.shared_urban_quantities(follower,response,start_sec=3300,horizon_steps=3)
                feasible=constraints.shared_quantity_constraints(follower,action,q,start_sec=3300,horizon_steps=3,
                    np_mode='cap',target_np_veh=action.N_P_star,np_tolerance_veh=1e-7,
                    nuf_mode='cap',target_nuf_veh_h=action.N_UF_star,nuf_tolerance_veh_h=1e-7)
                item=dict(omega_ttt_veh_h=point.ttt,costs_by_stock=inside,outside_costs_by_stock=outside,
                    predicted_merge=q['predicted_ramp_merge'],shared_constraints=feasible,conservation_states=4,
                    resource_max_exceedance=exceed,writer_three_blocks=True,wall_sec=elapsed,runtime_hooks=calls)
                write(arm+'.json',item);write(arm+'.stocks.json',stocks)
                (OUT/(arm+'.response.json.gz')).write_bytes(gzip.compress(json.dumps(response,allow_nan=False).encode()))
                results[arm]=item;print('SC105_FORECAST',arm,point.ttt,elapsed,'feasible',feasible['feasible'],flush=True)
        assert all(sha(p)==h for p,h in pins.items())
        write('summary.json',dict(status='complete',forecasts=3,results=results,source_pins=pins,
            only_current_SC105_projection_changed=True,commands_exact_previous332=True,
            native_runs=0,optimizer_calls=0,new_fits=0,future_observation_inputs=False,goal_complete=False))
        record['status']='complete'
    except BaseException:
        record.update(status='failed_preserved',error=traceback.format_exc());raise
    finally:
        record.update(forecasts=len(results),finished_utc=datetime.now(timezone.utc).isoformat());write('execution.json',record)

if __name__=='__main__':main()
