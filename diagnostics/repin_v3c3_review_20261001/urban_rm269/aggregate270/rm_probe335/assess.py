"""Saved scalar probes versus334 active-branch derivative and332 physical pair."""
from pathlib import Path
import hashlib,json,pickle,math
HERE=Path(__file__).resolve().parent;W=HERE.parent/'worker334'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (HERE/'assessment.json').exists()
    base=pickle.loads((W/'scalar/result.pickle').read_bytes())
    ad=pickle.loads((W/'ad_v3/result.pickle').read_bytes())
    req=pickle.loads((W/'capture_v2/request.pickle').read_bytes())
    eps=pickle.loads((HERE/'epsilon_run/result.pickle').read_bytes())
    release=pickle.loads((HERE/'release_run/result.pickle').read_bytes())
    for r in (base,eps,release):
        assert 'error' not in r and r['scalar_rollouts']==1
        p=r['surrogate_prediction']
        assert p['conditional_model_feasibility_witness'] and p['model_constraint_coverage']['complete']
        assert p['resource_summary']['max_exceedance_veh']<1e-7
    delta=0.0001
    axes=[(j,a) for j,a in enumerate(req['axes']) if a['kind']=='meter' and a['key']=='RM_C10681']
    first=next((j,a) for j,a in axes if a['block']==0)
    j,a=first;scale=a['scale']
    fd={k:(eps['costs'][i]-base['costs'][i])/delta for i,k in enumerate(req['costs_order'])}
    tangent={k:ad['cost_jacobian'][i][j]/scale for i,k in enumerate(req['costs_order'])}
    owner_error={k:fd[k]-tangent[k] for k in fd}
    resource_fd=[(e-b)/delta for b,e in zip(base['resources'],eps['resources'])]
    resource_ad=[r[j]/scale for r in ad['resource_jacobian']]
    actual={k:release['costs'][i]-base['costs'][i] for i,k in enumerate(req['costs_order'])}
    linear={k:sum(ad['cost_jacobian'][i][j]/a['scale']*(2+2*a['block']) for j,a in axes)
            for i,k in enumerate(req['costs_order'])}
    cap=[req['action'].N_P_star,req['action'].N_UF_star]
    physical=read(Path('E:/VISSIM_analysis/20261010_response332/forecast3300/summary.json'))['results']
    continuous={}
    for name,r in (('hold',base),('release',release)):
        p=r['surrogate_prediction']
        continuous[name]=dict(omega_ttt_veh_h=p['objective_veh_h'],owner_costs=p['sdmpc_omega_partition']['costs'],
            resources=r['resources'],caps=cap,cap_feasible=all(x<=c+1e-7 for x,c in zip(r['resources'],cap)),
            merge=p['control_area']['predicted_ramp_merge'],seconds=r['wall_sec_including_imports'])
    result=dict(status='complete_two_bounded_responses',
        small_direction=dict(epsilon_green_sec=delta,finite_difference_by_owner=fd,ad_by_owner=tangent,
            omega_fd=sum(fd.values()),omega_ad=sum(tangent.values()),max_owner_error=max(map(abs,owner_error.values())),
            resource_fd=resource_fd,resource_ad=resource_ad,
            scope='One-sided +0.0001s response; discrete travel-event switches may invalidate a single active-branch tangent'),
        finite_step=dict(greens_hold=[2,2,2],greens_release=[4,6,8],owner_delta=actual,omega_delta=sum(actual.values()),
            active_branch_linear_omega=sum(linear.values()),active_branch_linear_owners=linear,
            physical_clock332_omega_delta=physical['release']['omega_ttt_veh_h']-physical['hold']['omega_ttt_veh_h']),
        continuous=continuous,new_native=0,fits=0,full_selection=False,goal_complete=False,
        source_pins={str(p):sha(p) for p in (W/'scalar/result.pickle',W/'ad_v3/result.pickle',W/'capture_v2/request.pickle',
             HERE/'epsilon/request.pickle',HERE/'release/request.pickle',HERE/'epsilon_run/result.pickle',HERE/'release_run/result.pickle',
             HERE/'worker.py',HERE/'prepare.py',HERE/'plan.json',Path(__file__))})
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('small_direction','finite_step','continuous')},ensure_ascii=False))
if __name__=='__main__':main()
