"""Frozen-environment 5x1s local20/21 reactions; no traffic rollout or fitting."""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'protocol.json').exists(), 'Preserve any earlier attempt'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr, area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients
    from src.models.state import ControlAction

    protected = h.read(h.R / 'recurrent_node159/protocol.json')
    pins = {str(Path(__file__)): h.sha(__file__)}

    def read(path):
        pins[str(path)] = h.sha(path)
        return h.read(path)

    h.save(HERE / 'protocol.json', dict(
        previous_goal_turn='PROGRESS:159 verified coupled request20/receiving21 response loss;158 rejected.',
        purpose='Separate intrinsic local speed-response error from predicted neighbor-state error during renewed congestion.',
        prior_checked=['Claude P_PLANT term/FIFO audit', '134 native one-second terms/population ledgers',
                       '138 five-second cell22 probe', '150 corrected148 speed trace', '151 cell19 local operator',
                       '155 rejected4axis fit', '157 target feedback', '158 frozen combination', '159 coupled-state attribution'],
        budget=dict(cells=[20,21], lanes=[1], models=['148','158'],
                    contexts=['native_neighbors','predicted_neighbors'], max_five_second_probes=672,
                    fits=0, full_rollouts=0, native=0, FZP=0),
        domain='Seed67 RM release110,2700.1..3120.1; nativeVSL90 not used as nominal90 because exposure history must be respected.',
        operator='Start each probe at observed ownN/v, hold own density/class split and neighbor inputs for5s, update only local speed using five canonical1s calls. Compare native-current vs saved-model-current neighbors.',
        exit_feedback='Same shared21 receiving and actual5s merge/5; branch storage inactive in scored window.148 caps final speed;158 caps relaxation target. Class requests change with local speed during probe.',
        limits=['This local ODE probe does not advance vehicle counts, positions, lane exchange or neighbors; not a conservative traffic prediction.',
                'Observed5s accepted merges are future information relative to the probe start, used only to condition this diagnostic. Their within5s phase is unknown.',
                'Changing populations also change native mean speed. Following native mean is a scoring label, not an individual driver acceleration.',
                'Predicted-neighbor hybrids need not correspond to a jointly feasible state; not causal effects.',
                'No independent holdout, new coefficient or model adoption.'],
        protected_sha256=protected['protected_sha256'], STOP=protected['STOP']))
    h.save(HERE / 'status.json', dict(status='running'))
    context, _, _ = common.setup()
    mn = area._mn
    control = ControlAction(vsl={'FW_E':110})
    document = read(h.F / 'flow67/release_frames.json.gz')
    fields = document['fields']
    frames = {round(float(t),6):[dict(zip(fields,row)) for row in frame.values()]
              for t,frame in document['frames'].items()}
    mapping = read(h.F / 'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    midpoint19 = (mapping[19] + mapping[20]) / 2.
    native_exit = {round(r['start'],6):r for r in read(h.R / 'exit_sending131/attempt2/steps.json') if r['case']=='release'}
    native_receiving = {round(r['lo'],6):r for r in read(h.R / 'receiving_lane152/steps.json') if r['arm']=='release' and r['lane']==1}
    composition = {(round(r['time_s'],6),r['cell']):r for r in read(h.R / 'onset_reaction134/rows.json.gz')
                   if r['case']=='s67_late' and r['arm']=='release' and r['lane']==1}
    model_paths = [('148','spatial_context148',h.R/'lane_state132/eval_01/manifest.json'),
                   ('158','coupled_recovery158',h.R/'coupled_recovery153/candidate/manifest.json')]
    speed_context = mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX']
    state_context = mn.metanet_speed_update_kmh.__globals__['_FW_SEG_CTX_STATE']
    saved_context, saved_state = copy.deepcopy(speed_context), copy.deepcopy(state_context)
    rows, skipped = [], []
    canonical_calls = 0
    max_error = 0.
    try:
        state_context['profile'] = None
        for label,folder,manifest in model_paths:
            m = read(manifest)
            config_path = h.ROOT / m['sources']['reference_config']['path']
            read(config_path)
            assert h.sha(config_path) == m['sources']['reference_config']['sha256']
            cfg = lpr.load_sources(manifest)['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
            net = cfg.network
            pred = read(h.R/folder/'forecast/training/s67_late_release.json.gz')
            diag = pred['diagnostics']['roads'][0]['joint_lane_region']
            model_lanes = {(round(r['time_s'],6),r['cell']):r for r in diag['rows'] if r['lane']==1}
            model_half = {round(r['time_s'],6):r for r in read(h.R/folder/'forecast/training/s67_late_release_spatial.json.gz')
                          if r['lane']==1 and r['part']==1}
            model_supply = {round(r['time_s'],6):r['accepted_budget_veh'] for r in diag['receiving_rows'] if r['lane']==1}
            for j in diag['junction_rows']:
                if 2700.1-1e-6 <= j['time_s'] < 3120.1-1e-6:
                    assert abs(j['off_request_veh']-j['off_before_veh'])<1e-9
            for t in sorted(native_exit):
                assert 2700.1-1e-6 <= t < 3120.1-1e-6
                now, future = frames[t], frames[round(t+5,6)]
                for cell in (20,21):
                    own = [r for r in now if r['cell']==cell and r['lane']==1]
                    final = [r for r in future if r['cell']==cell and r['lane']==1]
                    up = [r for r in now if r['cell']==cell-1 and r['lane']==1 and (cell!=20 or r['x_m']>=midpoint19)]
                    down = [r for r in now if r['cell']==cell+1 and r['lane']==1]
                    if not own or not final or not up:
                        skipped.append(dict(model=label,time_s=t,cell=cell,n=len(own),final_n=len(final),up_n=len(up)))
                        continue
                    p = net.freeway_segment_params['FW_E'][cell]
                    pd = net.freeway_segment_params['FW_E'][cell+1]
                    n = len(own);rho = n/p['segment_length_km']
                    v0 = sum(r['speed_kmh'] for r in own)/n
                    v1 = sum(r['speed_kmh'] for r in final)/len(final)
                    e = native_exit[t]
                    if cell==20:
                        assert n==e['native_lane_n'] and abs(v0-e['native_lane_v'])<1e-9
                    spec = cell_state_response(net,'FW_E',cell)
                    merge = native_receiving[t]['physical_merge']/5.
                    for environment in ('native_neighbors','predicted_neighbors'):
                        if environment=='native_neighbors':
                            up_speed = sum(r['speed_kmh'] for r in up)/len(up)
                            downstream = len(down)/pd['segment_length_km']
                            supply = native_receiving[t]['supply_left5']/5.
                        else:
                            up_speed = model_half[t]['v_kmh'] if cell==20 else model_lanes[t,20]['v_kmh']
                            downstream = model_lanes[t,cell+1]['n_veh']/pd['segment_length_km']
                            supply = model_supply[t]
                        trajectory, terms = [v0], []
                        for _ in range(5):
                            v = trajectory[-1]
                            command = mn.segment_vsl(control,'FW_E',cell,cfg)
                            target = mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,command,net.alpha_vsl,
                                False,net.metanet_a_m,False,net.rho_max,0.)
                            base_target = target
                            cap = None
                            if cell==20 and e['n0']>0:
                                through = (n-e['n0'])*v/(p['segment_length_km']*3600.)
                                factor = min(1.,max(0.,supply-merge)/through) if through>1e-12 else 1.
                                if factor < 1.-1e-9:
                                    cap = v*factor
                            if label=='158' and cap is not None:
                                target = min(target,max(net.v_min,cap))
                            nu0 = mn.select_anticipation_nu(rho,net,command)
                            tau,nu = state_response_coefficients(spec,v,target,rho,downstream,p['rho_crit'],p['metanet_tau_h'],nu0)
                            relaxation = (target-v)/(tau*3600.)
                            convection = v*(up_speed-v)/(p['segment_length_km']*3600.)
                            anticipation = -nu*(downstream-rho)/(tau*p['segment_length_km']*3600.*(rho+p['metanet_kappa_veh_km_lane']))
                            raw = v+relaxation+convection+anticipation
                            velocity = mn.metanet_speed_update_kmh(v,up_speed,rho,downstream,target,1/3600.,p['segment_length_km'],
                                p['metanet_tau_h'],nu0,p['metanet_kappa_veh_km_lane'],net.v_min)
                            err = abs(velocity-max(net.v_min,raw));max_error=max(max_error,err)
                            assert err<1e-8
                            canonical_calls += 1
                            merge_loss = spec.get('delta_merge',net.metanet_delta_merge)*merge*v/(p['segment_length_km']*(rho+p['metanet_kappa_veh_km_lane'])) if cell==21 else 0.
                            after_merge = velocity-merge_loss
                            final_v = min(after_merge,cap) if label=='148' and cap is not None else after_merge
                            final_v = max(net.v_min,final_v)
                            terms.append(dict(relaxation=relaxation,convection=convection,anticipation=anticipation,
                                first_floor=max(net.v_min,raw)-raw,merge_loss=-merge_loss,
                                exit_and_last_floor=final_v-after_merge,base_target=base_target,target=target,
                                cap=cap,tau_sec=tau*3600.,nu=nu))
                            assert abs(sum(terms[-1][k] for k in ('relaxation','convection','anticipation','first_floor','merge_loss','exit_and_last_floor'))-(final_v-v))<1e-8
                            trajectory.append(final_v)
                        comp = composition[t,cell]
                        rows.append(dict(model=label,environment=environment,time_s=t,cell=cell,lane=1,
                            n=n,rho=rho,downstream_rho=downstream,downstream_ge=downstream>=rho,
                            upstream_speed=up_speed,receiving21=supply,observed_merge_per_sec=merge,
                            v0=v0,v1=v1,trajectory=trajectory,terms=terms,
                            observed_rate=(v1-v0)/5.,predicted_rate=(trajectory[-1]-v0)/5.,
                            observed_acceleration=comp['instantaneous_mean_acceleration'],
                            observed_stayer_contribution=comp['parts']['stayer']))
    finally:
        speed_context.clear();speed_context.update(saved_context)
        state_context.clear();state_context.update(saved_state)
    assert len(rows)<=672 and canonical_calls==len(rows)*5
    summaries=[]
    for label,_,_ in model_paths:
        for cell in (20,21):
            for environment in ('native_neighbors','predicted_neighbors'):
                for lo,hi in ((2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                    for regime in ('all','downstream_ge','downstream_lt'):
                        z=[r for r in rows if r['model']==label and r['cell']==cell and r['environment']==environment
                           and lo-1e-6<=r['time_s']<hi-1e-6 and (regime=='all' or r['downstream_ge']==(regime=='downstream_ge'))]
                        if not z:continue
                        summaries.append(dict(model=label,cell=cell,environment=environment,lo=lo,hi=hi,regime=regime,samples=len(z),
                            observed_rate=sum(r['observed_rate'] for r in z)/len(z),predicted_rate=sum(r['predicted_rate'] for r in z)/len(z),
                            endpoint_rmse=math.sqrt(sum((r['trajectory'][-1]-r['v1'])**2 for r in z)/len(z)),
                            initial_below_model_floor=sum(r['v0']<5 for r in z),
                            terms={k:sum(s[k] for r in z for s in r['terms'])/(5*len(z)) for k in
                                   ('relaxation','convection','anticipation','first_floor','merge_loss','exit_and_last_floor')}))
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    h.save(HERE/'rows.json',rows);h.save(HERE/'summary.json',summaries);h.save(HERE/'skipped.json',skipped)
    h.save(HERE/'verification.json',dict(canonical_calls=canonical_calls,term_max_error=max_error,probes=len(rows),
        input_sha256=pins,core=True,STOP=True,hooks_restored=True,new_rollouts=0,new_fits=0,new_native=0,new_FZP=0))
    h.save(HERE/'status.json',dict(status='complete_conditional_only',goal='ACTIVE_NOT_QUALIFIED',production_adopted=False))
    for r in summaries:
        if r['regime']=='all' and abs(r['lo']-2820.1)<1e-6:print(r)


if __name__=='__main__':
    main()
