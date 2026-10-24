"""Conditional FD-only feasibility, reusing verified native-state term records."""
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
CW=HERE.parent/'baseline_reproduction_20260929/cellwise_calibration'


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=CW/'freeway_first/merge_population'
    verification=read(source/'verification.json')
    assert verification['complete'] and verification['scalar_parity_max']<1e-9
    assert digest(source/'rows.json')==verification['artifacts']['rows.json']
    reference=CW/'expanded_joint/eval_036/reference_config.json'
    assert digest(reference)=='7f6df2d14795b22d858aa772f5813e42b67f9d1ec4296cc6203bd854c28d83a4'
    prior_pins=read(source/'summary.json')['pins']
    assert prior_pins[str(reference)]==digest(reference)
    fd=read(reference)['freeway']['physical_cell_fd']['FW_E']
    rows=[]
    for r in read(source/'rows.json'):
        if r['arm']!='release' or r['cell'] not in (24,25):continue
        m=r['model'];speed=r['speed_before'];desired=m['desired_speed']
        assert m['merge_loss']==0. and abs(m['relaxation'])>1e-12
        other=m['convection']+m['anticipation']
        assert abs(m['relaxation']+other-m['total_change'])<1e-9
        tau=(desired-speed)/m['relaxation'];assert tau>0
        a=fd[str(r['cell'])]['metanet_a_m']
        vf=desired*math.exp((m['rho']/m['rho_crit'])**a/a)
        required_zero=speed-tau*other
        required_observed=speed+tau*(r['observed_mean_rate']-other)
        # At fixed current state and all other terms, every positive critical
        # density/shape of the nominal exponential FD gives desired <= vf.
        upper_rate=(vf-speed)/tau+other
        assert abs((required_zero-speed)/tau+other)<1e-9
        assert abs((required_observed-speed)/tau+other-r['observed_mean_rate'])<1e-9
        rows.append(dict(time_s=r['time_s'],cell=r['cell'],tau_sec=tau,
            current_speed=speed,desired=desired,fitted_v_free=vf,
            required_desired_for_zero_drift=required_zero,
            required_desired_for_observed_5s_rate=required_observed,
            optimistic_rate_at_fitted_v_free=upper_rate,
            actual_5s_spatial_rate=r['observed_mean_rate'],
            modeled_1s_rate=m['total_change']))
    assert len(rows)==180
    groups=[]
    for cell in (24,25):
        all_rows=[r for r in rows if r['cell']==cell]
        assert len(all_rows)==90
        assert max(r['fitted_v_free'] for r in all_rows)-min(r['fitted_v_free'] for r in all_rows)<1e-9
        for block in (None,0,1,2):
            subset=all_rows if block is None else all_rows[30*block:30*(block+1)]
            groups.append(dict(cell=cell,block=block,samples=len(subset),
                mean={key:statistics.mean(r[key] for r in subset) for key in rows[0] if key not in ('time_s','cell')},
                zero_drift_unavailable_at_fixed_vfree=sum(r['required_desired_for_zero_drift']>r['fitted_v_free']+1e-9 for r in subset)))
    pins={str(p):digest(p) for p in [Path(__file__),source/'verification.json',source/'summary.json',source/'rows.json',reference]}
    result=dict(scope='seed67 release110,2670.1-3120.1;current native cell/neighbor states and native5s merges from the prior conditional audit',
        formula='V_required = v - tau*(convection+anticipation), for zero instantaneous spatial-mean drift',
        fixed='Current states, relaxation time, convection, anticipation, fitted free speed. Only the FD target is allowed to rise up to its current free speed.',
        limitations=['Not a bound for the entire parameter/control domain or autonomous rollout.',
            'V_free is the CURRENT calibrated FD ceiling, not a physical speed maximum or the posted110 limit.',
            'One-second model increments and native five-second spatial-average changes are distinct operators.',
            'Future-native samples are diagnostic labels only; none enters a forecast.',
            'No arbitrary increase of free speed is selected to compensate another term.'],
        groups=groups,rows=rows,pins=pins,new_forecasts=0,new_native=0,new_fzp_scans=0,coefficient_fits=0)
    target=HERE/'recovery_fd_limit.json';assert not target.exists()
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(groups,indent=2))


if __name__=='__main__':main()
