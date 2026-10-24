"""Exact offline velocity ledger: mixing, same-vehicle response, and weights.

Future membership supplies evaluation labels only. The unchanged model is
reset to each current native state; this is not an autonomous forecast gate.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import target_acceleration_coupling as c

K, e, s, g = c.K, c.e, c.s, c.g
OUT = K / 'velocity_ledger_audit_v1'
STARTS = (2280, 2400, 2550, 2700)


def statistics(rows, names, weight):
    total = sum(r[weight] for r in rows)
    assert total > 0
    return dict(rows=len(rows), weight=total, terms={name:dict(
        bias=sum(r[weight]*r[name] for r in rows)/total,
        rmse=math.sqrt(sum(r[weight]*r[name]**2 for r in rows)/total)) for name in names})


def labels(now, nxt, bins):
    """Mean current velocity of next-bin members plus their actual change."""
    ends = [b['start']+b['length']*1000 for b in bins]
    def address(row):
        return min(len(bins)-1, bisect.bisect_right(ends, row['x'])), row['lane']-1
    groups = defaultdict(list)
    for vid, row in nxt.items():
        if row['cell'] >= 15:
            groups[address(row)].append((vid, row))
    result = {}
    for key, members in groups.items():
        complete = [(vid, row, now[vid]) for vid, row in members if vid in now]
        values = dict(n=len(members), missing_current=len(members)-len(complete),
                      observed_v=sum(r['v'] for _, r in members)/len(members))
        if len(complete) == len(members):
            carrier = sum(before['v'] for _, _, before in complete)/len(complete)
            reaction = sum(row['v']-before['v'] for _, row, before in complete)/len(complete)
            assert abs(carrier+reaction-values['observed_v']) < 1e-10
            groups_count = Counter()
            for vid, row, before in complete:
                prior = address(before) if before['cell'] >= 15 else None
                kind = ('upstream_entry' if prior is None else 'same_bin_lane' if prior == key
                        else 'longitudinal' if prior[1] == key[1] else 'lateral_same_bin' if prior[0] == key[0]
                        else 'longitudinal_and_lateral')
                groups_count[kind] += 1
            values.update(carrier=carrier, reaction=reaction, transitions=dict(groups_count))
        result[key] = values
    return result


def main():
    OUT.mkdir(exist_ok=False)
    gp = s.d.H/'controller_response_s23_v1/none/geometry.json'
    cp = K/'transport_step1_exchange_off_v2/config.json'
    pp = K/'port_travel_fit_v1/selected_parameters.json'
    op = K/'compact_lane_state_v1/states.json'
    geometry, observed = e.load(gp), e.load(op)
    geo = {r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    model = e.load_base_model(geometry, cp)
    cfg = model._config('FW_E', e.load(pp)['parameters']['by_direction']['FW_E'])
    all_bins, all_cells, receipts, unavailable = [], [], {}, []
    prefixes = {'none':'run_retry1', 'rm_ramp':'run', 'vsl':'run_retry1'}
    max_mass = 0.
    for arm, run in prefixes.items():
        path = K/f'route_state_native_v1/{arm}_s23/{run}/vissim_eval/baseline_001.fzp'
        end = s.d.END
        try:
            s.d.END = max(STARTS)+30
            frames, receipts[arm] = g.read(path, True, min(STARTS)-30)
        finally:
            s.d.END = end
        located = s.locate(frames, geometry)
        for start in STARTS:
            for t in range(start, start+30):
                # Explicitly check this initializer's observation requirement;
                # do not catch arbitrary model assertions as missing data.
                lanes = {r['lane'] for r in located[t].values() if r['cell']==14}
                if lanes != {1, 2, 3}:
                    unavailable.append(dict(arm=arm, t=t, reason='missing_upstream_lane', lanes=sorted(lanes)))
                    continue
                inputs = s.initial_and_boundary(located, t, geo, 'lane_100m')
                trace, checks = s.rollout(inputs, cfg, 1, momentum_advection=True, collect_speed_terms=True)
                max_mass = max(max_mass, checks['max_mass_residual'])
                truth = labels(located[t], located[t+1], inputs['bins'])
                by_cell = defaultdict(list)
                for term in checks['speed_terms']:
                    i, lane = term['i'], term['g']
                    label = truth.get((i, lane))
                    if label is None:
                        continue
                    if label['missing_current']:
                        unavailable.append(dict(arm=arm, t=t, i=i, lane=lane,
                                                reason='missing_current_vehicle', **label))
                        continue
                    prediction = term['actual_function_value']
                    reaction = prediction-term['carrier']
                    mixing_error = term['carrier']-label['carrier']
                    reaction_error = reaction-label['reaction']
                    error = prediction-label['observed_v']
                    assert abs(error-mixing_error-reaction_error) < 1e-10
                    row = dict(arm=arm, start=start, t=t, i=i, lane=lane+1,
                        cell=inputs['bins'][i]['cell'], n=label['n'], n0=inputs['n'][i][lane],
                        current_v=inputs['v'][i][lane], actual=label, model=term,
                        mixing_error=mixing_error, reaction_error=reaction_error, error=error,
                        actual_reaction=label['reaction'], model_reaction=reaction,
                        pressure=term['pressure'], relaxation=term['relax'],
                        floor_correction=prediction-(term['carrier']+term['relax']+term['convection']+term['pressure']))
                    all_bins.append(row)
                    by_cell[row['cell']].append(row)
                for cell, rows in by_cell.items():
                    n = sum(r['n'] for r in rows)
                    target = observed[arm]['states'][str(t+1)][str(cell)]
                    # An incomplete destination membership must not be
                    # presented as a whole-cell decomposition.
                    if n != target['n']:
                        unavailable.append(dict(arm=arm, t=t, cell=cell, reason='incomplete_cell', known=n, actual=target['n']))
                        continue
                    actual = sum(r['n']*r['actual']['observed_v'] for r in rows)/n
                    assert abs(actual-target['v']) < 1e-8
                    reweighted = sum(r['n']*r['model']['actual_function_value'] for r in rows)/n
                    mixing = sum(r['n']*r['mixing_error'] for r in rows)/n
                    reaction = sum(r['n']*r['reaction_error'] for r in rows)/n
                    aggregate = trace[0]['cells'][cell]
                    weights = aggregate['v']-reweighted
                    error = aggregate['v']-actual
                    assert abs(error-mixing-reaction-weights) < 1e-8
                    all_cells.append(dict(arm=arm, start=start, t=t, cell=cell, n=n,
                        prediction=aggregate, actual=dict(n=n, v=actual), weight=1,
                        mixing_error=mixing, reaction_error=reaction, composition_weight_error=weights,
                        error=error, stock_error=aggregate['n']-n))
            print('LEDGER', arm, start, flush=True)
        del frames, located
    e.save(OUT/'bin_ledger.json', all_bins)
    e.save(OUT/'cell_ledger.json', all_cells)
    summaries = []
    for arm in prefixes:
        for start in STARTS:
            for scope in ('all15_20', 'cell16'):
                select = lambda row: row['arm']==arm and row['start']==start and (scope=='all15_20' or row['cell']==16)
                bs = [r for r in all_bins if select(r)]
                cs = [r for r in all_cells if select(r)]
                summaries.append(dict(arm=arm, start=start, scope=scope,
                    bins=statistics(bs, ('mixing_error','reaction_error','error','actual_reaction','model_reaction','pressure','relaxation','floor_correction'), 'n'),
                    cells=statistics(cs, ('mixing_error','reaction_error','composition_weight_error','error','stock_error'), 'weight')))
    sources = [Path(__file__), Path(s.__file__), Path(g.__file__), Path(s.d.__file__), gp, cp, pp, op]
    e.save(OUT/'result.json', dict(qualified=False, production_adopted=False, new_native_runs=0,
        forecast_type='one-step reset to current native state, causal model inputs; future membership labels only',
        starts=STARTS, seconds_per_window=30, summaries=summaries, unavailable=unavailable,
        bin_rows=len(all_bins), cell_rows=len(all_cells), max_mass_residual=max_mass,
        source_receipts=receipts,
        source_pins={p.relative_to(s.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Not recursive, gain, or full Omega qualification.',
            'Post-treatment states differ; this does not estimate a matched-state causal control effect.',
            'Bin metrics weight actual next vehicle counts, cell metrics weight each cell-second equally.',
            'Composition term includes predicted stock weights and predicted occupied bins absent in reality.',
            'Error terms can cancel; RMSEs are not additive or causal percentages.']))
    print(json.dumps(dict(bin_rows=len(all_bins), cell_rows=len(all_cells), unavailable=len(unavailable), max_mass=max_mass)))


def current_regional_law(continuous=False):
    """Reuse same-vehicle labels with the CURRENT 31-cell speed law.

    Local equation diagnostics only: no repeated native extraction, no fitting,
    and no future membership/state supplied to the equation. Cells 26--30 have
    single groups, no ramp ports or lane drops, and known current upstream cells.
    """
    import gzip
    import numpy as np
    from evaluation.controllers.freeway_fd import state_response_coefficients
    from src.models import metanet as mn

    root = s.d.ROOT
    base = K.parent/'segment_resolution_20260921'
    out = base/'recovery_entry_ledger_v1'
    prefix='continuous_' if continuous else ''
    assert out.is_dir() and not (out/(prefix+'result.json')).exists()
    load = e.load
    pins = [Path(__file__), Path(mn.__file__),
            root/'evaluation/controllers/freeway_fd.py',
            root/'evaluation/controllers/physical_lane_groups.py',
            base/'geometry_200_branch_guard.json', base/'guard_initial_groups.json',
            base/'prepare.py', K/'velocity_ledger_audit_v1/bin_ledger.json',
            K/'velocity_ledger_audit_v1/result.json',
            base/'recovery_acceleration_v1/ra_disabled/effective_config.json']
    geo = {r['cell']:r for r in load(pins[4])['cells'] if r['road']=='FW_E'}
    initial = load(pins[5])
    effective = {r['arm']:r for r in load(pins[-1])}
    cells = tuple(range(26,31))
    for i in cells:
        assert geo[i]['parent_cell']==i-10
        assert abs(sum(initial['widths'][i])-3)<1e-10 and len(initial['widths'][i])==1
        assert initial['matrices'][i-1]==[[1.0]]
        assert all(p['cell']!=i for p in list(initial['ramp_access'].values())+list(initial['off_access'].values()))
    labels_by_key = defaultdict(list)
    for row in load(K/'velocity_ledger_audit_v1/bin_ledger.json'):
        # The older per-vehicle ledger clamps vehicles beyond the geometric
        # terminal into its last bin. Do not mix that population with this
        # strictly geometric stock cache. Exclude terminal cell30 from labels.
        if row['cell']+10 in cells and row['cell']+10 != 30:
            assert row['actual']['missing_current']==0
            labels_by_key[row['arm'],row['t'],row['cell']+10].append(row)
    compact=None
    if continuous:
        cp=K/'compact_lane_state_v1/states.json';pins.extend([cp,K/'compact_lane_state.py'])
        compact=load(cp)
        # Independently match this second, continuous same-vehicle label bank
        # against every compatible old per-vehicle ledger row before reuse.
        for (arm,t,i),members in labels_by_key.items():
            label=compact[arm]['states'][str(t+1)][str(i-10)]
            count=sum(r['n'] for r in members)
            assert label['history_coverage']==1. and label['n']==count
            assert abs(label['acceleration']-sum(r['n']*r['actual']['reaction'] for r in members)/count)<1e-8
            assert abs(label['v']-sum(r['n']*r['actual']['observed_v'] for r in members)/count)<1e-8
        labels_by_key={(arm,t,i):None for arm in ('none','rm_ramp','vsl') for t in range(2280,2850) for i in range(26,30)}

    def equation(arm, i, v, up, rho, down):
        cfg = effective[arm];p=cfg['rows'][i]
        response=cfg['state_response']['FW_E']
        response=response.get('cell_overrides',{}).get(str(i),response)
        assert not cfg['receiving_speed_response'] and not cfg['vsl_fd_response']
        # There is no local reduced VSL here; equivalence to actual saved
        # canonical updates is checked below. No merge/exit in these cells.
        desired=mn.desired_speed_kmh(rho,p['v_free'],p['rho_crit'],p['metanet_a_m'])
        tau,nu=state_response_coefficients(response,v,desired,rho,down,p['rho_crit'],p['metanet_tau_h'],p['metanet_nu_km2_h'])
        dt=1/3600;length=p['segment_length_km'];kappa=p['metanet_kappa_veh_km_lane']
        relaxation=dt/tau*(desired-v)
        convection=dt/length*v*(up-v)
        pressure=-nu*dt/(tau*length)*(down-rho)/(rho+kappa)
        predicted=mn.metanet_speed_update_kmh(v,up,rho,down,desired,dt,length,tau,nu,kappa,0.)
        assert abs(predicted-max(0.,v+relaxation+convection+pressure))<1e-10
        assert predicted>0.,'Floor must be inactive for this diagnostic decomposition'
        return dict(predicted=predicted,desired=desired,relaxation=relaxation,
                    convection=convection,pressure=pressure,tau_seconds=tau*3600,nu=nu)

    # Validate this local equation against the ACTUAL saved recursive runner,
    # not just a second copy of its algebra. Each input is previous model state.
    canonical_checks=0;max_error=0.;predictions={}
    for arm in ('none','rm_ramp','vsl','both'):
        path=base/f'recovery_acceleration_v1/ra_disabled/refined_guard1_{arm}.json.gz'
        pins.append(path)
        with gzip.open(path,'rt',encoding='utf-8') as stream:p=json.load(stream)
        states=defaultdict(dict)
        for row in p['lane_groups']['FW_E']:
            if row['cell']>=25:
                assert row['group']==0
                states[int(row['time_s'])][row['cell']]=(row['n_veh'],row['v_kmh'])
        states[2400]={i:(initial['initial_groups'][i][0]['n_veh'],initial['initial_groups'][i][0]['v_kmh']) for i in range(25,31)}
        assert set(states)==set(range(2400,2851))
        for t in range(2400,2850):
            for i in cells:
                n,v=states[t][i];rho=n/geo[i]['lane_km']
                down=states[t][i+1][0]/geo[i+1]['lane_km'] if i<30 else rho
                terms=equation(arm,i,v,states[t][i-1][1],rho,down)
                err=abs(terms['predicted']-states[t+1][i][1])
                assert err<1e-8,(arm,t,i,err,terms)
                max_error=max(max_error,err);canonical_checks+=1
        predictions[arm]=states

    rows=[];events=[];mean_checks=0
    for arm in ('none','rm_ramp','vsl'):
        path=base/f'{arm}_s23_0.npz';pins.append(path)
        with np.load(path) as z:
            n=z['n'].sum(axis=2);mom=z['mom'].sum(axis=2)
            v=np.divide(mom,n,out=np.zeros_like(mom),where=n>0)
        assert n.shape==(752,21)  # prepare.py defines index = t - 2249.
        for (label_arm,t,i),members in sorted(labels_by_key.items()):
            if label_arm!=arm:continue
            j=t-2249;c=i-10
            assert min(n[j,c-1],n[j,c],n[j,min(c+1,20)])>0
            rho=n[j,c]/geo[i]['lane_km']
            down=n[j,c+1]/geo[i+1]['lane_km'] if i<30 else rho
            terms=equation(arm,i,float(v[j,c]),float(v[j,c-1]),rho,down)
            features={}
            if compact is not None:
                now=compact[arm]['states'][str(t)][str(c)]
                label=compact[arm]['states'][str(t+1)][str(c)]
                assert now['n']==n[j,c] and abs(now['v']-v[j,c])<1e-8
                assert label['history_coverage']==1. and label['n']==n[j+1,c]
                count=label['n'];reaction=label['acceleration'];carrier=label['v']-reaction
                features={key:now[key] for key in ('sd','closing','braking','acceleration','history_coverage')}
            else:
                count=sum(r['n'] for r in members)
                assert count==n[j+1,c]
                carrier=sum(r['n']*r['actual']['carrier'] for r in members)/count
                reaction=sum(r['n']*r['actual']['reaction'] for r in members)/count
            actual=float(v[j+1,c]);assert abs(carrier+reaction-actual)<1e-8
            mixing_error=float(v[j,c])+terms['convection']-carrier
            reaction_error=terms['relaxation']+terms['pressure']-reaction
            error=terms['predicted']-actual
            assert abs(error-mixing_error-reaction_error)<1e-8
            mean_checks+=1
            rows.append(dict(arm=arm,t=t,cell=i,n=count,weight=1,current_v=float(v[j,c]),
                rho=rho,downstream_rho=down,actual=actual,carrier=carrier,actual_reaction=reaction,
                model_reaction=terms['relaxation']+terms['pressure'],mixing_error=mixing_error,
                reaction_error=reaction_error,error=error,current_features=features,**terms))
        critical_speed=effective[arm]['rows'][26]['v_free']*math.exp(-1/effective[arm]['rows'][26]['metanet_a_m'])
        for i in cells:
            c=i-10
            # A diagnostic event: first five consecutive observed seconds below
            # the existing FD critical speed. Never used as a forecast input.
            eligible=[t for t in range(2400,2847) if np.all(v[t-2249:t-2249+5,c]<critical_speed)]
            if eligible:
                t=eligible[0]
                events.append(dict(arm=arm,cell=i,time=t,observed_v=float(v[t-2249,c]),
                    recursive_model_v=predictions[arm][t][i][1],critical_speed=critical_speed,
                    already_below_at_start=t==2400))
    assert mean_checks==(6840 if continuous else 1440) and canonical_checks==9000
    names=('mixing_error','reaction_error','error','actual_reaction','model_reaction','relaxation','pressure')
    summaries=[]
    for arm in ('none','rm_ramp','vsl'):
        for start in (sorted(set(STARTS+(2460,))) if continuous else STARTS):
            rs=[r for r in rows if r['arm']==arm and start<=r['t']<start+30]
            for scope in ('all26_29','cell26'):
                group=[r for r in rs if scope=='all26_29' or r['cell']==26]
                opposite=[r for r in group if r['actual_reaction'] < -1. and r['model_reaction'] > 1.]
                summaries.append(dict(arm=arm,start=start,scope=scope,stats=statistics(group,names,'weight'),
                    opposite_rows=len(opposite),opposite_stats=statistics(opposite,names,'weight') if opposite else None))
    extra={}
    if continuous:
        sample=load(out/'rows.json');bykey={(r['arm'],r['t'],r['cell']):r for r in rows}
        for row in sample:
            current=bykey[row['arm'],row['t'],row['cell']]
            for key in ('current_v','rho','downstream_rho','actual','carrier','actual_reaction','mixing_error','reaction_error','error','predicted'):
                assert abs(current[key]-row[key])<1e-8
        extra['sampled_rows_exact']=len(sample)
        extra['phase_summary']=[]
        for arm in ('none','rm_ramp','vsl'):
            for condition in ('all','current_braking_ge_half','current_braking_lt_half'):
                group=[r for r in rows if r['arm']==arm and r['cell']==26 and
                    (condition=='all' or ((r['current_features']['braking']>=.5)==(condition=='current_braking_ge_half')))]
                if group:
                    extra['phase_summary'].append(dict(arm=arm,condition=condition,stats=statistics(group,names,'weight'),
                        counts_by_sign_threshold={str(eps):int(sum(r['actual_reaction'] < -eps and r['model_reaction']>eps for r in group)) for eps in (0.,.5,1.)}))
        extra['first_onset_window']=[r for r in rows if r['arm']=='none' and r['cell']==26 and 2460<=r['t']<2490]
    row_path=out/(prefix+'rows.json')
    if row_path.exists():assert load(row_path)==rows
    else:e.save(row_path,rows)
    e.save(out/(prefix+'result.json'),dict(qualified=False,production_adopted=False,new_native_runs=0,new_autonomous_forecasts=0,
        fitted_parameters=0,local_equation_evaluations=canonical_checks+mean_checks,
        scope='Current whole-cell law, refined cells26--29 labels,26--30 canonical reconstruction; one-step current-state reset, NOT a 450s forecast or control-effect estimate.',
        canonical_reconstruction=dict(rows=canonical_checks,max_absolute_kmh=max_error),
        independent_native_mean_checks=mean_checks,events=events,summaries=summaries,continuous=continuous,**extra,
        source_pins={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},
        limitations=['Continuous2280--2849 if enabled, otherwise four30s windows; development data, no unused validation.',
            'Actual next membership and speeds are labels only, never equation inputs.',
            'Convection is compared with exact composition mixing; internal reaction is relaxation plus pressure.',
            'Terms can cancel; bias decomposition is exact, RMSE terms and causal shares are not additive.',
            'Cell25 excluded because its upstream observed refined split differs from available original-cell cache.',
            'Cell30 excluded from native reaction labels: old ledger clamps beyond-terminal positions, geometric cache excludes them. Canonical reconstruction and stock-based event audit still include30.',
            'Gate events use a fitted FD critical speed and five-second persistence, not a universal definition of congestion.']))
    print(json.dumps(dict(canonical_checks=canonical_checks,native_checks=mean_checks,max_error=max_error,events=events)))


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1] in ('current-regional','current-regional-continuous'):current_regional_law(sys.argv[1].endswith('-continuous'))
    else:main()
