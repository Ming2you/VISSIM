"""Condition the active operator on held-native states; no autonomous rollout or fit.

The measured membership term uses the next observation for attribution only.
It is never supplied to the model operator or proposed as a forecast input.
"""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import collections
import copy
import datetime
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

A = Path(__file__).resolve().parent
V = A.parent
O = V / 'closure_recovery_20261020'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
PINS = {}


def read(p):
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def save(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not O.exists()
    extraction = read(A/'interaction_response/completion.json')
    data = read(A/'interaction_response/hold_records.json.gz')
    assert PINS[str(A/'interaction_response/hold_records.json.gz')] == extraction['cases']['hold']['output_sha256']
    verified = read(A/'approach_terms_summary.json')
    assert verified['max_formula_error'] < 1e-7 and verified['max_recorded_speed_error'] < 2e-5
    sys.path[:0] = [str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import lane_plant_runtime as lpr, freeway_fd as fd
    from evaluation.controllers import area_freeway_accounting as area, vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    tuning = read(ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json')
    ctx = lpr.load_sources(tuning['freeway']['lane_plant'])
    component = ctx['component']
    cfg = component._config('FW_E',ctx['parameters']['by_direction']['FW_E'])
    net, mn = cfg.network, area._mn
    assert not component.lane_groups_enabled and ctx['plant_mode'] == 'v2'
    active = read(V/'cached_vsl_exposure_audit_v2/active_component_config.json')
    parent = read(V/'matched_off2250_v3/network.json')
    assert net.freeway_segment_params['FW_E'] == active['parameters']
    heads = parent['freeway_vsl_zone_heads']['FW_E']
    net.freeway_vsl_zone_heads['FW_E'] = heads
    net.freeway_vsl_zone_head_of_cell['FW_E'] = active['head_of_physical_cell']
    net.freeway_vsl_zone_of_cell['FW_E'] = [heads.index(h) for h in active['head_of_physical_cell']]
    net.freeway_vsl_zone_free = tuning['freeway']['vsl_zone_free']
    lanes = list(net.freeway_segment_lanes['FW_E'])
    params = active['parameters']
    lengths = [p['segment_length_km'] for p in params]
    assert all(lanes[c] == 4 for c in (15,16,17,18))
    action = ControlAction(vsl={'FW_E':110, **{f'FW_E__seg{h}':110 for h in heads}})
    frames = collections.defaultdict(lambda: collections.defaultdict(dict))
    for row in data['rows']:
        frames[row[0]][row[2]][row[1]] = row
    times = sorted(frames)
    O.mkdir()
    save(O/'protocol.json', dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='seed29 hold110 only, cells16/17/18, same saved 5s observations2240.1..2695.1',
        hypothesis='Separate wrong local reaction from incorrect transported population mixing. Check density-heterogeneity-only FD averaging as a conditional diagnostic, not an autonomous closure.',
        fits=0, new_native=0, new_fzp_scans=0, autonomous_forecasts=0,
        active_path=dict(plant_mode=ctx['plant_mode'], lane_groups_enabled=component.lane_groups_enabled,
            parent_lane_flag=tuning['freeway'].get('physical_mainline_lane_groups'), runtime_lane_source='component manifest/config overrides parent flag by validated contract'),
        previous_goal_turn='progress: two CDF-cap forecasts and cached lane residual audit completed; candidate unadopted',
        source_pins=dict(PINS)))
    result = []
    def mean(group):
        return math.fsum(r[5] for r in group.values())/len(group)
    for t0,t1 in zip(times,times[1:]):
        dt=t1-t0
        assert abs(dt-5)<1e-7
        for cell in (16,17,18):
            first,second = frames[t0][cell],frames[t1][cell]
            if not first or not second or not frames[t0][cell-1] or not frames[t0][cell+1]:
                continue
            v,truth,up=mean(first),mean(second),mean(frames[t0][cell-1])
            n0,n1=len(first),len(second)
            rho=n0/(lengths[cell]*lanes[cell])
            down=len(frames[t0][cell+1])/(lengths[cell+1]*lanes[cell+1])
            p=params[cell]
            adapter._FW_SEG_CTX_STATE['profile']={'FW_E':lanes}
            shown=mn.segment_vsl(action,'FW_E',cell,cfg)
            desired=p['v_free']*math.exp(-(rho/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            desired=fd.literature_desired_speed(component.base.network.freeway_vsl_fd_response['FW_E'],cfg,'FW_E',cell,rho,desired,110,False)
            nu0=mn.select_anticipation_nu(rho,net,shown)
            armed=copy.deepcopy(adapter._FW_SEG_CTX)
            tau,nu=fd.state_response_coefficients(fd.cell_state_response(net,'FW_E',cell),v,desired,rho,down,
                armed['response_rho_crit'],p['metanet_tau_h'],nu0)
            relax=dt*(desired-v)/(tau*3600)
            conv=dt*v*(up-v)/(lengths[cell]*3600)
            anti=-dt*nu*(down-rho)/(tau*lengths[cell]*3600*(rho+p['metanet_kappa_veh_km_lane']))
            loss=dt*armed['phi']*armed['dlam']*rho*v*v/(3600*lengths[cell]*max(armed['lanes'],1e-9)*p['rho_crit']) if armed['phi']>0 and armed['dlam']>0 else 0.
            predicted=mn.metanet_speed_update_kmh(v,up,rho,down,desired,dt/3600,lengths[cell],net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
            direct=max(net.v_min,max(net.v_min,v+relax+conv+anti)-loss)
            assert abs(predicted-direct)<1e-7
            common=first.keys() & second.keys()
            reaction=math.fsum(second[i][5]-first[i][5] for i in common)/n1
            membership=(math.fsum(second[i][5] for i in second.keys()-first.keys())
                -math.fsum(first[i][5] for i in first.keys()-second.keys())-v*(n1-n0))/n1
            assert abs(truth-v-reaction-membership)<1e-10
            counts=collections.Counter(r[3] for r in first.values())
            hetero=math.fsum(n*p['v_free']*math.exp(-((n/lengths[cell])/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m']) for n in counts.values())/n0
            htau,hnu=fd.state_response_coefficients(fd.cell_state_response(net,'FW_E',cell),v,hetero,rho,down,
                armed['response_rho_crit'],p['metanet_tau_h'],nu0)
            hrelax=dt*(hetero-v)/(htau*3600)
            hanti=-dt*hnu*(down-rho)/(htau*lengths[cell]*3600*(rho+p['metanet_kappa_veh_km_lane']))
            hpred=max(net.v_min,max(net.v_min,v+hrelax+conv+hanti)-loss)
            result.append(dict(start=t0,end=t1,cell=cell,n=n0,next_n=n1,speed=v,truth=truth,rho=rho,
                predicted=predicted,relaxation=relax,convection=conv,anticipation=anti,lane_drop=-loss,
                observed_mean_delta=truth-v,retained_vehicle_term=reaction,population_membership_term=membership,
                current_recorded_acceleration_delta=dt*3.6*math.fsum(r[7] for r in first.values())/n0,
                retained_vehicles=len(common),observed_lane_density_target=hetero,original_target=desired,
                heterogeneous_target_only_prediction=hpred))
    def scores(rows):
        weight=math.fsum(r['n'] for r in rows)
        def metrics(errors):
            return dict(rmse=math.sqrt(math.fsum(r['n']*e*e for r,e in zip(rows,errors))/weight),
                bias=math.fsum(r['n']*e for r,e in zip(rows,errors))/weight)
        return dict(rows=len(rows),
            aggregate=metrics([r['predicted']-r['truth'] for r in rows]),
            heterogeneous_target=metrics([r['heterogeneous_target_only_prediction']-r['truth'] for r in rows]),
            persistence=metrics([r['speed']-r['truth'] for r in rows]),
            reaction_comparison=metrics([r['relaxation']+r['anticipation']+r['lane_drop']-r['retained_vehicle_term'] for r in rows]),
            mixing_comparison=metrics([r['convection']-r['population_membership_term'] for r in rows]),
            mean_observed_reaction=math.fsum(r['n']*r['retained_vehicle_term'] for r in rows)/weight,
            mean_observed_mixing=math.fsum(r['n']*r['population_membership_term'] for r in rows)/weight)
    groups={str(cell):scores([r for r in result if r['cell']==cell]) for cell in (16,17,18)}
    regimes={label:scores([r for r in result if predicate(r)]) for label,predicate in [
        ('below40',lambda r:r['speed']<40),('above80',lambda r:r['speed']>80)]}
    for path in [Path(__file__),Path(lpr.__file__),Path(fd.__file__),Path(area.__file__),Path(adapter.__file__),*ctx['paths'].values()]:
        PINS[str(path)]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    save(O/'operator_audit.json',dict(status='completed_observed_state_operator_audit',groups=groups,regimes=regimes,
        rows=result,source_pins=PINS,app_goal_status='active',goal_complete=False,
        local_operator_evaluations=len(result)*2,autonomous_forecasts=0,new_native=0,new_fzp_scans=0,fits=0,
        limitations=['Observed current-state reset at every sample is a conditional operator diagnostic, not an autonomous450s forecast.',
          'Membership attribution uses next-frame identities only as an outcome decomposition, never a future model input.',
          'The retained-vehicle term excludes acceleration of vehicles that leave before the next sample; reaction/mixing comparisons are diagnostic, not exact PDE-term labels.',
          'Heterogeneous FD averaging changes only the target, and uses observed lane counts; it has no prognostic variance/lane-state update and is not deployable.',
          'Native five-second samples are correlated; no fit or causal VSL effect is identified.']))
    print(json.dumps(dict(groups=groups,regimes=regimes),indent=2))


if __name__ == '__main__':
    main()
