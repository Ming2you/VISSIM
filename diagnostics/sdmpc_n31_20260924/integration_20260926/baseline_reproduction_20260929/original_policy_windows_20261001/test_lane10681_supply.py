"""One parameter-free posthead supply hypothesis; frozen-mainline buffer check."""
import copy,gzip,json,math
from pathlib import Path
from diagnostics.sdmpc_n31_20260924.integration_20260926 import replay_congested_component as r
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary,LaneResolvedRampBoundary
HERE=Path(__file__).resolve().parent;OUT=HERE/'lane10681/supply_candidate';OUT.mkdir(exist_ok=False)
prior=r.load(HERE/'lane10681/summary.json');cap=r.load(HERE/'capture.json')
model=lpr.load_sources(r.load(HERE/'protocol.json')['manifest'])['component'];meter='RM_C10681'
pins={str(Path(__file__)):r.sha(__file__),str(HERE/'lane10681/summary.json'):r.sha(HERE/'lane10681/summary.json')}
for p in (r.ROOT/'evaluation/controllers').glob('*.py'):pins[str(p)]=r.sha(p)
r.save(OUT/'protocol.json',dict(maximum_buffer_replays=4,fit_parameters=0,core_modified=False,new_full_forecasts=0,
    formula='Qsat=max_g service(g)/(g*lanes); kj=1/spacing; kc=Qsat/vtravel; w=Qsat/(kj-kc); Rpost=min(Qsat,w*(kj-Npost/Lpost)), clamped nonnegative. Head service=min(existing service,Rpost*dt).',
    scope='Only10681; same queued masses, physical receiving, arrivals, signals, finite geometry and bookkeeping.',
    acceptance='Compare all4 prior states; no coefficient search. This frozen-mainline test is not autonomous gain qualification.',pins=pins))
original=PhysicalRampBoundary.apply_head_service;rows=[];checks=[]
try:
 for ev in prior['evidence']:
    case=ev['case'];rec=next(z for z in cap['records'] if z['case']==case)
    args,kw=r.read_primitive_capture(rec['input'],rec['sha256']);spec=kw['ramp_dynamics']['ramps'][meter]
    p=HERE/'predictions'/(case+'.json.gz');pins[str(p)]=r.sha(p)
    with gzip.open(p,'rt') as f:pred=json.load(f)
    saved=[z for z in pred['ramps'] if z['ramp']==meter]
    # Infer intrinsic within-green saturation from the existing curve, not demand.
    curve=model.ramp_head_service_veh_per_cycle[meter]
    sat=max(float(q)/(float(g)*spec['lanes']) for g,q in curve.items())
    speed=spec.get('posthead_travel_speed_kmh',spec['travel_speed_kmh'])/3.6
    kj=1/spec['spacing_m'];kc=sat/speed
    assert 0<kc<kj
    wave=sat/(kj-kc);calls=[]
    def bounded(self,service_veh,**kwargs):
        if self.connector_id!='10681':return original(self,service_veh,**kwargs)
        assert self.lanes==1
        stock=self._merge_ready+sum(n for _,n in self._downstream)
        length=self.length_m-self.head_position_m
        receiving=max(0.,min(sat,wave*(kj-stock/length)))
        limited=min(service_veh,receiving*self._receipt['duration_sec'])
        before=self._stocks()['connector_veh']
        served=original(self,limited,**kwargs)
        assert abs(before-self._stocks()['connector_veh'])<1e-7
        calls.append(dict(stock=stock,receiving=receiving,requested=service_veh,served=served))
        return served
    # Geometry empty/jam limits. Existing pulse never exceeds sat.
    assert abs(min(sat,wave*kj)-sat)<1e-12
    assert max(0.,min(sat,wave*(kj-kj)))==0
    PhysicalRampBoundary.apply_head_service=bounded
    buffer=LaneResolvedRampBoundary(**copy.deepcopy(spec));receipts=[]
    for i,old in enumerate(saved):
        step=args[1][i];service=model._head_service(meter,step['ramp_head_service'][meter],10.)
        assert service['service_veh']/((10 if service['mode']=='OFF' else service['green_sec'])*spec['lanes'])<=sat+1e-12
        receipts.append(buffer.advance_local_interval(start_sec=old['start_sec'],duration_sec=1.,cycle_sec=10.,
            receiving_budget_veh=old['receiving_budget_veh'],request_arrivals_veh=step['ramp_arrival_vph'][meter]/3600,
            allow_partial_cycle=True,**service))
    PhysicalRampBoundary.apply_head_service=original
    end=receipts[-1]['end']
    totals=dict(arrivals=sum(z['admitted_arrivals_veh'] for z in receipts),head=sum(z['head_service_veh'] for z in receipts),
        merges=sum(z['accepted_merge_veh'] for z in receipts),pre=end['upstream_travelling_veh']+end['head_ready_veh'],
        post=end['downstream_travelling_veh']+end['merge_ready_veh'])
    old=next(z for z in prior['rows'] if z['case']==case and z['mode']=='baseline');actual=old['actual']
    row=dict(case=case,predicted=totals,actual=actual,error={k:totals[k]-v for k,v in actual.items()},
        baseline_error=old['error'],post_wave_mps=wave,sat_vps_lane=sat,calls=len(calls),
        restricted_calls=sum(z['served']<min(z['requested'],sat)-1e-8 for z in calls),
        mass_max=max(abs(z['conservation_residual_veh']) for z in receipts))
    assert len(calls)==300 and row['mass_max']<1e-7
    rows.append(row)
    with gzip.open(OUT/(case+'.json.gz'),'wt') as f:json.dump(dict(receipts=receipts,supply_calls=calls),f)
finally:PhysicalRampBoundary.apply_head_service=original
for p,h in pins.items():assert r.sha(p)==h
r.save(OUT/'summary.json',dict(rows=rows,pins=pins,new_buffer_replays=4,new_full_forecasts=0,new_native=0,
    calibration=False,adopted=False,gain_qualified=False))
(OUT/'source_executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(rows))

