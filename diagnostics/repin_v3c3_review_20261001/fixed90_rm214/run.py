"""Four bounded current-plant forecasts; reuse canonical causal initializer."""
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    raw=json.dumps(value,indent=None if name.endswith('.gz') else 2,allow_nan=False).encode()
    (HERE/name).write_bytes(gzip.compress(raw) if name.endswith('.gz') else raw)

def run(captured,candidates,coord,output):
    from evaluation.controllers import sdmpc_sequence as sequence
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.area_follower_objective import shared_query_runtime_scope
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.controllers import rollout_endpoint as endpoint
    assert list(candidates)==['held_actual','release_actual']
    cfg,state=captured['cfg'],captured['state']
    assert state.time_sec==2700 and len(captured['forecast'])==3
    actions={'hold110':candidates['held_actual'],'release110':candidates['release_actual']}
    for arm in ('hold','release'):
        action=actions[arm+'110'];z=coord.encode(action);changed=[]
        for j,axis in enumerate(coord.axes):
            if axis['kind']=='vsl' and axis['key']=='FW_E__seg13':
                assert coord.reference.vsl[axis['key']]==110
                z[j]=(90.-110.)/axis['scale'];changed.append(axis['block'])
        assert changed==[0,1,2]
        actions[arm+'90']=coord.decode(z,action)
    segment_vsl=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
    results={};start=time.perf_counter()
    for name,action in actions.items():
        receipt=coord.validate(action)
        blocks=sequence.actions(action,3)
        commands=[dict(vsl=c.vsl,green_times=c.green_times,offsets=c.offsets,
                      meters={r:c.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}) for c in blocks]
        with shared_query_runtime_scope():
            effective=[{road:[float(segment_vsl(c,road,i,cfg)) for i in range(len(
                cfg.network.freeway_vsl_zone_head_of_cell[road]))] for road in cfg.network.freeway_links} for c in blocks]
        begun=time.perf_counter()
        with sequence.prediction_scope(action,cfg,state.time_sec,3) as visits:
            point=endpoint.evaluate_price_point(state,action,captured['forecast'],(),
                endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=False,score_mode='raw'),capture_response=True)
        elapsed=time.perf_counter()-begun
        assert visits==[0,1,2] and not point.aborted and len(point.states)==3
        response=point.control_area_response;costs={};outside={}
        for row in response['residence']:
            for key,n in row['inside_veh'].items():
                costs[key]=costs.get(key,0.)+row['dt_h']*n
                extra=row['model_stock_veh'][key]-n
                assert extra>=-1e-7
                outside[key]=outside.get(key,0.)+row['dt_h']*max(0.,extra)
        assert abs(sum(costs.values())-point.ttt)<1e-7
        stocks=[]
        for saved in (state,*point.states):
            inventory=model_inventory(saved,cfg);get_ledger(saved).assert_stocks(inventory)
            stocks.append(dict(time_sec=saved.time_sec,stock=inventory))
        flows={}
        for event in response['transfers']:
            key=(event['source'],event['target'],event['route_key'])
            flows[key]=flows.get(key,0.)+event['vehicles']
        transfers=[dict(source=k[0],target=k[1],route_key=k[2],vehicles=n) for k,n in flows.items()]
        first,last=stocks[0]['stock'],stocks[-1]['stock']
        residuals={k:last.get(k,0.)-first.get(k,0.)-math.fsum(t['vehicles'] for t in transfers if t['target']==k)
                   +math.fsum(t['vehicles'] for t in transfers if t['source']==k) for k in first.keys()|last.keys()}
        error=max(map(abs,residuals.values()));assert error<1e-7
        resources=max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)
        assert resources<1e-7
        totals={k:0. for k in ('source','merge','off','terminal')};merges={}
        for event in transfers:
            s,t,n=event['source'],event['target'],event['vehicles']
            if t=='freeway:FW_E':
                if s=='origin:FW_E':totals['source']+=n
                else:
                    assert s.startswith('merge_pending:')
                    totals['merge']+=n;merges[s]=merges.get(s,0.)+n
            elif s=='freeway:FW_E':
                if t=='external:terminal:FW_E':totals['terminal']+=n
                else:
                    assert t.startswith('storage:');totals['off']+=n
        metrics=dict(omega=point.ttt,east=costs['freeway:FW_E'],west=costs['freeway:FW_W'],
            ramps=sum(v for k,v in costs.items() if k.startswith('ramp:')),outside=sum(outside.values()),
            tracked_total=point.ttt+sum(outside.values()),end_east_vehicles=last['freeway:FW_E'],**totals)
        item=dict(metrics=metrics,cost_by_stock=costs,outside_cost_by_stock=outside,commands=commands,
            effective_cell_vsl=effective,validation=receipt,stocks=stocks,transfers=transfers,
            actual_mainline_merges=merges,balance_error=error,resource_exceedance=resources,wall_sec=elapsed)
        save(name+'.json',item)
        save(name+'_response.json.gz',response)
        results[name]=item
        print(json.dumps(dict(case=name,metrics=metrics,seconds=elapsed)),flush=True)
    for name,legacy in (('hold110','held_actual'),('release110','release_actual')):
        old=json.loads((I/'closedloop_recorded2700_lever450_service66rm47_after_rm47'/(legacy+'.json')).read_bytes())
        assert results[name]['commands']==old['commands']
        assert results[name]['cost_by_stock']==old['cost_by_stock']
        assert results[name]['metrics']['omega']==old['ttt_omega_veh_h']
    differences={speed:{k:results['release'+speed]['metrics'][k]-results['hold'+speed]['metrics'][k]
                       for k in results['hold'+speed]['metrics']} for speed in ('110','90')}
    save('summary.json',dict(status='MODEL_COUNTERFACTUAL_ONLY_NOT_NATIVE90_VALIDATION',
        results={k:v['metrics'] for k,v in results.items()},release_minus_hold=differences,
        actual110=json.loads((R/'rm47_service66_response/assessment.json').read_bytes())['release_minus_hold']['native'],
        parity110_exact=True,forecasts=4,fit=0,optimizer_iterations=0,new_native=0,new_FZP=0,
        prediction_compute_sec=sum(x['wall_sec'] for x in results.values()),total_callback_sec=time.perf_counter()-start,
        limitation='Common native47 state at2700 with prior110;90 switches at2700, not fixed90 since900. No fresh N_P/N_UF cap or optimizer selection test.'))

def main():
    assert not (HERE/'protocol.json').exists(),'Do not overwrite or retry completed/failed runs'
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    prior=json.loads((R/'restart_supply210/protocol.json').read_bytes())
    pins={k:sha(ROOT/k) for k in prior['source_sha256']}
    assert pins==prior['source_sha256']
    assert sha(Path(prior['STOP']['path']))==prior['STOP']['sha256']
    config=R/'rm47_service66_response/candidate_config.json'
    save('protocol.json',dict(question='Does strong RM gain remain under a fixed VSL90 counterfactual?',
        budget=dict(forecasts450=4,fits=0,optimizer_iterations=0,native=0,FZP=0),
        seed=47,start_sec=2700,source_sha256=pins,STOP=prior['STOP'],
        config=dict(path=str(config),sha256=sha(config)),driver_sha256=sha(Path(__file__)),
        future_observations_used=False,production_adopted=False))
    from evaluation.controllers import obs150_contract as oc
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    original_probe,original_write=probe.probe_levers,oc.write_derived
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        return p
    def capture(captured,reference,output,**kwargs):
        assert kwargs['replay_pair']['seed']==47 and not kwargs['replay_pair']['future_states_used']
        save('input_receipt.json',dict(replay_pair=kwargs['replay_pair'],output=str(output)))
        return original_probe(captured,reference,output,prepared_probe_callback=run,**kwargs)
    oc.write_derived=existing;probe.probe_levers=capture
    sys.argv=[str(probe.__file__),'--closedloop-recorded','--at=2700','--warm-head-history','--replay-vsl-history',
        '--output-suffix=fixed90_rm214','--lever-probe450',
        '--recording-dir=D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47',
        '--fixed-replay-summary='+str(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json'),
        '--tuning-json='+str(config)]
    try:probe.main()
    finally:oc.write_derived=original_write;probe.probe_levers=original_probe
    assert {k:sha(ROOT/k) for k in pins}==pins
    assert sha(Path(prior['STOP']['path']))==prior['STOP']['sha256']
    save('completion.json',dict(status='COMPLETE',source_101_unchanged=len(pins)==101,STOP_unchanged=True))

if __name__=='__main__':main()
