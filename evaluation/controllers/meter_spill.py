"""Meter-owner attribution of pre-head spill (K8-3 S1-OWN, user decision D-K8-2).

S1 (`PhysicalRampBoundary._admission_space_veh`) admits urban traffic into a metered ramp only up to the free
pre-head compartment. Traffic that S1 rejects although the pre-S1 whole-connector room (the K7 rule) would have
taken it stays in its upstream feeder stock: physical stocks, accepted transfers, the ledger TTT (Omega) and the
leader resources are exactly those of S1. What changes is only the Omega owner partition (`sdmpc.omega_costs`):
the residence cost of that pre-head spill is charged to the ramp's meter owner o(r) =
sdmpc_cost_ownership['ramp:' + r] (FW_W / FW_E) instead of the feeder's owner.

Spill stock E[r][f] >= 0 (vehicles) lives on the candidate ledger (`ModelAreaLedger.meter_spill`, absent until the
first entry; the ledger copy carries it). It starts empty: queues standing at the decision time stay with their
owner. At the four ramp admission sites, right after the site fixes its actual S1 admission A and before the
ramp stock is updated:

    K7 room   F7 = max(0, room_K7(r) - sum_f' E[r][f'])      room_K7 = max(0, space_K7 - max(0, pending))
    request   capped feeders (movement, SC2001 branch, shared branch):  R0 = min(R, max(0, Y - E))
              proportional feeder (legsplit W_out, R = c*Y):             R0 = max(0, R - c*E),  c = reach/arrived
    A0        the site's own admission rule applied to R0 with room F7
    update    E' = min(max(0, E + A0 - A), max(0, Y - A))

E grows only while the pre-head limit binds below the K7 room and is released as admissions exceed what the
unspilled feeder would have sent. Only the S1 increment is attributed: a ramp full under the K7 rule too keeps its
upstream queue with the feeder's owner (amendment 2 N-A10).

Creation uses primal values only (A < R and E' > THRESHOLD_VEH), decided before any AD operation, so a rollout
without pre-head rejection runs no new Dual operation and creates nothing. A created entry is updated by min/max
arithmetic and never deleted (a zero keeps its derivative). `has_transfer` is not used for creation: its tape test
would create zero entries in tangent runs only and break the scalar/tangent state comparison.

Cost (`spill_inside`, `move`): in a residence row that contains feeder f, s_r = min(E[r][f], n_f) * in_f / n_f
(0 when the primal n_f is 0; scaled down proportionally when sum_r s_r > in_f) moves dt*s_r of f's Omega residence
from owner(f) to o(r). The partition total, Omega and every physical quantity are unchanged.

Ported from the K8 scratch prototype amend1/s1/k8own.py (sha256 d5d1be912689611f...); arithmetic order is kept.
Known limits (J1 caveats): E starts at 0; the K7 counterfactual assumes K7 connector = S1 connector + sum E, so a
K7-full interval can be over-attributed and upstream feedback is not represented; the route-less mixed W_out of
the legsplit site is bounded only by Y - A.
"""
from __future__ import annotations

from math import fsum

from evaluation.controllers.control_area_objective import get_ledger

THRESHOLD_VEH = 1e-9


def _primal(value):
    """Primal float of a model value; never an AD operation or branch record."""
    return float(getattr(value, '_validation_primal', value))


def _runtime(state, ramp):
    runtime = getattr(state, 'lane_ramp_runtime', None)
    if runtime is None or ramp not in runtime.buffers:
        return None
    return runtime


def _entry(ledger, ramp, feeder):
    table = getattr(ledger, 'meter_spill', None)
    return None if not table else table.get(ramp, {}).get(feeder)


def _values(ledger, ramp):
    table = getattr(ledger, 'meter_spill', None) or {}
    return list(table.get(ramp, {}).values())


def _store(ledger, ramp, feeder, value):
    table = ledger.__dict__.setdefault('meter_spill', {})
    table.setdefault(ramp, {})[feeder] = value


def _dsum(values):
    out = 0.
    for value in values:
        out = out + value
    return out


def _update(old, virtual, actual, ready):
    """E' = min(max(0, E + A0 - A), max(0, Y - A))."""
    return min(max(0., old + virtual - actual), max(0., ready - actual))


def _room_primal(state, ramp, spill_total):
    return max(0., state.lane_ramp_runtime.total_receiving_space_primal(state, ramp) - spill_total)


def _room(state, ramp, spill_total):
    return max(0., state.lane_ramp_runtime.total_receiving_space(state, ramp) - spill_total)


# ---- site 1: urban movement -> ramp (urban_flow_accounting.urban_substep_accounted) ------------------------------
def movement_virtual(state, cfg, ramp, requests, ramp_space):
    """Before the movement loop: the unspilled-feeder admissions A0 of one ramp, or None (no entry, no rejection)."""
    ledger = get_ledger(state)
    if ledger is None or _runtime(state, ramp) is None:
        return None
    olds = {m: _entry(ledger, ramp, 'movement:' + m) for m in requests}
    p_req = {m: _primal(r) for m, r in requests.items()}
    p_total = sum(p_req[m] for m in requests)
    p_space = _primal(ramp_space)
    if all(o is None for o in olds.values()) and not p_total > p_space:
        return None
    p_ready = {m: max(0., _primal(state.urban_movement_queue.get(m, 0.0))) for m in requests}
    p_old = {m: (_primal(o) if o is not None else 0.) for m, o in olds.items()}
    p_spill = fsum(_primal(v) for v in _values(ledger, ramp))
    p_r0 = {m: min(p_req[m], max(0., p_ready[m] - p_old[m])) for m in requests}
    room7 = _room_primal(state, ramp, p_spill)
    s0 = sum(p_r0.values())
    scale7 = 1.0 if s0 <= room7 else room7 / max(s0, 1.0e-9)
    scale = 1.0 if p_total <= p_space else p_space / max(p_total, 1.0e-9)
    p_a = {m: min(p_ready[m], p_req[m] * scale) for m in requests}
    p_new = {m: _update(p_old[m], p_r0[m] * scale7, p_a[m], p_ready[m]) for m in requests}
    if all(olds[m] is None and not p_new[m] > THRESHOLD_VEH for m in requests):
        return None
    spill = _dsum(_values(ledger, ramp))
    ready = {m: max(0.0, state.urban_movement_queue.get(m, 0.0)) for m in requests}
    r0 = {m: min(requests[m], max(0., ready[m] - (olds[m] if olds[m] is not None else 0.))) for m in requests}
    room = _room(state, ramp, spill)
    t0 = _dsum(r0.values())
    s7 = 1.0 if _primal(t0) <= _primal(room) else room / max(t0, 1.0e-9)
    return {m: (olds[m], r0[m] * s7, ready[m], p_new[m]) for m in requests}


def movement_commit(state, ramp, movement, virtual, accepted):
    """After one movement's actual admission: create/update E[ramp]['movement:' + movement]."""
    if virtual is None or movement not in virtual:
        return
    old, a0, ready, p_new = virtual[movement]
    if old is None and not p_new > THRESHOLD_VEH:
        return
    _store(get_ledger(state), ramp, 'movement:' + movement,
           _update(old if old is not None else 0., a0, accepted, ready))


# ---- site 2: shared approach branch -> ramp (shared_approach.advance) --------------------------------------------
def shared_branch(state, ramp, feeder, ready, service, accepted):
    ledger = get_ledger(state)
    if ledger is None or _runtime(state, ramp) is None:
        return
    old = _entry(ledger, ramp, feeder)
    p_r = min(_primal(ready), _primal(service))
    p_a = _primal(accepted)
    if old is None and not p_a < p_r:
        return
    p_old = _primal(old) if old is not None else 0.
    p_spill = fsum(_primal(v) for v in _values(ledger, ramp))
    p_r0 = min(p_r, max(0., _primal(ready) - p_old))
    p_a0 = min(p_r0, _room_primal(state, ramp, p_spill))
    p_new = _update(p_old, p_a0, p_a, _primal(ready))
    if old is None and not p_new > THRESHOLD_VEH:
        return
    o = old if old is not None else 0.
    r = min(ready, service)
    r0 = min(r, max(0., ready - o))
    a0 = min(r0, _room(state, ramp, _dsum(_values(ledger, ramp))))
    _store(ledger, ramp, feeder, _update(o, a0, accepted, ready))


# ---- site 3: SC2001 corridor branch -> ramp (sc2001_corridor.advance; shared two-lane service factor) -------------
def sc2001_branches(state, spec, ready, pre, accepted, sat, dt_h):
    """pre: branch admissions before the common two-lane factor; accepted: after it."""
    ledger = get_ledger(state)
    if ledger is None:
        return
    feeder = 'storage:' + spec['storage']
    shared = sat * spec['lanes'] * dt_h
    rows = {}
    for key, branch in spec['branches'].items():
        if branch['target_kind'] != 'ramp' or _runtime(state, branch['target']) is None:
            continue
        ramp = branch['target']
        rows[key] = (ramp, _entry(ledger, ramp, feeder), sat * branch['lanes'] * dt_h)
    if not rows:
        return
    if not any(old is not None or _primal(accepted[k]) < min(_primal(ready[k]), _primal(service))
               for k, (ramp, old, service) in rows.items()):
        return
    p_pre0 = {k: _primal(v) for k, v in pre.items()}
    for k, (ramp, old, service) in rows.items():
        p_old = _primal(old) if old is not None else 0.
        p_r0 = min(min(_primal(ready[k]), _primal(service)), max(0., _primal(ready[k]) - p_old))
        p_pre0[k] = min(p_r0, _room_primal(state, ramp, fsum(_primal(v) for v in _values(ledger, ramp))))
    tot = sum(p_pre0.values())
    f7 = min(1., shared / tot) if tot else 1.
    p_new = {}
    for k, (ramp, old, service) in rows.items():
        p_old = _primal(old) if old is not None else 0.
        p_new[k] = _update(p_old, p_pre0[k] * f7, _primal(accepted[k]), _primal(ready[k]))
    if all(rows[k][1] is None and not p_new[k] > THRESHOLD_VEH for k in rows):
        return
    d_pre0 = dict(pre)
    for k, (ramp, old, service) in rows.items():
        o = old if old is not None else 0.
        r0 = min(min(ready[k], service), max(0., ready[k] - o))
        d_pre0[k] = min(r0, _room(state, ramp, _dsum(_values(ledger, ramp))))
    total = _dsum(d_pre0.values())
    f = min(1., shared / total) if _primal(total) > 0 else 1.
    for k, (ramp, old, service) in rows.items():
        if old is None and not p_new[k] > THRESHOLD_VEH:
            continue
        _store(ledger, ramp, feeder, _update(old if old is not None else 0., d_pre0[k] * f, accepted[k], ready[k]))


# ---- site 4: legsplit W_out -> ramp (urban_flow_accounting.legsplit_substep_accounted, two stages) ----------------
def legsplit_request(state, memo, link, ramp, request, reach, arrived, conn, allowed, space):
    """Stage 1 (request prepared against the S1 space): remember the K7 room for stage 2."""
    ledger = get_ledger(state)
    if ledger is None or _runtime(state, ramp) is None:
        return
    values = _values(ledger, ramp)
    p_room = _room_primal(state, ramp, fsum(_primal(v) for v in values))
    if values or (_primal(allowed) < _primal(request) and _primal(space) < p_room):
        # The K7 room differs from the S1 space only through the pre-head limit or an existing spill.
        room1 = (p_room, _room(state, ramp, _dsum(values)))
    else:
        room1 = (p_room, space)
    memo[(link, ramp)] = dict(request=request, reach=reach, arrived=arrived, conn=conn, room1=room1)


def legsplit_accepted(state, memo, accepted_transfers):
    """Stage 2 (after reconciling against the remaining room): create/update E[ramp]['storage:' + link]."""
    ledger = get_ledger(state)
    if ledger is None or not memo:
        return
    amounts = {}
    for link, ramp, amount in accepted_transfers:
        if ramp is not None:
            amounts.setdefault((link, ramp), []).append(amount)
    by_ramp = {}
    for (link, ramp) in memo:
        by_ramp.setdefault(ramp, []).append(link)
    for ramp, links in by_ramp.items():
        rows = {}
        for link in links:
            m = memo[(link, ramp)]
            feeder = 'storage:' + link
            old = _entry(ledger, ramp, feeder)
            parts = amounts.get((link, ramp), [])
            if old is None and not sum(_primal(x) for x in parts) < _primal(m['request']):
                continue
            rows[link] = (feeder, old, parts, m)
        if not rows:
            continue
        p_pre0, p_new, p_ready = {}, {}, {}
        for link, (feeder, old, parts, m) in rows.items():
            p_old = _primal(old) if old is not None else 0.
            p_c = _primal(m['reach']) / _primal(m['arrived']) if _primal(m['arrived']) > 0 else 0.
            p_ready[link] = _primal(m['request']) / p_c if p_c > 0 else 0.
            v = max(0., _primal(m['request']) - p_c * p_old)
            if _primal(m['conn']) > 0.:
                v = min(v, _primal(m['conn']))
            v = min(v, m['room1'][0])
            p_pre0[link] = v
        room2 = _room_primal(state, ramp, fsum(_primal(v) for v in _values(ledger, ramp)))
        tot = sum(p_pre0.values())
        f7 = min(1., room2 / tot) if tot > 0 else 1.
        for link, (feeder, old, parts, m) in rows.items():
            p_old = _primal(old) if old is not None else 0.
            p_new[link] = _update(p_old, p_pre0[link] * f7, sum(_primal(x) for x in parts), p_ready[link])
        if all(rows[k][1] is None and not p_new[k] > THRESHOLD_VEH for k in rows):
            continue
        d_pre0, d_ready = {}, {}
        for link, (feeder, old, parts, m) in rows.items():
            o = old if old is not None else 0.
            c = m['reach'] / m['arrived'] if _primal(m['arrived']) > 0 else 0.
            d_ready[link] = m['request'] / c if _primal(c) > 0 else 0.
            v = max(0., m['request'] - c * o)
            if _primal(m['conn']) > 0.:
                v = min(v, m['conn'])
            v = min(v, m['room1'][1])
            d_pre0[link] = v
        room = _room(state, ramp, _dsum(_values(ledger, ramp)))
        total = _dsum(d_pre0.values())
        f = min(1., room / total) if _primal(total) > 0 else 1.
        for link, (feeder, old, parts, m) in rows.items():
            if old is None and not p_new[link] > THRESHOLD_VEH:
                continue
            _store(ledger, ramp, feeder, _update(old if old is not None else 0., d_pre0[link] * f, _dsum(parts),
                                                 d_ready[link]))


# ---- cost attribution (sdmpc.omega_costs partition only) ---------------------------------------------------------
def spill_inside(row):
    """{feeder: {ramp: s_r}} for one residence row carrying 'meter_spill_veh'."""
    out = {}
    for ramp, by_feeder in row['meter_spill_veh'].items():
        for feeder, amount in by_feeder.items():
            if feeder not in row['inside_veh']:
                continue
            inside = row['inside_veh'][feeder]
            total = row['model_stock_veh'].get(feeder, 0.)
            if not _primal(total) > 0.:
                continue
            out.setdefault(feeder, {})[ramp] = min(amount, total) * (inside / total)
    for feeder, by_ramp in out.items():
        inside = row['inside_veh'][feeder]
        moved = _dsum(by_ramp.values())
        if _primal(moved) > _primal(inside) and _primal(moved) > 0.:
            factor = inside / moved
            for ramp in by_ramp:
                by_ramp[ramp] = by_ramp[ramp] * factor
    return out


def move(pieces, table, passive, by_ramp, dt, value, feeder, attributed):
    """Move dt*s_r of feeder's residence value to each ramp's meter owner; return the feeder owner's remainder.

    attributed[ramp][feeder] accumulates the moved primal veh*h (diagnostic meter_spill_veh_h)."""
    for ramp, share in by_ramp.items():
        piece = dt * share
        pieces[table.get('ramp:' + ramp, passive)].append(piece)
        value = value - piece
        row = attributed.setdefault(ramp, {})
        row[feeder] = row.get(feeder, 0.) + _primal(piece)
    return value
