"""One bounded, independent parameter fit per physical cell, using cached hold data.

This is an observed-state identification screen, never an autonomous forecast.
It changes no production configuration and does not use VSL outcomes for fitting.
"""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import collections
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares

V = Path(__file__).resolve().parent
A = V/'outflow_followup_20261019'
O = V/'cellwise_recalibration_20261020'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
OLD = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not O.exists(), 'Reuse the existing screen; no automatic second fitting attempt.'
    config = read(OLD/'expanded_joint/eval_036/reference_config.json')
    geometry = read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    active = read(V/'cached_vsl_exposure_audit_v2/active_component_config.json')
    audit = read(V/'closure_recovery_20261020/operator_audit.json')
    terms = read(A/'approach_terms_summary.json')
    spec = read(OLD/'parameter_spec.json')
    previous = read(OLD/'expanded_joint/summary.json')
    old_protocol = read(OLD/'expanded_joint/protocol.json')
    extract = read(A/'interaction_response/completion.json')
    cache = read(A/'interaction_response/hold_records.json.gz')
    cachepath = str(A/'interaction_response/hold_records.json.gz')
    assert PINS[cachepath] == extract['cases']['hold']['output_sha256']
    for path, value in PINS.items():
        if path in audit['source_pins']:
            assert value == audit['source_pins'][path], path
    assert terms['max_formula_error'] < 1e-7 and terms['max_recorded_speed_error'] < 2e-5
    params = active['parameters']
    cells = [c for c in geometry['cells'] if c['road']=='FW_E']
    response = config['freeway']['state_response']['FW_E']['cell_overrides']
    assert len(params) == len(response) == 31
    frames = collections.defaultdict(lambda: collections.Counter())
    for row in cache['rows']:
        frames[row[0]][row[2]] += 1
    names = ['rho_crit', 'metanet_a_m', 'tau_sec', 'nu_ge', 'nu_lt']
    bounds = {(r['cell'], r['parameter']): (r['lower'], r['upper']) for r in spec['variables']}
    inventory = []
    for cell, p in enumerate(params):
        sr = response[str(cell)]
        inventory.append(dict(cell=cell, length_m=1000*p['segment_length_km'],
            v_free=p['v_free'], rho_crit=p['rho_crit'], shape=p['metanet_a_m'],
            tau_acc_sec=sr['relaxation']['acceleration_sec'],
            tau_dec_sec=sr['relaxation']['deceleration_sec'],
            nu_ge=sr['anticipation']['downstream_ge_local'],
            nu_lt=sr['anticipation']['downstream_lt_local'],
            other_response={k:v for k,v in sr.items() if k not in ('relaxation','anticipation')}))
    protocol = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        purpose='User-directed cell-specific recalibration: assess separately identifiable FD and dynamic coefficients before a coupled450s refit.',
        cells=[16,17,18], physical_cell_ids_are_zero_based=True,
        inputs='Previously qualified seed29 hold110 five-second current states. Next-state speed is a training label, never a forecast input.',
        training=dict(start=2240.1,end=2445.1), validation=dict(start=2475.1,end=2695.1),
        gap_seconds=30, validation_is_blind=False,
        qualification='Exploratory time-block development check; the entire trajectory was previously inspected. Adjacent samples are correlated, and this is not independent seed validation.',
        parameters=names, bounds='Reuse original cellwise parameter_spec engineering bounds, not confidence intervals; no widening after results.',
        fixed=['v_free','kappa','lane_drop_phi','geometry','convection law','VSL A/E','urban/RM/demand','production sources'],
        loss='Weighted next-speed squared error/100 plus0.1*mean(log(parameter/current)**2). FD and dynamic terms fitted together, separately per cell.',
        optimizer='scipy least_squares trf, single current-parameter start per cell, max_nfev100, numerical Jacobian; no grid, restarts or selection on validation.',
        budget=dict(fits=3, autonomous_forecasts=0, native=0, fzp_scans=0, optimizer_controller_calls=0),
        identification_gate='Converged; no active/borderline parameter bound; data-only normalized Jacobian full rank with condition<=1000; validation speed RMSE improves>=10% and no speed-regime RMSE worsens>10%. This only permits preparation of autonomous verification, never adoption.',
        future_verification='Freeze any eligible candidate, evaluate conserved coupled150/300/450 trajectories with actualFW5/U10, then previously seen independent seeds67/71 and VSL contrasts. No automatic native/fullSDMPC run.',
        supersedes_pending_cdf_independent_plan=True,
        app_goal_status_last_observed='blocked', user_resumed_analysis=True, goal_complete=False)
    O.mkdir()
    save(O/'protocol.json', protocol)
    save(O/'parameter_inventory.json', dict(cells=inventory,
        provenance=dict(reference=str(OLD/'expanded_joint/eval_036/reference_config.json'),
            physical_coefficients=old_protocol['physical_coefficients'], update_directions=old_protocol['update_directions'],
            original_limit=old_protocol['limit'], optimizer=previous['optimizer'],
            old_fit_selected_index=previous['selected_index']), source_pins=dict(PINS)))
    results = []
    for cell in protocol['cells']:
        p = params[cell]
        sr = response[str(cell)]
        assert set(sr) == {'relaxation','anticipation'}
        assert sr['relaxation']['acceleration_sec'] == sr['relaxation']['deceleration_sec']
        base = np.array([p['rho_crit'],p['metanet_a_m'],sr['relaxation']['acceleration_sec'],
                         sr['anticipation']['downstream_ge_local'],sr['anticipation']['downstream_lt_local']])
        rows = [dict(r) for r in audit['rows'] if r['cell']==cell]
        for row in rows:
            row['downstream_rho'] = frames[row['start']][cell+1]/cells[cell+1]['lane_km']
        train = [r for r in rows if r['start']>=2240.1-1e-7 and r['end']<=2445.1+1e-7]
        valid = [r for r in rows if r['start']>=2475.1-1e-7 and r['end']<=2695.1+1e-7]
        assert len(train)==41 and len(valid)==44
        lower = np.array([bounds[cell,name][0] for name in names])
        upper = np.array([bounds[cell,name][1] for name in names])
        assert np.all(base>=lower) and np.all(base<=upper)
        calls = 0
        def predict(samples, coefficient):
            rhoc,shape,tau,nge,nlt = coefficient
            values=[]
            for row in samples:
                target=p['v_free']*math.exp(-(row['rho']/rhoc)**shape/shape)
                relax=(row['end']-row['start'])*(target-row['speed'])/tau
                nu=nge if row['downstream_rho']>=row['rho'] else nlt
                anticipation=-(row['end']-row['start'])*nu*(row['downstream_rho']-row['rho'])/(tau*p['segment_length_km']*(row['rho']+p['metanet_kappa_veh_km_lane']))
                # The lane-reduction term contains 1/rhoc; phi and geometry stay fixed.
                loss=row['lane_drop']*base[0]/rhoc
                values.append(max(5.,max(5.,row['speed']+relax+row['convection']+anticipation)+loss))
            return np.array(values)
        baseline_error=max(abs(predict(rows,base)-np.array([r['predicted'] for r in rows])))
        assert baseline_error<1e-7, baseline_error
        weight=np.array([r['n'] for r in train],float)
        weight=weight/weight.sum()
        truth=np.array([r['truth'] for r in train])
        def data_residual(z):
            return np.sqrt(weight)*(predict(train,base*np.exp(z))-truth)/10.
        def objective(z):
            nonlocal calls
            calls+=1
            return np.r_[data_residual(z),math.sqrt(.1/5)*z]
        zlo,zhi=np.log(lower/base),np.log(upper/base)
        fit=least_squares(objective,np.zeros(5),bounds=(zlo,zhi),method='trf',
                          max_nfev=100,ftol=1e-9,xtol=1e-9,gtol=1e-9)
        candidate=base*np.exp(fit.x)
        # Exclude the prior from identifiability: it cannot manufacture data rank.
        jac=[]
        for j in range(5):
            dz=np.zeros(5);dz[j]=1e-5
            jac.append((data_residual(fit.x+dz)-data_residual(fit.x-dz))/(2e-5))
        jac=np.array(jac).T
        column_norm=np.linalg.norm(jac,axis=0)
        normalized=jac/np.maximum(column_norm,1e-15)
        singular=np.linalg.svd(normalized,compute_uv=False)
        rank=int(np.linalg.matrix_rank(normalized,tol=1e-7))
        condition=float(singular[0]/singular[-1]) if singular[-1]>1e-15 else None
        fraction=(candidate-lower)/(upper-lower)
        bound_hits=[names[i] for i in range(5) if fraction[i]<.001 or fraction[i]>.999]
        def score(samples,coef=None,persist=False):
            if not samples:return None
            weights=np.array([r['n'] for r in samples],float)
            pred=np.array([r['speed'] for r in samples]) if persist else predict(samples,coef)
            error=pred-np.array([r['truth'] for r in samples])
            return dict(rows=len(samples),rmse=float(np.sqrt(np.average(error**2,weights=weights))),
                        bias=float(np.average(error,weights=weights)),floor_count=int(sum(pred<=5.+1e-8)))
        scores={}
        for label,samples in [('training',train),('validation',valid)]:
            scores[label]={variant:score(samples,coef,persist) for variant,coef,persist in
                           [('baseline',base,False),('fitted',candidate,False),('persistence',None,True)]}
        regime_scores={label:dict(baseline=score([r for r in valid if pred(r)],base),
                                 fitted=score([r for r in valid if pred(r)],candidate))
                       for label,pred in [('slow',lambda r:r['speed']<40),('middle',lambda r:40<=r['speed']<=80),('fast',lambda r:r['speed']>80)]}
        regime_ok=all(v['baseline'] is None or v['fitted']['rmse']<=1.1*v['baseline']['rmse'] for v in regime_scores.values())
        gate=bool(fit.success and not bound_hits and rank==5 and condition is not None and condition<=1000
                  and scores['validation']['fitted']['rmse']<=.9*scores['validation']['baseline']['rmse'] and regime_ok)
        coverage={label:dict(rows=len(samples),density_range=[min(r['rho'] for r in samples),max(r['rho'] for r in samples)],
            slow=sum(r['speed']<40 for r in samples),fast=sum(r['speed']>80 for r in samples),
            downstream_ge=sum(r['downstream_rho']>=r['rho'] for r in samples)) for label,samples in [('training',train),('validation',valid)]}
        result=dict(cell=cell,baseline=dict(zip(names,base.tolist())),candidate=dict(zip(names,candidate.tolist())),
            bounds=dict(zip(names,zip(lower.tolist(),upper.tolist()))),scores=scores,validation_regimes=regime_scores,
            coverage=coverage,solver=dict(success=bool(fit.success),status=int(fit.status),message=fit.message,nfev=int(fit.nfev),
                residual_calls=calls,optimality=float(fit.optimality)),bound_hits=bound_hits,data_jacobian_rank=rank,
            data_normalized_condition=condition,baseline_formula_error=float(baseline_error),
            eligible_for_autonomous_verification=gate,candidate_adopted=False)
        save(O/f'cell{cell}.json',result)
        results.append(result)
        print(json.dumps(dict(cell=cell,scores=scores,bound_hits=bound_hits,eligible=gate)),flush=True)
    for path,h in PINS.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save(O/'completion.json',dict(status='completed_three_cellwise_identification_screens',fits=3,
        result_files=[f'cell{c}.json' for c in protocol['cells']],
        eligible_cells=[r['cell'] for r in results if r['eligible_for_autonomous_verification']],
        production_edits=0,new_native=0,new_fzp_scans=0,autonomous_forecasts=0,controller_optimizations=0,
        goal_complete=False,source_pins=PINS,
        limitations=['Five-second conditional fit is not coupled450s validation or evidence of VSL gain.',
          'Data comes from one already-inspected seed/window; parameters may compensate aggregation, convection or lane-drop model error.',
          'The current FD/dynamic coefficients are cell-specific already; neither past nonconvergence nor this bounded screen rejects all cellwise calibration.',
          'No widening, restart, new native or production adoption follows automatically.']))


if __name__=='__main__':
    main()
