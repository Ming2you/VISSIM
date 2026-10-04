"""Use existing external-boundary rollout for six conditional phase checks."""
from collections import Counter
import copy
import csv
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def save(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    assert not (HERE/'status.json').exists(), 'No automatic repeat'
    protocol=read(HERE/'protocol.json')
    for p,h in protocol['inputs_sha256'].items(): assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for p,h in protocol['protected_sha256'].items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(HERE.parent/'retained10638/candidate_manifest.json')
    from evaluation.controllers import area_freeway_accounting as area
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as replay
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    capture=read(I/'heldout67_freeway_20260930/capture.json')
    model=context['component'];nodes=copy.deepcopy(model.ramp_receiving_nodes)
    assert not model.aggregate_merge_speed and not model.lane_groups_enabled and not model.ramp_lane_coupling
    model.ramp_receiving_nodes={}
    initial=2670.1;endtime=3120.1
    times=[round(initial+30*i,6) for i in range(16)]
    inputs={};obs={};counts={};reference={};actual={}
    for arm in protocol['arms']:
        rec=next(r for r in capture['records'] if r['arm']==arm)
        args,kw=replay.read_primitive_capture(rec['input'],rec['sha256'])
        assert args[2]==context['parameters'] and len(args[1])==450
        kw['offramp_inventory']=dict(contract=read(F/'route_inventory/contract.json'),raw=read(F/'route_inventory/s67_late/initial_raw.json'))
        kw['port_dynamics']['entry_capacity_mode']='storage'
        kw.pop('ramp_dynamics')
        inputs[arm]=(args,kw)
        obs[arm]=ObservationData(I/'heldout67_freeway_20260930/observations'/arm)
        counter=Counter()
        with (obs[arm].folder/'port_events.csv').open(encoding='utf-8-sig',newline='') as f:
            for e in csv.DictReader(f):
                if e['kind']=='departure' and initial<float(e['time_s'])<=endtime+1e-7:
                    counter[round(float(e['time_s']),6),e['connector']]+=1
        for ramp,spec in model.ramps.items():
            if spec['road']!='FW_E':continue
            cell=model._config('FW_E',context['parameters']['by_direction']['FW_E']).network.ramp_merge_segment_index[ramp]
            for end in times[1:]:
                native=sum(counter[round(end-d,6),str(spec['connector'])] for d in (0,5,10,15,20,25))
                assert native==float(obs[arm].flows[end,'FW_E',cell]['ramp_merges'])
        counts[arm]=counter
        with gzip.open(F/'conditional_boundary67'/('obs_'+arm+'.json.gz'),'rt',encoding='utf-8') as f:reference[arm]=json.load(f)
        actual[arm]=read(F/'conditional_boundary67'/('obs_'+arm+'_result.json'))['actual']
    assert inputs['release'][0][0]==inputs['release_vsl90'][0][0]
    def measure(pred):
        stocks={initial:sum(r['n_veh'] for r in inputs['release'][0][0] if r['road']=='FW_E')}
        for r in pred['cells']:stocks[r['time_s']]=stocks.get(r['time_s'],0.)+r['n_veh']
        return dict(mainline_ttt=sum((stocks[a]+stocks[b])*(b-a)/7200 for a,b in zip(times,times[1:])),
                    end_n=stocks[endtime],flows={k:sum(r[k] for r in pred['flows']) for k in ('source_admissions','ramp_merges','off_departures','terminal_exits')},
                    downstream_by_cell={str(c):sum(r['downstream_crossings'] for r in pred['flows'] if r['cell']==c) for c in range(31)})
    original_transition=area._freeway_substep_events
    rows=[];started=time.perf_counter();completed=0
    save(HERE/'status.json',dict(status='running',completed=0,maximum=6))
    try:
        for phase in protocol['phases']:
            for arm in protocol['arms']:
                args,kw=copy.deepcopy(inputs[arm]);counter=counts[arm]
                imposed=Counter()
                for index,step in enumerate(args[1]):
                    assert abs(step['window_start_s']-(initial+index))<1e-6
                    end=round(initial+(index//5+1)*5,6)
                    factor=(1. if phase=='uniform' else 5. if index%5==(0 if phase=='front' else 4) else 0.)
                    step['ramp_release_vph']={r:counter[end,str(spec['connector'])]*720.*factor for r,spec in model.ramps.items() if spec['road']=='FW_E'}
                    for r,q in step['ramp_release_vph'].items():imposed[end,r]+=q/3600
                    step['source_demand_vph']['FW_E']=float(obs[arm].flows[times[index//30+1],'FW_E',0]['source_admissions'])*120.
                for (end,r),n in imposed.items():assert abs(n-counter[end,str(model.ramps[r]['connector'])])<1e-9
                violations={r:dict(seconds=0,excess_veh=0.,max_excess_vph=0.) for r in nodes}
                def observe(state,control,demand,cfg,*a,**kw):
                    scratch=copy.copy(state);scratch.ramp_queue=dict(state.ramp_queue);scratch._control_area_ledger=None
                    command=copy.deepcopy(control)
                    for r in cfg.network.ramps:
                        cap=cfg.network.ramp_capacity_veh_h[r]
                        scratch.ramp_queue[r]=math.nextafter(cap*cfg.simulation.T_f_h,math.inf)
                        command.ramp_metering[r]=cap
                    supply,_=area._mn.compute_ramp_release_flows(scratch,command,demand,cfg,include_current_arrivals=False)
                    for r in cfg.network.ramps:
                        up=cfg.network.ramp_merge_segment_index[r]-1
                        split=sum(cfg.network.off_ramp_split_ratio[o] for o in cfg.network.off_ramps if cfg.network.off_ramp_segment_index[o]==up)
                        conflict=state.freeway_density['FW_E'][up]*state.freeway_speed['FW_E'][up]*(1-split)
                        spec=nodes[r]
                        gap=model.ramps[r]['lanes']*gap_acceptance_supply_vph(conflict,spec['critical_gap_sec'],spec['followup_sec'])
                        excess=max(0.,kw['ramp_release_veh_h'][r]-min(supply[r],gap))
                        v=violations[r];v['seconds']+=int(excess>1e-7);v['excess_veh']+=excess*cfg.simulation.T_f_h
                        v['max_excess_vph']=max(v['max_excess_vph'],excess)
                    return original_transition(state,control,demand,cfg,*a,**kw)
                area._freeway_substep_events=observe
                try:pred=model.rollout(*args,**kw)
                finally:area._freeway_substep_events=original_transition
                completed+=1;label=phase+'_'+arm
                with gzip.open(HERE/(label+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
                parity=None
                if phase=='uniform':
                    parity={k:pred[k]==reference[arm][k] for k in ('cells','flows','ports')}
                    save(HERE/(label+'_parity.json'),parity)
                    assert all(parity.values()), 'Investigate current/archived uniform mismatch before phase runs'
                scored=score_rollout(obs[arm],initial,pred,'FW_E',include_source_boundary=True,horizon_sec=450)
                assert not scored['invalid']
                for end in times[1:]:
                    flow=[r for r in pred['flows'] if abs(r['window_end_s']-end)<1e-6]
                    for r in flow:
                        assert abs(r['ramp_merges']-float(obs[arm].flows[end,'FW_E',r['cell']]['ramp_merges']))<1e-7
                    assert abs(sum(r['source_admissions'] for r in flow)-float(obs[arm].flows[end,'FW_E',0]['source_admissions']))<1e-7
                row=dict(phase=phase,arm=arm,predicted=measure(pred),actual=actual[arm],
                         score={k:scored[k] for k in ('invalid','speed','density','cell_n','flow_vph','horizons')},
                         parity=parity,receiving_envelope_exceedance=violations,
                         continuity_residual=pred['diagnostics']['roads'][0]['continuity_residual_max_veh'])
                rows.append(row);save(HERE/'partial.json',dict(completed=completed,rows=rows))
                save(HERE/'status.json',dict(status='running',completed=completed,maximum=6,last=label))
                print(json.dumps(dict(case=label,ttt=row['predicted']['mainline_ttt'],flows=row['predicted']['flows'])),flush=True)
        response=[]
        for phase in protocol['phases']:
            base=next(r for r in rows if r['phase']==phase and r['arm']=='release')
            vsl=next(r for r in rows if r['phase']==phase and r['arm']=='release_vsl90')
            def delta(key):return vsl['predicted'][key]-base['predicted'][key]
            response.append(dict(phase=phase,mainline_ttt=delta('mainline_ttt'),end_n=delta('end_n'),
                discharge=sum(vsl['predicted']['flows'][k]-base['predicted']['flows'][k] for k in ('off_departures','terminal_exits'))))
        native_delta=actual['release_vsl90']['mainline_ttt']-actual['release']['mainline_ttt']
        span=max(r['mainline_ttt'] for r in response)-min(r['mainline_ttt'] for r in response)
        reference_error=abs(response[0]['mainline_ttt']-native_delta)
        for r in response:r['response_error_reduction_fraction']=1-abs(r['mainline_ttt']-native_delta)/reference_error
        result=dict(status='complete_conditional_not_qualified',rows=rows,response=response,native_mainline_delta=native_delta,
                    pair_phase_span_veh_h=span,small_sensitivity=span<.1 and max(r['response_error_reduction_fraction'] for r in response)<.2,
                    completed=completed,elapsed_seconds=time.perf_counter()-started,fit=False,new_native=0,new_FZP=0,
                    production_adopted=False,goal_qualified=False,limits=protocol['scope']+' '+protocol['interpretation'])
        save(HERE/'summary.json',result);save(HERE/'status.json',dict(status='complete_conditional_not_qualified',completed=completed))
        print(json.dumps(dict(response=response,native_delta=native_delta,span=span)),flush=True)
    except BaseException as exc:
        save(HERE/'failure.json',dict(error=repr(exc),completed=completed))
        save(HERE/'status.json',dict(status='failed',completed=completed,error=repr(exc)))
        raise
    finally:
        area._freeway_substep_events=original_transition;model.ramp_receiving_nodes=nodes
        for p,h in protocol['protected_sha256'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
        for p,h in protocol['inputs_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest()==protocol['STOP']['sha256']
        save(HERE/'restoration.json',dict(hooks_restored=True,model_receiving_nodes_restored=True,core_inputs_STOP_unchanged=True))


if __name__=='__main__':main()
