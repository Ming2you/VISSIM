"""Read-only speed-law audit for flowing lanes beside off-ramp blockage.

Reconstruct consumed terms, and compare the FD to measured current lane states.
No gain fitting, model changes or future input to the conserved forecasts.
"""
from pathlib import Path
import sys, math, json, hashlib, statistics, inspect
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
import canonical_harness as ch

HERE=Path(__file__).resolve().parent


@contextmanager
def trace_speed():
    mn=ch.accounting._mn;original=mn.metanet_speed_update_kmh;rows=[]
    def speed(*args,**kwargs):
        frame=inspect.currentframe().f_back
        selected=(frame.f_code.co_name=='advance' and
                  Path(frame.f_code.co_filename).resolve()==e.ROOT/'evaluation/controllers/physical_lane_groups.py' and
                  frame.f_locals['road']=='FW_E' and frame.f_locals['i'] in (7,8,9))
        if selected:
            local=frame.f_locals;net=local['net'];i=local['i'];g=local['g']
            v,up,rho,down,veq,dt,length,tau,nu,kappa,vmin=args
            p=dict(net.freeway_segment_params['FW_E'][i])
            assert not getattr(net,'vsl_fd_two_branch',False)
            assert not getattr(net,'freeway_state_response',{})
            assert net.freeway_lane_drop_phi==0
            tau=p.get('metanet_tau_h',tau);length=p.get('segment_length_km',length)
            kappa=p.get('metanet_kappa_veh_km_lane',kappa)
            vf=p.get('v_free',net.v_free);critical=p.get('rho_crit',net.rho_crit);a=p.get('metanet_a_m',net.metanet_a_m)
            uncapped=vf*math.exp(-((rho/critical)**a)/a)
            cap=(1+net.alpha_vsl)*float(local['vsl'])
            assert abs(veq-(min(uncapped,cap) if local['active'] else uncapped))<1e-9
            terms=dict(relaxation=dt/tau*(veq-v),convection=dt/length*v*(up-v),
                       anticipation=-nu*dt/tau/length*(down-rho)/(rho+kappa))
            row=dict(time_s=local['state'].time_sec,cell=i,group=g,n=local['before'][i][g],start_v=local['oldv'][i][g],
                rho=rho,v=v,upstream_speed=up,downstream_rho=down,uncapped_equilibrium=uncapped,
                applied_equilibrium=veq,vsl=float(local['vsl']),active=local['active'],
                binding=local['active'] and uncapped>cap+1e-9,
                fifo=local['fifo'][i][g],fd=dict(vf=vf,critical=critical,a=a,length=length),terms=terms)
        del frame
        value=original(*args,**kwargs)
        if selected:
            assert abs(value-max(vmin,v+sum(terms.values())))<1e-8
            row['speed_before_merge_fifo']=value;rows.append(row)
        return value
    mn.metanet_speed_update_kmh=speed
    try:yield rows
    finally:mn.metanet_speed_update_kmh=original


def main():
    out=HERE/'lane_speed_terms_v2';out.mkdir(exist_ok=False)
    config=HERE/'port_origin_split_v1/config.json';param=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(param)['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),config,param,MODEL/'port_profile.json',e.CAL/'canonical_harness.py',
           e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
           e.ROOT/'evaluation/controllers/freeway_fd.py',e.ROOT/e.load(config)['freeway']['segment_params']]
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    results={};exact=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        for arm in ('none','vsl'):
            model=e.load_base_model(data.geometry,config);original=model._config
            def configured(road,p):
                c=original(road,p)
                if road=='FW_E':c.network.terminal_zero_gradient=True
                return c
            model._config=configured
            seq=protocol['candidate_bank'].get(arm,dict(vsl=[]))
            def command(t):return ({},{d:seq['vsl'][int((t-start)//150)] for d in protocol['dsd_ids']} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origins['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                'initial_ramp_origin':origins['counts'][str(start)],'initial_off_eligible':origins['eligible_before_off'][str(start)]}}
            with trace_speed() as trace:pred=e.simulate(model,w,params)
            reference=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
            assert json.loads(json.dumps(pred))==reference;exact+=1
            assert len(trace)==405
            native={(int(r['time_s']),int(r['cell']),int(r['group'])):r
                    for r in e.rows(HERE/f'lane_blocking_audit_v1/s{seed}_{arm}_groups.csv')}
            summary={}
            for g in range(3):
                rows=[r for r in trace if r['cell']==8 and r['group']==g]
                for r in rows:
                    obs=native[int(r['time_s']),8,g];n=int(obs['n']);v=float(obs['v']) if n else None
                    p=r['fd'];rho=n/(p['length']*lane['geometry']['widths'][8][g])
                    eq=p['vf']*math.exp(-((rho/p['critical'])**p['a'])/p['a'])
                    r['native_state']=dict(n=n,v=v,rho=rho,uncapped_equilibrium=eq)
                s=dict(steps=len(rows),binding_steps=sum(r['binding'] for r in rows),
                    mean_terms={key:statistics.mean(r['terms'][key] for r in rows) for key in ('relaxation','convection','anticipation')},
                    modeled_mean_density=statistics.mean(r['rho'] for r in rows),
                    native_mean_density=statistics.mean(r['native_state']['rho'] for r in rows),
                    modeled_vehicle_weighted_speed=sum(r['n']*r['start_v'] for r in rows)/sum(r['n'] for r in rows),
                    mean_pre_speed_update_shift=statistics.mean(r['v']-r['start_v'] for r in rows),
                    modeled_mean_uncapped_equilibrium=statistics.mean(r['uncapped_equilibrium'] for r in rows),
                    native_vehicle_weighted_speed=sum(r['native_state']['n']*(r['native_state']['v'] or 0) for r in rows)/sum(r['native_state']['n'] for r in rows),
                    equilibrium_at_native_mean=statistics.mean(r['native_state']['uncapped_equilibrium'] for r in rows),
                    native_above100_steps=sum((r['native_state']['v'] or 0)>100 for r in rows),
                    fd_at_native_above100_steps=sum(r['native_state']['uncapped_equilibrium']>100 for r in rows))
                summary[str(g)]=s
            e.save(out/f's{seed}_{arm}_trace.json',trace);results[f'{seed}_{arm}']=summary
            print(seed,arm,'free lanes3/4',summary['2'],flush=True)
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,pins=pins,full_prediction_json_exact=exact,
        reconstructed_speed_updates=exact*405,core_changed=False,new_native_runs=0,production_adopted=False,
        scope='Read-only runtime speed-law audit; FD at future native states is retrospective comparison only, not rollout input or proof of equilibrium.'))


if __name__=='__main__':main()
