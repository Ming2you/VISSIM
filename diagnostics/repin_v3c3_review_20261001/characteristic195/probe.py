"""One frozen local velocity-transport probe, not a complete ARZ network solver.

Only cells20..25 substitute the homogeneous ARZ characteristic operator for
METANET convection/pressure. Existing mass/node, FD, relaxation, merge, VSL
cohorts and off-ramp restrictions remain. No fitted coefficients or future data.
"""
import copy
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def fd_piece(rho, command, maximum, row, net, spec):
    from evaluation.controllers.freeway_fd import literature_vsl_parameters
    vf = row.get('v_free', net.v_free)
    critical = row.get('rho_crit', net.rho_crit)
    shape = row.get('metanet_a_m', net.metanet_a_m)
    active = command < maximum-.5
    if active and spec is not None:
        vf, critical, shape = literature_vsl_parameters(spec, vf, critical, shape, command, maximum)
    assert shape > 1 and rho >= 0
    power = (rho/critical)**shape
    value = vf*math.exp(-power/shape)
    derivative = -value*power/rho if rho else 0.
    if active and spec is None and (1+net.alpha_vsl)*command < value:
        return (1+net.alpha_vsl)*command, 0.
    return value, derivative


def fd_local(cfg, road, cell, rho, command, exposure):
    """Partial density derivative at fixed current passive cohort fractions."""
    net = cfg.network
    assert not getattr(net, 'vsl_fd_two_branch', False)
    row = net.freeway_segment_params[road][cell]
    spec = (getattr(net, 'freeway_vsl_fd_response', {}) or {}).get(road)
    maximum = max(cfg.freeway_follower.vsl_set)
    cohort = exposure.cohorts[cell] if exposure is not None else {}
    stock = sum(cohort.values())
    if stock <= 1e-12:
        return fd_piece(rho, float(command), maximum, row, net, spec)
    parts = [(n, fd_piece(rho, c, maximum, row, net, spec)) for c,n in cohort.items()]
    return tuple(sum(n*p[j] for n,p in parts)/stock for j in (0,1))


def local_speed(ctx, cfg, rho, down_rho, speed, up_speed, down_speed, target,
                derivative, nu, dt, length, legacy):
    """Use current patched coefficients; check rather than undo clipped terms."""
    from evaluation.controllers.freeway_fd import state_response_coefficients
    net = cfg.network
    assert ctx['armed']
    p = ctx['p']
    length = p.get('segment_length_km', length)
    tau = p.get('metanet_tau_h', net.metanet_tau_h)
    kappa = p.get('metanet_kappa_veh_km_lane', net.metanet_kappa_veh_km_lane)
    tau, nu = state_response_coefficients(ctx.get('state_response', {}), speed, target,
        rho, down_rho, ctx.get('response_rho_crit', net.rho_crit), tau, nu)
    relax = dt/tau*(target-speed)
    convection = dt/length*speed*(up_speed-speed)
    pressure = -nu*dt/(tau*length)*(down_rho-rho)/(rho+kappa)
    drop = 0.
    if ctx.get('phi', 0.) > 0 and ctx.get('dlam', 0.) > 0:
        drop = (ctx['phi']*dt*ctx['dlam']*rho*speed**2 /
                (length*max(1e-9, ctx['lanes'])*p.get('rho_crit', ctx['rho_crit_link'])))
    old = max(net.v_min, max(net.v_min, speed+relax+convection+pressure)-drop)
    assert abs(old-legacy) < 1e-8, (old, legacy)
    lam = speed+rho*derivative
    neighbor = up_speed if lam >= 0 else down_speed
    courant = dt*abs(lam)/length
    weight = courant+dt/tau
    assert derivative <= 1e-12 and weight <= 1+1e-12, (derivative, weight)
    transport = courant*(neighbor-speed)
    raw = speed+relax+transport
    # Convex relaxation/transport is nonnegative before retained merge/drop.
    assert raw >= -1e-10
    value = max(net.v_min, max(net.v_min, raw)-drop)
    return value, dict(speed=speed, up_speed=up_speed, down_speed=down_speed,
        rho=rho, down_rho=down_rho, target=target, derivative=derivative,
        tau_h=tau, length_km=length, dt_h=dt, relaxation=relax,
        legacy_convection=convection, legacy_pressure=pressure, legacy=legacy,
        characteristic_kmh=lam, transport=transport, courant=courant,
        convex_weight=weight, physical_lane_drop=drop, before_merge=value)


def prepare():
    assert not (HERE/'protocol.json').exists()
    previous = h.read(h.R/'neighbor_information194/protocol.json')
    sourcepath = h.R/'spatial_context148/forecast/executed_function_sources.json'
    source = h.read(sourcepath)
    original = copy.deepcopy(source)
    cls = source['RouteLaneRegion']
    token = "        self.rates = copy.deepcopy(spec['exchange_rates_per_sec'])\n"
    assert cls.count(token) == 1
    cls = cls.replace(token, token+"        self.characteristic195 = spec.get('characteristic195',False)\n        self.characteristic_rows = []\n")
    old = '''            velocity = mn.metanet_speed_update_kmh(self.exchange_v[i][g],up,rho,down,target,dt,self.lengths[i],
                net.metanet_tau_h,mn.select_anticipation_nu(rho,net,command),net.metanet_kappa_veh_km_lane,net.v_min)
'''
    new = '''            nu = mn.select_anticipation_nu(rho,net,command)
            if self.characteristic195:
                from evaluation.controllers import vissim_stackelberg_adapter as adapter
                from diagnostics.repin_v3c3_review_20261001.characteristic195.probe import fd_local,local_speed
                ctx = copy.deepcopy(adapter._FW_SEG_CTX)
                pure_target,derivative = fd_local(cfg,road,i,rho,command,exposure)
                assert abs(pure_target-target)<1e-8,(i,pure_target,target)
            velocity = mn.metanet_speed_update_kmh(self.exchange_v[i][g],up,rho,down,target,dt,self.lengths[i],
                net.metanet_tau_h,nu,net.metanet_kappa_veh_km_lane,net.v_min)
            if self.characteristic195:
                down_speed = self.oldv[i+1][g] if i+1 in self.oldv else state.freeway_speed[road][i+1]
                velocity,audit = local_speed(ctx,cfg,rho,down,self.exchange_v[i][g],up,down_speed,
                    target,derivative,nu,dt,self.lengths[i],velocity)
                audit.update(time_s=state.time_sec,cell=i,lane=g+1,stock=n,
                    merge_veh=self.merge[i][g],old_speed=self.oldv[i][g],merge_delta=delta,merge_kappa=kappa)
'''
    assert cls.count(old) == 1
    cls = cls.replace(old, new)
    old = '''            values.append(max(net.v_min,velocity))
        self.next_v[i] = values
'''
    new = '''            values.append(max(net.v_min,velocity))
            if self.characteristic195:
                audit.update(off_requested=requests,off_sent=sent,through=self.outgoing[i][g],final=values[-1])
                self.characteristic_rows.append(audit)
        self.next_v[i] = values
'''
    assert cls.count(old) == 1
    cls = cls.replace(old, new)
    source['RouteLaneRegion'] = cls
    assert all(v == source[k] for k,v in original.items() if k != 'RouteLaneRegion')
    compile(cls, 'characteristic195', 'exec')
    runner = h.R/'state_lateral168/run.py'
    # Preserve the previous runner, including earlier user-authorized edits.
    (HERE/'runner_before195.py.txt').write_bytes(runner.read_bytes())
    spec = h.read(h.F/'joint_lane_25/protocol.json')['candidate']
    spec.update(congested_receiving_cells=[21], reciprocal_off='10483', characteristic195=True)
    h.save(HERE/'spec.json', spec)
    h.save(HERE/'coefficients.json', dict(new_fitted_coefficients=0, parent='132+148+171', cells=list(range(20,26))))
    h.save(HERE/'executed_function_sources.json', source)
    h.save(HERE/'protocol.json', dict(
        hypothesis='Replace density-pressure plus convective velocity update locally with signed characteristic transport to test stop-front/recovery direction. No additive braking/reward.',
        equation='lambda=v+rho*dV/drho; dv=dt/tau*(V-v)+dt*abs(lambda)/L*(v_up if lambda>=0 else v_down - v); parentheses mean neighbor-v.',
        equation_precise='v_next=v+(dt/tau)*(V-v)+(dt*abs(lambda)/L)*(neighbor-v), neighbor=up if lambda>=0 else down; retained lane-drop, merge, off restriction follow.',
        derivative='Actual calibrated FD/Carlson and present passive VSL cohort mixture, density partial at fixed cohort fractions. Pure target must equal runtime target on every call.',
        literature=['https://bayen.berkeley.edu/sites/default/files/prediction_of_traffic.pdf'],
        scope='FW_E31 plus4on/4off cost. Velocity operator cells20..25 only;19 split unchanged. Not wholeOmega/8ramp or complete ARZ network model.',
        limitations='Homogeneous ARZ identity transplanted locally: heterogeneous FD/cohort spatial derivatives and junction invariant conditions not solved. Mass and node solver remain existing METANET/lane-group. Therefore a structural probe, not exact ARZ or GKT.',
        prior_reviewed='Claude REVIEW_CHECK: no foreign coefficient transfer;139pressure cap/165convection/178phase/190split/191refit/194neighbor failures reused. Different signed transport hypothesis.',
        budget=dict(fits=0,forecasts450_max=13,native=0,FZP=0),
        gate='At150 and450: all observed pair abs(deltaTTT)>=.5 vehh signs correct, paired loss at least10pct better, absolute loss no worse10pct, selected actual regret<=.5. Exact disabled4tables, continuity, CFL and targets required.',
        no_future_states=True, frozen_before_forecast=True, known_previously_inspected_states_not_blind=True,
        protected_sha256=previous['protected_sha256'], STOP=previous['STOP']))
    pins = {str(sourcepath):h.sha(sourcepath), str(Path(__file__)):h.sha(__file__),
            str(HERE/'runner_before195.py.txt'):h.sha(runner)}
    h.save(HERE/'pins.json', pins)
    h.save(HERE/'status.json', dict(status='prepared', forecasts=0, adopted=False))
    print('Prepared one frozen characteristic probe; no forecasts or fits')


if __name__ == '__main__':
    prepare()
