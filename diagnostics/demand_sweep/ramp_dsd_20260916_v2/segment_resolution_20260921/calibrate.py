"""Bounded NC-only calibration on the ramp-exclusive mesh; no new simulator.

Train2400-2700; freeze parameters before late NC2700-2850/action checks.
The latter is temporal validation within one trajectory, not a fresh seed.
"""
from pathlib import Path
import bisect, hashlib, itertools, json, math, subprocess, sys, time
import numpy as np
from prepare import native, save, table

B=Path(__file__).resolve().parent; O=B/'calibration_v1'; ROOT=B.parents[3]
PARENTS=json.loads((B/'parent_map.json').read_text())['FW_E']
G=json.loads((B/'geometry_200_branch_guard.json').read_text())
S=json.loads((B/'guard_initial_groups.json').read_text())
TARGET=[8,9,12,13,14]
CELLS=[i for i,p in enumerate(PARENTS) if p in TARGET]
WIDTHS=S['widths']

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def observe(case='none_s23',output=O):
    proof0=load(B/'sources.json')[case];proof={}
    n=np.zeros((15,31,4));mom=n.copy();q=np.zeros((15,31));previous=None
    chain={p['link']:p for p in G['chains']['FW_E']};bounds=G['bounds']['FW_E']
    on={p['connector']:p['chain_pos_m'] for p in G['boundaries'] if p['road']=='FW_E' and p['kind']=='ramp'}
    off={p['connector']:p['chain_pos_m'] for p in G['boundaries'] if p['road']=='FW_E' and p['kind']=='offramp'}
    count=0
    for t,frame in native.native(native.ROOT/proof0['path'],proof):
        if t<2400 or t>2850:continue
        pos={v:chain[r.link]['offset_m']+r.pos for v,r in frame.items() if r.link in chain}
        pos={v:x for v,x in pos.items() if 0<=x<bounds[-1]}
        if t==2400:previous=(frame,pos);continue
        j=(t-2401)//30;count+=1
        for vid,x in pos.items():
            c=bisect.bisect_right(bounds,x)-1;r=frame[vid]
            g=next(k for k in range(len(WIDTHS[c])) if r.lane<=sum(WIDTHS[c][:k+1]))
            n[j,c,g]+=1/30;mom[j,c,g]+=r.speed/30
        old,oldpos=previous
        for vid in set(oldpos)|set(pos):
            a=oldpos.get(vid);z=pos.get(vid)
            if a is None:
                # Only crossed mainline boundaries after an observed merge;
                # ramp admissions themselves are not longitudinal flow.
                if vid not in old or old[vid].link not in on:continue
                a=on[old[vid].link]
            if z is None:
                # Explicit exit to an observed off connector. Disappearances
                # are not reclassified as terminal/normal exits.
                if vid not in frame or frame[vid].link not in off:continue
                z=off[frame[vid].link]
            assert z>=a-1e-6,(t,vid,a,z)
            for k in range(bisect.bisect_right(bounds,a),bisect.bisect_right(bounds,z)):
                if 0<k<31:q[j,k-1]+=1
        previous=(frame,pos)
    assert count==450 and proof['file_sha256']==proof0['file_sha256']
    np.savez_compressed(output/('observed_'+case.removesuffix('_s23')+'.npz'),n=n,mom=mom,q=q)
    proof_name='observation_proof.json' if case=='none_s23' else case+'_observation_proof.json'
    save(output/proof_name,dict(source=proof,interval_sec=30,forecast_start_s=2400,
        samples=450,group_widths=WIDTHS,refined_geometry_sha256=sha(B/'geometry_200_branch_guard.json'),
        flow_definition='Observed forward mainline boundary crossings; on/off transitions localized at their physical ports. Unknown disappearance is not an exit. No terminal is in calibration cells.'))

def predicted(p):
    n=np.zeros((15,31,4));mom=n.copy();q=np.zeros((15,31));counts=np.zeros((15,31,4))
    for r in p['lane_groups']['FW_E']:
        j=(int(r['time_s'])-2401)//30;c=r['cell'];g=r['group']
        n[j,c,g]+=r['n_veh']/30;mom[j,c,g]+=r['n_veh']*r['v_kmh']/30
        q[j,c]+=r['mainline_out_veh'];counts[j,c,g]+=1
    for c in range(31):assert np.all(counts[:,c,:len(WIDTHS[c])]==30)
    return dict(n=n,mom=mom,q=q)

def score(p,lo=0,hi=10,cells=CELLS):
    with np.load(O/'observed_none.npz') as f:obs={k:f[k] for k in f.files}
    pred=predicted(p);vs=[];ns=[];qs=[]
    for c in cells:
        ng=len(WIDTHS[c]);a=obs['n'][lo:hi,c,:ng];b=pred['n'][lo:hi,c,:ng]
        mask=a>=1 # sparse/empty groups do not provide a speed target
        av=np.divide(obs['mom'][lo:hi,c,:ng],a,out=np.zeros_like(a),where=a>0)
        bv=np.divide(pred['mom'][lo:hi,c,:ng],b,out=np.zeros_like(b),where=b>0)
        vs.extend((bv-av)[mask]);ns.extend((b-a).ravel())
        qs.extend((pred['q'][lo:hi,c]-obs['q'][lo:hi,c])*120)
    rmse=lambda xs:float(np.sqrt(np.mean(np.square(xs))))
    v,n,q=rmse(vs),rmse(ns),rmse(qs)
    return dict(objective=(v/20)**2+(n/5)**2+(q/500)**2,speed_rmse_kmh=v,
        group_n_rmse_veh=n,boundary_q_rmse_vph=q,speed_samples=len(vs),stock_samples=len(ns),flow_samples=len(qs))

def screen(p):
    lengths={c['cell']:c['length_km']*1000 for c in G['cells'] if c['road']=='FW_E'}
    vmax=0.;courant=0.;res=0.
    for r in p['lane_groups']['FW_E']:
        assert r['n_veh']>=-1e-8 and math.isfinite(r['v_kmh'])
        vmax=max(vmax,r['v_kmh']);courant=max(courant,r['v_kmh']/(3.6*lengths[r['cell']]))
    for d in p['diagnostics']['roads']:
        assert d['negative_density_count']==d['jam_density_exceedance_count']==0
        res=max(res,d['continuity_residual_max_veh'])
        for r in d.get('branch_partition_trace',[]):
            cell=next(c for c in G['cells'] if c['road']=='FW_E' and c['cell']==r['cell'])
            port=next(x for x in G['boundaries'] if x['connector']==10643)
            for side,length in [('pre',port['chain_pos_m']-cell['start_m']),('post',cell['end_m']-port['chain_pos_m'])]:
                v=r[side+'_v'];vmax=max(vmax,v);courant=max(courant,v/(3.6*length))
    for r in p['ramps']+p['ports']:res=max(res,abs(r['conservation_residual_veh']))
    return dict(passed=vmax<=180 and courant<=1 and res<1e-7,max_speed_kmh=vmax,max_courant=courant,max_mass_residual_veh=res)

def run(name,tau,nu,rho=1.,delta=1.,nc=True,regions=None):
    spec=dict(name=name,parent_cells=TARGET,tau_sec=tau,nu_km2_h=nu,rho_multiplier=rho,delta_merge=delta,nc_only=nc)
    assert 12<=tau<=60 and 3<=nu<=90 and .6<=rho<=1.4 and 0<=delta<=1
    if regions is not None:
        assert sum(len(r['parent_cells']) for r in regions)==len(set(p for r in regions for p in r['parent_cells']))
        assert all(12<=r['tau_sec']<=60 and 3<=r['nu_km2_h']<=90 and .6<=r['rho_multiplier']<=1.4 for r in regions)
        spec['regions']=regions
    path=O/(name+'.json');save(path,spec)
    t=time.perf_counter()
    with (O/(name+'_process.log')).open('x',encoding='utf-8') as log:
        subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,
            stdout=log,stderr=subprocess.STDOUT,check=True)
    p=load(O/name/'refined_guard1_none.json');check=screen(p)
    result=dict(name=name,parameters=spec,train=score(p),numerics=check,wall_seconds=time.perf_counter()-t)
    save(O/(name+'_score.json'),result)
    print(name,round(result['train']['objective'],4),check['passed'],round(result['wall_seconds'],1),flush=True)
    return result

def fit():
    protocol=dict(train_interval=[2400,2700],temporal_check_interval=[2700,2850],initial_state_s=2400,seed=23,
        tau_sec=[12,24,40],nu_km2_h=[12,35,70],rho_followup=[.8,1.2],delta_followup=[.5,.75],
        parent_cells=TARGET,refined_cells=CELLS,maximum_nc_candidates=13,
        loss='(group speed RMSE/20)^2+(group N RMSE/5)^2+(total boundary q RMSE/500)^2; 30s means/counts, only train interval.',
        selection='Best numerical-pass NC training loss, then two rho candidates, then two delta candidates. Freeze before late NC or action evaluation.',
        fixed=['geometry','free speed','kappa17','lane exchange','VSL spatial coverage','actuation','demand forecast','route fractions','urban/off dynamics'],
        no_gain_or_control_data_in_fit=True,no_heldout_initial_state=True,no_new_native=True,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),B/'run.py',B/'geometry_200_branch_guard.json',B/'initial_2400.json']})
    save(O/'protocol.json',protocol)
    if not (O/'observed_none.npz').exists():observe()
    assert load(O/'observation_proof.json')['refined_geometry_sha256']==sha(B/'geometry_200_branch_guard.json')
    baseline=load(B/'refined_guard1_none.json')
    save(O/'baseline_train.json',dict(train=score(baseline),numerics=screen(baseline)))
    records=[]
    for tau,nu in itertools.product(protocol['tau_sec'],protocol['nu_km2_h']):
        record=run(f'v2_t{tau}_n{nu}',tau,nu);records.append(record)
        if tau==12 and nu==35:
            assert load(O/record['name']/'refined_guard1_none.json')==baseline,'No-change calibration hook changed forecast'
    best=min((r for r in records if r['numerics']['passed']),key=lambda r:r['train']['objective'])
    for rho in protocol['rho_followup']:
        par=best['parameters'];records.append(run('v2_rho'+str(rho).replace('.','_'),par['tau_sec'],par['nu_km2_h'],rho))
    best=min((r for r in records if r['numerics']['passed']),key=lambda r:r['train']['objective'])
    for delta in protocol['delta_followup']:
        par=best['parameters'];records.append(run('v2_delta'+str(delta).replace('.','_'),par['tau_sec'],par['nu_km2_h'],par['rho_multiplier'],delta))
    best=min((r for r in records if r['numerics']['passed']),key=lambda r:r['train']['objective'])
    save(O/'selected.json',best);save(O/'candidates.json',records)
    table(O/'candidates.csv',[dict(name=r['name'],**{k:r['parameters'][k] for k in ('tau_sec','nu_km2_h','rho_multiplier','delta_merge')},**r['train'],numerical_pass=r['numerics']['passed'],wall_seconds=r['wall_seconds']) for r in records])
    par=best['parameters'];run('selected_actions',par['tau_sec'],par['nu_km2_h'],par['rho_multiplier'],par['delta_merge'],False)

def local_fit():
    # Prior NC training-only regional residuals: F preferrednu35, Dnu12.
    # Do not read late NC or any controlled observations for selection.
    save(O/'local_protocol.json',dict(reason='Shared regional coefficients hid opposing NC training preferences.',
        parent_regions=[[8,9],[12,13,14]],first_region_nu=[25,35,45],second_region_tau=12,second_region_nu=12,
        followup='One tau24 first-region candidate at the best training-only nu.',maximum_additional_nc_candidates=4,
        training=[2400,2700],no_gain_fitting=True,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),B/'run.py',O/'selected.json',O/'candidates.json']}))
    records=[load(O/'selected.json')]
    for nu in (25,35,45):
        regions=[dict(parent_cells=[8,9],tau_sec=12,nu_km2_h=nu,rho_multiplier=1.),
                 dict(parent_cells=[12,13,14],tau_sec=12,nu_km2_h=12,rho_multiplier=1.)]
        records.append(run('local_f'+str(nu)+'_d12',12,35,regions=regions))
    best=min((r for r in records if r['numerics']['passed']),key=lambda r:r['train']['objective'])
    nu=best['parameters'].get('regions',[{'nu_km2_h':35}])[0]['nu_km2_h']
    regions=[dict(parent_cells=[8,9],tau_sec=24,nu_km2_h=nu,rho_multiplier=1.),
             dict(parent_cells=[12,13,14],tau_sec=12,nu_km2_h=12,rho_multiplier=1.)]
    records.append(run('local_f_t24_n'+str(nu)+'_d12',12,35,regions=regions))
    best=min((r for r in records if r['numerics']['passed']),key=lambda r:r['train']['objective'])
    save(O/'local_candidates.json',records);save(O/'local_selected.json',best)
    par=best['parameters']
    if 'regions' in par:
        run('local_selected_actions',par['tau_sec'],par['nu_km2_h'],par['rho_multiplier'],par['delta_merge'],False,par['regions'])
    else:assert best['name']==load(O/'selected.json')['name']

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='local':local_fit()
    else:fit()
