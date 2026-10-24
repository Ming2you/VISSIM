"""One frozen coefficient ablation: restore cells24/25, no optimizer/native."""
from pathlib import Path
import copy,gzip,json,math,sys,time

OUT=Path(__file__).resolve().parent
CW=OUT.parent
ROOT=next(p for p in OUT.parents if (p/'evaluation/controllers/lane_plant_runtime.py').is_file())
sys.path.insert(0,str(ROOT))
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r
from evaluation.controllers import lane_plant_runtime as lpr
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData


def main():
    out=OUT/'reset24_25';out.mkdir(exist_ok=False)
    spec=r.load(CW/'parameter_spec.json');selected=r.load(CW/'jacobian_step/selection.json')
    baseline=r.load(CW/'jacobian_step'/selected['selected']/'result.json')
    cap=r.load(OUT/'capture.json');wide=r.load(OUT/'summary.json')
    document=r.load(spec['initial_manifest']);ctx=lpr.load_sources(spec['initial_manifest'])
    original=r.load(ROOT/document['sources']['reference_config']['path'])
    values=list(selected['values']);relative=list(selected['relative_values']);changed=[]
    for i,v in enumerate(spec['variables']):
        if v['cell'] in (24,25):
            changed.append(dict(cell=v['cell'],parameter=v['parameter'],before=values[i],after=v['initial']))
            values[i]=v['initial'];relative[i]=0.
    assert len(changed)==10
    config=r._cellwise_config(spec,values,original,ctx['parameters']['by_direction']['FW_E']['rho_crit_multiplier'])
    path=out/'reference_config.json';r.save(path,config)
    document['sources']['reference_config']=dict(path=path.relative_to(ROOT).as_posix(),sha256=r.sha(path))
    document['qualification']='One unqualified frozen-cellwise ablation, only24/25 restored. No fit or deployment.'
    path=out/'manifest.json';r.save(path,document);model=lpr.load_sources(path)['component']
    pairs=[x for x in r.load(CW/'data_catalog.json')['checked_records'] if x['role']=='train']
    train=pairs+[x for x in cap['records'] if x['seed']==29]
    checks=[x for x in r.load(CW/'data_catalog.json')['checked_records'] if x['case']=='s43_early']
    checks += [x for x in cap['records'] if x['seed']==43]
    assert len(train)==13 and len(checks)==6
    loss_protocol=r.load(CW/'protocol.json')
    base_rows=baseline['rows']+[x for x in wide['rows']['cellwise'] if x['case'].startswith('s29_')]
    base_loss=r._cellwise_losses(base_rows,selected['relative_values'],loss_protocol)
    pins={**r.load(OUT/'protocol.json')['core_pins'],str(Path(__file__)):r.sha(__file__),str(Path(r.__file__)):r.sha(r.__file__)}
    for x in train+checks:
        pins[x['input']]=x['sha256']
        for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv','boundaries_30s.csv','geometry.json'):
            p=Path(x['truth'])/name;pins[str(p)]=r.sha(p)
    for p,h in pins.items():assert r.sha(p)==h
    r.save(out/'protocol.json',dict(changes=changed,train_cases=[(x['case'],x['arm']) for x in train],
        checks=[(x['case'],x['arm']) for x in checks],max_new_forecasts=19,pins=pins,
        selection='One ablation only, no coefficient tuning. Only proceed to checks if train paired loss<=105% frozen and meanN/q RMSE<=110%, with meaningful signs retained.',
        justification='Five broader seed29 NC states show worsening24/25 bias after prior159 fit. Other fitted cells retained.',
        old_loss=base_loss,fit=False,new_native=0,production_adopted=False))
    started=time.perf_counter();completed=0;observations={}
    def run(records,label):
        nonlocal completed
        folder=out/label;folder.mkdir();rows=[]
        for x in records:
            args,kw=r.read_primitive_capture(x['input'],x['sha256']);assert args[2]==ctx['parameters']
            pred=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kw));completed+=1
            name=x['case']+'_'+x['arm']
            with gzip.open(folder/(name+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            if x['truth'] not in observations:observations[x['truth']]=ObservationData(x['truth'])
            row=r._cellwise_measure(model,pred,x,observations[x['truth']]);rows.append(row)
            r.save(folder/(name+'_result.json'),row)
            r.save(out/'status.json',dict(stage=label,completed=completed,last_case=name))
            print(json.dumps(dict(stage=label,case=name,completed=completed)),flush=True)
        return dict(rows=rows,loss=r._cellwise_losses(rows,relative,loss_protocol))
    result=run(train,'train');loss=result['loss']
    gate=loss['response']<=1.05*base_loss['response'] and loss['mean_n_rmse']<=1.1*base_loss['mean_n_rmse'] and loss['mean_q_rmse']<=1.1*base_loss['mean_q_rmse'] and loss['meaningful_signs_pass']
    r.save(out/'train.json',result);r.save(out/'selection.json',dict(proceed_to_checks=gate,train_loss=loss,old_loss=base_loss))
    check=run(checks,'checks') if gate else None
    for p,h in pins.items():assert r.sha(p)==h
    r.save(out/'summary.json',dict(train=result,check=check,gate=gate,completed=completed,wall_sec=time.perf_counter()-started,
        scope='East31+8connectors, not fullOmega',fit=False,new_native=0,production_adopted=False,gain_qualified=False))
    r.save(out/'status.json',dict(stage='complete',completed=completed,training_gate_passed=gate))


if __name__=='__main__':main()
