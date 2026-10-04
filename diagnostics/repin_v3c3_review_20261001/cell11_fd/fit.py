"""One bounded physical-cell FD candidate; existing native caches only."""
import copy
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from scipy.optimize import minimize_scalar
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
B=I/'baseline_reproduction_20260929'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def write(path,data):
    if path.exists():
        assert read(path)==data,str(path)
        return
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    assert not (HERE/'fit.json').exists()
    manifest=read(HERE.parent/'retained10638/candidate_manifest.json')
    for key in ('geometry','reference_config','parameters'):
        path=ROOT/manifest['sources'][key]['path'];read(path)
        assert PINS[str(path)]==manifest['sources'][key]['sha256']
    reference=read(ROOT/manifest['sources']['reference_config']['path'])
    geometry=read(ROOT/manifest['sources']['geometry']['path'])
    parameters=read(ROOT/manifest['sources']['parameters']['path'])['parameters']
    component=CanonicalFreewayModel(geometry,(ROOT/manifest['sources']['reference_config']['path']).resolve())
    cfg=component._config('FW_E',parameters['by_direction']['FW_E']);net=cfg.network
    cell=11;p=net.freeway_segment_params['FW_E'][cell]
    response=net.freeway_state_response['FW_E']['cell_overrides'][str(cell)]
    tau=response['relaxation']['acceleration_sec']
    assert tau==response['relaxation']['deceleration_sec']
    assert all(c['to_cell']!=cell for c in component.ramps.values() if c['road']=='FW_E')
    assert net.freeway_segment_lanes['FW_E'][cell]==net.freeway_segment_lanes['FW_E'][cell+1]==4
    spec=read(B/'cellwise_calibration/parameter_spec.json')
    bound=next(x for x in spec['variables'] if x['cell']==cell and x['parameter']=='rho_crit')
    protocol=dict(status='prepared_one_candidate',parameter='FW_E physical cell11 effective rho_crit',
        fit_seed=29,fit_policy='none',fit_window_s=[2220.1,2970.1],fit_budget_scalar_evaluations=25,
        bounds=[bound['lower'],bound['upper']],autonomous_forecast_budget=6,
        checks=['43 sameinitial NC/RM/VSL/both','47 sameinitial RM hold/city-selected pair'],
        acceptance=['No conservation, initial-state or executable-command change',
            'Reduce10682 entry/stock error and cell11 speed error without falsely congesting recovered seed47 cell10',
            'No gain-qualification from conditional derivative fit; retain8port/queue/OmegaTTT diagnostics'],
        forbidden=['Future native boundary in autonomous forecast','Additional coefficient grids','NewVISSIM','Push'])
    if (HERE/'protocol.json').exists():
        assert read(HERE/'protocol.json')==protocol
    else:
        write(HERE/'protocol.json',protocol)

    def dataset(seed):
        path=B/f'cellwise_calibration/freeway_first/cohort_early/s{seed}_none_frames.json.gz'
        source=read(path);assert source['fields']==['cell','speed_kmh','x_m','lane']
        snapshots=[]
        bounds=geometry['bounds']['FW_E']
        for stamp,vehicles in sorted(source['frames'].items(),key=lambda pair:float(pair[0])):
            groups=defaultdict(list)
            for c,v,x,lane in vehicles.values():
                if c in (10,11,12):
                    assert bounds[c]-1e-4<=x<=bounds[c+1]+1e-4
                    groups[c].append(v)
            if any(len(groups[c])<5 for c in (10,11,12)):
                snapshots.append(None);continue
            rho=lambda c:len(groups[c])/(net.freeway_segment_length_profile_km['FW_E'][c]*4)
            snapshots.append(dict(time_s=float(stamp),v=sum(groups[11])/len(groups[11]),
                up=sum(groups[10])/len(groups[10]),rho=rho(11),down=rho(12),n=len(groups[11])))
        rows=[]
        for previous,current,following in zip(snapshots,snapshots[1:],snapshots[2:]):
            if any(x is None for x in (previous,current,following)):continue
            assert abs(following['time_s']-previous['time_s']-10)<1e-6
            rows.append(dict(current,observed_kmh_per_s=(following['v']-previous['v'])/10))
        return rows

    training=dataset(29)
    def terms(row,critical):
        desired=p['v_free']*math.exp(-(row['rho']/critical)**p['metanet_a_m']/p['metanet_a_m'])
        relaxation=(desired-row['v'])/tau
        convection=row['v']*(row['up']-row['v'])/(3600*p['segment_length_km'])
        nu=response['anticipation']['downstream_ge_local' if row['down']>=row['rho'] else 'downstream_lt_local']
        anticipation=-nu/(tau*p['segment_length_km'])*(row['down']-row['rho'])/(row['rho']+p['metanet_kappa_veh_km_lane'])
        total=max(net.v_min,row['v']+relaxation+convection+anticipation)-row['v']
        return dict(desired=desired,relaxation=relaxation,convection=convection,anticipation=anticipation,total=total)

    # Reconstruct all450 current autonomous cell11 equation updates exactly.
    # No merge or lane-drop/post-equation cap is active in this saved reference.
    trace=read(I/'closedloop_recorded2250_lever450_trace10681_retained43/held_actual_RM_C10681_trace.json.gz')
    parity=0.
    for row in trace['mainline_diagnostics']['speed_terms']:
        if row['cell']!=cell:continue
        assert abs(row['lane_drop_raw'])<1e-12 and abs(row['post_equation_change'])<1e-12
        up=row['speed_before']+row['convection']*3600*row['length_km']/row['speed_before']
        rebuilt=terms(dict(v=row['speed_before'],up=up,rho=row['rho'],down=row['downstream_rho']),p['rho_crit'])
        parity=max(parity,abs(rebuilt['total']-(row['speed_final']-row['speed_before'])),abs(rebuilt['desired']-row['desired']))
    assert parity<1e-8,parity
    def loss(critical):
        errors=[terms(row,critical)['total']-row['observed_kmh_per_s'] for row in training]
        # Huber threshold1km/h persecond, fixed before optimization.
        return sum(.5*x*x if abs(x)<=1 else abs(x)-.5 for x in errors)/len(errors)
    saved_reference=HERE/'reference_config.json'
    if saved_reference.exists():
        # The first optimization completed and wrote its selected reference;
        # only manifest packaging then failed. Reuse that scalar, no second fit.
        selected=read(saved_reference)['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']*parameters['by_direction']['FW_E']['rho_crit_multiplier']
        evaluations=None
    else:
        solution=minimize_scalar(loss,bounds=(bound['lower'],bound['upper']),method='bounded',
                                 options=dict(maxiter=25,xatol=.01))
        assert solution.success
        selected=float(solution.x)
        evaluations=solution.nfev
    # Fixed before reading43 evaluation data; no adjustment after evaluation.
    validation=dataset(43)
    def metrics(rows,critical):
        errors=[terms(row,critical)['total']-row['observed_kmh_per_s'] for row in rows]
        return dict(n=len(rows),mae_kmh_per_s=sum(abs(x) for x in errors)/len(errors),
                    bias_kmh_per_s=sum(errors)/len(errors),rmse_kmh_per_s=math.sqrt(sum(x*x for x in errors)/len(errors)))
    fitted=copy.deepcopy(reference)
    multiplier=parameters['by_direction']['FW_E']['rho_crit_multiplier']
    fitted['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']=selected/multiplier
    reference_path=HERE/'reference_config.json';write(reference_path,fitted)
    manifest['sources']['reference_config']=pin(reference_path)
    manifest['qualification']='Onecell11 FD diagnostic; NOT operationally adopted or gain qualified'
    manifest_path=HERE/'candidate_manifest.json';write(manifest_path,manifest)
    tuning=read(HERE.parent/'retained10638/candidate_config.json')
    tuning['freeway']['lane_plant']=manifest_path.relative_to(ROOT).as_posix()
    write(HERE/'candidate_config.json',tuning)
    rebuilt=CanonicalFreewayModel(geometry,reference_path)._config('FW_E',parameters['by_direction']['FW_E'])
    assert abs(rebuilt.network.freeway_segment_params['FW_E'][11]['rho_crit']-selected)<1e-10
    reference_check=copy.deepcopy(fitted)
    reference_check['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']=reference['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']
    assert reference_check==reference
    result=dict(status='fit_complete_not_adopted',original_effective_critical=p['rho_crit'],candidate_effective_critical=selected,
        candidate_config_critical=selected/multiplier,bounds=protocol['bounds'],evaluations=evaluations,
        optimizer_recovery_note='Selected scalar reused after packaging failure; first nfev was not persisted, bounded by25. No optimization retry.' if evaluations is None else None,
        exact_current_equation_reconstruction_max_error=parity,
        training=dict(before=metrics(training,p['rho_crit']),after=metrics(training,selected)),
        cross_state43=dict(before=metrics(validation,p['rho_crit']),after=metrics(validation,selected)),source_pins=PINS,
        limitation='Conditional local derivative calibration on measured future states; not an autonomous forecast. Eulerian mean derivatives include vehicle replacement and noise. No dynamic off-ramp constraint is applied in this isolated fit. Full conserved rollout must decide adoption.')
    write(HERE/'fit.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'}))


if __name__=='__main__':main()
