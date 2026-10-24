"""Bounded state-response hypotheses on frozen native records, not live patches.

Training uses seed13; already-seen seed23 is development validation. All hooks
are restored after each rollout. Adoption requires later installed-code replay
and a fresh native seed. No benefit term or state reset is used.
"""
import argparse
import copy
from contextlib import contextmanager
import json
import math
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=H.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import canonical_harness as ch

BASE=H/'controller_response_4500_v1/model_v5_node'
ARMS=('none','rm_ramp','vsl','both')

def direction_parts(data,model,start,pred=None):
    parts={road:{'mainline':0.,'on':0.,'off':0.} for road in model.roads}
    old={}
    for t in range(start,start+451,30):
        for road in model.roads:
            ramps={m for m,r in model.ramps.items() if r['road']==road}
            offs={m for m,r in model.offramps.items() if r['road']==road}
            if pred is None or t==start:
                cohorts=data.port_cohorts[str(t)]
                n=[sum(r['n_veh'] for r in data.cells[t] if r['road']==road),
                   sum(len(cohorts[str(model.ramps[m]['connector'])]) for m in ramps),
                   sum(len(cohorts[m]) for m in offs)]
            else:
                n=[sum(r['n_veh'] for r in pred['cells'] if r['time_s']==t and r['road']==road),
                   sum(r['end']['connector_veh'] for r in pred['ramps'] if r['end_sec']==t and r['ramp'] in ramps),
                   sum(r['n_veh'] for r in pred['ports'] if r['time_s']==t and r['connector'] in offs)]
            if road in old:
                for k,a,b in zip(parts[road],old[road],n):parts[road][k]+=(a+b)*30/7200
            old[road]=n
    return parts

@contextmanager
def mechanism(spec):
    """Only change an explicitly listed equation; preserve segment context."""
    mn=ch.accounting._mn
    old_update=mn.metanet_speed_update_kmh
    old_desired=mn.effective_desired_speed_kmh
    old_config=ch.CanonicalFreewayModel._config
    def config(model,road,parameters):
        cfg=old_config(model,road,parameters)
        if getattr(cfg.network,'vsl_fd_two_branch',False):
            cfg.network.vsl_fd_two_branch=road=='FW_E' and 'triangular_critical' in spec
            if cfg.network.vsl_fd_two_branch:
                cfg.network.rho_crit_two_branch=spec['triangular_critical']
                cfg.network.rho_crit_two_branch_by_direction={'FW_E':spec['triangular_critical']}
        if road=='FW_E':
            for p in cfg.network.freeway_segment_params[road]:p['_study_target']=True
        return cfg
    ch.CanonicalFreewayModel._config=config
    def update(speed,upstream,rho,downstream,desired,dt,length,tau,nu,kappa,vmin):
        ctx=ch.adapter._FW_SEG_CTX
        p=ctx['p'] if ctx['armed'] else {}
        # p is never mutated: the temporary dict belongs only to this call.
        original=p
        if p.get('_study_target'):
            p=dict(p)
            if 'tau_acc_sec' in spec:
                p['metanet_tau_h']=(spec['tau_acc_sec'] if desired>=speed else spec['tau_dec_sec'])/3600
            if 'nu_high' in spec:
                nu=spec['nu_high'] if downstream>=rho else spec['nu_low']
            if 'nu_congested_factor' in spec and rho>p['rho_crit']:
                nu*=spec['nu_congested_factor']
            ctx['p']=p
        try:return old_update(speed,upstream,rho,downstream,desired,dt,length,tau,nu,kappa,vmin)
        finally:
            if p:ctx['p']=original
    def desired(*args):
        ctx=ch.adapter._FW_SEG_CTX;p=ctx['p'] if ctx['armed'] else {}
        if 'dsd_gamma' in spec and p.get('_study_target') and args[5]:
            r=spec['dsd_ratios'][str(int(args[3]))]
            original=p
            ctx['p']={**p,'v_free':p['v_free']*r,'rho_crit':p['rho_crit']/r**spec['dsd_gamma']}
            base=list(args);base[5]=False
            try:return old_desired(*base)
            finally:ctx['p']=original
        if 'fd_shape' in spec and p.get('_study_target'):
            original=p;ctx['p']={**p,'metanet_a_m':spec['fd_shape']}
            try:return old_desired(*args)
            finally:ctx['p']=original
        if spec.get('vsl_mean_ratio') and args[5]:
            base=list(args);base[5]=False
            return old_desired(*base)*spec['vsl_mean_ratio'][str(int(args[3]))]
        return old_desired(*args)
    mn.metanet_speed_update_kmh=update
    mn.effective_desired_speed_kmh=desired
    try:yield
    finally:
        mn.metanet_speed_update_kmh=old_update
        mn.effective_desired_speed_kmh=old_desired
        ch.CanonicalFreewayModel._config=old_config

def candidates():
    xs=[('baseline',{})]
    for hi,lo in [(35,12),(70,12),(70,35),(90,12)]:
        xs.append((f'gradient_{hi}_{lo}',{'nu_high':hi,'nu_low':lo}))
    for factor in [.5,2.]:xs.append((f'critical_nu_{factor}',{'nu_congested_factor':factor}))
    for acc,dec in [(24,12),(40,12),(60,12),(12,24)]:
        xs.append((f'tau_{acc}_{dec}',{'tau_acc_sec':acc,'tau_dec_sec':dec}))
    for key,values in [('rho_crit_multiplier',[.8,1.2,1.4]),('v_free_multiplier',[1.,1.15]),
                       ('kappa_veh_km_lane',[5.,40.]),('delta_merge',[0.,.5]),('lane_drop_phi',[1.5,3.,6.])]:
        xs.extend((f'{key}_{v}',{'parameters':{key:v}}) for v in values)
    xs.extend((f'fd_shape_{a}',{'fd_shape':a}) for a in [1.2,2.5])
    return xs

def build_cases(config_path=None):
    cases={}
    for seed,folder,bank,start in [(13,'controller_response_4500_v1',H/'response_pairs_v1',1650),
                                   (23,'controller_response_s23_v1',H/'response_late_s23_v1',2400)]:
        data=e.ObservationData(H/folder/'none')
        model=e.load_base_model(data.geometry,config_path or BASE/'config.json')
        profile=e.load(BASE/'port_profile.json');protocol=e.load(bank/'protocol.json')
        cases[seed]={'data':data,'model':model,'profile':profile,'protocol':protocol,'start':start,'items':{}}
        for cutoff in [900,1650,2400,3600]:
            name='nc_'+str(cutoff)
            cases[seed]['items'][name]={'data':data,'start':cutoff,'window':e.window(data,model,cutoff,'history_forecast',profile,lambda t: ({},{}))}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def command(t):
                i=int((t-start)//150)
                return ({protocol.get('meter_id','RM_C10490'):seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            observed=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            cases[seed]['items']['pair_'+arm]={'data':observed,'start':start,
                'window':e.window(data,model,start,'history_forecast',profile,command)}
        for item in cases[seed]['items'].values():
            item['actual']=direction_parts(item['data'],model,item['start'])
    return cases

def assess(case,spec,params):
    p=copy.deepcopy(params);p['by_direction']['FW_E'].update(spec.get('parameters',{}))
    result={};invalid=False
    with mechanism(spec):
        for name,item in case['items'].items():
            prediction=e.simulate(case['model'],item['window'],p)
            scores=e.score_rollout(item['data'],item['start'],prediction,'FW_E')
            invalid|=scores['invalid']
            result[name]={'parts':direction_parts(case['data'],case['model'],item['start'],prediction),
                'speed_rmse':scores['speed']['rmse'],'rho_rmse':scores['density']['rmse'],
                'flow_rmse':scores['flow_vph']['rmse'],'invalid':scores['invalid'],
                'congestion':scores['congestion_confusion'],
                'merge10490':e.component(case['data'],case['model'],item['start'],prediction)['merges']['RM_C10490']}
    absolute=statistics.mean((r['speed_rmse']/20)**2+(r['rho_rmse']/10)**2+(r['flow_rmse']/1000)**2 for n,r in result.items() if n.startswith('nc_'))
    deltas={};response=[]
    for arm in ARMS[1:]:
        n='pair_'+arm
        pred={k:result[n]['parts']['FW_E'][k]-result['pair_none']['parts']['FW_E'][k] for k in ['mainline','on','off']}
        obs={k:case['items'][n]['actual']['FW_E'][k]-case['items']['pair_none']['actual']['FW_E'][k] for k in pred}
        deltas[arm]={'predicted':pred,'observed':obs,'predicted_total':sum(pred.values()),'observed_total':sum(obs.values())}
        response.extend(((pred[k]-obs[k])/.5)**2 for k in pred)
    return {'invalid':invalid,'absolute_loss':absolute,'response_loss':statistics.mean(response),
            'loss':absolute+statistics.mean(response),'deltas':deltas,'records':result}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screen',default='v1',choices=['v1','v2','v3'])
    args=parser.parse_args()
    out=HERE/('screen_'+args.screen);out.mkdir(exist_ok=False)
    variants=candidates()
    if args.screen=='v2':
        audit=e.load(H/'response_late_s23_v1/model_mechanism_audit.json')
        distributions=next(v for v in audit.values() if isinstance(v,dict) and '120' in v)
        ratios={k:v['mean_kmh']/distributions['120']['mean_kmh'] for k,v in distributions.items()}
        variants=[('baseline',{})]
        for g in [0.,.5,1.]:
            variants.append(('dsd_gamma_'+str(g),{'dsd_gamma':g,'dsd_ratios':ratios}))
        variants.extend([('gamma1_tau24',{'dsd_gamma':1.,'dsd_ratios':ratios,'tau_acc_sec':24,'tau_dec_sec':12}),
                         ('gamma1_vf1',{'dsd_gamma':1.,'dsd_ratios':ratios,'parameters':{'v_free_multiplier':1.}})])
    config_path=None
    if args.screen=='v3':
        cfg=e.load(BASE/'config.json');cfg['freeway']['two_branch']={'enabled':True,'rho_crit_two_branch':20.}
        config_path=out/'config.json';e.save(config_path,cfg)
        variants=[('baseline',{})]+[(f'triangle_{rc}_{vf}',{'triangular_critical':rc,'parameters':{'v_free_multiplier':vf}}) for rc in [16.,20.,24.,28.] for vf in [.91,1.]]
    cases=build_cases(config_path)
    e.save(out/'protocol.json',{'candidates':variants,'training_seed':13,'development_validation_seed':23,
        'horizon_sec':450,'no_control_starts':[900,1650,2400,3600],
        'training_objective':'NC E speed/20,density/10,flow/1000 squared plus paired E mainline/on/off delta TTT error/.5 squared',
        'same_state_controlled_banks':[1650,2400],'no_future_observation_in_forecasts':True,
        'not_claimed':'No fresh-seed qualification; no full GNE; no benefit assumed; no ad hoc capacity gain.'})
    e.save(out/'actual_parts.json',{str(seed):{n:i['actual'] for n,i in c['items'].items()} for seed,c in cases.items()})
    params=e.load(BASE/'selected_parameters.json')['parameters'];results=[]
    for name,spec in variants:
        row={'name':name,'spec':spec,'scores':{}}
        for seed,case in cases.items():
            try:row['scores'][str(seed)]=assess(case,spec,params)
            except (ArithmeticError,ValueError) as err:row['scores'][str(seed)]={'invalid':True,'error':str(err)}
        results.append(row);e.save(out/(name+'.json'),row)
        print(name,{s:{k:r.get(k) for k in ['invalid','absolute_loss','response_loss']} for s,r in row['scores'].items()},flush=True)
    e.save(out/'results.json',results)

if __name__=='__main__':main()
