"""Bounded Hadiuzzaman Eq6/7/8 ablation using the existing conserved runner.

Only NC train data select coefficients. A 15% drop and Eq3/Eq8 mode switch
are explicitly unqualified sensitivities, never candidates for adoption.
"""
import copy,json,math,subprocess,sys,time
from pathlib import Path
import numpy as np
import calibrate as c
from prepare import save,table
B=c.B;O=B/'hadiuzzaman_v1';K=B.parent/'cohort_dynamics_20260920';ROOT=c.ROOT

def evidence():
    with np.load(c.O/'observed_none.npz') as f:a={k:f[k] for k in f.files}
    geo={r['cell']:r for r in c.G['cells'] if r['road']=='FW_E'};rows=[];rates=[];waves=[]
    for i in c.CELLS:
        rho=a['n'][:10,i].sum(axis=1)/geo[i]['lane_km']
        down=a['n'][:10,i+1].sum(axis=1)/geo[i+1]['lane_km']
        q=a['q'][:10,i-1]*120/sum(c.WIDTHS[i]);rates.extend(q);waves.extend(q/(180-rho))
        # Necessary conditions only: even passing this cannot prove demand
        # saturation or exclude off-ramp/lane-specific downstream restrictions.
        pre=q[(rho<=27)&(down<=27)];post=q[(rho>27)&(down<=27)]
        enough=len(pre)>=5 and len(post)>=5
        rows.append(dict(cell=i,parent=c.PARENTS[i],rho_min=float(min(rho)),rho_max=float(max(rho)),
            free_down_pre_bins=len(pre),free_down_congested_bins=len(post),minimum_sample_gate=bool(enough),
            pre_q90=float(np.quantile(pre,.9)) if len(pre) else None,
            post_q90=float(np.quantile(post,.9)) if len(post) else None,
            theta_identified=False))
    table(O/'capacity_evidence.csv',rows)
    # Upper observed flow is a LOWER BOUND on capacity, not a measured capacity.
    # Keep a common, rounded training-envelope bracket, then test its sensitivity.
    q=math.ceil(max(rates)/100)*100;w=math.ceil(max(waves)/2.5)*2.5
    save(O/'receiving_seed.json',dict(capacity_vphpl=q,wave_kmh=w,jam_density=180.,rho_critical=27.,theta=0.,
        max_observed_inflow_vphpl=max(rates),max_observed_supply_ratio=max(waves),
        provenance='NC2400-2700 observed rate envelope, not identified Qmax/w; rounded upper bracket',
        drop_status='Unidentified: too few paired states and no proof of saturation/unrestricted exit lanes; no positive theta fitted.',
        observation_sha256=c.sha(c.O/'observed_none.npz')))
    return q,w

def run(name,law=None,ctm=True,tau=12,nu=35,kappa=17,q=2200,w=17.5,theta=0.,nc=True,scope=None,
        branch=None,critical=27.,output_group='hadiuzzaman_v1'):
    destination=B/output_group
    spec=dict(name='hd_'+name,output_group=output_group,parent_cells=list(range(21)) if law else c.TARGET,
        tau_sec=tau,nu_km2_h=nu,rho_multiplier=1.,delta_merge=1.,nc_only=nc)
    if law:
        spec['kappa']=kappa
        spec['hadiuzzaman']=dict(ctm=ctm,relaxation=law,cells=[dict(capacity_vphpl=q,wave_kmh=w,
            rho_critical=critical,theta=theta if i in (8,12,21,23) else 0.) for i in range(31)])
        if scope is not None:spec['hadiuzzaman']['relaxation_cells']=scope
        if branch is not None:spec['hadiuzzaman']['congested_branch']=branch
    path=destination/(spec['name']+'.json');prior=destination/(spec['name']+'_score.json')
    if prior.exists():
        row=c.load(prior);assert row['spec']==spec and row['exit_code']==0;return row
    save(path,spec);t=time.perf_counter()
    with (destination/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    row=dict(name=spec['name'],spec=spec,exit_code=p.returncode,seconds=time.perf_counter()-t)
    if p.returncode==0:
        pred=c.load(destination/spec['name']/'refined_guard1_none.json')
        row.update(train=c.score(pred),numerics=c.screen(pred))
    save(prior,row);print(name,row.get('train',{}).get('objective'),row.get('numerics',{}).get('passed'),p.returncode,flush=True)
    return row

def choose(rows):
    valid=[r for r in rows if r['exit_code']==0 and r['numerics']['passed']]
    if not valid:raise RuntimeError('No valid candidate: inspect retained outputs')
    return min(valid,key=lambda r:r['train']['objective'])

def replay(name,row):
    p=row['spec'];h=p.get('hadiuzzaman');cell=h['cells'][0] if h else {}
    return run(name,h['relaxation'] if h else None,h['ctm'] if h else True,p['tau_sec'],p['nu_km2_h'],p.get('kappa',17),
        cell.get('capacity_vphpl',2200),cell.get('wave_kmh',17.5),nc=False)

def main():
    q,w=evidence()
    pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',ROOT/'evaluation/controllers/physical_lane_groups.py',
        ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',c.O/'observed_none.npz']}
    save(O/'protocol.json',dict(train=[2400,2700],late=[2700,2850],seed=23,start=2400,step=1,
        source_pins=pins,selection='NC speed/N/boundary-flow loss only; freeze before actions',
        positive_drop_identified=False,new_native_runs=0,production_adopted=False,independent_validation=False,
        same_model_command_comparison=True,theta15_sensitivity_only=True,mode_switch_sensitivity_only=True))
    base=run('disabled',nc=False);assert base['exit_code']==0
    for arm in ('none','rm_ramp','vsl','both'):assert c.load(O/base['name']/f'refined_guard1_{arm}.json')==c.load(B/f'refined_guard1_{arm}.json')
    rows=[base]
    rows.append(run('receiving','fd_cap',q=q,w=w))
    rows.append(run('command_only','command',False,q=q,w=w))
    for tau,nu,kappa in [(12,35,17),(30,35,35),(60,35,35),(108,35,47),(108,50,47)]:
        rows.append(run(f'hybrid_{tau}_{nu}_{kappa}','command',True,tau,nu,kappa,q,w))
    winner=choose([r for r in rows if 'hybrid' in r['name']]);p=winner['spec']
    for label,qs,ws in [('q90',.9,1),('q110',1.1,1),('w75',1,.75),('w125',1,1.25)]:
        rows.append(run('hybrid_'+label,'command',True,p['tau_sec'],p['nu_km2_h'],p['kappa'],q*qs,w*ws))
    hybrid=choose([r for r in rows if 'hybrid' in r['name']]);best=choose(rows)
    save(O/'candidates.json',rows);save(O/'selected.json',best);save(O/'selected_hybrid.json',hybrid)
    table(O/'candidates.csv',[dict(name=r['name'],exit_code=r['exit_code'],objective=r.get('train',{}).get('objective'),
        numerical_pass=r.get('numerics',{}).get('passed'),seconds=r['seconds']) for r in rows])
    for name,row in [('hybrid_actions',hybrid),('receiving_actions',rows[1])]:replay(name,row)
    # Never permit either sensitivity to change the frozen selected candidate.
    run('paper_switch_actions','paper_switch',True,12,35,17,q,w,nc=False)
    p=hybrid['spec'];cell=p['hadiuzzaman']['cells'][0]
    run('theta15_sensitivity','command',True,p['tau_sec'],p['nu_km2_h'],p['kappa'],cell['capacity_vphpl'],cell['wave_kmh'],.15,nc=False)
    print('DONE: frozen selection plus isolated sensitivities',flush=True)

def scope_main():
    seed=c.load(O/'receiving_seed.json');q=seed['capacity_vphpl'];w=seed['wave_kmh']
    p=c.load(B/'refined_guard1_vsl.json')
    d=next(x for x in p['diagnostics']['roads'] if x['road']=='FW_E')
    scope=[r['cell'] for r in d['vsl_binding_audit']['cells'] if r['command_active_samples']]
    # Scope derives only from known actuator coverage, not observed traffic.
    save(O/'scope_protocol.json',dict(cells=scope,same_scope_in_none_and_vsl=True,
        purpose='Eq8 only in VSL-equipped cells; Eq3 elsewhere. Compare nominal and controlled with the same law.',
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',ROOT/'evaluation/controllers/physical_lane_groups.py']}))
    rows=[]
    for tau,nu,kappa in [(12,35,17),(30,35,35),(60,35,35),(108,35,47),(108,50,47)]:
        rows.append(run(f'scope_{tau}_{nu}_{kappa}','command',True,tau,nu,kappa,q,w,nc=tau!=12,scope=scope))
    best=choose(rows);save(O/'scope_selected.json',best);save(O/'scope_candidates.json',rows)
    p=best['spec']
    run('scope_actions','command',True,p['tau_sec'],p['nu_km2_h'],p['kappa'],q,w,nc=False,scope=scope)
    print('DONE fixed VSL-equipped scope',flush=True)

if __name__=='__main__':scope_main() if '--scope' in sys.argv else main()
