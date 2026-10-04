"""Tangent probe for the K8-6 SA tests (T13, T13b, T20); run only as a fresh subprocess.

    python -B stopline_tangent_probe.py <forward|reverse-v1> <derivatives|tie|carry|parity>

The tangent Finder is installed before any model import, exactly as the
non-surrogate AD worker does, so SA, UQM, LOR, the DelayedPort and the toy
driver run instrumented. Prints one JSON line. Toy states only.

T20 (parity) compares through the K8 amendment 10 rule (k8_gates/sa/sa_s3parity.py,
imported before the finder so that it runs untransformed): ledger flow_counts
keys that only the tangent run has, with primal exactly 0.0, created by a K8-2
S3-admitted ledger transfer outside SA are set aside and counted; SA must create
none; any other difference still fails.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (str(HERE), str(ROOT / 'vendor/NumSim-mine'), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

BACKEND, SCENARIO = sys.argv[1], sys.argv[2]
sys.path.append(str(HERE.parent / 'k8_gates' / 'sa'))
import sa_s3parity as S3P  # noqa: E402  (K8 amendment 10; before rt.install: untransformed)
from evaluation.controllers import sdmpc_tangent_runtime as rt  # noqa: E402

rt.install(ROOT, backend=BACKEND)
if BACKEND == 'forward':
    from evaluation.controllers import sdmpc_dual as ad  # noqa: E402
else:
    from evaluation.controllers import sdmpc_tangent_reverse as ad  # noqa: E402
import stopline_toy as T  # noqa: E402
from evaluation.controllers import stopline_approach as SA  # noqa: E402
from src.models import urban_queue_model as uqm  # noqa: E402

AXES = ('p3', 'p4', 'offset')
G3, G4, OFFSET = 45.4, 24.3, 0.0


def trace():
    return ad.Trace([1.0, 1.0, 1.0]) if BACKEND == 'forward' else ad.Trace([1.0, 1.0, 1.0], track_stencils=False)


def dual_inputs(g3=G3, g4=G4, offset=OFFSET):
    tr = trace()
    return tr, ad.Dual(g3, {0: 1.0}, tr), ad.Dual(g4, {1: 1.0}, tr), ad.Dual(offset, {2: 1.0}, tr)


def derivative(value):
    return [ad.derivative(value).get(j, 0.0) for j in range(3)] if BACKEND == 'forward' else None


def tangent_abs(value):
    return math.fsum(abs(v) for v in ad.derivative(value).values()) if isinstance(value, ad.Dual) else 0.0


def is_dual(value):
    return isinstance(value, ad.Dual)


# ---------------------------------------------------------------- derivatives

def derivative_case(g3, g4, offset):
    cohorts = {'10491': [[231.4 - i, 30.0, 1] for i in range(3)], '10481': [[454.3 - i, 30.0, 1 + i % 2] for i in range(6)]}
    cfg, st = T.bare(118, cohorts=cohorts)
    s = st.stopline_approach_state
    T.add_ready(st, cfg, 1, T.E, 70.4, 110)
    T.add_ready(st, cfg, 1, T.S, 11.5, 112)
    s['init_excess'][1] = 0.9
    T.add_ready(st, cfg, 2, T.E, 62.9, 110)
    T.add_ready(st, cfg, 3, T.N, 100.0, 110)
    ctl = T.control(greens={**T.GREENS, 'SC1001_p3': g3, 'SC1001_p4': g4}, offset=offset)
    released = {'10491': 0.0, '10481': 0.0}
    served = {T.E: 0.0, T.S: 0.0, T.N: 0.0}
    for t in range(118, 152):
        _diag, record = T.drive(st, cfg, ctl, t, landing={'10491': 0.15, '10481': 0.3})
        for off, n in record['released'].items():
            released[off] = released[off] + n
        for member, x in record['departed'].items():
            served[member] = served[member] + x
    out = {'stock_%d' % l: s['stock'][l] for l in SA.LANES}
    out.update({'queue_' + m[10:]: st.urban_movement_queue[m] for m in (T.E, T.S, T.N)})
    out.update({'served_' + m[10:]: v for m, v in served.items()})
    out.update({'released_' + off: v for off, v in released.items()})
    out['in_available'] = st.urban_link_storage[T.IN]
    out.update({'port_stock_' + off: p.stock for off, p in st.lane_offramp_runtime.ports.items()})
    return out


def run_derivatives():
    _tr, g3, g4, offset = dual_inputs()
    taped = derivative_case(g3, g4, offset)
    h = 1e-5
    fd = {}
    for axis, (dg3, dg4, doff) in enumerate(((h, 0, 0), (0, h, 0), (0, 0, h))):
        plus = derivative_case(G3 + dg3, G4 + dg4, OFFSET + doff)
        minus = derivative_case(G3 - dg3, G4 - dg4, OFFSET - doff)
        for key in taped:
            fd[(key, axis)] = (ad.primal(plus[key]) - ad.primal(minus[key])) / (2 * h)
    worst, max_rel, checks = None, 0.0, 0
    report = {}
    for (key, axis), value in fd.items():
        tangent = derivative(taped[key])[axis]
        if AXES[axis] == 'offset':
            report.setdefault('offset', {})[key] = [tangent, value]
            continue
        scale = max(abs(value), abs(tangent))
        if scale <= 1e-9:
            continue
        checks += abs(value) > 1e-6
        rel = abs(tangent - value) / scale
        if rel > max_rel:
            max_rel, worst = rel, [key, AXES[axis], tangent, value]
    return {'max_rel_error': max_rel, 'worst': worst, 'nonzero_checks': checks, 'report_only': report}


# ------------------------------------------------------------------------ tie

def tie_case(g3, *, float_residual=False):
    cfg, st = T.bare(120)
    s = st.stopline_approach_state
    specs = uqm.movement_specs(cfg)
    budget = (SA.view(cfg)['lanes'][1]['s_veh_h'] * cfg.simulation.T_u_h
              * uqm._phase_green_fraction(T.control(greens={**T.GREENS, 'SC1001_p3': G3}), cfg, specs[T.E],
                                          urban_step_index=120))
    amount = math.nextafter(budget, 1.0) if float_residual else budget
    tied = T.add_ready(st, cfg, 1, T.E, amount, 110)
    T.add_ready(st, cfg, 1, T.S, 0.5, 111)
    T.add_ready(st, cfg, 2, T.E, 0.3, 111)
    ctl = T.control(greens={**T.GREENS, 'SC1001_p3': g3})
    mirror = []
    T.drive(st, cfg, ctl, 120)
    mirror.append(mirror_error(st))
    deleted = all(p is not tied for p in s['lanes'][1])
    carry = s['carry'][1][T.E]
    T.drive(st, cfg, ctl, 121, gate=1.0)
    mirror.append(mirror_error(st))
    folded = next(p for p in s['lanes'][1] if p[2] == 'city' and p[3] == T.E)
    return cfg, st, deleted, carry, folded, mirror


def mirror_error(st):
    if BACKEND != 'forward':
        return 0.0
    s = st.stopline_approach_state
    step = s['last_step']
    worst = 0.0
    for member in (T.E, T.S, T.N):
        index = [p[4] for l in SA.LANES for p in s['lanes'][l] if p[0] <= step and p[3] == member]
        index += [row[member] for row in s['carry'].values() if member in row]
        for axis in range(3):
            a = math.fsum(ad.derivative(x).get(axis, 0.0) for x in index)
            b = ad.derivative(st.urban_movement_queue[member]).get(axis, 0.0)
            worst = max(worst, abs(a - b))
    return worst


def run_tie():
    _tr, g3, _g4, _off = dual_inputs()
    _cfg, st, deleted, carry, folded, mirror = tie_case(g3)
    _cfg2, st2, deleted2, carry2, _folded2, _m2 = tie_case(G3, float_residual=True)
    return {'tie_packet_deleted': deleted, 'tie_carry_primal': ad.primal(carry),
            'tie_carry_tangent_abs': tangent_abs(carry),
            'carry_after_fold': ad.primal(st.stopline_approach_state['carry'][1][T.E])
            + tangent_abs(st.stopline_approach_state['carry'][1][T.E]),
            'folded_packet_tangent_abs': tangent_abs(folded[4]),
            'float_residual_deleted': deleted2, 'float_residual_carry': ad.primal(carry2),
            'mirror_tangent_error': max(mirror)}


def run_carry():
    tr, g3, _g4, _off = dual_inputs()
    _cfg, st, _deleted, carry, _folded, _mirror = tie_case(g3)
    if BACKEND == 'forward':
        row = derivative(carry)
    else:
        row = [float(x) for x in tr.jacobian([carry], workers=1)[0]]
    return {'primal': ad.primal(carry), 'derivative': row}


# --------------------------------------------------------------------- parity

def parity_case(g3, g4, offset, zero):
    cohorts = {'10491': [[231.4 - i, 30.0, 1] for i in range(3)]}
    cfg, st = T.bare(120, cohorts=cohorts)
    s = st.stopline_approach_state
    specs = uqm.movement_specs(cfg)
    budget = (SA.view(cfg)['lanes'][1]['s_veh_h'] * cfg.simulation.T_u_h
              * uqm._phase_green_fraction(T.control(greens={**T.GREENS, 'SC1001_p3': G3}), cfg, specs[T.E],
                                          urban_step_index=120))
    T.add_ready(st, cfg, 1, T.E, budget, 102)              # ties the step-120 budget exactly
    T.add_ready(st, cfg, 1, T.S, 0.6, 103)
    T.add_ready(st, cfg, 1, T.E, 0.4, 104)
    T.add_ready(st, cfg, 2, T.E, 0.9, 103)
    T.add_ready(st, cfg, 3, T.N, 1.4, 103)
    T.add_moving(st, cfg, 1, T.E, 0.35, 140, source='init:port')
    from evaluation.controllers.control_area_objective import get_ledger
    T.attach_ledger(st, cfg)
    ctl = T.control(greens={**T.GREENS, 'SC1001_p3': g3, 'SC1001_p4': g4}, offset=offset)
    seen = {'tie': False, 'zero': False}
    for t in range(120, 240):
        landing = {'10491': 0.12}
        if t == 121:
            landing['10481'] = zero
        T.drive(st, cfg, ctl, t, gate=0.25, landing=landing)
        if t == 120:
            seen['tie'] = not any(p[0] == 102 for p in s['lanes'][1])
    port = st.lane_offramp_runtime.ports['10481']
    seen['zero'] = port.stock == 0.0 and s['counters']['port_release_veh_10481'] == 0.0
    snapshot = {'sa': s, 'queues': st.urban_movement_queue, 'storage': st.urban_link_storage,
                'arrival': st.urban_arrival_buffer, 'release': st.urban_storage_release_buffer,
                'flow_counts': dict(get_ledger(st).flow_counts), 'ledger_stocks': get_ledger(st).stocks,
                'ports': {off: [p.ready, p.pending, p.departed] for off, p in st.lane_offramp_runtime.ports.items()}}
    return snapshot, seen


def count_duals(value):
    if isinstance(value, dict):
        return sum(count_duals(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(count_duals(v) for v in value)
    return 1 if is_dual(value) else 0


def run_parity():
    from evaluation.controllers.sdmpc_tangent_state import state_error
    from evaluation.controllers import control_area_objective as cao
    log = S3P.install(cao, root=ROOT)     # K8 amendment 10: the K8-2 S3 ledger gate, instrumented
    scalar, _seen = parity_case(G3, G4, OFFSET, 0.0)
    _tr, g3, g4, offset = dual_inputs()
    zero = g3 - G3                        # primal 0, tangent 1: the LOR:85 n<=0 skip
    taped, seen = parity_case(g3, g4, offset, zero)
    error = S3P.compare(scalar, taped, log, comparator=state_error, snapshot_keys=('flow_counts',))
    report = log.report()
    ok, why = S3P.verdict(report, error)
    return {'state_error': error, 'tie_seen': seen['tie'], 'zero_release_seen': seen['zero'],
            'dual_values': count_duals(taped), 's3_rule_ok': ok, 's3_rule_why': why,
            's3': {k: report[k] for k in ('installed', 's3_calls', 's3_calls_by_origin', 'sa_created',
                                          'sa_created_by_origin', 'compares', 'excluded_records',
                                          'excluded_by_site', 'excluded_by_origin', 'excluded_keys',
                                          'not_excluded', 'not_excluded_count', 'sites')}}


if __name__ == '__main__':
    result = {'derivatives': run_derivatives, 'tie': run_tie, 'carry': run_carry, 'parity': run_parity}[SCENARIO]()
    print(json.dumps(result, default=float))
