"""Continuous actuator relaxation used only by the isolated SDMPC Jacobian.

Traffic stocks, receiving limits, routes and conservation equations are kept.
Signal windows are convolved with a compact, unit-integral kernel; meter head
service is interpolated and spread over its cycle. The native execution model
and command writer never install these hooks.
"""
from __future__ import annotations
import math
from evaluation.controllers.sdmpc_dual import primal


def step_integral(x, width):
    """Antiderivative of a C1 cubic transition from 0 to 1 over +/-width/2."""
    z = x/width + .5
    if z <= 0:
        return 0.
    if z >= 1:
        return width*(z-.5)
    return width*(z**3-.5*z**4)


def periodic_fraction(start, duration, cycle, offset, lo, hi, width):
    """Exact interval average of the smoothed periodic GREEN indicator.

    The integral over a complete cycle is exactly hi-lo, preserving effective
    green time. Finite support includes wrapped windows on both cycle edges.
    """
    left, right = start+offset, start+offset+duration
    first = math.floor((primal(left)-primal(hi)-width)/cycle)
    last = math.ceil((primal(right)-primal(lo)+width)/cycle)
    total = 0.
    for k in range(first, last+1):
        a, b = lo+k*cycle, hi+k*cycle
        total += (step_integral(right-a, width)-step_integral(left-a, width)
                  -step_integral(right-b, width)+step_integral(left-b, width))
    return max(0., min(1., total/duration))


def phase_fraction(control, cfg, spec, urban_step_index=None):
    from evaluation.controllers import signal_actuation_contract as native
    net = cfg.network
    if not native.enabled(net) or not spec.get('phase'):
        return None
    if spec.get('unsignalized'):
        return 1.
    signal, _, phase = spec['phase'].rpartition('_')
    if signal not in net.signal_actuation_contract['nodes']:
        return None
    basis = native.native_clock_basis(net, signal)
    if basis is None:
        raise ValueError('Continuous prediction requires a verified native clock basis: '+signal)
    cycle = basis['cycle_sec']
    greens = {p: control.green_times.get(signal+'_'+p, 0.) for p in native.PHASES}
    from evaluation.controllers.sdmpc_prediction_cache import signal_entry
    operands = (*greens.values(), control.offsets.get(signal, 0.),
                cfg.simulation.T_u_sec, net.sdmpc_options['signal_transition_width_sec'])
    cache, cache_key, cached = signal_entry(cfg, signal, phase, urban_step_index, operands, basis)
    if cached is not None:
        return cached[1]
    clearance = basis['amber_sec']+basis['all_red_sec']
    windows = {}
    if basis['kind'] == 'serial':
        cursor = 0.
        for p in basis['phase_order']:
            windows[p] = cursor, cursor+greens[p]
            cursor += greens[p]+clearance+basis['idle_after_phase_sec'][p]
    elif basis['kind'] == 'concurrent_p1_p2':
        windows = {'p1': (0., greens['p1']), 'p2': (0., greens['p2']),
                   'p4': (greens['p2']+clearance, cycle-clearance)}
    else:
        raise ValueError('Unknown continuous native clock topology')
    if phase not in windows:
        return 0.
    lo, hi = windows[phase]
    if urban_step_index is None:
        return (hi-lo)/cycle
    dt = cfg.simulation.T_u_sec
    result = periodic_fraction(urban_step_index*dt, dt, cycle, control.offsets.get(signal, 0.),
        lo, hi, net.sdmpc_options['signal_transition_width_sec'])
    if cache is not None:
        cache.signals[cache_key] = (operands, result)
    return result


def meter_rate(green, row):
    """Continuous, monotone interpolation of the existing measured table.

    Interpolate between adjacent measured knots; a knot uses the right-hand
    derivative (left at the upper bound), a valid piecewise-linear selection.
    No capacity or calibration value is invented.
    """
    knots = sorted((int(g), rate) for g, rate in row['service_by_green_veh_h'].items())
    g = primal(green)
    if g < knots[0][0] or g > knots[-1][0]:
        raise ValueError('Continuous meter outside measured domain')
    index = next((i for i in range(len(knots)-1) if g < knots[i+1][0]), len(knots)-2)
    (x0, y0), (x1, y1) = knots[index:index+2]
    return y0+(green-x0)*(y1-y0)/(x1-x0)


def prepare_control(control, cfg):
    spec = cfg.network.physical_ramp_branches
    if set(control.ramp_metering) != set(spec['ramps']):
        raise ValueError('Continuous prediction requires all physical meters')
    for name, row in spec['ramps'].items():
        control.ramp_metering[name] = meter_rate(control.diagnostics['rw_meter_green_'+name], row)
    return control


def ramp_services(control, cfg, cycle):
    # OFF here means an ungated continuous service envelope in this surrogate,
    # not an OFF native command. Exact GREEN/RED commands are verified later.
    return {name: dict(mode='OFF', green_sec=None,
        service_veh=meter_rate(control.diagnostics['rw_meter_green_'+name], row)*cycle/3600.)
        for name, row in cfg.network.physical_ramp_branches['ramps'].items()}


def local_fraction(self, time, sg, *, controller_offset_sec):
    if self.cfg is None or controller_offset_sec != 0:
        raise ValueError('Missing local continuous signal binding')
    phase = {2:'SC1004_p3', 5:'SC1004_p4'}[sg]
    return phase_fraction(self.control, self.cfg, {'signal':'SC1004','phase':phase}, int(time)-1)


def install(cfg):
    from evaluation.controllers import signal_actuation_contract as signals
    from evaluation.controllers import physical_ramp_branches as ramps
    from evaluation.controllers.lane_urban_runtime import CandidateSignalProgram
    if cfg.network.sdmpc_options.get('derivatives') != 'tangent-v1':
        raise ValueError('Continuous relaxation is an explicit SDMPC derivative option')
    if cfg.network.signal_actuation_contract['offset_writer'] not in ('experiment', 'production'):
        raise ValueError('Continuous SDMPC offsets require a writer that applies optimizer offsets')
    cfg.network._sdmpc_continuous_prediction = True
    signals.phase_fraction = phase_fraction
    ramps.prepare_control = prepare_control
    # Routing remains possible; per-lane exit budgets apply the fraction once.
    CandidateSignalProgram.state_at = lambda self, *a, **kw: 'GREEN'
    CandidateSignalProgram.service_fraction_at = local_fraction
