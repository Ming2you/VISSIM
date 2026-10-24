"""Derivative preflight and independent saved-update/gain verification."""
import math
import sys
from types import SimpleNamespace
from .probe import HERE, fd_local, local_speed
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h


def preflight():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    context, _, _ = common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import VSLExposure, _literature_speed
    model = lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')['component']
    cfg = model._config('FW_E', context['parameters']['by_direction']['FW_E'])
    net = cfg.network
    exposure = VSLExposure([10.]*31, dict(sign_cells=[14,16,26,28], initial_command=110., ramp_command=110.), 110.)
    tests = 0
    maximum = 0.
    target_error = 0.
    for cell in range(20,26):
        row = net.freeway_segment_params['FW_E'][cell]
        spec = net.freeway_vsl_fd_response['FW_E']
        def canonical(rho, command):
            if command < 109.5:
                return _literature_speed(spec,cfg,'FW_E',cell,rho,command)
            return row['v_free']*math.exp(-(rho/row['rho_crit'])**row['metanet_a_m']/row['metanet_a_m'])
        for cohort in ({110.:10.},{90.:10.},{110.:4.,90.:6.},{50.:2.,70.:3.,100.:5.}):
            exposure.cohorts[cell] = cohort
            exposure.tangents[cell] = {c:0. for c in cohort}
            for rho in (0.,1.,5.,15.,30.,50.,90.,150.,180.):
                for command in (50.,90.,110.):
                    value, slope = fd_local(cfg,'FW_E',cell,rho,command,exposure)
                    expected = exposure.target(cfg,'FW_E',cell,rho,canonical(rho,command),command)
                    target_error = max(target_error,abs(value-expected))
                    if rho:
                        eps = 1e-4
                        def target_at(x):
                            return exposure.target(cfg,'FW_E',cell,x,canonical(x,command),command)
                        finite = (target_at(rho+eps)-target_at(rho-eps))/(2*eps)
                        maximum = max(maximum,abs(finite-slope))
                    assert slope <= 0
                    tests += 1
    assert maximum < 1e-7 and target_error < 1e-9
    # Known homogeneous cases: a uniform equilibrium stays fixed, while a
    # congested characteristic takes its speed information from downstream.
    net = SimpleNamespace(metanet_tau_h=10/3600,metanet_kappa_veh_km_lane=5.,rho_crit=30.,v_min=0.)
    toy = SimpleNamespace(network=net)
    ctx = dict(armed=True,p={},state_response={},response_rho_crit=30.)
    def call(speed,up,down,derivative):
        legacy = speed+(1/3600)/.2*speed*(up-speed)
        return local_speed(ctx,toy,30.,30.,speed,up,down,speed,derivative,0.,1/3600,.2,legacy)
    assert call(20.,20.,20.,-2.)[0] == 20.
    faster = call(20.,20.,60.,-2.)
    slower = call(20.,20.,0.,-2.)
    assert faster[0]>20 and slower[0]<20
    assert call(60.,40.,90.,0.)[0] < 60.
    result = dict(status='pass', derivative_cases=tests, derivative_max_error=maximum,
        canonical_target_max_error=target_error, homogeneous_equilibrium=True,
        signed_information_direction=True, fits=0)
    h.save(HERE/'preflight.json',result)
    print(result)


def results():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    context, _, _ = common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr
    model = lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')['component']
    v_min = model._config('FW_E',context['parameters']['by_direction']['FW_E']).network.v_min
    out = HERE/'forecast'
    assert h.read(out/'status.json') == dict(status='complete',forecasts=13)
    assert all(h.read(out/'old178_parity.json').values())
    rows = h.read(out/'rows.json')
    assessment = h.read(out/'assessment.json')
    checks = 0
    error = 0.
    max_weight = 0.
    max_courant = 0.
    signs = {'upstream':0,'downstream':0}
    cell_terms = {}
    def exact(a,b):
        nonlocal checks,error
        error=max(error,abs(a-b));checks+=1
        assert abs(a-b)<1e-8,(a,b)
    for r in (r for r in rows if r['mode']=='characteristic' and r['horizon']==450):
        doc = h.read(out/'characteristic'/(r['case']+'_'+r['arm']+'_transport.json.gz'))
        assert len(doc['rows']) == 8100
        for z in doc['rows']:
            lam = z['speed']+z['rho']*z['derivative']
            exact(lam,z['characteristic_kmh'])
            c = z['dt_h']*abs(lam)/z['length_km']
            a = z['dt_h']/z['tau_h']
            neighbor = z['up_speed'] if lam>=0 else z['down_speed']
            # Independent convex-weight form, not the update's delta form.
            value = (1-a-c)*z['speed']+a*z['target']+c*neighbor
            value = max(v_min,max(v_min,value)-z['physical_lane_drop'])
            exact(value,z['before_merge'])
            value -= z['merge_delta']*z['merge_veh']*z['old_speed']/(z['length_km']*(z['rho']+z['merge_kappa']))
            if z['off_requested']>z['off_sent']+1e-9 and z['stock']:
                value=min(value,(z['through']+z['off_sent'])*z['length_km']/(z['dt_h']*z['stock']))
            exact(max(v_min,value),z['final'])
            max_weight=max(max_weight,a+c);max_courant=max(max_courant,c)
            signs['upstream' if lam>=0 else 'downstream']+=1
            key=f"{r['case']}/{r['arm']}/{z['cell']}"
            accum=cell_terms.setdefault(key,dict(n=0,relaxation=0.,legacy_pressure=0.,legacy_convection=0.,transport=0.))
            accum['n']+=1
            for term in ('relaxation','legacy_pressure','legacy_convection','transport'):
                accum[term]+=z[term]
    assert max_weight<=1+1e-12
    gates={};regrets={};contrasts=[]
    for horizon in (150,450):
        loss={mode:h.losses([r for r in rows if r['mode']==mode and r['horizon']==horizon],[]) for mode in ('baseline','characteristic')}
        assert loss==assessment['losses'][str(horizon)]
        old,new=loss['baseline'],loss['characteristic']
        regrets[str(horizon)]=[]
        for case in sorted({r['case'] for r in rows}):
            arms=[r for r in rows if r['horizon']==horizon and r['case']==case and r['mode']=='characteristic']
            chosen=min(arms,key=lambda r:r['predicted']['ttt'])
            regrets[str(horizon)].append(dict(case=case,chosen=chosen['arm'],actual_regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in arms)))
        gates[str(horizon)]=dict(meaningful_signs=all(p['sign_correct'] for p in new['pairs'] if p['meaningful']),
            response=new['response']<=.9*old['response'],absolute=new['absolute']<=1.1*old['absolute'],
            regret=all(z['actual_regret']<=.5 for z in regrets[str(horizon)]))
        for p,q in zip(old['pairs'],new['pairs']):
            assert (p['case'],p['left'],p['right'])==(q['case'],q['left'],q['right'])
            contrasts.append(dict(horizon=horizon,case=p['case'],left=p['left'],right=p['right'],
                actual=p['actual']['ttt'],baseline=p['predicted']['ttt'],candidate=q['predicted']['ttt']))
    proto=h.read(HERE/'protocol.json')
    pins=h.read(out/'preservation.json')['input_sha256']
    for p,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():
        assert h.sha(p)==d,p
    result=dict(status='pass',checks=checks,max_error=error,max_courant=max_courant,max_convex_weight=max_weight,
        characteristic_directions=signs,v_min=v_min,disabled_four_table_exact=True,protected_STOP_preserved=True,
        gates=gates,regrets=regrets)
    h.save(HERE/'verification.json',result)
    h.save(HERE/'contrasts.json',contrasts)
    h.save(HERE/'cell_terms.json',cell_terms)
    passed=all(all(v.values()) for v in gates.values())
    h.save(HERE/'completion.json',dict(status='complete',forecasts450=13,seconds=assessment['seconds'],
        result='SCREEN_PASSED_ONLY' if passed else 'REJECTED',production_adopted=False,
        fits=0,native=0,FZP=0,push=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print(result)
    print('CONTRAST67', [z for z in contrasts if z['horizon']==450 and z['case']=='s67_late'])


def local_diagnostic():
    """Reuse saved forecasts and small observation tables; no trajectories reread."""
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    _, _, Obs = common.setup()
    out=HERE/'forecast';summary=[]
    for record in common.records(False):
        if record['arm'] not in ('release','release_vsl90'):
            continue
        key=record['case']+'_'+record['arm'];start=record['cutoff']
        obs=Obs(record['truth'])
        traces=h.read(out/'characteristic'/(key+'_transport.json.gz'))['rows']
        for mode in ('baseline','characteristic'):
            pred=h.read(out/mode/(key+'.json.gz'))
            for period in range(3):
                lo,hi=start+150*period,start+150*(period+1)
                for cell in range(20,26):
                    pairs=[]
                    for p in pred['cells']:
                        if p['cell']==cell and lo+1e-6<p['time_s']<=hi+1e-6:
                            a=next(x for x in obs.cells[round(p['time_s'],6)] if x['road']=='FW_E' and x['cell']==cell)
                            pairs.append((p,a))
                    assert len(pairs)==5 and all(a['v_kmh'] is not None for p,a in pairs)
                    flows=[p for p in pred['flows'] if p['cell']==cell and lo+1e-6<p['window_end_s']<=hi+1e-6]
                    native=[obs.flows[round(p['window_end_s'],6),'FW_E',cell] for p in flows]
                    row=dict(arm=record['arm'],mode=mode,cell=cell,period=period,
                        speed_snapshot_mean=sum(p['v_kmh'] for p,a in pairs)/5,
                        actual_speed_snapshot_mean=sum(a['v_kmh'] for p,a in pairs)/5,
                        end_n=pairs[-1][0]['n_veh'],actual_end_n=pairs[-1][1]['n_veh'],
                        downstream=sum(p['downstream_crossings'] for p in flows),
                        actual_downstream=sum(float(a['downstream_crossings']) for a in native),
                        off=sum(p['off_departures'] for p in flows),
                        actual_off=sum(float(a['off_departures']) for a in native))
                    if mode=='characteristic':
                        local=[z for z in traces if z['cell']==cell and lo-1e-6<=z['time_s']<hi-1e-6]
                        assert len(local)==450
                        row['downstream_information_fraction']=sum(z['characteristic_kmh']<0 for z in local)/450
                        for name in ('target','speed','relaxation','transport','legacy_convection','legacy_pressure'):
                            row[name+'_mean']=sum(z[name] for z in local)/450
                    summary.append(row)
    h.save(HERE/'local_diagnostic.json',dict(
        definition='5 equal-time30s snapshots per150s for speed; actual native windows for flows. Legacy terms recomputed at candidate states, NOT baseline trajectory effects.',rows=summary))
    print([r for r in summary if r['period']==1 and r['cell'] in (20,21,24)])


if __name__=='__main__':
    if '--preflight' in sys.argv:preflight()
    elif '--local' in sys.argv:local_diagnostic()
    else:results()
