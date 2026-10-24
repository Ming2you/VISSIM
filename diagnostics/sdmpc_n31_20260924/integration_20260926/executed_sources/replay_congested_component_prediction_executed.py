"""Bridge completed response inputs into the selected checkout's sole plant.

Capture runs in a separate process against the historical input builder and
stops BEFORE its rollout/scoring. Prediction imports only the selected checkout.
No native runs, fitting, future observed inputs, or new adapter are involved.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT.parent/'control-full-review'
OUT=HERE/'congested_replay'


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def capture():
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c
    data,ctx,_,_=c.inputs()
    prior=e.HERE/'legal_release2670'
    assert load(prior/'status.json')['stage']=='complete_response_validation'
    protocol=load(prior/'protocol.json')
    assert protocol['source_sha']==load(HERE/'selected/plant_n31_v2.json')['sources']['network']['sha256']
    ctx=list(copy.deepcopy(ctx));ctx[3]=protocol['port_profile']
    model=c.prior.one.base.load_base_model(data['rm'].geometry,e.HERE/'local_fd/candidate.json')
    OUT.mkdir(exist_ok=False)
    class Captured(BaseException): pass
    records=[]
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        commands={int(k):v for k,v in load(prior/f'{arm}_commands.json').items()}
        def intercept(*args,**kwargs):
            # Native future truth is scored only after model.rollout, which
            # this capture deliberately never enters.
            json.dumps([args,kwargs],allow_nan=False)
            payload=pickle.dumps((args,kwargs),protocol=5)
            path=OUT/(arm+'_input.pickle');path.write_bytes(payload)
            records.append(dict(arm=arm,input=path.name,sha256=sha(path),
                truth=str(prior/'observations'/arm),previous_native_result=str(prior/f'{arm}_result.json'),
                previous_prediction=str(prior/f'{arm}_prediction.json.gz'),
                command_sha256=sha(prior/f'{arm}_commands.json')))
            raise Captured()
        model.rollout=intercept
        try:
            c.prior.forecast(model,protocol['parameters'],data['rm'],data['rm'],2670.1,450,
                             *ctx[:-1],commands,True)
            raise AssertionError('Rollout input not captured')
        except Captured: pass
    save(OUT/'capture.json',dict(source_network=protocol['source_sha'],cutoff=2670.1,horizon=450,
        geometry_sha256=sha(data['rm'].folder/'geometry.json'),records=records,
        parameter_source=str(prior/'protocol.json'),parameter_sha256=sha(prior/'protocol.json'),
        builder_sources={str(p):sha(p) for p in (Path(c.prior.__file__),Path(c.prior.one.__file__),Path(__file__))},
        cutoff_truncation_assertion_passed=True,native_started=False,future_truth_read_for_prediction=False))
    print(json.dumps(dict(captured=len(records),folder=str(OUT))),flush=True)


def predict():
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];manifest=load(OUT/'capture.json')
    assert context['document']['sources']['network']['sha256']==manifest['source_network']
    results=[]
    for row in manifest['records']:
        p=OUT/row['input'];assert sha(p)==row['sha256']
        args,kwargs=pickle.loads(p.read_bytes()) # only our locally generated pinned primitives
        assert args[2]==context['parameters'], 'Selected coefficients differ; do not silently replace them'
        assert kwargs['roads']==['FW_E'] and kwargs['horizon_sec']==450
        started=time.perf_counter();pred=model.rollout(*args,**kwargs)
        wall=time.perf_counter()-started
        with gzip.open(OUT/(row['arm']+'_prediction.json.gz'),'wt',encoding='utf-8') as f:
            json.dump(pred,f,allow_nan=False)
        # Open future observations ONLY after completing this prediction.
        truth=ObservationData(row['truth']);t0=manifest['cutoff']
        initial_n=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
        times=[round(t0+d,6) for d in range(0,451,30)]
        port_ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
        port_ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
        observed_main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
        observed_port={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in port_ids) for t in times}
        predicted_main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
        predicted_port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
            sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
        assert observed_main[t0]==initial_n
        predicted_main[t0]=initial_n;predicted_port[t0]=observed_port[t0]
        integral=lambda values:sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        flows={}
        for label,records in [('predicted',pred['flows']),('actual',[dict(v,window_end_s=t)
                for (t,r,c),v in truth.flows.items() if r=='FW_E' and t0<t<=times[-1]])]:
            flows[label]={key:sum(float(x[key]) for x in records) for key in
                          ('source_admissions','off_departures','terminal_exits' if label=='predicted' else 'terminal_exits_inferred')}
        merges={r:sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']==r) for r,v in model.ramps.items() if v['road']=='FW_E'}
        actual_merges={r:sum(float(truth.ports[t,str(model.ramps[r]['connector'])]['departures_veh']) for t in times[1:]) for r in merges}
        score=score_rollout(truth,t0,pred,'FW_E',include_source_boundary=True)
        assert not score['invalid']
        residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']]+[abs(x['conservation_residual_veh']) for x in pred['ramps']])
        assert residual<1e-7
        previous=load(row['previous_native_result'])
        item=dict(arm=row['arm'],wall_sec=wall,score=score,conservation_max=residual,
            predicted_mainline_ttt=integral(predicted_main),actual_mainline_ttt=integral(observed_main),
            predicted_port_ttt=integral(predicted_port),actual_port_ttt=integral(observed_port),
            predicted_merge=merges,actual_merge=actual_merges,flows=flows,
            native_total_cost=previous['native'])
        item['predicted_component_ttt']=item['predicted_mainline_ttt']+item['predicted_port_ttt']
        item['actual_component_ttt']=item['actual_mainline_ttt']+item['actual_port_ttt']
        results.append(item);save(OUT/(row['arm']+'_result.json'),item)
        print(json.dumps(dict(arm=row['arm'],wall_sec=wall,predicted=item['predicted_component_ttt'],actual=item['actual_component_ttt'])),flush=True)
    base=results[0]
    for row in results:
        row['deltas']={k:row[k]-base[k] for k in ('predicted_component_ttt','actual_component_ttt','predicted_mainline_ttt','actual_mainline_ttt','predicted_port_ttt','actual_port_ttt')}
        row['deltas']['predicted_merge']=sum(row['predicted_merge'].values())-sum(base['predicted_merge'].values())
        row['deltas']['actual_merge']=sum(row['actual_merge'].values())-sum(base['actual_merge'].values())
    save(OUT/'summary.json',dict(results=results,gain_qualified=False,calibration=False,
        scope='East31 cells plus8 ramp connectors; not full urban/Omega prediction',
        total_native_cost_scope='All network plus latent waiting; independent scope, not compared numerically to component prediction',
        independent_holdout=False,source_file_pins={str(p):sha(p) for p in
            (Path(lpr.__file__),Path(sys.modules[model.__class__.__module__].__file__),HERE/'selected/plant_n31_v2.json',Path(__file__))}))


if __name__=='__main__':
    {'capture':capture,'predict':predict}[sys.argv[1]]()
