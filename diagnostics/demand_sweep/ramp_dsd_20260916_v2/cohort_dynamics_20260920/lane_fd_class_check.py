"""One identification ablation of aggregate exit-FD reuse on flowing lanes.

Restore the already documented ordinary4 critical density in the equilibrium
speed law only, cells7..9 group2. Not a calibrated FD/capacity or production law.
No fitted gain, future states, lane deletion, or change to the receiving limits.
"""
from pathlib import Path
import sys, inspect, math, json, hashlib, statistics
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
import canonical_harness as ch

HERE=Path(__file__).resolve().parent


@contextmanager
def ordinary_equilibrium(active):
    mn=ch.accounting._mn;original=mn.effective_desired_speed_kmh;rows=[]
    def desired(*args,**kwargs):
        frame=inspect.currentframe().f_back;primary=True
        if frame.f_code.co_name=='record_desired' and Path(frame.f_code.co_filename).resolve()==e.CAL/'canonical_harness.py':
            primary='baseline_args' not in frame.f_locals
            frame=frame.f_back
        match=(frame.f_code.co_name=='advance' and Path(frame.f_code.co_filename).resolve()==e.ROOT/'evaluation/controllers/physical_lane_groups.py'
               and frame.f_locals['road']=='FW_E' and frame.f_locals['i'] in (7,8,9) and frame.f_locals['g']==2)
        if not match:
            del frame
            return original(*args,**kwargs)
        v=frame.f_locals;ctx=ch.adapter._FW_SEG_CTX;p=ctx['p'];net=v['net'];i=v['i'];g=v['g']
        assert ctx['armed'] and not getattr(net,'vsl_fd_two_branch',False)
        assert v['self'].widths[i]==[1.,1.,2.]
        critical=net.freeway_segment_params['FW_E'][6]['rho_crit']
        assert abs(critical-25)<1e-9 and abs(p['rho_crit']-20)<1e-9
        before=original(*args,**kwargs)
        if active:ctx['p']={**p,'rho_crit':critical}
        try:result=original(*args,**kwargs)
        finally:ctx['p']=p
        uncap=p['v_free']*math.exp(-((args[0]/(critical if active else p['rho_crit']))**p['metanet_a_m'])/p['metanet_a_m'])
        cap=(1+net.alpha_vsl)*v['vsl']
        assert abs(result-(min(uncap,cap) if args[5] else uncap))<1e-9
        if primary:
            rows.append(dict(time_s=v['state'].time_sec,cell=i,group=g,old_equilibrium=before,new_equilibrium=result,
                critical=critical if active else p['rho_crit'],binding=args[5] and uncap>cap+1e-9,
                n=v['before'][i][g],v=v['oldv'][i][g]))
        del frame
        return result
    mn.effective_desired_speed_kmh=desired
    try:yield rows
    finally:mn.effective_desired_speed_kmh=original


def main():
    out=HERE/'lane_fd_class_check_v2';out.mkdir(exist_ok=False)
    config=HERE/'port_origin_split_v1/config.json';param=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(param)['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),config,param,MODEL/'port_profile.json',e.CAL/'canonical_harness.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        e.ROOT/'evaluation/controllers/freeway_fd.py',e.ROOT/e.load(config)['freeway']['segment_params']]
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,new_native_runs=0,fit_evaluations=0,future_inputs=False,
        scope='Diagnostic equilibrium-only ablation in physical groups, receiving law and nominal capacity unchanged; no production feature. Existing ordinary4 value25 replaces exit-complex20 in flowing group2 of7..9 only.',
        state_guard='12 NC states, objective<=1.10*established internal_cost; all seeds already inspected development data.'))
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores'];results={};exact=0;forecasts=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);original=model._config
        def configured(road,p):
            c=original(road,p)
            if road=='FW_E':c.network.terminal_zero_gradient=True
            return c
        model._config=configured
        def window(t,command):
            w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                'initial_ramp_origin':origin['counts'][str(t)],'initial_off_eligible':origin['eligible_before_off'][str(t)]}}
            return w
        guards={}
        for t in [900,1650,2400,3600]:
            with ordinary_equilibrium(True):p=e.simulate(model,window(t,lambda _: ({},{})),params)
            s=e.score_rollout(data,t,p,'FW_E');assert not s['invalid']
            guards[str(t)]=dict(score=s,ratio=s['objective']/established[str(seed)][str(t)]['objective'])
        arms={};audits={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=window(start,command)
            reference=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
            with ordinary_equilibrium(False):p=e.simulate(model,w,params)
            assert json.loads(json.dumps(p))==reference;exact+=1
            with ordinary_equilibrium(True) as audit:p=e.simulate(model,w,params)
            assert len(audit)==135
            for key in ['cells','flows']:
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            for r in p['diagnostics']['roads']:
                assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
            for r in p['ports']:assert abs(r['conservation_residual_veh'])<1e-7
            for r in p['ramps']:assert abs(r['conservation_residual_veh'])<1e-7
            forecasts+=1;arms[arm]=parts(p)
            r8=[r for r in audit if r['cell']==8]
            audits[arm]=dict(binding_steps=sum(r['binding'] for r in r8),
                vehicle_weighted_speed=sum(r['n']*r['v'] for r in r8)/sum(r['n'] for r in r8),
                changed_desired_calls=sum(abs(r['new_equilibrium']-r['old_equilibrium'])>1e-9 for r in audit))
            e.save(out/f'prediction_s{seed}_{arm}.json',p);e.save(out/f'trace_s{seed}_{arm}.json',audit)
        deltas={arm:{k:v-arms['none'][k] for k,v in row.items()} for arm,row in arms.items() if arm!='none'}
        for row in deltas.values():row['total']=sum(row.values())
        results[str(seed)]=dict(guards=guards,guards_passed=sum(r['ratio']<=1.1 for r in guards.values()),
            arms=arms,deltas=deltas,audits=audits)
        print(seed,'guards',results[str(seed)]['guards_passed'],'deltas',deltas,'audit',audits,flush=True)
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,reference_exact=exact,candidate_forecasts=forecasts,
        source_pins_verified=True,production_adopted=False,qualified=False))


if __name__=='__main__':main()
