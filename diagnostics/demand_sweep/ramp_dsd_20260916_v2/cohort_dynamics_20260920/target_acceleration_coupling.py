"""NC-fit, two-weight acceleration coupling in existing conserved transport.

This is a30s local falsification gate, not a450s controller or gain model.
The original force remains one term of a convex response-memory hypothesis.
"""
from pathlib import Path
from collections import Counter
import bisect
import copy
import hashlib
import importlib.util
import json
import math
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as s
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g

K,e=s.d.HERE,s.d.e
OUT=K/'target_acceleration_coupling_v1'


def acceleration(frames,t,bins,geometry):
    shifts={r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    ends=[b['start']+b['length']*1000 for b in bins]
    sums=[[0.]*3 for _ in bins];known=[[0]*3 for _ in bins]
    for vid,row in frames[t].items():
        x=shifts[row['link']]+row['pos']
        if x<bins[0]['start']:continue
        before=frames[t-1].get(vid)
        if before is None:continue
        i=min(len(bins)-1,bisect.bisect_right(ends,x));j=row['lane']-1
        sums[i][j]+=row['v']-before['v'];known[i][j]+=1
    return [[v/n if n else 0. for v,n in zip(row,ks)] for row,ks in zip(sums,known)],known


def fit(rows):
    data=np.array([[r['self_a']-r['base'],r['forward_a']-r['base']] for r in rows])
    y=np.array([r['label']-r['base'] for r in rows]);weights=np.array([r['known'] for r in rows])
    def loss(x):return float(np.sum(weights*(data@np.array(x)-y)**2)/weights.sum())
    def line(origin,direction):
        z=data@np.array(direction);res=y-data@np.array(origin)
        alpha=float(np.clip(np.sum(weights*z*res)/np.sum(weights*z*z),0.,1.))
        return (np.array(origin)+alpha*np.array(direction)).tolist()
    self_only=line([0.,0.],[1.,0.])
    candidates=[self_only,line([0.,0.],[0.,1.]),line([1.,0.],[-1.,1.])]
    free=np.linalg.lstsq(data*np.sqrt(weights[:,None]),y*np.sqrt(weights),rcond=None)[0]
    if np.all(free>=0) and free.sum()<=1:candidates.append(free.tolist())
    best=min(candidates,key=loss)
    return dict(base=dict(self_weight=0.,forward_weight=0.,training_mse=loss([0.,0.])),
        self_only=dict(self_weight=self_only[0],forward_weight=0.,training_mse=loss(self_only)),
        coupled=dict(self_weight=best[0],forward_weight=best[1],training_mse=loss(best)),
        objective='Same-vehicle acceleration at the next destination-bin, weighted by observed vehicle count.',
        source_rows=len(rows),vehicle_labels=int(weights.sum()),
        constraints='weights>=0, self+forward<=1; a boundary optimum with no original force is explicitly unqualified.',
        unconstrained=free.tolist())


def score(trace,observed,arm,start):
    ev=[];en=[];ttt=actual=0.
    for row in trace:
        for cell,value in row['cells'].items():
            target=observed[arm]['states'][str(start+row['step'])][str(cell)]
            ev.append(value['v']-target['v']);en.append(value['n']-target['n'])
            ttt+=value['n']/3600;actual+=target['n']/3600
    return dict(speed_rmse=math.sqrt(sum(x*x for x in ev)/len(ev)),stock_mae=sum(abs(x) for x in en)/len(en),
        local_ttt=ttt,actual_ttt=actual,final_cells=trace[-1]['cells'])


def main():
    gp=s.d.H/'controller_response_s23_v1/none/geometry.json';geometry=e.load(gp)
    geo={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    cp=K/'transport_step1_exchange_off_v2/config.json';pp=K/'port_travel_fit_v1/selected_parameters.json'
    op=K/'compact_lane_state_v1/states.json';observed=e.load(op)
    model=e.load_base_model(geometry,cp);cfg=model._config('FW_E',e.load(pp)['parameters']['by_direction']['FW_E'])
    spec=importlib.util.spec_from_file_location('frozen_spatial_before_acceleration',OUT/'source_before.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    initial_bank={};receipts={};runs=[];training=[];skip=Counter();exact=zero_exact=0
    for arm,path,lo in (
        ('none',K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp',899),
        ('rm_ramp',K/'route_state_native_v1/rm_ramp_s23/run/vissim_eval/baseline_001.fzp',2249),
        ('vsl',K/'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp',2249)):
        frames,receipts[arm]=g.read(path,True,lo)
        located=s.locate(frames,geometry)
        if arm=='none':
            for t in range(930,2091):
                try:
                    inputs=s.initial_and_boundary(located,t,geo,'lane_100m')
                    _,checks=s.rollout(inputs,cfg,1,collect_speed_terms=True,momentum_advection=True)
                except AssertionError as exc:
                    # The original initializer requires observed source speeds
                    # in every lane. Never fabricate them at empty snapshots.
                    if str(exc):raise
                    skip['missing_current_upstream_lane_speed']+=1;continue
                except ValueError as exc:
                    if 'exceeds configured jam storage' not in str(exc):raise
                    skip['observed_initial_storage_excess']+=1;continue
                current,_=acceleration(frames,t,inputs['bins'],geometry)
                target,known=acceleration(frames,t+1,inputs['bins'],geometry)
                forward=s.forward_acceleration(current,inputs['n'])
                for term in checks['speed_terms']:
                    i,j=term['i'],term['g']
                    if not known[i][j] or not inputs['n'][i][j] or forward[i][j] is None:continue
                    training.append(dict(t=t,i=i,g=j,base=term['actual_function_value']-term['carrier'],
                        self_a=current[i][j],forward_a=forward[i][j],label=target[i][j],known=known[i][j]))
            fitted=fit(training)
            e.save(OUT/'training_rows.json',training)
            e.save(OUT/'fit.json',{**fitted, 'skipped_training_snapshots':dict(skip),
                'training_cutoffs':[930,2090],'last_label_time':2091,'network_parameters_changed':False})
            print('FIT',json.dumps(fitted),flush=True)
        initial_bank[arm]={}
        for start in (2280,2400,2550,2700):
            inputs=s.initial_and_boundary(located,start,geo,'lane_100m')
            current,known=acceleration(frames,start,inputs['bins'],geometry)
            initial_bank[arm][str(start)]=dict(inputs=inputs,initial_acceleration=current,known=known)
            old=frozen.rollout(inputs,cfg,30,momentum_advection=True)
            baseline=s.rollout(inputs,cfg,30,momentum_advection=True)
            assert old==baseline;exact+=1
            disabled=s.rollout(inputs,cfg,30,momentum_advection=True,acceleration_memory=dict(
                self_weight=0.,forward_weight=0.,initial=current))
            assert disabled[0]==baseline[0];zero_exact+=1
            for name in ('base','self_only','coupled'):
                coefficients=fitted[name];record=dict(arm=arm,start_s=start,variant=name)
                try:
                    memory=None if name=='base' else dict(self_weight=coefficients['self_weight'],
                        forward_weight=coefficients['forward_weight'],initial=current)
                    trace,checks=baseline if name=='base' else s.rollout(inputs,cfg,30,momentum_advection=True,acceleration_memory=memory)
                    record.update(status='completed',**score(trace,observed,arm,start),checks=checks)
                    e.save(OUT/f'{arm}_{start}_{name}.json',trace)
                except (AssertionError,ArithmeticError,ValueError) as exc:
                    record.update(status='failed',reason=str(exc))
                runs.append(record)
            print('RUN',arm,start,[(v['variant'],v['status'],v.get('speed_rmse')) for v in runs[-3:]],flush=True)
        del frames,located
    e.save(OUT/'initials.json',initial_bank)
    sources=[Path(__file__),Path(s.__file__),Path(g.__file__),gp,cp,pp,op,OUT/'source_before.py',OUT/'fit.json',OUT/'initials.json']
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,new_native_runs=0,future_inputs=False,
        fitted=fitted,runs=runs,default_traces_exact=exact,zero_weight_traces_exact=zero_exact,
        source_receipts=receipts,source_pins={p.relative_to(s.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Local15-20cells,30s recursive prediction; not450s lever/cost/ranking qualification.',
          'Old local100m transport and native parameters unchanged; acceleration coupling is optional and defaultoff.',
          'Current initial mean same-vehicle acceleration is measured from t-1,t; after cutoff only model reaction updates it.',
          'Acceleration is an Eulerian response-memory field, not an independently conserved vehicle property.',
          'Local source speed/flow/lane-exchange rates use unchanged current/past30s estimate; no future observation resets.',
          'Destination-bin future accelerations are NC training labels only; their membership is not a runtime feature.',
          'Empty initial bins have zero reaction history and no invented vehicles; terminal missing forward exposure returns its weight to original force.',
          'If fitted weights remove original force, preserve that failure rather than treating persistence as a calibrated METANET.',
          'Post-treatment2550/2700 initial states differ by arm; only2400 shares initial control state.']))


if __name__=='__main__':main()
