"""Seed13-only mechanism sensitivity; not fitted coefficients or a new holdout."""
import copy
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
CAL=HERE.parent/'metanet_calibration_v1'
sys.path.insert(0,str(CAL))
from boundary_factory import ObservationData,build_window,PROTOCOL
from canonical_harness import load_base_model
from scoring import score_rollout
from evaluate import pooled,check_freeze
from src.models import metanet


def main():
    output=HERE/'term_sensitivity.json'
    if output.exists():raise ValueError('Do not overwrite exploratory results')
    check_freeze(CAL/'FREEZE.json',CAL/'fit_v2/parameters.json')
    data=ObservationData(CAL/'seed13_observations')
    fit=json.loads((CAL/'fit_v2/parameters.json').read_text(encoding='utf-8'))['parameters']
    model=load_base_model(data.geometry)
    speed_update=metanet.metanet_speed_update_kmh
    arms=[('fitted_reference',{}),('drop_phi0',{'phi':0.}),('drop_phi1p5',{'phi':1.5}),
          ('drop_phi6',{'phi':6.}),('merge_delta0',{'delta':0.}),('merge_delta0p3',{'delta':.3}),
          ('merge_delta1',{'delta':1.}),('gradient_high1p5_low0p5',{'high':1.5,'low':.5}),
          ('gradient_high2_low0p5',{'high':2.,'low':.5})]
    scores=[];summaries=[];failures=[]
    windows={t:build_window(data,t,'conditioned_diagnostic') for t in PROTOCOL['training_cutoffs_sec']}
    for name,change in arms:
        parameters=copy.deepcopy(fit)
        model.base.network.freeway_lane_drop_phi=change.get('phi',3.)
        if 'delta' in change:
            for p in parameters['by_direction'].values():p['delta_merge']=change['delta']
        def asymmetric(speed,upstream_speed,rho,downstream_rho,v_eff,dt_h,length_km,tau_h,nu_km2_h,kappa_veh_km_lane,v_min):
            multiplier=change.get('high',1.) if downstream_rho>=rho else change.get('low',1.)
            return speed_update(speed,upstream_speed,rho,downstream_rho,v_eff,dt_h,length_km,tau_h,
                                nu_km2_h*multiplier,kappa_veh_km_lane,v_min)
        for cutoff,w in windows.items():
            try:
                with patch.object(metanet,'metanet_speed_update_kmh',asymmetric):
                    pred=model.rollout(w['initial_cells'],w['boundary_steps'],overrides=parameters,
                                       initial_origin_queue=w['initial_origin_queue'])
                for road in ('FW_E','FW_W'):
                    scores.append({'arm':name,**score_rollout(data,cutoff,pred,road)})
            except Exception as e:failures.append({'arm':name,'cutoff':cutoff,'error':repr(e)})
        for road in ('FW_E','FW_W'):
            selected=[s for s in scores if s['arm']==name and s['road']==road]
            e14=[e for s in selected for e in s['onset_events'] if road=='FW_E' and e['cell']==13]
            summaries.append({'arm':name,'road':road,'windows':len(selected),'invalid_windows':sum(s['invalid'] for s in selected),
                **{f:pooled(selected,f) for f in ('density','speed','flow_vph')},
                'e14_sustained_observed':sum(e['observed_first_sustained_in_window_s'] is not None for e in e14),
                'e14_missed':sum(e['status']=='miss' for e in e14),
                'e14_total_observed':sum(s['e14_discharge_observed_veh'] or 0 for s in selected),
                'e14_total_predicted':sum(s['e14_discharge_predicted_veh'] or 0 for s in selected)})
    model.base.network.freeway_lane_drop_phi=3.
    check_freeze(CAL/'FREEZE.json',CAL/'fit_v2/parameters.json')
    value={'kind':'mechanism_sensitivity_not_calibration','seed':13,'windows':list(windows),
        'boundary_mode':'conditioned_diagnostic','arms':dict(arms),'summary':summaries,'scores':scores,'failures':failures,
        'limitations':['Hand-picked ablations, no optimizer or coefficient adoption.',
            'Uses already seen training seed13 only, not an independent test.',
            'Observed future off-entry capacity proxy retained; no dynamic off-ramp/drain reconstruction.',
            'Asymmetric factors multiply canonical nu after gradient-sign selection; all other canonical speed hooks retained.',
            'No native control runs or evidence of actual VSL/RM benefit.'],
        'frozen_source_files_unchanged':True}
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(output),'rollouts':len(arms)*len(windows),'failures':len(failures)},ensure_ascii=False))
    for r in summaries:
        print(json.dumps({k:r[k] for k in ('arm','road','invalid_windows','density','speed','flow_vph','e14_missed')}))

if __name__=='__main__':main()
