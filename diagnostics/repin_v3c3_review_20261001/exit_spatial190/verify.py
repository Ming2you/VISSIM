"""Verify cell20 physical half lengths, per-call parameters and saved ledgers."""
import ast
import copy
import math
from pathlib import Path
from types import SimpleNamespace as NS
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def preflight():
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    from evaluation.controllers import physical_lane_groups as lanes,area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    from src.models.state import ControlAction
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    source=h.read(HERE/'executed_function_sources.json')
    ns={};exec(compile(source['RouteLaneRegion'],'190_candidate','exec'),lanes.__dict__,ns)
    cls=ns['RouteLaneRegion'];obj=cls.__new__(cls)
    obj.road='FW_E';obj.groups=3;net=cfg.network;mn=area._mn
    p=net.freeway_segment_params['FW_E'][20];half=p['segment_length_km']/2
    obj.lengths=[z['segment_length_km'] for z in net.freeway_segment_params['FW_E']]
    obj.split20_n0=[[rho*half for rho in (20.,30.,40.)],[rho*half for rho in (25.,35.,45.)]]
    obj.split20_oldv=[[20.,40.,60.],[25.,45.,65.]];obj.split20_exchange_v=copy.deepcopy(obj.split20_oldv)
    obj.split20_next=[[{'test':n} for n in row] for row in obj.split20_n0]
    obj.split19_oldv=[[30.,40.,50.],[35.,45.,55.]]
    obj.n0={21:[rho*obj.lengths[21] for rho in (20.,25.,30.)]};obj.next_v={}
    obj.off_requests={};obj.off_sent={};obj.off_access={'10483':0}
    target=mn.effective_desired_speed_kmh;update=mn.metanet_speed_update_kmh
    ctx=update.__globals__['_FW_SEG_CTX'];original_ctx=copy.deepcopy(ctx);calls=[]
    def observe(*a,**kw):
        call=dict(context=copy.deepcopy(ctx),args=list(a));call['value']=update(*a,**kw);calls.append(call);return call['value']
    try:
        mn.metanet_speed_update_kmh=observe
        obj._split20_speed(NS(),cfg,ControlAction(vsl={'FW_E':max(cfg.freeway_follower.vsl_set)}),mn,None)
    finally:
        mn.metanet_speed_update_kmh=update;ctx.clear();ctx.update(original_ctx)
    assert len(calls)==6
    response=cell_state_response(net,'FW_E',20);errors=[]
    for part in (0,1):
        for g in range(3):
            rho=obj.split20_n0[part][g]/half;v=obj.split20_oldv[part][g]
            down=obj.split20_n0[1][g]/half if part==0 else obj.n0[21][g]/obj.lengths[21]
            up=obj.split19_oldv[1][g] if part==0 else obj.split20_oldv[0][g]
            desired=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            tau,nu=state_response_coefficients(response,v,desired,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
            dt=cfg.simulation.T_f_h
            expected=max(net.v_min,v+dt/tau*(desired-v)+dt/half*v*(up-v)-nu*dt/(tau*half)*(down-rho)/(rho+p['metanet_kappa_veh_km_lane']))
            actual=calls[part*3+g]
            assert actual['context']['armed'] and actual['context']['p']['segment_length_km']==half
            errors.append(abs(actual['value']-expected));assert errors[-1]<1e-9
    # Empty downstream storage, full receiving storage, and CFL rejection are
    # exercised in the actual candidate internal movement helper.
    obj.split20_max_courant=0.
    obj.split20_v=[[40.]*3,[60.]*3]
    obj.split20=[[{'a|10483':4.,'b|end':2.} for _ in range(3)],[{} for _ in range(3)]]
    obj._split20_plan(cfg)
    expected=6*40*dt/half
    assert all(abs(sum(z.values())-expected)<1e-10 for z in obj.split20_inner)
    obj.split20[1]=[{'x|end':net.rho_max*half} for _ in range(3)]
    obj._split20_plan(cfg);assert all(sum(z.values())==0. for z in obj.split20_inner)
    obj.split20_v[0][0]=half/dt*1.01
    try:obj._split20_plan(cfg)
    except ArithmeticError:pass
    else:raise AssertionError('Invalid CFL accepted')
    before=ast.parse((HERE/'runner_before190.py.txt').read_text(encoding='utf8'))
    after=ast.parse((h.R/'state_lateral168/run.py').read_text(encoding='utf8'))
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert all(a[k]==b[k] for k in a if k!='queue178')
    proto=h.read(HERE/'protocol.json')
    for f,d in {**h.read(HERE/'pins.json'),**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(f)==d,f
    h.save(HERE/'unit_traces.json',calls)
    h.save(HERE/'preflight.json',dict(status='pass',actual_speed_calls=6,all_contexts_armed=True,half_length_km=half,
        manual_speed_max_error=max(errors),internal_transport_fixture=True,CFL_guard=True,prior_runner_functions_preserved=True))
    print(h.read(HERE/'preflight.json'))


def completed():
    work=HERE/'attempt2';out=work/'forecast';proto=h.read(work/'protocol.json')
    assert h.read(out/'status.json')=={'status':'complete','forecasts':13}
    assert all(h.read(out/'old178_parity.json').values())
    old=h.read(HERE/'executed_function_sources.json');new=h.read(work/'executed_function_sources.json')
    assert old['RouteLaneRegion']==new['RouteLaneRegion']
    checks=0;maximum=0.;max_courant=0.;profiles=[]
    pins=dict(h.read(out/'preservation.json')['input_sha256'])
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    def exact(a,b):
        nonlocal checks,maximum
        e=abs(a-b);assert e<1e-7,(a,b,e)
        checks+=1;maximum=max(maximum,e)
    mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    offsets=dict(zip(mapping['chain_links'],mapping['chain_offsets_m']));bounds=mapping['segment_bounds_m']
    mid=(bounds[20]+bounds[21])/2;half=(bounds[21]-bounds[20])/2000
    rows=read(out/'rows.json')
    for r in [r for r in rows if r['mode']=='spatial' and r['horizon']==450]:
        key=r['case']+'_'+r['arm'];d=read(out/'spatial'/(key+'_spatial.json.gz'));pred=read(out/'spatial'/(key+'.json.gz'))
        raw=read(h.F/'route_inventory'/('initial_raw.json' if r['case']=='s29_late' else r['case']+'/initial_raw.json'))
        native=[[[] for _ in range(3)] for _ in (0,1)]
        for z in raw['vehicle_records']['records']:
            if z['link_no'] not in offsets:continue
            x=offsets[z['link_no']]+z['position_m']
            if bounds[20]<=x<bounds[21]:native[int(x>=mid)][z['lane_index']-1].append(z['speed_kph'])
        previous={}
        for p in (0,1):
            for g in range(3):
                n=sum(d['initial']['stocks'][p][g].values());v=d['initial']['speeds'][p][g]
                exact(n,len(native[p][g]))
                if n:exact(v,sum(native[p][g])/n)
                previous[p,g+1]=(n,v)
        assert len(d['parts'])==2700
        parts={}
        for z in d['parts']:parts.setdefault(z['time_s'],[]).append(z)
        lane={(round(z['time_s'],6),z['cell'],z['lane']):z for z in d['lanes']}
        junction={round(z['time_s']+1,6):z for z in d['junction']}
        for t,zs in sorted(parts.items()):
            assert len(zs)==6
            for z in zs:
                p,g=z['part'],z['lane'];n,v=previous[p,g]
                assert z['n_veh']>=-1e-8 and z['n_veh']<=180*half+1e-7
                assert math.isfinite(z['v_kmh']) and z['v_kmh']>=0
                c=v/3600/half;assert c<=1+1e-9;max_courant=max(max_courant,c)
            inner=sum(z['internal_veh'] for z in zs if z['part']==0)
            ends=[sum(z['n_veh'] for z in zs if z['part']==p) for p in (0,1)]
            starts=[sum(previous[p,g][0] for g in (1,2,3)) for p in (0,1)]
            incoming=sum(lane[round(t,6),20,g]['mainline_in_veh'] for g in (1,2,3))
            outgoing=sum(lane[round(t,6),20,g]['mainline_out_veh'] for g in (1,2,3))
            off=junction[round(t,6)]['off_accepted_veh']
            exact(ends[0]-starts[0],incoming-inner)
            exact(ends[1]-starts[1],inner-outgoing-off)
            for g in (1,2,3):
                ps=[z for z in zs if z['lane']==g];n=sum(z['n_veh'] for z in ps);parent=lane[round(t,6),20,g]
                exact(n,parent['n_veh'])
                if n>1e-9:exact(sum(z['n_veh']*z['v_kmh'] for z in ps)/n,parent['v_kmh'])
                exact(ps[0]['internal_veh'],ps[1]['internal_veh'])
            previous={(z['part'],z['lane']):(z['n_veh'],z['v_kmh']) for z in zs}
        assert d['max_residual']<1e-7 and d['max_courant']<=1+1e-9
        if r['case']=='s67_late':
            observed=read(h.R/'blocking176'/f"{r['arm']}_frames.json.gz");ix={k:i for i,k in enumerate(observed['fields'])}
            pp={(round(z['time_s'],6),z['part'],z['lane']):z for z in d['parts']}
            for lo,hi in ((2670.1,2700.1),(2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                ts=[round(float(t),6) for t in observed['frames'] if lo<float(t)<=hi]
                for part in (0,1):
                    nobs=vobs=npred=vpred=0.
                    for t in ts:
                        fr=observed['frames'][str(t)]
                        ns=[z for z in fr.values() if z[ix['cell']]==20 and z[ix['lane']]==1 and int(z[ix['x']]>=mid)==part]
                        nobs+=len(ns);vobs+=sum(z[ix['speed']] for z in ns)
                        z=pp[t,part,1];npred+=z['n_veh'];vpred+=z['n_veh']*z['v_kmh']
                    profiles.append(dict(arm=r['arm'],window=[lo,hi],part=part,native_mean_n=nobs/len(ts),
                        predicted_mean_n=npred/len(ts),native_weighted_v=vobs/nobs if nobs else None,
                        predicted_weighted_v=vpred/npred if npred else None))
    assessment=read(out/'assessment.json');gates={};regrets={}
    for horizon in ('150','450'):
        a=assessment['losses'][horizon];b,p=a['baseline'],a['spatial']
        rs=[r for r in rows if r['horizon']==int(horizon) and r['mode']=='spatial'];regrets[horizon]=[]
        for case in sorted({r['case'] for r in rs}):
            cr=[r for r in rs if r['case']==case];chosen=min(cr,key=lambda r:r['predicted']['ttt'])
            regrets[horizon].append(dict(case=case,chosen=chosen['arm'],actual_regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in cr)))
        gates[horizon]=dict(meaningful_signs=all(z['sign_correct'] for z in p['pairs'] if z['meaningful']),
            response=p['response']<=.9*b['response'],absolute=p['absolute']<=1.1*b['absolute'],
            regret=all(z['actual_regret']<=.5 for z in regrets[horizon]))
    for path,digest in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(HERE/'verification.json',dict(status='pass',checks=checks,max_residual=maximum,max_courant=max_courant,
        disabled_four_tables_exact=True,half_initial_and_speed_moment=True,half_stock_conservation=True,
        protected_STOP_preserved=True,input_sha256=pins))
    h.save(HERE/'results.json',dict(status='complete',gates=gates,regrets=regrets,profiles=profiles,
        scope='East component; current190 change only20, no wholeOmega gain claim',adopted=False))
    h.save(HERE/'completion.json',dict(status='complete',result='REJECTED' if not all(gates['450'].values()) else 'SCREEN_PASSED_ONLY',
        completed450=14,valid_candidate450=12,first_failed_enabled_steps=1,valid_attempt_seconds=assessment['seconds'],
        fit=0,VISSIM=0,FZP=0,push=False,production_adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print(dict(gates=gates,checks=checks,max_residual=maximum,max_courant=max_courant))


if __name__=='__main__':
    import sys
    if '--completed' in sys.argv:completed()
    else:preflight()
