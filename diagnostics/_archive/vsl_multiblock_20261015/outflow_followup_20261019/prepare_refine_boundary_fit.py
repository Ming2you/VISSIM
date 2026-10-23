"""Prepare one finite boundary-response identification from audited replay code."""
import ast, hashlib, json
from pathlib import Path
A=Path(__file__).resolve().parent
source=A/'run_refine15_regime_fit_v3.py'
target=A/'run_refine_boundary_fit.py'
assert not target.exists()
text=source.read_text(encoding='utf8')
def replace(old,new):
    global text
    assert text.count(old)==1,(old[:100],text.count(old))
    text=text.replace(old,new)
def section(first,last,new):
    global text
    i=text.index(first);j=text.index(last,i)
    text=text[:i]+new+text[j:]
replace('Two bounded regime-inclusive updates; reserve independent validation.',
        'One bounded update of cells14/18 dynamic responses; no VSL-outcome fitting.')
replace("O=A/'refine15_regime_fit_v3'","O=A/'refine_boundary_fit'")
section("    initial_audit=read(A/'refine15_update_audit.json');spec=read(SPEC)\n",
        "    prior=ROOT/'diagnostics/repin_v3c3_review_20261001/aggregate_recovery247'\n",'''    audit=read(A/'refine15_residual_audit.json')
    assert audit['new_forecasts']==0
    prior_fit=read(A/'refine15_regime_fit_v3/selection.json')
    fixed15=prior_fit['fitted']['values']
    active=read(HERE/'cached_vsl_exposure_audit_v2/active_component_config.json')
    reference=read(Path(active['reference_config']))
    responses={str(i):reference['freeway']['state_response']['FW_E']['cell_overrides'][str(i)] for i in (14,18)}
    names=['tau14','nu14','tau18','nu18'];initial=[1.]*4
    spec=read(SPEC);ranges={(v['cell'],v['parameter']):v for v in spec['variables']}
    lower=[];upper=[]
    for cell,kind in ((14,'tau'),(14,'nu'),(18,'tau'),(18,'nu')):
        r=responses[str(cell)]
        entries=([(r['relaxation']['acceleration_sec'],ranges[cell,'tau_sec']),
                  (r['relaxation']['deceleration_sec'],ranges[cell,'tau_sec'])] if kind=='tau' else
                 [(r['anticipation']['downstream_ge_local'],ranges[cell,'nu_ge']),
                  (r['anticipation']['downstream_lt_local'],ranges[cell,'nu_lt'])])
        lower.append(max(-.25,*(bound['lower']/value-1 for value,bound in entries)))
        upper.append(min(.25,*(bound['upper']/value-1 for value,bound in entries)))
    assert all(lo<0<hi for lo,hi in zip(lower,upper))
    previous_completion=read(A/'refine15_regime_fit_v3/completion.json')
    for p,h in previous_completion['source_pins'].items():assert sha(p)==h,p
''')
replace("hypothesis='Transferred FD and dynamic coefficients jointly misrepresent the refined transient; identify a finite local correction from autonomous baseline trajectories, not one-step population changes.'",
        "hypothesis='Cell15-only sensitivity cannot explain most baseline errors; test whether the preexisting dynamic response at upstream14 and diverge approach18 is identifiable from the same baseline trajectories. This is a bounded identification experiment, not an established root-cause repair.'")
replace("parameters=names,initial=initial,relative_lower=lower,relative_upper=upper,historical_bounds=str(SPEC),",
        "parameters=names,initial=initial,relative_lower=lower,relative_upper=upper,historical_bounds=str(SPEC),original_response=responses,fixed_cell15=fixed15,")
replace("fixed='v_free, kappa, remaining cells, geometry, VSL law, city/ramp physics, source/demand; FW5/U10,internalcap0.625,terminalOFF,Omega701'",
        "fixed='All FD coefficients, lane-drop, cell15 fitted values, all other cells, geometry, VSL law, city/ramp physics, demand; FW5/U10,internalcap0.625,terminalOFF,Omega701'")
replace("optimizer='At most two measured bounded regularized Gauss-Newton updates. Relative0.05 forward Jacobian; no grid, line-search or restart. Stop after a non-improving nonlinear step. Reuse two previous identical trajectories.'",
        "optimizer='One bounded regularized Gauss-Newton update, four relative5percent probes. Max25percent changes intersect historical bounds. No grid, line-search or restart. Reuse three identical fitted2 trajectories.'")
replace("budgets=dict(max_new_training450=37,max_development_response450=1,max_new_forecasts=38,max_updates=2,native=0,SDMPC_optimizations=0)",
        "budgets=dict(max_new_training450=15,max_development_response450=1,max_new_forecasts=16,max_updates=1,native=0,SDMPC_optimizations=0)")
replace("        assert forecasts_count<38\n","        assert forecasts_count<16\n")
section("        for net in (cfg.network,state.lane_freeway_runtime.configs['FW_E'].network):\n",
        "        actions=copy.deepcopy(captured[at]['actions'])\n",'''        for net in (cfg.network,state.lane_freeway_runtime.configs['FW_E'].network):
            net.freeway_segment_params['FW_E'][15].update(rho_crit=fixed15[0],metanet_a_m=fixed15[1])
            if not hasattr(net,'freeway_state_response'):net.freeway_state_response={}
            overrides=net.freeway_state_response.setdefault('FW_E',{}).setdefault('cell_overrides',{})
            overrides['15']=dict(relaxation=dict(acceleration_sec=fixed15[2],deceleration_sec=fixed15[2]),anticipation=dict(downstream_ge_local=fixed15[3],downstream_lt_local=fixed15[4]))
            for j,cell in enumerate((14,18)):
                if net is state.lane_freeway_runtime.configs['FW_E'].network:
                    assert overrides[str(cell)]==responses[str(cell)],('unexpected boundary source',cell)
                r=copy.deepcopy(responses[str(cell)])
                r['relaxation']={k:float(v*values[j*2]) for k,v in r['relaxation'].items()}
                r['anticipation']={k:float(v*values[j*2+1]) for k,v in r['anticipation'].items()}
                overrides[str(cell)]=r
''')
replace("        prior={1650:read(A/'refine15_joint_fit/fitted_1650.json'),2250:read(A/'refine15_joint_fit/validation_hold.json')}\n",
        "        prior={at:read(A/f'refine15_regime_fit_v3/fitted2_{at}.json') for at in (1650,2250,2850)}\n")
replace("            assert p['values']==list(initial) and p['physical']\n","            assert p['values']==fixed15 and p['physical']\n")
replace("            assert len(records)<13\n","            assert len(records)<6\n")
replace("        z=np.zeros(5);current=evaluate(z,'baseline');best=records[-1];base=records[0];updates=[]\n",
        "        z=np.zeros(4);current=evaluate(z,'baseline');best=records[-1];base=records[0];updates=[]\n")
replace("        for iteration in (1,2):\n","        for iteration in (1,):\n")
replace("            for i in range(5):\n","            for i in range(4):\n")
replace("np.vstack([J,.1*np.eye(5)])","np.vstack([J,.1*np.eye(4)])")
replace("method='At most two measured bounded Gauss-Newton updates'","method='One bounded four-parameter boundary-response update'")
replace("reused_forecasts=2,SDMPC_optimizations=0","reused_forecasts=3,SDMPC_optimizations=0")
# Reused initial state qualification applies to both experiments; these files are immutable.
ast.parse(text)
target.write_text(text,encoding='utf8')
receipt=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
             prepared=str(target),prepared_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
             new_forecasts=0,new_native=0,max_new_forecasts=16,max_updates=1,
             physical_change='Only cells14/18 existing relaxation and anticipation scale factors; frozen cell15 fit; no FD/VSL/capacity bonus.',
             qualification='Preparation only. No run launched by this script.')
(A/'refine_boundary_preparation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(receipt,indent=2))
