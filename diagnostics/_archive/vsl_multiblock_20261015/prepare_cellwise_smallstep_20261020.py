"""Prepare one smaller measured step using the already completed Jacobian."""
import ast, datetime, hashlib, json, math, os
from pathlib import Path
import numpy as np
from scipy.optimize import lsq_linear

V = Path(__file__).resolve().parent
OLD = V / 'cellwise_coupled_20261020'
OUT = V / 'cellwise_smallstep_20261020'
PINS = {}

def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def save(path, value):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    os.replace(tmp, path)

def main():
    assert not OUT.exists(), 'Reuse prepared continuation; no duplicate preparation.'
    closure = read(OLD/'owner_closure.json')
    assert closure['recorded_pid_absent'] and closure['actual_exit_code'] == 0
    protocol = read(OLD/'protocol.json')
    audit = read(OLD/'step_audit.json')
    assert audit['observed_reduction'] < 0
    truth = read(OLD/'training_truth.json')
    evaluations = {r['label']:r for r in read(OLD/'evaluations.json')}
    def residual(label):
        parts=[]
        for at in protocol['train_starts']:
            result=read(OLD/f'{label}_{at}.json')
            q=truth[str(at)]
            dn=np.array([r['n'] for r in result['frames']])-np.array([r['n'] for r in q])
            dv=np.array([r['speed'] for r in result['frames']])-np.array([r['speed'] for r in q])
            parts.extend((dn[:,14:21].ravel()/10,dv[:,14:21].ravel()/20))
        return np.concatenate(parts)/math.sqrt(63)
    base=residual('baseline')
    assert abs(float(base@base)-evaluations['baseline']['data_loss'])<1e-12
    columns=[]
    for j,(cell,name) in enumerate(protocol['parameters']):
        label=f'probe1_c{cell}_{name}'
        step=evaluations[label]['relative'][j]
        assert abs(step-.05)<1e-12
        columns.append((residual(label)-base)/step)
    J=np.column_stack(columns)
    lo=np.maximum(protocol['relative_lower'],-.05)
    hi=np.minimum(protocol['relative_upper'],.05)
    solve=lsq_linear(np.vstack([J,math.sqrt(.1/15)*np.eye(15)]),np.r_[-base,np.zeros(15)],bounds=(lo,hi),tol=1e-9,max_iter=100)
    assert solve.success and max(abs(solve.x))<=.05000001
    linear=base+J@solve.x
    assert float(linear@linear)<float(base@base)
    source=V/'run_cellwise_coupled_20261020.py'
    text=source.read_text(encoding='utf8')
    PINS[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
    tree=ast.parse(text)
    old_main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    helpers={n.name:ast.get_source_segment(text,n) for n in old_main.body if isinstance(n,ast.FunctionDef)}
    assert all(k in helpers for k in ('capture','truth','predict'))
    # Copy the three reviewed helper bodies verbatim, except the tighter counter.
    helper_text='\n'.join('    '+line if line else '' for name in ('capture','truth','predict') for line in helpers[name].splitlines())
    # get_source_segment retains inner indentation; normalize each function separately.
    helper_text='\n\n'.join('    '+helpers[name].splitlines()[0]+'\n'+'\n'.join(helpers[name].splitlines()[1:]) for name in ('capture','truth','predict'))
    helper_text=helper_text.replace('assert forecast_count<100','assert forecast_count<4')
    header=text[:text.index('def main():')]
    header=header.replace("O=V/'cellwise_coupled_20261020'", "O=V/'cellwise_smallstep_20261020'\nPREVIOUS=V/'cellwise_coupled_20261020'")
    imports=text[text.index('    sys.path[:0]'):text.index('    initial=np.array(initial)')]
    runtime='''def main():
    assert not (O/'launch.json').exists(), 'Reuse existing invocation.'
    assert not any((p/'STOP').exists() for p in (V,A,O,PREVIOUS))
    preparation=read(O/'protocol.json')
    for path,digest in preparation['source_pins'].items():
        assert sha(path)==digest,path
    assert sha(Path(__file__))==read(O/'preparation_receipt.json')['runner_sha256']
    save(O/'launch.json',dict(pid=os.getpid(),entry_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv,attempts=1))
    active=read(V/'cached_vsl_exposure_audit_v2/active_component_config.json')
    reference=read(OLD/'expanded_joint/eval_036/reference_config.json')
    params=active['parameters'];responses=reference['freeway']['state_response']['FW_E']['cell_overrides']
'''+imports+'''    initial=np.array(preparation['initial'])
    z=np.array(preparation['relative_step'])
    sdmpc.load_prices=lambda *a,**k:(np.zeros(2),dict(source='offline_cellwise_coupled_cold_prices',committed=False))
    captured={};forecast_count=0
'''+helper_text+'''
    for p in (Path(__file__),CONFIG,VERIFY,ROOT/'evaluation/controllers/lane_freeway_runtime.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',ROOT/'evaluation/controllers/freeway_fd.py'):
        PINS[str(p)]=sha(p)
    for at in TIMES:
        capture(at)
        previous=read(PREVIOUS/f'capture_{at}/isolated_capture.json')
        current=read(O/f'capture_{at}/isolated_capture.json')
        assert previous==current,'Initial capture changed'
    actual={str(at):truth(at) for at in TIMES}
    assert actual==read(PREVIOUS/'training_truth.json'),'Training targets changed'
    rows=[predict(at,initial*(1+z),f'fitted_small_{at}') for at in TIMES]
    parts=[];scores={}
    for row in rows:
        q=actual[str(row['start'])]
        dn=np.array([p['n'] for p in row['frames']])-np.array([p['n'] for p in q])
        dv=np.array([p['speed'] for p in row['frames']])-np.array([p['speed'] for p in q])
        nd,vd=dn[:,14:21],dv[:,14:21]
        parts.extend((nd.ravel()/10,vd.ravel()/20))
        scores[str(row['start'])]=dict(n_rmse=float(np.sqrt(np.mean(nd**2))),speed_rmse=float(np.sqrt(np.mean(vd**2))),all31_n_rmse=float(np.sqrt(np.mean(dn**2))),all31_speed_rmse=float(np.sqrt(np.mean(dv**2))))
    residual=np.concatenate(parts)/math.sqrt(63)
    loss=float(residual@residual)
    baseline=preparation['baseline']
    guard=all(scores[str(at)][key]<=1.1*baseline['scores'][str(at)][key] for at in TIMES for key in ('n_rmse','speed_rmse','all31_n_rmse','all31_speed_rmse'))
    eligible=bool(loss<=.99*baseline['data_loss'] and guard)
    selection=dict(candidate_loss=loss,baseline_loss=baseline['data_loss'],training_reduction=1-loss/baseline['data_loss'],scores=scores,retention_guard=guard,eligible_for_development=eligible,relative_step=z.tolist(),values=(initial*(1+z)).tolist(),candidate_adopted=False,nonlinear_convergence_proven=False)
    save(O/'selection.json',selection)
    print('MEASURED_STEP',json.dumps(selection),flush=True)
    if eligible:
        selected=predict(2250,initial*(1+z),'development_twozone90',zones={'FW_E__seg10':90,'FW_E__seg13':90})
        hold=next(r for r in rows if r['start']==2250)
        save(O/'development_response.json',dict(hold=hold,selected=selected,flow_delta=[b-a for a,b in zip(hold['through'],selected['through'])],ttt_delta=selected['ttt']-hold['ttt']))
    for path,digest in PINS.items():assert sha(path)==digest,path
    save(O/'completion.json',dict(status='complete_pending_assessment',forecasts=forecast_count,new_jacobian_probes=0,new_native=0,controller_optimizations=0,production_edits=0,new_fzp_scans=0,future_state_input=False,all_physical_checks_passed=True,source_pins=PINS,candidate_adopted=False,goal_complete=False))
    print('SMALLSTEP_COMPLETE',forecast_count,'eligible',eligible,flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if O.is_dir():save(O/'failure.json',dict(error=repr(error),traceback=traceback.format_exc(),native=0))
        raise
'''
    runner=header+runtime
    ast.parse(runner)
    OUT.mkdir()
    script=V/'run_cellwise_smallstep_20261020.py'
    assert not script.exists()
    script.write_text(runner,encoding='utf8')
    proposal=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reason='Measured rejection of the0.25 step; retain baseline and reduce coordinate trust radius to0.05 using the same15 cached columns. No new derivative probes or coefficient grid.',
        reused_protocol=str(OLD/'protocol.json'),parameters=protocol['parameters'],initial=protocol['initial'],relative_step=solve.x.tolist(),
        values=(np.array(protocol['initial'])*(1+solve.x)).tolist(),baseline=evaluations['baseline'],
        linear_prediction_loss=float(linear@linear),linear_active_bounds=solve.active_mask.tolist(),
        fixed=protocol['fixed'],controls=protocol['controls'],objective=protocol['objective'],gate=protocol['gate'],validation=protocol['validation'],
        budgets=dict(training450=3,development90=1,new_jacobian_probes=0,native=0,controller_optimizations=0),
        decision='Exactly one measured step, no automatic repeat or further optimization. If same training gate passes, one predeclared twozone90 development forecast. No production adoption.',
        source_pins=PINS,candidate_adopted=False,goal_complete=False)
    save(OUT/'protocol.json',proposal)
    save(OUT/'preparation_receipt.json',dict(runner=str(script),runner_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
        helper_source_sha256=PINS[str(source)],helper_names=['capture','truth','predict'],only_helper_edit='prediction counter100 to4',
        new_forecasts=0,new_native=0))
    print(json.dumps({k:proposal[k] for k in ('relative_step','linear_prediction_loss','budgets')},indent=2))

if __name__=='__main__':main()
