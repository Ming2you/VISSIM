"""One bounded cell20 congesting-pressure fit, from completed160 local probes."""
import collections
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'fit_protocol.json').exists()
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response,state_response_coefficients
    protected=h.read(h.R/'local_transition160/protocol.json')
    verification=h.read(h.R/'local_transition160/verification.json')
    assert h.read(h.R/'local_transition160/status.json')['status']=='complete_conditional_only'
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    for path,digest in verification['input_sha256'].items():assert h.sha(path)==digest,path
    rows=[r for r in read(h.R/'local_transition160/rows.json') if r['model']=='158' and r['cell']==20 and r['environment']=='native_neighbors']
    exits={round(r['start'],6):r for r in read(h.R/'exit_sending131/attempt2/steps.json') if r['case']=='release'}
    parent=h.R/'coupled_recovery153/candidate';manifest=read(parent/'manifest.json')
    config=read(parent/'reference_config.json');original=copy.deepcopy(config)
    context,_,_=common.setup()
    cfg=lpr.load_sources(parent/'manifest.json')['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    p=cfg.network.freeway_segment_params['FW_E'][20]
    original_spec=copy.deepcopy(cell_state_response(cfg.network,'FW_E',20));original_spec.pop('cell_overrides',None)
    before=original_spec['anticipation']['downstream_ge_local']
    h.save(HERE/'fit_protocol.json',dict(
        previous_goal_turn='PROGRESS:159 coupled-state diagnosis.160 completed native-neighbor5x1s probe;20 remains too strongly decelerating.',
        reason='158 native-neighbor middle150 actual mean rate-.589 vs predicted-4.231kmh/s;anticipation-5.324. Current20ge branch has not been the155 calibration axis.',
        parameter='Only physical20 anticipation.downstream_ge_local; all3lanes share the existing coefficient.',
        bounds=[.1,1.],prior_weight=.01,before=before,
        fitting='One bounded golden scalar fit,at most16objective evaluations,bracket tolerance.01;30s mean5s endpoint-rate residuals with>=4samples.',
        training='67 release110,2700.1..3120.1,20lane1 native-current local environment. Other lanes and other commands must be checked autonomously.',
        future_observation_limit='Observed5s merge count conditions the local identification problem,never passed to any450s forecast. Labels and current measured states are calibration data; local fit is not operational prediction.',
        fixed='Exact157 physical source and153 config except this one20ge coefficient; FD,tau,positive anticipation,othercells,merge,flow/receiving/storage/ramp/cost/exposure/commands unchanged.',
        budget=dict(scalar_fits=1,max_objective_evaluations=16,parity450=1,autonomous450=8,total450=9,new_native=0,FZP=0),
        gate='Original meaningful paired signs,10%response improvement,absolute<=110%148,choice<=.5;local discharge and conservation. No bounds expansion or second fit on failure;independent/fullOmega/SDMPC still required.',
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))

    def trajectory(row,z):
        spec=copy.deepcopy(original_spec);spec['anticipation']['downstream_ge_local']=before*z
        rho=row['rho'];down=row['downstream_rho'];up=row['upstream_speed'];n=row['n'];ne=exits[round(row['time_s'],6)]['n0']
        values=[row['v0']]
        for _ in range(5):
            v=values[-1];target=row['terms'][0]['base_target']
            through=(n-ne)*v/(p['segment_length_km']*3600.)
            factor=min(1.,max(0.,row['receiving21']-row['observed_merge_per_sec'])/through) if through>1e-12 else 1.
            if ne>0 and factor<1.-1e-9:target=min(target,max(cfg.network.v_min,v*factor))
            tau,nu=state_response_coefficients(spec,v,target,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
            v=max(cfg.network.v_min,v+(target-v)/(tau*3600.)+v*(up-v)/(p['segment_length_km']*3600.)
                  -nu*(down-rho)/(tau*p['segment_length_km']*3600.*(rho+p['metanet_kappa_veh_km_lane'])))
            values.append(v)
        return values

    error=max(abs(a-b) for row in rows for a,b in zip(trajectory(row,1.),row['trajectory']))
    assert error<1e-8,error
    blocks=collections.defaultdict(list)
    for row in rows:blocks[int(round((row['time_s']-2700.1)/5))//6].append(row)
    blocks={k:v for k,v in blocks.items() if len(v)>=4}
    assert len(blocks)>=10 and len(rows)>=70
    evaluations=[]
    def loss(z,record=True):
        residuals=[sum((trajectory(r,z)[-1]-r['v1'])/5. for r in rr)/len(rr) for rr in blocks.values()]
        value=sum(r*r for r in residuals)/len(residuals)+.01*(z-1.)**2
        if record:evaluations.append(dict(z=z,objective=value))
        return value
    left,right=.1,1.;ratio=(math.sqrt(5.)-1.)/2.
    a,b=right-ratio*(right-left),left+ratio*(right-left);fa,fb=loss(a),loss(b)
    while right-left>.01 and len(evaluations)<16:
        if fa<fb:right,b,fb=b,a,fa;a=right-ratio*(right-left);fa=loss(a)
        else:left,a,fa=a,b,fb;b=left+ratio*(right-left);fb=loss(b)
    assert right-left<=.01 and len(evaluations)<=16
    z=min(evaluations,key=lambda r:r['objective'])['z']
    overrides=config['freeway']['state_response']['FW_E']['cell_overrides']
    had='20' in overrides
    overrides.setdefault('20',{}).setdefault('anticipation',copy.deepcopy(original_spec['anticipation']))
    overrides['20']['anticipation']['downstream_ge_local']=before*z
    dest=HERE/'candidate';dest.mkdir();h.save(dest/'reference_config.json',config)
    manifest['sources']['reference_config']=dict(path=(dest/'reference_config.json').relative_to(h.ROOT).as_posix(),sha256=h.sha(dest/'reference_config.json'))
    manifest['qualification']='Unqualified161 scalar20ge fit.Requires exact157 physical source and autonomous validation;not production.'
    h.save(dest/'manifest.json',manifest)
    ccfg=lpr.load_sources(dest/'manifest.json')['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    assert ccfg.network.freeway_segment_params==cfg.network.freeway_segment_params
    for i in range(31):
        old=copy.deepcopy(cell_state_response(cfg.network,'FW_E',i));new=copy.deepcopy(cell_state_response(ccfg.network,'FW_E',i))
        old.pop('cell_overrides',None);new.pop('cell_overrides',None)
        if i==20:old['anticipation']['downstream_ge_local']=before*z
        assert old==new,i
    restored=copy.deepcopy(config)
    if had:restored['freeway']['state_response']['FW_E']['cell_overrides']['20']=original['freeway']['state_response']['FW_E']['cell_overrides']['20']
    else:del restored['freeway']['state_response']['FW_E']['cell_overrides']['20']
    assert restored==original
    for path,digest in {**pins,**protected['protected_sha256']}.items():assert h.sha(path)==digest,path
    assert h.sha(protected['STOP']['path'])==protected['STOP']['sha256']
    predictions=[dict(time_s=r['time_s'],rho=r['rho'],downstream_rho=r['downstream_rho'],
        observed_final=r['v1'],baseline=r['trajectory'],candidate=trajectory(r,z)) for r in rows]
    h.save(HERE/'conditional_predictions.json',predictions)
    h.save(HERE/'proposal.json',dict(z=z,before=before,after=before*z,baseline_loss=loss(1.,False),candidate_loss=loss(z,False),
        evaluations=evaluations,final_bracket=[left,right],blocks=len(blocks),rows=len(rows),
        active_rows=sum(r['downstream_ge'] for r in rows),baseline160_max_error=error,verified_updates=len(rows)*5,
        input_sha256=pins,only20ge_changed=True,FD_unchanged=True,core=True,STOP=True))
    print('20nu_ge',before,'->',before*z,'z',z,'loss',loss(1.,False),'->',loss(z,False),'rows',len(rows),'blocks',len(blocks),'parity',error)


if __name__=='__main__':main()
