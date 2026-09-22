"""One local resolution hypothesis; retain the existing plant and all coefficients.

The port mesh did not subdivide the 526m approach cells5-7. Test cell7 alone
and then the contiguous5-7 approach at the existing <=200m target. No fitting.
"""
from pathlib import Path
import bisect,copy,json,math,subprocess,sys,time
from collections import Counter
import numpy as np
import vsl_response as v
from prepare import save,table
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.segment_resolution_20260921 import run as runner
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;K=v.K;O=B/'approach_resolution_v1'
GUARD=c.load(B/'geometry_200_branch_guard.json');PARENT=c.load(B/'parent_map.json')


def refine(selected,max_m=200):
    # Restrict this diagnostic to port-free approaches or downstream cells.
    # Existing ramp cells and the internal10643 partition remain unchanged.
    assert set(selected)<=set(range(5,8)) or set(selected)<=set(range(25,31))
    assert max_m in (100,200)
    geo=copy.deepcopy(GUARD);geo['cells']=[];geo['bounds']={}
    parents={};previous={}
    for road in GUARD['chains']:
        parents[road]=[];previous[road]=[];geo['bounds'][road]=[0.]
        old=[r for r in GUARD['cells'] if r['road']==road]
        for cell in old:
            n=math.ceil(cell['length_km']*1000/max_m) if road=='FW_E' and cell['cell'] in selected else 1
            for j in range(n):
                a=cell['start_m']+(cell['end_m']-cell['start_m'])*j/n
                z=cell['start_m']+(cell['end_m']-cell['start_m'])*(j+1)/n
                child=copy.deepcopy(cell);pieces=[];cursor=cell['start_m']
                for piece in cell['physical_pieces']:
                    length=max(0.,min(z,cursor+piece['length_m'])-max(a,cursor))
                    if length>1e-8:pieces.append({**piece,'length_m':length})
                    cursor+=piece['length_m']
                assert abs(sum(x['length_m'] for x in pieces)-(z-a))<1e-7
                child.update(cell=len(parents[road]),start_m=a,end_m=z,length_km=(z-a)/1000,
                    lane_km=sum(p['length_m']*p['lanes'] for p in pieces)/1000,physical_pieces=pieces)
                geo['cells'].append(child);geo['bounds'][road].append(z)
                parents[road].append(PARENT[road][cell['cell']]);previous[road].append(cell['cell'])
        for cell in old:
            children=[r for r,p in zip([r for r in geo['cells'] if r['road']==road],previous[road]) if p==cell['cell']]
            for key in ('length_km','lane_km'):assert abs(sum(r[key] for r in children)-cell[key])<1e-8
            assert children[0]['start_m']==cell['start_m'] and children[-1]['end_m']==cell['end_m']
    for p in geo['boundaries']:
        road=p['road'];i=min(len(parents[road])-1,bisect.bisect_right(geo['bounds'][road],p['chain_pos_m'])-1)
        if p['from_cell'] is not None:p['from_cell']=i
        if p['to_cell'] is not None:p['to_cell']=i
        if p['kind'] in ('ramp','offramp'):
            row=next(r for r in geo['cells'] if r['road']==road and r['cell']==i)
            assert row['start_m']<p['chain_pos_m']<row['end_m']
    ports=[p for p in geo['boundaries'] if p['kind'] in ('ramp','offramp')]
    assert len(ports)==16
    assert max(Counter((p['road'],p['from_cell'] if p['kind']=='offramp' else p['to_cell']) for p in ports).values())==1
    assert [r for r in geo['cells'] if r['road']=='FW_W']==[r for r in GUARD['cells'] if r['road']=='FW_W']
    return geo,parents,previous


def run_case(label,selected,initial,max_m=200,reference=None,arms=None,rm_fit=False):
    geo,parents,previous=refine(selected,max_m)
    reference_folder=reference or v.O/'vr_hadi_fd_cap_r2_validation'
    arms=list(f.ARMS if arms is None else arms)
    spec=copy.deepcopy(initial);spec.update(name='ar_'+label,output_group=O.name,arms=arms)
    if selected:
        save(O/(label+'_geometry.json'),geo);save(O/(label+'_parents.json'),parents)
        save(O/(label+'_guard_parents.json'),previous)
        spec['diagnostic_mesh']=dict(geometry=O.name+'/'+label+'_geometry.json',parents=O.name+'/'+label+'_parents.json',initial_groups=O.name+'/'+label+'_initial_groups.json')
        old=spec['hadiuzzaman'];old['cells']=[copy.deepcopy(old['cells'][i]) for i in previous['FW_E']]
        old['relaxation_cells']=[i for i,p in enumerate(previous['FW_E']) if p in initial['hadiuzzaman']['relaxation_cells']]
        if spec['state_response'].get('cell_overrides'):
            overrides=initial['state_response']['cell_overrides']
            spec['state_response']['cell_overrides']={str(i):copy.deepcopy(overrides[str(p)])
                for i,p in enumerate(previous['FW_E']) if str(p) in overrides}
        for region in spec.get('regional_physical_coefficients',[]):
            old_cells=set(region['cells']);region['cells']=[i for i,p in enumerate(previous['FW_E']) if p in old_cells]
    specpath=O/(spec['name']+'.json');receiptpath=O/spec['name']/'refined_guard1_receipt.json'
    reused=receiptpath.exists()
    if reused:
        receipt=c.load(receiptpath);assert c.load(specpath)==spec and receipt['fit']==spec
        assert receipt['completed'] and receipt['forecasts']==len(arms) and receipt['runner_sha256']==c.sha(B/'run.py')
        wall=None # Original parent elapsed time was not persisted; do not invent it.
    else:
        save(specpath,spec);started=time.perf_counter()
        with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(specpath)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        wall=time.perf_counter()-started
    checks={};arrays={};exact=[];source=[];rm_predictions={}
    oldcells={(r['road'],r['cell']):r for r in GUARD['cells']}
    for arm in arms:
        p=f.load_prediction(O/spec['name']/f'refined_guard1_{arm}.json')
        reference=f.load_prediction(reference_folder/f'refined_guard1_{arm}.json')
        c.G=geo
        try:checks[arm]=c.screen(p)
        finally:c.G=GUARD
        for key in ('cells','flows'):
            assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
        if not selected:assert p==reference;exact.append(arm)
        aggregate=runner.aggregate(p,previous,oldcells) if selected else p
        if arm=='none':nc=dict(train=c.score(aggregate),late=c.score(aggregate,10,15),
            all_nonterminal=c.score(aggregate,0,15,range(30)),
            downstream=c.score(aggregate,0,15,range(25,30)))
        if arm in ('none','vsl'):arrays[arm]=c.predicted(aggregate)
        if rm_fit and arm in ('none','rm_ramp'):rm_predictions[arm]=aggregate
        # Conservative aggregation includes only the ORIGINAL external border
        # discharge, not the additional internal child-boundary crossings.
        for lo,hi in ((0,5),(5,10),(10,15)):
            rows=aggregate['lane_groups']['FW_E'];a=2400+lo*30;z=2400+hi*30
            part=[r for r in rows if r['cell']==7 and a<r['time_s']<=z]
            source.append(dict(label=label,arm=arm,start_s=a,end_s=z,
                boundary_veh=sum(r['mainline_out_veh'] for r in part),
                stock_mean=sum(r['n_veh'] for r in part)/(z-a),
                speed_mean=sum(r['n_veh']*r['v_kmh'] for r in part)/sum(r['n_veh'] for r in part)))
    effective=c.load(O/spec['name']/'effective_config.json');assert len(effective)==len(arms)
    for entry in effective:
        assert entry['receiving']['FW_E']==spec['hadiuzzaman']
        assert entry['state_response']['FW_E']==spec['state_response']
        assert entry['scalar']==spec['physical_coefficients'] and entry['port_response']['FW_E']==spec['port_response']
        for i,row in enumerate(entry['rows']):
            expected={k:spec['physical_coefficients'][k] for k in ('v_free','rho_crit','rho_max','metanet_a_m','metanet_kappa_veh_km_lane')}
            for region in spec.get('regional_physical_coefficients',[]):
                if i in region['cells']:expected.update(region['coefficients'])
            assert all(row[k]==x for k,x in expected.items())
    if selected:
        new=c.load(O/(label+'_initial_groups.json'));old=c.load(B/'guard_initial_groups.json')
        for i,group in enumerate(old['initial_groups']):
            indices=[j for j,p in enumerate(previous['FW_E']) if p==i]
            for g,r in enumerate(group):
                children=[new['initial_groups'][j][g] for j in indices]
                assert sum(x['n_veh'] for x in children)==r['n_veh']
                # Empty observed groups have no measured mean speed (None).
                moment=sum(x['n_veh']*x['v_kmh'] for x in children if x['n_veh'])
                assert abs(moment-(r['n_veh']*r['v_kmh'] if r['n_veh'] else 0.))<1e-6
            for j in indices:
                assert new['widths'][j]==old['widths'][i]
                assert new['exchange_rates_per_sec'][j]==old['exchange_rates_per_sec'][i]
                assert spec['hadiuzzaman']['cells'][j]==initial['hadiuzzaman']['cells'][i]
                assert (j in spec['hadiuzzaman']['relaxation_cells'])==(i in initial['hadiuzzaman']['relaxation_cells'])
        for p in new['off_access'].values():assert p['cell'] not in [j for j,i in enumerate(previous['FW_E']) if i in selected]
    result=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
    scores={}
    if set(arrays)=={'none','vsl'}:
        for phase,lo,hi in [('train',0,10),('late',10,15)]:_,scores[phase]=v.response_metrics(arrays,lo,hi)
    value=dict(label=label,selected_guard_cells=selected,max_child_length_m=max_m,numerics=checks,nc=nc,response=scores,deltas=result['deltas'],
        exact_default_arms=exact,wall_seconds=wall,reused_completed_predictions=reused,east_cell_count=len(parents['FW_E']),adopted=False)
    if rm_fit:
        residual,metrics=rm_residual(rm_predictions);np.save(O/(label+'_residual.npy'),residual)
        value.update(rm_fit=metrics)
    save(O/(label+'_summary.json'),value);table(O/(label+'_approach.csv'),source)
    print(json.dumps(dict(label=label,**value['rm_fit'],seconds=wall) if rm_fit else value),flush=True);return value


def rm_residual(predictions):
    """Same error scales as the VSL fit, now measuring RM response explicitly."""
    import ramp_region as regional
    pred={a:c.predicted(p) for a,p in predictions.items()};obs={'none':v.observed('none')}
    with np.load(O/'observed_rm_ramp.npz') as z:obs['rm_ramp']={k:z[k] for k in z.files}
    errors=[[],[],[]]
    for i in range(30):
        ng=len(c.WIDTHS[i]);speed={}
        for arm in ('none','rm_ramp'):
            speed[arm]=[]
            for data in (obs,pred):
                n=data[arm]['n'][:,i,:ng];m=data[arm]['mom'][:,i,:ng]
                speed[arm].append(np.divide(m,n,out=np.zeros_like(n),where=n>0))
        mask=(obs['none']['n'][:,i,:ng]>=1)&(obs['rm_ramp']['n'][:,i,:ng]>=1)
        errors[0].extend(((speed['rm_ramp'][1]-speed['none'][1])-(speed['rm_ramp'][0]-speed['none'][0]))[mask])
        for dest,key,scale in ((errors[1],'n',1),(errors[2],'q',120)):
            sl=(slice(None),i,slice(ng)) if key=='n' else (slice(None),i)
            dest.extend(((pred['rm_ramp'][key][sl]-pred['none'][key][sl]-(obs['rm_ramp'][key][sl]-obs['none'][key][sl]))*scale).ravel())
    response=np.concatenate([np.asarray(e)/scale/np.sqrt(len(e)) for e,scale in zip(errors,(10,2,200))])
    state=regional.nc_residual(predictions['none'],0,15,range(30));r=np.concatenate((state,response))
    return r,dict(objective=float(r@r),nc_loss=float(state@state),response_loss=float(response@response),
        delta_speed_rmse=float(np.sqrt(np.mean(np.square(errors[0])))),
        delta_group_n_rmse=float(np.sqrt(np.mean(np.square(errors[1])))),
        delta_boundary_q_rmse=float(np.sqrt(np.mean(np.square(errors[2])))))


def main():
    resume=len(sys.argv)>1 and sys.argv[1]=='resume'
    if not resume:assert not (O/'protocol.json').exists()
    initial=c.load(v.O/'vr_hadi_fd_cap_r2_validation.json')
    protocol_path=O/('resume_protocol.json' if resume else 'protocol.json');assert not protocol_path.exists()
    save(protocol_path,dict(hypothesis='Port-only refinement left the causal VSL approach in526m cells; isolate spatial averaging in cells5-7.',
        variants={'baseline':[],'cell7':[7],'cells5_7':[5,6,7]},max_child_length_m=200,
        no_parameter_fitting=True,future_inputs=False,independent_validation=False,adopted=False,
        initial_s=2400,end_s=2850,seed=23,arms=list(f.ARMS),fixed=['coefficients','demand','commands','physical_geometry','branch pre/post lengths','widths','lane exchange rates','costs','1s diagnostic step'],
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',B/'geometry_200_branch_guard.json',B/'guard_initial_groups.json',v.O/'vr_hadi_fd_cap_r2_validation.json']}))
    results=[]
    for label,selected in [('baseline',[]),('cell7',[7]),('cells5_7',[5,6,7])]:
        results.append(run_case(label,selected,initial));save(O/('results_resume.json' if resume else 'results.json'),dict(results=results,qualified=False))


def downstream():
    """Test attenuation beyond the ramps, using frozen current coefficients."""
    global O
    O=B/'downstream_resolution_v1';assert not (O/'protocol.json').exists()
    reference=B/'ramp_region_v1/region_selected_actions'
    initial=c.load(reference.with_suffix('.json'))
    sources=[Path(__file__),B/'run.py',B/'geometry_200_branch_guard.json',B/'guard_initial_groups.json',
        reference.with_suffix('.json'),B/'none_s23_0.npz',B/'rm_ramp_s23_0.npz']
    save(O/'protocol.json',dict(hypothesis='RM native response changes sign over time and propagates beyond the refined ramps, but remaining downstream500m cells may attenuate that response.',
        variants={'dr_baseline':dict(cells=[],max_m=200),'dr_200':dict(cells=list(range(25,31)),max_m=200),
                  'dr_100':dict(cells=list(range(25,31)),max_m=100)},
        initial_s=2400,end_s=2850,seed=23,arms=list(f.ARMS),forecasts_planned=12,new_native=0,
        future_inputs=False,independent_validation=False,production_adopted=False,no_parameter_fitting=True,
        fixed=['all coefficients including regional overrides','ramp/off cells and partition lengths','physical geometry','initial stock and speed moment per original cell',
               'demand/route forecast','actuators and timing','lane exchange and receiving rates','1s diagnostic integration','waiting costs'],
        checks='Default4 wholeJSON exact; children inherit parameters/widths/exchange, source stock/momentum preserved, west exact, numeric/CFL/conservation. Compare original external boundary flows after aggregation.',
        gate='VSL gain sign and RM magnitude/components must improve without >10% all-nonterminal or downstream NC loss; a resolution-only match is not qualification.',
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    # Native side uses the existing1s spatial aggregates; predictions are
    # aggregated by vehicle count and velocity moment, never by unweighted v.
    native={};pred={};rows=[]
    for arm in ('none','rm_ramp'):
        with np.load(B/(arm+'_s23_0.npz')) as z:native[arm]={k:z[k][152:602].sum(axis=2) for k in ('n','mom')}
        p=f.load_prediction(reference/f'refined_guard1_{arm}.json')
        pred[arm]={k:np.zeros((450,21)) for k in ('n','mom')}
        for r in p['lane_groups']['FW_E']:
            t=int(r['time_s'])-2401;i=PARENT['FW_E'][r['cell']]
            pred[arm]['n'][t,i]+=r['n_veh'];pred[arm]['mom'][t,i]+=r['n_veh']*r['v_kmh']
    for i in range(21):
        for lo in (0,150,300):
            row=dict(original_cell=i,start_s=2400+lo,end_s=2550+lo)
            for tag,data in [('native',native),('model',pred)]:
                ns=[data[a]['n'][lo:lo+150,i].sum() for a in ('none','rm_ramp')]
                vs=[data[a]['mom'][lo:lo+150,i].sum()/ns[j] for j,a in enumerate(('none','rm_ramp'))]
                row.update({tag+'_RM_delta_ttt':float((ns[1]-ns[0])/3600),tag+'_RM_delta_speed':float(vs[1]-vs[0])})
            rows.append(row)
    table(O/'rm_space_time_before.csv',rows)
    results=[]
    for label,selected,size in [('dr_baseline',[],200),('dr_200',list(range(25,31)),200),('dr_100',list(range(25,31)),100)]:
        results.append(run_case(label,selected,initial,size,reference));save(O/'results.json',dict(results=results,qualified=False))


def recalibrate_downstream():
    """Refit each mesh separately; test shared-state response, not a lever bonus."""
    global O
    O=B/'downstream_calibration_v1';assert not (O/'protocol.json').exists()
    sys.path.insert(0,str(ROOT/'tmp/calibration_dependencies'));from scipy.optimize import least_squares
    keys=('rho_crit','shape','tau_acc','tau_dec','nu_high','nu_low')
    reference=B/'ramp_region_v1/region_selected_actions';initial=c.load(reference.with_suffix('.json'))
    initial['control_response_fit']=dict(training=[2400,2850],commands=['none','rm_ramp'],
        independent_validation=False,protocol=O.name+'/protocol.json',scope='Downstream port-free cells25-30 only')
    sources=[Path(__file__),B/'run.py',B/'calibrate.py',B/'ramp_region.py',B/'geometry_200_branch_guard.json',
        B/'guard_initial_groups.json',reference.with_suffix('.json'),c.O/'observed_none.npz']
    save(O/'protocol.json',dict(meshes=[200,100],original_guard_cells=list(range(25,31)),parameters=list(keys),
        bounds={k:f.BOUNDS[k][:2] for k in keys},maximum_fit_pairs_per_mesh=16,optimizer_max_nfev=2,
        train=[2400,2850],commands_for_fit=['none','rm_ramp'],checks_after_freeze=['vsl','both'],
        check_independence='Same development seed and previously examined controls; NOT independent holdout or late-time validation.',
        objective='Original30 nonterminal cells; NC speed/20,N/5,q/500 plus RM-NC speed/10,N/2,q/200 squared RMSE; fixed observed masks.',
        selection='Lowest training objective with numerics PASS and NC all-nonterminal AND downstream losses <=110% of frozen original31-cell reference.',
        fixed=['geometry per mesh','ramp-neighbor parameters','merge delta','receiving Q/wave/jam/drop','physical widths/storage',
               'port drainage','signals/routes/demand','command profiles','waiting costs','1s diagnostic step'],
        new_native=0,future_inputs=False,independent_validation=False,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in sources}))
    if not (O/'observed_rm_ramp.npz').exists():c.observe('rm_ramp_s23',O)
    assert c.load(O/'rm_ramp_s23_observation_proof.json')['refined_geometry_sha256']==c.sha(B/'geometry_200_branch_guard.json')
    print('RM observation complete',flush=True)
    low=np.array([f.BOUNDS[k][0] for k in keys]);span=np.array([f.BOUNDS[k][1]-f.BOUNDS[k][0] for k in keys])
    x0=(np.array([initial['calibration_values'][k] for k in keys])-low)/span
    guard=c.load(B/'downstream_resolution_v1/dr_baseline_summary.json')['nc']
    def specification(values):
        spec=copy.deepcopy(initial);spec['local_calibration_values']=values
        local={k:copy.deepcopy(x) for k,x in spec['state_response'].items() if k!='cell_overrides'}
        local['relaxation']=dict(acceleration_sec=values['tau_acc'],deceleration_sec=values['tau_dec'])
        local['anticipation']=dict(downstream_ge_local=values['nu_high'],downstream_lt_local=values['nu_low'])
        for i in range(25,31):
            spec['state_response']['cell_overrides'][str(i)]=copy.deepcopy(local)
            spec['hadiuzzaman']['cells'][i]['rho_critical']=values['rho_crit']
        spec['regional_physical_coefficients']=[dict(cells=list(range(25,31)),coefficients=dict(rho_crit=values['rho_crit'],metanet_a_m=values['shape']))]
        return spec
    for size in (200,100):
        history=[];seen={};jacobians=[]
        class Budget(Exception):pass
        def objective(x):
            key=tuple(x)
            if key in seen:return seen[key]
            if len(history)>=16:raise Budget()
            values=({k:initial['calibration_values'][k] for k in keys} if np.array_equal(x,x0)
                    else dict(zip(keys,(low+span*x).tolist())))
            label=f'dc{size}_{len(history):02}'
            row=run_case(label,list(range(25,31)),specification(values),size,reference,('none','rm_ramp'),True)
            row['values']=values;history.append(row)
            residual=np.load(O/(label+'_residual.npy'))
            if not all(r['passed'] for r in row['numerics'].values()):residual=np.full(len(residual),100.)
            seen[key]=residual;save(O/f'fit_{size}_history.json',history)
            if len(history)==1:
                for arm in ('none','rm_ramp'):
                    assert f.load_prediction(O/('ar_'+label)/f'refined_guard1_{arm}.json')==f.load_prediction(B/f'downstream_resolution_v1/ar_dr_{size}'/f'refined_guard1_{arm}.json')
                save(O/f'identity_{size}.json',dict(full_json_exact=2,regional_values=values))
            return residual
        def jac(x):
            base=objective(x);cols=[];entries=[]
            for i,key in enumerate(keys):
                step=.025 if x[i]+.025<=1 else -.025;z=x.copy();z[i]+=step
                difference=objective(z)-base;cols.append(difference/step)
                entries.append(dict(parameter=key,absolute_step=float(step*span[i]),residual_change_norm=float(np.linalg.norm(difference))))
            jacobians.append(dict(x=x.tolist(),entries=entries));save(O/f'fit_{size}_jacobians.json',jacobians)
            return np.stack(cols,axis=1)
        try:
            opt=least_squares(objective,x0,jac=jac,bounds=(np.zeros(len(keys)),np.ones(len(keys))),max_nfev=2,
                ftol=.005,xtol=.005,gtol=.005,tr_solver='lsmr')
            stop=dict(status=int(opt.status),message=opt.message,nfev=int(opt.nfev),njev=int(opt.njev))
        except Budget:stop=dict(status=0,message='16 paired candidate budget reached')
        good=[r for r in history if all(x['passed'] for x in r['numerics'].values()) and
            all(r['nc'][zone]['objective']<=1.1*guard[zone]['objective'] for zone in ('all_nonterminal','downstream'))]
        best=min(good,key=lambda r:r['rm_fit']['objective'])
        save(O/f'selection_{size}.json',dict(selected=best['label'],values=best['values'],
            baseline_training=history[0]['rm_fit'],selected_training=best['rm_fit'],optimizer=stop,
            fit_pairs=len(history),production_adopted=False,qualified=False))
        print('FROZEN',size,best['label'],best['rm_fit'],stop,flush=True)
        label=f'dc{size}_actions';result=run_case(label,list(range(25,31)),specification(best['values']),size,reference,None,True)
        for arm in ('none','rm_ramp'):
            assert f.load_prediction(O/('ar_'+label)/f'refined_guard1_{arm}.json')==f.load_prediction(O/('ar_'+best['label'])/f'refined_guard1_{arm}.json')
        save(O/f'validation_{size}.json',dict(result=result,selected_fit_outputs_exact=2,qualified=False,
            independent_validation=False,production_adopted=False,new_native=0))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='downstream':downstream()
    elif len(sys.argv)>1 and sys.argv[1]=='calibrate-downstream':recalibrate_downstream()
    else:main()
