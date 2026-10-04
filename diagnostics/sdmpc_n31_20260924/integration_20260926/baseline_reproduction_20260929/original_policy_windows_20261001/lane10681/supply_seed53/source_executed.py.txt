"""Frozen10681 supply hypothesis on existing seed53 common-state450 tests."""
import copy,gzip,json,time
from pathlib import Path
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
HERE=Path(__file__).resolve().parent;OUT=HERE/'lane10681/supply_seed53';OUT.mkdir(exist_ok=False)
cw=r.HERE/'baseline_reproduction_20260929/cellwise_calibration'
admission=r.load(cw/'additional_admission_s53.json');records=admission['records']
model=lpr.load_sources(cw/'expanded_joint/eval_036/manifest.json')['component'];meter='RM_C10681'
pins={str(Path(__file__)):r.sha(__file__)}
for p in (r.ROOT/'evaluation/controllers').glob('*.py'):pins[str(p)]=r.sha(p)
for z in model.provenance['model_files']:pins[str(r.ROOT/z)]=r.sha(r.ROOT/z)
r.save(OUT/'protocol.json',dict(maximum_full_forecasts=8,expected_forecasts=5,calibration=False,
    candidate='Same parameter-free10681 posthead triangular receiving as supply_candidate; every other cell/ramp unchanged.',
    acceptance='One cached baseline exact replay permits other3baseline reuse. Evaluate4independent-seed arms includingVSL; no parameter changes or fit. All cohorts/conservation and material response directions must remain.',
    previously_inspected_seed=True,not_fit_seed=True,new_native=0,scope='East31+8connector,notfullOmega',pins=pins))
started=time.perf_counter();rows=[];baseline_rows=[];baseline_exact=None;completed=0
original=PhysicalRampBoundary.apply_head_service
for rec in records:
    args,kw=r.read_primitive_capture(rec['input'],rec['sha256'])
    oldp=cw/'freeway_first/expanded_seed53/expanded'/(rec['arm']+'_prediction.json.gz');pins[str(oldp)]=r.sha(oldp)
    with gzip.open(oldp,'rt') as f:old=json.load(f)
    truth=ObservationData(rec['truth'])
    if baseline_exact is None:
        begin=time.perf_counter();base=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kw));completed+=1
        base=json.loads(json.dumps(base))
        same={key:base[key]==old[key] for key in ['cells','flows','ports','ramps']}
        baseline_exact=all(same.values());r.save(OUT/'baseline_parity.json',dict(arrays=same,rollout_sec=time.perf_counter()-begin))
    elif not baseline_exact:
        base=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kw));completed+=1
    else:base=old
    if baseline_exact:base=old
    baseline_rows.append(r._cellwise_measure(model,base,rec,truth))
    spec=kw['ramp_dynamics']['ramps'][meter];curve=model.ramp_head_service_veh_per_cycle[meter]
    sat=max(float(q)/(float(g)*spec['lanes']) for g,q in curve.items())
    speed=spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh'])/3.6
    kj=1/spec['spacing_m'];kc=sat/speed;assert 0<kc<kj;wave=sat/(kj-kc);calls=[]
    def bounded(self,service_veh,**kwargs):
        if self.connector_id!='10681':return original(self,service_veh,**kwargs)
        assert self.lanes==1
        stock=self._merge_ready+sum(n for _,n in self._downstream)
        receiving=max(0.,min(sat,wave*(kj-stock/(self.length_m-self.head_position_m))))
        limited=min(service_veh,receiving*self._receipt['duration_sec'])
        before=self._stocks()['connector_veh'];served=original(self,limited,**kwargs)
        assert abs(before-self._stocks()['connector_veh'])<1e-7
        calls.append((stock,receiving,service_veh,served));return served
    begin=time.perf_counter();PhysicalRampBoundary.apply_head_service=bounded
    try:pred=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kw))
    finally:PhysicalRampBoundary.apply_head_service=original
    completed+=1;assert len(calls)==900
    row=r._cellwise_measure(model,pred,rec,truth);assert not row['score']['invalid'] and row['conservation_max']<1e-7
    row.update(rollout_sec=time.perf_counter()-begin,supply_calls=len(calls),wave_mps=wave);rows.append(row)
    with gzip.open(OUT/(rec['arm']+'.json.gz'),'wt') as f:json.dump(pred,f)
    r.save(OUT/(rec['arm']+'_result.json'),row)
    r.save(OUT/'status.json',dict(stage='running',completed=completed,last_arm=rec['arm']))
    print(json.dumps(dict(arm=rec['arm'],compute_sec=row['rollout_sec'],cost=row['predicted']['ttt'])),flush=True)
base=next(z for z in rows if z['arm']=='hold');oldbase=next(z for z in baseline_rows if z['arm']=='hold')
pairs=[]
for z in rows:
    b=next(a for a in baseline_rows if a['arm']==z['arm'])
    assert b['actual']==z['actual']
    pairs.append(dict(arm=z['arm'],actual={k:z['actual'][k]-base['actual'][k] for k in ['ttt','mainline_ttt','ramp_ttt','off_ttt','exits']},
        baseline={k:b['predicted'][k]-oldbase['predicted'][k] for k in ['ttt','mainline_ttt','ramp_ttt','off_ttt','exits']},
        candidate={k:z['predicted'][k]-base['predicted'][k] for k in ['ttt','mainline_ttt','ramp_ttt','off_ttt','exits']}))
for p,h in pins.items():assert r.sha(p)==h
r.save(OUT/'summary.json',dict(rows=rows,baseline_rows=baseline_rows,pairs=pairs,pins=pins,new_full_forecasts=completed,
    cached_baseline_arrays_exact=baseline_exact,wall_sec=time.perf_counter()-started,new_native=0,calibration=False,adopted=False))
r.save(OUT/'status.json',dict(stage='complete',completed=completed))
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(pairs),flush=True)

