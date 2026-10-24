"""Observe the consumed speed law and actual treatment-response attenuation.

No equation/parameter alteration. Term sums are bookkeeping, not independent
causal effects. Conditional self-velocity derivative is not network stability.
"""
from pathlib import Path
import copy
import hashlib
import inspect
import json
import math
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as u
import canonical_harness as ch
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
from evaluation.controllers.freeway_fd import state_response_coefficients

HERE = Path(__file__).resolve().parent
ARMS = ('none', 'rm_ramp', 'vsl', 'both')
CELLS = tuple(range(13, 21))


def main():
    out = HERE / 'downstream_response_terms_v4'
    out.mkdir(exist_ok=False)
    original = PhysicalLaneGroups.advance
    mn = ch.accounting._mn
    a = ch.adapter
    rows = []
    calls = 0
    core = [u.e.ROOT / 'evaluation/controllers' / name for name in
            ('vissim_stackelberg_adapter.py', 'physical_lane_groups.py', 'physical_ramp_boundary.py')]
    core += [u.e.CAL / 'canonical_harness.py', Path(__file__), Path(u.__file__)]
    pins = {p.relative_to(u.e.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in core}

    def advance(self, state, control, demand, cfg, **kw):
        nonlocal calls
        if self.road != 'FW_E':
            return original(self, state, control, demand, cfg, **kw)
        assert self.sec == 1
        assert all(c not in self.partitions for c in CELLS)
        step_rows = []
        speed_function = mn.metanet_speed_update_kmh

        def observed_speed(*args, **kwargs):
            frame = inspect.currentframe().f_back
            selected = (frame.f_code.co_name == 'advance' and
                Path(frame.f_code.co_filename).resolve() == u.e.ROOT / 'evaluation/controllers/physical_lane_groups.py' and
                frame.f_locals['i'] in CELLS)
            if selected:
                local = frame.f_locals
                context = copy.deepcopy(a._FW_SEG_CTX)
                assert context['armed'] and not kwargs
                v, upstream, rho, downstream, equilibrium, dt, length, tau, nu, kappa, vmin = args
                p = context['p']
                length = p.get('segment_length_km', length)
                tau = p.get('metanet_tau_h', tau)
                kappa = p.get('metanet_kappa_veh_km_lane', kappa)
                tau, nu = state_response_coefficients(context.get('state_response', {}),
                    v, equilibrium, rho, downstream, context['response_rho_crit'], tau, nu)
                assert not (context.get('phi', 0) and context.get('dlam', 0))
                terms = dict(relaxation=dt/tau*(equilibrium-v),
                    convection=dt/length*v*(upstream-v),
                    anticipation=-nu*dt/tau/length*(downstream-rho)/(rho+kappa))
                i, g = local['i'], local['g']
                row = dict(arm=ARMS[calls//450], time_s=state.time_sec, cell=i, group=g,
                    n0=local['before'][i][g], v0=local['oldv'][i][g], v_at_equation=v,
                    upstream=upstream, rho=rho, downstream=downstream, equilibrium=equilibrium,
                    tau_s=tau*3600, nu=nu, kappa=kappa, length=length, dt_s=dt*3600,
                    terms=terms, pre_equation_shift=v-local['oldv'][i][g],
                    conditional_velocity_derivative=1-dt/tau+dt/length*(upstream-2*v),
                    derivative_scope='Fixed current densities/upstream/equilibrium and coefficient regime; not full-network stability.')
            del frame
            value = speed_function(*args, **kwargs)
            if selected:
                assert abs(value-max(vmin, v+sum(terms.values()))) < 1e-8
                row['equation_output'] = value
                step_rows.append(row)
            return value

        mn.metanet_speed_update_kmh = observed_speed
        try:
            answer = original(self, state, control, demand, cfg, **kw)
        finally:
            mn.metanet_speed_update_kmh = speed_function
        assert len(step_rows) == sum(len(self.n[c]) for c in CELLS)
        for row in step_rows:
            c, g = row['cell'], row['group']
            row['v1'] = self.v[c][g]
            row['post_equation_shift'] = row['v1']-row['equation_output']
            if c >= 15:
                assert g == 0
                assert abs(row['post_equation_shift']) < 1e-9
            rows.append(row)
        calls += 1
        return answer

    PhysicalLaneGroups.advance = advance
    try:
        # Two caller-frame speed observers cannot be nested. The old limit
        # observer is pure diagnostics; exact full JSON comparison below
        # verifies that omitting it changes no forecast output.
        u.run_probe(lateral_access=True, prefer_receiving=True, trace_limits=False,
            network_exit_intent=True, current_exit_intent=True, branch_partition='on',
            branch_exchange='off', partition_context='on', transport_step=1,
            output_name='downstream_terms_reference_v3')
    finally:
        PhysicalLaneGroups.advance = original
    assert calls == 1800
    for arm in ARMS:
        got = u.e.load(HERE / 'downstream_terms_reference_v3' / f'prediction_{arm}.json')
        ref = u.e.load(HERE / 'transport_step1_exchange_off_v2' / f'prediction_{arm}.json')
        assert got == ref, arm
        u.e.save(out / (arm + '_terms.json'), [r for r in rows if r['arm'] == arm])
    traces = {arm: {(r['time_s'], r['cell'], r['group']): r for r in rows if r['arm'] == arm} for arm in ARMS}
    budget = {}
    for arm in ARMS[1:]:
        budget[arm] = []
        for c in range(15, 21):
            contributions = dict.fromkeys(('pre_equation_shift', 'relaxation', 'convection', 'anticipation', 'post_equation_shift'), 0.)
            integrated = dict(contributions)
            difference = 0.
            for t in range(2400, 2850):
                base, ctl = traces['none'][t, c, 0], traces[arm][t, c, 0]
                for name in contributions:
                    change = ctl.get(name, ctl['terms'].get(name))-base.get(name, base['terms'].get(name))
                    contributions[name] += change
                    integrated[name] += (2850-t)*change
                difference += ctl['v1']-base['v1']
            final = traces[arm][2849, c, 0]['v1']-traces['none'][2849, c, 0]['v1']
            assert abs(sum(contributions.values())-final) < 1e-7
            assert abs(sum(integrated.values())-difference) < 1e-6
            budget[arm].append(dict(cell=c, final_delta_v=final, speed_time_delta_kmh_s=difference,
                final_terms=contributions, speed_time_terms=integrated))
    native_folders = dict(none=u.H/'controller_response_s23_v1/none',
        **{arm:u.H/'response_late_s23_v1/observations'/arm for arm in ARMS[1:]})
    observed = {arm:{(int(r['time_s']), int(r['cell'])):r for r in u.e.rows(path/'cells_30s.csv')
        if r['road']=='FW_E'} for arm,path in native_folders.items()}
    predicted = {arm:{(r['time_s'], r['cell']):r for r in u.e.load(HERE/'downstream_terms_reference_v3'/f'prediction_{arm}.json')['cells']
        if r['road']=='FW_E'} for arm in ARMS}
    contrasts=[]
    rms=lambda xs:float(np.sqrt(np.mean(np.array(xs)**2)))
    for arm in ARMS[1:]:
        for start in (2400,2550,2700):
            for cells in ((13,14),tuple(range(15,21))):
                keys=[(t,c) for t in range(start+30,start+151,30) for c in cells]
                actual=[float(observed[arm][k]['v_kmh'])-float(observed['none'][k]['v_kmh']) for k in keys]
                model=[predicted[arm][k]['v_kmh']-predicted['none'][k]['v_kmh'] for k in keys]
                contrasts.append(dict(arm=arm,start_s=start,cells=list(cells),
                    native_response_rms_kmh=rms(actual),model_response_rms_kmh=rms(model),
                    response_error_rmse_kmh=rms(np.array(model)-actual),
                    native_mean_delta_kmh=float(np.mean(actual)), model_mean_delta_kmh=float(np.mean(model))))
    for name,digest in pins.items():
        assert hashlib.sha256((u.e.ROOT/name).read_bytes()).hexdigest()==digest,name
    downstream=[r for r in rows if r['cell']>=15]
    u.e.save(out/'result.json',dict(status='READ_ONLY_SPEED_RESPONSE_AUDIT',qualified=False,
        exact_reference_predictions=4, reconstructed_updates=len(rows), downstream_updates=len(downstream),
        max_downstream_pre_equation_shift=max(abs(r['pre_equation_shift']) for r in downstream),
        tau_s=sorted({r['tau_s'] for r in downstream}), nu=sorted({r['nu'] for r in downstream}),
        conditional_velocity_derivative_range=[min(r['conditional_velocity_derivative'] for r in downstream),max(r['conditional_velocity_derivative'] for r in downstream)],
        term_budgets=budget, matched_clock_contrasts=contrasts, source_pins=pins,
        new_native_runs=0,production_changes=0,causal_forecast_unchanged=True,
        limitations='Native states used after forecast only for comparison; term differences are bookkeeping, not causal ablations.'))
    print(json.dumps(dict(exact=4, updates=len(rows),contrasts=[r for r in contrasts if r['cells'][0]==15])),flush=True)


if __name__=='__main__':
    main()
