"""Bounded Eq9/Eq10/Eq22 + gradient-sign anticipation identification.

Reuses the existing runner and NC loss; action results never choose coefficients.
"""
import copy, hashlib, json, subprocess, sys, time
from pathlib import Path
import calibrate as c
from prepare import save, table
B=c.B;O=B/'literature_v2';ROOT=c.ROOT

def run(name,merge=False,diverge=False,mode=None,gamma=.5,b=2.,nu=None,nc=True,tau=12,delta=1.):
    if mode is not None:name+='_width_corrected'
    if name=='selected':name='selected_final'
    spec=dict(name='lit_'+name,output_group='literature_v2',parent_cells=c.TARGET,tau_sec=tau,
        nu_km2_h=35,rho_multiplier=1.,delta_merge=delta,nc_only=nc)
    if merge or diverge or mode:
        spec['port_response']=dict(merge_speed=merge,diverge_density=diverge,
            spillback=None if mode is None else dict(mode=mode,gamma=gamma,b=b))
    if nu is not None:spec['anticipation']=dict(downstream_ge_local=nu[0],downstream_lt_local=nu[1])
    prior=O/(spec['name']+'_score.json')
    if prior.exists():
        row=c.load(prior)
        assert row['spec']==spec
        if row['exit_code']==0:
            print(name,'reused completed result',flush=True);return row
        spec['name']+='_retry1'
        retry=O/(spec['name']+'_score.json')
        if retry.exists():
            row=c.load(retry);assert row['spec']==spec and row['exit_code']==0
            print(name,'reused completed retry',flush=True);return row
    path=O/(spec['name']+'.json');save(path,spec);t=time.perf_counter()
    with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
        process=subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,
                               stdout=log,stderr=subprocess.STDOUT)
    row=dict(name=spec['name'],spec=spec,wall_seconds=time.perf_counter()-t,exit_code=process.returncode)
    if process.returncode==0:
        p=c.load(O/spec['name']/'refined_guard1_none.json');row.update(train=c.score(p),numerics=c.screen(p))
        print(name,round(row['train']['objective'],5),row['numerics']['passed'],flush=True)
    else:print(name,'FAILED, retained',flush=True)
    save(O/(spec['name']+'_score.json'),row);return row

def best(records):
    return min((r for r in records if r['exit_code']==0 and r['numerics']['passed']),key=lambda r:r['train']['objective'])

def main():
    protocol=dict(train=[2400,2700],late_check=[2700,2850],initial=2400,seed=23,
        fixed='31-cell guarded mesh, current stocks/intents, past-based demand, controls and objective,kappa17/rhoc. Tau12/delta1 initially, then one tau24 and one delta0.5 full-term candidate. No VSL capacity bonus.',
        stages=['Exact four-arm disabled replay','Single/both junction terms and two spillback modes',
                'Asymmetric anticipation alone','All terms with three anticipation pairs','gamma0.25/0.75 and b4 at selected all-term nu'],
        anticipation_pairs=[[35,12],[50,12],[35,5],[35,30],[50,30],[65,30]],gamma_candidates=[.25,.5,.75],b_candidates=[2,4],
        loss=c.load(c.O/'protocol.json')['loss'],selection='Numerical-pass minimum NC training loss, all models including baseline; freeze before final actions/late check.',
        eq9='Accepted entering-flow weighted virtual upstream speed; zero-flow retains old upstream value. No extra stock speed mixing.',
        eq10='Density-weighted virtual downstream density among continuing mainline and accessible off outlet. Off density from predicted t-start stock.',
        eq22='Exact exponential one-lane sending-width loss allocated over exit-accessible groups. Physical storage/density denominator unchanged. This is a conserved lane-group adaptation, not the whole paper discretization.',
        spillback_modes={'replace_fifo':'Replace shared-through FIFO penalty, keep hard off storage/destination queues.',
                         'envelope':'Minimum of old FIFO factor and operational-width factor; never multiply both.'},
        temporal_and_action_checks_are_development_not_fresh=True,production_adopted=False,new_native_runs=0,
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',B/'calibrate.py',
            ROOT/'evaluation/controllers/physical_lane_groups.py',ROOT/'evaluation/controllers/freeway_fd.py',
            ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',
            B/'geometry_200_branch_guard.json',c.O/'observed_none.npz']})
    save(O/'protocol.json',protocol)
    base=run('disabled',nc=False);assert base['exit_code']==0
    for arm in ('none','rm_ramp','vsl','both'):
        assert c.load(O/'lit_disabled'/f'refined_guard1_{arm}.json')==c.load(B/f'refined_guard1_{arm}.json'),arm
    save(O/'disabled_exact.json',dict(full_json_exact=4))
    records=[base]
    for name,merge,diverge,mode in [('merge',True,False,None),('diverge',False,True,None),('junction',True,True,None),
                                  ('lane',False,False,'replace_fifo'),('envelope',False,False,'envelope'),
                                  ('junction_lane',True,True,'replace_fifo'),('junction_envelope',True,True,'envelope')]:
        records.append(run(name,merge,diverge,mode))
    for hi,lo in protocol['anticipation_pairs']:records.append(run(f'asym{hi}_{lo}',nu=[hi,lo]))
    structural=[r for r in records if r['spec'].get('port_response',{}).get('merge_speed')
                and r['spec']['port_response']['diverge_density'] and r['spec']['port_response']['spillback'] is not None]
    valid=[r for r in structural if r['exit_code']==0 and r['numerics']['passed']]
    if not valid:
        save(O/'candidates.json',records);raise RuntimeError('Both complete structures failed; no calibration promotion')
    mode=best(valid)['spec']['port_response']['spillback']['mode']
    combos=[]
    for hi,lo in protocol['anticipation_pairs']:
        row=run(f'all{hi}_{lo}',True,True,mode,nu=[hi,lo]);records.append(row);combos.append(row)
    winner=best(combos);v=winner['spec']['anticipation'];nu=[v['downstream_ge_local'],v['downstream_lt_local']]
    for label,gamma,b in [('gamma025',.25,2),('gamma075',.75,2),('b4',.5,4)]:
        records.append(run('all_'+label,True,True,mode,gamma,b,nu))
    full=best([r for r in records if r['name'].startswith('lit_all')]);sp=full['spec']['port_response']['spillback']
    for label,tau,delta in [('tau24',24,1),('delta05',12,.5)]:
        records.append(run('all_'+label,True,True,mode,sp['gamma'],sp['b'],nu,tau=tau,delta=delta))
    selected=best(records);save(O/'selected.json',selected);save(O/'candidates.json',records)
    table(O/'candidates.csv',[dict(name=r['name'],exit_code=r['exit_code'],
        objective=r.get('train',{}).get('objective'),speed_rmse=r.get('train',{}).get('speed_rmse_kmh'),
        n_rmse=r.get('train',{}).get('group_n_rmse_veh'),q_rmse=r.get('train',{}).get('boundary_q_rmse_vph'),
        numerical_pass=r.get('numerics',{}).get('passed'),wall_seconds=r['wall_seconds']) for r in records])
    # Also retain a complete-request candidate if NC selection prefers fewer
    # terms. This does not allow gain-based selection or after-the-fact tuning.
    full=best([r for r in records if r['name'].startswith('lit_all')]);save(O/'selected_all_terms.json',full)
    for label,row in [('selected',selected),('all_terms',full)]:
        if label=='all_terms' and row['name']==selected['name']:continue
        spec=row['spec'];pr=spec.get('port_response',{});s=pr.get('spillback') or {};a=spec.get('anticipation')
        run(label,pr.get('merge_speed',False),pr.get('diverge_density',False),s.get('mode'),s.get('gamma',.5),s.get('b',2),
            None if a is None else [a['downstream_ge_local'],a['downstream_lt_local']],False,spec['tau_sec'],spec['delta_merge'])
    print('DONE. Selection frozen; run post-check.',flush=True)

if __name__=='__main__':main()
