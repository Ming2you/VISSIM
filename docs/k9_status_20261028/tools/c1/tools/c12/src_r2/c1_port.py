"""C1 port (K8 amendment C1, D-K9-94): Omega701 approaches, the meter decision bundle and the FW_E head table.

Inert without the tuning section `c1_port`: apply_tuning returns the very same object with empty metadata,
install_head_service does nothing.  Evidence is named and sha256-pinned only (no path string in the tuning);
a name resolves inside the code-constant folders C1_DIRS.  Probe build (scratch, not a commit).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C1_DIRS = {'omega701': 'diagnostics/b0_v3c3/omega701', 'pack': 'diagnostics/b0_v3c3/evidence',
           'c1': 'diagnostics/sdmpc_n31_20260924/c1/evidence'}
KEYS = ('omega701', 'meter_neighbor_audit', 'max_leader_candidates', 'allow_zero_green', 'storage_release_guard',
        'held_retention', 'head_service', 'storage_capacity_guard')
GUARD_KEYS = ('segments_name', 'segments_sha256', 'unit', 'full_rule', 'capacity_threshold', 'min_source_capacity_veh',
              'feeder_attribution', 'landing_sources', 'short_receiver_rule', 'reserve_green_sec', 'meter_rule')
GUARD_FIXED = {'unit': 'lane', 'full_rule': 'count_or_spill', 'feeder_attribution': 'cell_chain_max',
               'landing_sources': True, 'short_receiver_rule': 'count', 'meter_rule': 'approach_chain_or_m4'}
NETWORK_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
BUNDLE_SCHEMA = 'c1-omega701-bundle/v1'
HEAD_SCHEMA = 'c1-head-service-fwe/v1'
HEAD_METERS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
ROLE_COUNTS = {'membership': 1, 'route_contract': 1, 'pack': 8, 'lane_plant_manifest': 1}
HEX = frozenset('0123456789abcdef')


def _name(value, key):
    if (not isinstance(value, str) or not value or '/' in value or '\\' in value or '..' in value or ':' in value
            or Path(value).is_absolute()):
        raise ValueError('c1_port.' + key + ' must be a plain evidence name (no path)')
    return value


def _sha(value, key):
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError('c1_port.' + key + ' must be a lowercase sha256')
    return value


def check_value(key, value):
    """Shape of one c1_port sub-key (amendment C1 section 2.1)."""
    if key == 'omega701':
        if not isinstance(value, dict) or set(value) != {'bundle_name', 'bundle_sha256'}:
            raise ValueError('c1_port.omega701 requires exactly bundle_name and bundle_sha256')
        _name(value['bundle_name'], 'omega701.bundle_name')
        _sha(value['bundle_sha256'], 'omega701.bundle_sha256')
    elif key in ('meter_neighbor_audit', 'held_retention'):
        if value is not True:
            raise ValueError('c1_port.' + key + ' accepts only true (remove the key to disable)')
    elif key == 'allow_zero_green':
        if value is not False:
            raise ValueError('c1_port.allow_zero_green accepts only false (remove the key to disable)')
    elif key == 'max_leader_candidates':
        if type(value) is not int or value < 1:
            raise ValueError('c1_port.max_leader_candidates must be a positive integer')
    elif key == 'storage_release_guard':
        if (not isinstance(value, dict) or set(value) != {'enabled', 'trigger_fraction'} or value['enabled'] is not True
                or type(value['trigger_fraction']) not in (int, float)
                or not math.isfinite(value['trigger_fraction']) or not 0 < value['trigger_fraction'] <= 1):
            raise ValueError('c1_port.storage_release_guard requires {"enabled": true, "trigger_fraction": (0, 1]}')
    elif key == 'head_service':
        if (not isinstance(value, dict)
                or set(value) != {'evidence_name', 'evidence_sha256', 'meters', 'full_service_rule'}):
            raise ValueError('c1_port.head_service requires evidence_name, evidence_sha256, meters, full_service_rule')
        _name(value['evidence_name'], 'head_service.evidence_name')
        _sha(value['evidence_sha256'], 'head_service.evidence_sha256')
        if value['meters'] != list(HEAD_METERS):
            raise ValueError('c1_port.head_service.meters must be ' + ', '.join(HEAD_METERS) + ' in that order')
        if value['full_service_rule'] != 'keep_green_10':
            raise ValueError('c1_port.head_service.full_service_rule must be keep_green_10')
    elif key == 'storage_capacity_guard':
        if not isinstance(value, dict) or set(value) != set(GUARD_KEYS):
            raise ValueError('c1_port.storage_capacity_guard requires exactly ' + ', '.join(GUARD_KEYS))
        _name(value['segments_name'], 'storage_capacity_guard.segments_name')
        _sha(value['segments_sha256'], 'storage_capacity_guard.segments_sha256')
        for k, accepted in GUARD_FIXED.items():
            x = value[k]
            ok = (x is accepted) if isinstance(accepted, bool) else (type(x) is str and x == accepted)
            if not ok:
                raise ValueError('c1_port.storage_capacity_guard.%s accepts only %r' % (k, accepted))
        for k, lo_open, hi in (('capacity_threshold', True, 1.0), ('min_source_capacity_veh', False, None),
                               ('reserve_green_sec', True, 2.0)):
            x = value[k]
            if (isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                    or (x <= 0 if lo_open else x < 0) or (hi is not None and x > hi)):
                raise ValueError('c1_port.storage_capacity_guard.%s is out of range' % k)
    else:
        raise ValueError('c1_port has an unknown key: ' + str(key))


def validate(section, tuning=None):
    if not isinstance(section, dict) or not section:
        raise ValueError('c1_port must be a non-empty object')
    unknown = sorted(set(section) - set(KEYS))
    if unknown:
        raise ValueError('c1_port has unknown keys: ' + ', '.join(map(str, unknown)))
    for key, value in section.items():
        check_value(key, value)
    if 'meter_neighbor_audit' in section and not {'allow_zero_green', 'storage_release_guard'} <= set(section):
        raise ValueError('c1_port.meter_neighbor_audit requires allow_zero_green and storage_release_guard '
                         '(D-K9-94 Q1/Q11)')
    if 'storage_capacity_guard' in section and 'storage_release_guard' not in section:
        raise ValueError('c1_port.storage_capacity_guard requires storage_release_guard (amendment C1-2)')
    if tuning is not None:
        if 'head_service' in section and not (tuning.get('freeway') or {}).get('lane_plant'):
            raise ValueError('c1_port.head_service requires freeway.lane_plant')
        if 'meter_neighbor_audit' in section and (tuning.get('adapter') or {}).get('sdmpc_control_blocks') != 3:
            raise ValueError('Finite meter schedule audit requires three control blocks')
    return section


def load_named(dir_key, name, digest, schema=None):
    path = ROOT / C1_DIRS[dir_key] / _name(name, 'evidence name')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('C1 evidence sha256 differs: ' + name)
    doc = json.loads(raw.decode('utf-8-sig'))
    if schema is not None and (not isinstance(doc, dict) or doc.get('schema') != schema):
        raise ValueError('C1 evidence schema differs: ' + name)
    return doc


def _get(doc, pointer):
    x = doc
    for part in pointer.strip('/').split('/'):
        x = x[int(part)] if isinstance(x, list) else x[part]
    return x


def _set(doc, pointer, value):
    parts = pointer.strip('/').split('/')
    x = doc
    for part in parts[:-1]:
        x = x[int(part)] if isinstance(x, list) else x[part]
    last = parts[-1]
    if isinstance(x, list):
        x[int(last)] = value
    else:
        if last not in x:
            raise ValueError('c1_port tuning pointer missing: ' + pointer)
        x[last] = value


def _file_sha(rel):
    if not isinstance(rel, str) or not rel:
        return None
    path = ROOT / rel
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _leaf_diff(a, b, pointer=''):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(pointer + '/' + k)
            else:
                out += _leaf_diff(a[k], b[k], pointer + '/' + k)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [pointer]
        out = []
        for i, (u, v) in enumerate(zip(a, b)):
            out += _leaf_diff(u, v, pointer + '/' + str(i))
        return out
    return [] if (type(a) is type(b) and a == b) else [pointer]


def apply_tuning(tuning, state_json=None):
    """(i) no c1_port -> the same object, {}; (ii) the 11 Omega701 pointers all at their c20aff1d files (sha = bundle
    /before_c20aff1d) -> a deep copy with the 11 pointers replaced; (iii) all already replaced -> unchanged (checks
    and metadata only); anything else -> ValueError.  Without omega701 the pointers are not touched."""
    if not isinstance(tuning, dict) or 'c1_port' not in tuning:
        return tuning, {}
    section = tuning['c1_port']
    validate(section, tuning)
    if state_json is not None:
        from evaluation.controllers.network_provenance import snapshot_network_sha256
        if snapshot_network_sha256(state_json) != NETWORK_SHA256:
            raise ValueError('c1_port evidence belongs to network v3c3; the observed state is another network')
    meta = {'keys': sorted(section), 'network_sha256': NETWORK_SHA256}
    result = tuning
    if 'omega701' in section:
        om = section['omega701']
        bundle = load_named('c1', om['bundle_name'], om['bundle_sha256'], BUNDLE_SCHEMA)
        if bundle.get('network_sha256') != NETWORK_SHA256:
            raise ValueError('Omega701 bundle network differs')
        entries = bundle['entries']
        counts = {}
        for e in entries:
            counts[e['role']] = counts.get(e['role'], 0) + 1
        if len(entries) != 11 or counts != ROLE_COUNTS:                                   # O1
            raise ValueError('Omega701 bundle must hold 11 entries (membership 1, route_contract 1, pack 8, '
                             'lane_plant_manifest 1)')
        pointers = {}
        for e in entries:
            rel = C1_DIRS[e['dir']] + '/' + _name(e['name'], 'omega701 entry')
            if _file_sha(rel) != e['sha256']:                                              # O2
                raise ValueError('Omega701 bundle file differs from its pin: ' + e['name'])
            for ptr in e['tuning_pointers']:
                if ptr in pointers:
                    raise ValueError('Omega701 bundle pointer listed twice: ' + ptr)
                pointers[ptr] = (rel, e)
        before = bundle['before_c20aff1d']
        if len(pointers) != 11 or set(before) != set(pointers):
            raise ValueError('Omega701 bundle pointers and before_c20aff1d differ')
        current = {ptr: _get(tuning, ptr) for ptr in pointers}
        if all(current[p] == pointers[p][0] for p in pointers):
            pass                                                                          # (iii)
        elif all(_file_sha(current[p]) == before[p]['sha256'] for p in pointers):
            result = copy.deepcopy(tuning)                                                # (ii)
            for ptr, (rel, _e) in pointers.items():
                _set(result, ptr, rel)
            changed = sorted(_leaf_diff(tuning, result))
            if changed != sorted(pointers):                                               # O8
                raise ValueError('Omega701 replacement changed a tuning leaf outside its 11 pointers')
        else:
            raise ValueError('c1_port.omega701 needs the c20aff1d tuning pointers or the applied ones')
        meta['omega701'] = {'bundle_sha256': om['bundle_sha256'],
                            'replaced': {ptr: {'before_sha256': before[ptr]['sha256'], 'after_name': e['name'],
                                               'after_sha256': e['sha256']}
                                         for ptr, (_rel, e) in sorted(pointers.items())}}
    if 'head_service' in section:
        hs = section['head_service']
        ev = load_named('c1', hs['evidence_name'], hs['evidence_sha256'], HEAD_SCHEMA)
        meta['head_service'] = {'evidence_sha256': hs['evidence_sha256'], 'meters': list(hs['meters']),
                                'rule': hs['full_service_rule'], 'dropped': copy.deepcopy(ev['values']['dropped'])}
    return result, meta


def install_head_service(lane_context, tuning):
    """Replace the four FW_E meter curves of the lane-plant component (reference_config source) by the evidence
    curves; the installer (lane_plant_runtime) then normalises them with keep_green_10.  No key -> nothing."""
    section = (tuning or {}).get('c1_port') or {}
    if 'head_service' not in section:
        return None
    if lane_context is None:
        raise ValueError('c1_port.head_service requires freeway.lane_plant')
    hs = section['head_service']
    check_value('head_service', hs)
    ev = load_named('c1', hs['evidence_name'], hs['evidence_sha256'], HEAD_SCHEMA)
    values = ev['values']
    if values['meters'] != list(HEAD_METERS) or values['full_service_rule'] != hs['full_service_rule']:
        raise ValueError('C1 head evidence meters / rule differ from the tuning')
    from evaluation.controllers.physical_ramp_branches import measured_head_service_table
    settings = tuning['actuation']['real_world_ramp_metering']
    minimum = settings['min_green_sec']
    component = lane_context['component']
    old = dict(component.ramp_head_service_veh_per_cycle or {})
    table = dict(old)
    for meter in HEAD_METERS:
        curve = values['curves_veh_per_cycle'][meter]
        if not isinstance(curve, dict) or set(curve) != set(map(str, range(2, 11))):                    # H1
            raise ValueError('C1 head curve requires green2 through10: ' + meter)
        seq = [curve[str(g)] for g in range(2, 11)]
        if (any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in seq)
                or seq != sorted(seq)):
            raise ValueError('C1 head curve must be finite, nonnegative, monotone: ' + meter)
        if meter not in component.ramps:
            raise ValueError('C1 head meter is not a lane-plant ramp: ' + meter)
        installed, dropped = measured_head_service_table(curve, minimum, full_service_rule=hs['full_service_rule'])
        if (repr(installed) != repr(values['installed_service_by_green_veh_h'][meter])                  # H2
                or dropped != values['dropped'][meter]):
            raise ValueError('C1 head installed table differs from its evidence: ' + meter)
        lanes = settings.get('meter_lanes', {}).get(meter, 1)
        if installed['10'] != lanes * float(settings['per_lane_veh_per_cycle']['10']) * 3600 / settings['cycle_sec']:
            raise ValueError('C1 head green10 service differs from the current full service: ' + meter)    # H5
        table[meter] = copy.deepcopy(curve)
    changed = {k for k in set(table) | set(old) if table.get(k) != old.get(k)}
    if changed != set(HEAD_METERS):                                                                     # H4
        raise ValueError('C1 head install must change exactly the four FW_E meters')
    component.ramp_head_service_veh_per_cycle = table
    component.provenance['physical_ramp_head_service_veh_per_cycle'] = copy.deepcopy(table)
    lane_context['c1_head_service'] = {'meters': list(HEAD_METERS), 'rule': hs['full_service_rule'],
                                       'evidence_sha256': hs['evidence_sha256']}
    return lane_context['c1_head_service']


def operating_bounds(state, cfg, reference):
    """codex configure_operating_bounds (unchanged), then (amendment C1 RV-2) a floor that is not a green of the
    meter's own service table is lowered to the largest table green in [base, floor]; recorded when lowered."""
    from evaluation.controllers.physical_ramp_branches import configure_operating_bounds
    result = configure_operating_bounds(state, cfg, reference)
    spec = cfg.network.physical_ramp_branches
    base = 0. if spec.get('allow_zero_green', True) else spec['minimum_green_sec']
    floors = cfg.network.ramp_operating_green_floors
    guard = getattr(cfg.network, 'c1_storage_capacity_guard', None)
    if guard is not None:
        # amendment C1-2 section 5.7 (E28): the approach-chain trigger OR M4, same floor formula (CX PRB:901 form)
        for ramp in list(floors):
            row = guard['meters'][ramp]
            evidence = result['ramps'][ramp]
            evidence['guard_triggered'] = bool(row['triggered'])
            evidence['guard_sources'] = list(row['sources']) if row['triggered'] else []
            if evidence['guard_triggered'] and not evidence['triggered']:
                floors[ramp] = max(base, min(spec['cycle_sec'], evidence['previous_green_sec']+spec['max_green_change_sec']))
                evidence['minimum_green_sec'] = floors[ramp]
    for ramp in list(floors):
        greens = sorted(int(g) for g in spec['ramps'][ramp]['service_by_green_veh_h'])
        evidence = result['ramps'][ramp]
        floor = floors[ramp]
        if not any(g == floor for g in greens):
            lower = [g for g in greens if base <= g <= floor]
            if not lower:
                raise ValueError('C1 storage floor has no table green: ' + ramp)
            floors[ramp] = float(max(lower))
            evidence['minimum_green_sec'] = floors[ramp]
            evidence['table_rounded_from'] = floor
        value = floors[ramp]
        if (not any(g == value for g in greens) or value < base                                         # G-A7
                or ((evidence['triggered'] or evidence.get('guard_triggered', False))
                    and value < min(evidence['previous_green_sec'] + 1, spec['cycle_sec']))):
            raise ValueError('C1 storage floor has no table green: ' + ramp)
    return result


# ================================================================================================ amendment C1-2 guard
# E29: the general storage-capacity guard (section 5).  Every line below runs only when the tuning holds
# c1_port.storage_capacity_guard (RS E23 -> cfg.network.c1_storage_capacity_guard -> SD E24-E27, C1P E28).
import bisect  # noqa: E402
from collections import deque  # noqa: E402

import numpy as np  # noqa: E402  (the two codex functions use np, CX urban_storage_guard.py:10)

GUARD_SCHEMA = 'c1g-storage-segments/v1'
GUARD_OBSERVED_SCHEMA = 'c1g-observed-lane-storage/v1'
GUARD_SPILL = {'top_window_m': 12.0, 'stop_speed_kph': 5.0, 'max_clear_gap_m': 20.0,
               'bottom_reach': 'max(20.0, 0.2 * length_m)', 'short_length_m': 12.0}
GUARD_METERS = ('RM_C10480', 'RM_C10482', 'RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10644', 'RM_C10646', 'RM_C10681')
_GUARD_CACHE = {}


def guard_index(doc):
    """Lookup tables of one evidence document (no network read; section 5.9-5.10)."""
    seg = {s['id']: s for s in doc['segments']}
    lanes = {}
    for s in doc['segments']:
        lanes.setdefault((str(s['link']), int(s['lane'])), []).append((float(s['start_m']), float(s['end_m']), s['id']))
    for v in lanes.values():
        v.sort()
    cells = {c['id']: c for c in doc['cells']}
    attr = {}
    for e in doc['attribution']:
        adj = {}
        for u, v in e['edges']:
            adj.setdefault(u, []).append(v)
        attr.setdefault(e['segment'], []).append((e, adj))
    return {'_index': True, 'doc': doc, 'seg': seg, 'lanes': lanes, 'cells': cells, 'attr': attr,
            'groups': doc.get('overlap_groups') or {}, 'meters': doc['meters']}


def load_segments(section, cfg=None):
    """Evidence by name + sha256, schema, network, spacing, spill constants, short threshold (section 5.10)."""
    check_value('storage_capacity_guard', section)
    key = (section['segments_name'], section['segments_sha256'])
    ev = _GUARD_CACHE.get(key)
    if ev is None:
        ev = guard_index(load_named('c1', section['segments_name'], section['segments_sha256'], GUARD_SCHEMA))
        _GUARD_CACHE[key] = ev
    doc = ev['doc']
    if doc.get('network_sha256') != NETWORK_SHA256:
        raise ValueError('C1G evidence belongs to another network')
    if doc.get('spill_rule') != GUARD_SPILL:
        raise ValueError('C1G evidence spill constants differ from the code constants')
    if doc.get('min_source_capacity_veh') != section['min_source_capacity_veh']:
        raise ValueError('C1G evidence short threshold differs from c1_port.storage_capacity_guard')
    if cfg is not None and float(cfg.network.urban_avg_vehicle_length_m) != doc.get('spacing_m'):
        raise ValueError('C1G evidence spacing differs from cfg.network.urban_avg_vehicle_length_m')
    return ev


def _guard_spill(sub, start, end, lengths):
    """S of one segment (section 5.2): sub = [(position, veh_no, speed)] sorted, all inside [start, end]."""
    j0 = -1
    zone_end = start + GUARD_SPILL['top_window_m']
    for j, (p, _veh, speed) in enumerate(sub):
        if p > zone_end:
            break
        if speed < GUARD_SPILL['stop_speed_kph']:
            j0 = j
            break
    if j0 < 0:
        return False
    length = end - start
    if length <= GUARD_SPILL['short_length_m']:
        return True
    cur = sub[j0]
    for nxt in sub[j0 + 1:]:
        if nxt[0] - lengths[nxt[1]] - cur[0] <= GUARD_SPILL['max_clear_gap_m']:
            cur = nxt
        else:
            break
    return cur[0] >= end - max(GUARD_SPILL['max_clear_gap_m'], 0.2 * length)


def storage_capacity_core(records, frame_lengths, evidence, live_phases, meter_names, capacity_threshold=1.0):
    """Pure function (section 5.2-5.7): counts, spill, full, cell full, receivers, attribution, overlap max, phase
    weights (equal live-phase weights zeroed), meter triggers.  records = complete vehicle records, frame_lengths =
    {veh_no: length_m} of the same-time lane frame, live_phases = {signal: live phases} in cfg.network.signals order."""
    ix = evidence if evidence.get('_index') else guard_index(evidence)
    seg, cells = ix['seg'], ix['cells']
    by_lane = {}
    for r in records:
        by_lane.setdefault((str(r['link_no']), int(r['lane_no'])), []).append(
            (float(r['position_m']), int(r['veh_no']), float(r['speed_kph'])))
    for v in by_lane.values():
        v.sort()
    count, spill, full = {}, {}, {}
    for key, rows in ix['lanes'].items():
        vs = by_lane.get(key, [])
        pos = [v[0] for v in vs]
        for start, end, sid in rows:
            sub = vs[bisect.bisect_left(pos, start):bisect.bisect_right(pos, end)]
            for v in sub:
                if v[1] not in frame_lengths:
                    raise ValueError('C1G lane frame lacks the length of a counted vehicle')
            s = seg[sid]
            count[sid] = len(sub)
            spill[sid] = _guard_spill(sub, start, end, frame_lengths)
            by_count = len(sub) / s['capacity_veh'] >= capacity_threshold
            full[sid] = by_count if (s['kind'] == 'R' and s['short']) else (by_count or spill[sid])

    def cell_ok(cid):
        c = cells[cid]
        return bool(c['short'] or (c['judge'] is not None and full[c['judge']]))
    all_full = {sid: bool(s['receivers']) and all(full[r] for r in s['receivers'])
                for sid, s in seg.items() if s['kind'] == 'A'}
    scores, minus_one, attributed = {}, [], {}
    meters = {m: [] for m in meter_names}
    for sid in sorted(all_full):
        s = seg[sid]
        if not s['source']:
            continue
        if all_full[sid]:
            score = -1.
            minus_one.append(sid)
        elif full[sid] and s['receivers']:
            score = max(1., count[sid] / s['capacity_veh'])
        else:
            score = 0.
        for srv in s['servers']:
            scores.setdefault(srv, []).append((sid, score))
    cells_seen = set()
    for sid in sorted(ix['attr']):
        s = seg[sid]
        if not s['source'] or not full[sid]:
            continue
        reached = {}
        for e, adj in ix['attr'][sid]:
            cells_seen.update(e['cells'])
            start, head = e['start_cell'], e['head_cell']
            if not cell_ok(start):
                continue
            seen, q, hit = {start}, deque([start]), start == head
            while q and not hit:
                u = q.popleft()
                for v in adj.get(u, ()):
                    if v not in seen and cell_ok(v):
                        if v == head:
                            hit = True
                            break
                        seen.add(v)
                        q.append(v)
            if hit:
                reached.setdefault(e['server'], set()).add(e['head_lane_segment'])
        for srv in sorted(reached):
            attributed.setdefault(sid, []).append(srv)
            if srv in meters:
                meters[srv].append(sid)
                continue
            heads = reached[srv]
            score = 0. if all(all_full.get(h, False) for h in heads) else max(1., count[sid] / s['capacity_veh'])
            scores.setdefault(srv, []).append((sid, score))
    weights, dropped = {}, []
    for srv, items in sorted(scores.items()):
        member = {}
        for gi, g in enumerate(ix['groups'].get(srv, [])):
            for m in g:
                member[m] = gi
        best, negative = {}, []
        for sid, score in sorted(items):
            if score < 0:
                negative.append(score)
            elif score > 0:
                k = ('g', member[sid]) if sid in member else ('s', sid)
                best.setdefault(k, []).append((score, sid))
        kept = []
        for k in sorted(best):
            rows = sorted(best[k], key=lambda x: (-x[0], x[1]))
            kept.append(rows[0][0])
            dropped.extend([srv, sid] for _score, sid in rows[1:])
        weights[srv] = math.fsum(kept + negative)
    signals, zeroed = {}, []
    for owner, live in live_phases.items():
        w = {owner + '_' + p: weights.get(owner + '_' + p, 0.) for p in live}
        vals = list(w.values())
        if vals and max(vals) - min(vals) <= 1e-12:
            if any(v != 0. for v in vals):
                zeroed.append(owner)
            w = {k: 0. for k in w}
        signals[owner] = w
    full_ids = sorted(k for k, v in full.items() if v)
    by_kind = {}
    for k in full_ids:
        by_kind[seg[k]['kind']] = by_kind.get(seg[k]['kind'], 0) + 1
    return {'signals': signals,
            'meters': {m: {'triggered': bool(meters[m]), 'sources': sorted(meters[m])} for m in meter_names},
            'full': full_ids, 'full_by_kind': by_kind, 'minus_one_lanes': minus_one, 'equal_weights_zeroed': zeroed,
            'overlap_dropped': sorted(dropped), 'short_segment_count': sum(1 for s in seg.values() if s['short']),
            'detail': {'counts': {k: v for k, v in sorted(count.items()) if v},
                       'spill': sorted(k for k, v in spill.items() if v),
                       'cells_full': sorted(c for c in cells_seen if not cells[c]['short'] and cell_ok(c)),
                       'attributed': {k: v for k, v in sorted(attributed.items())},
                       'scores': {k: [[sid, sc] for sid, sc in sorted(v)] for k, v in sorted(scores.items())},
                       'weights_before_equal_zero': {k: v for k, v in sorted(weights.items())}}}


def observe_storage_capacity(cfg, tuning, state_json):
    """E23 (RS, after the physical ramp configuration): observe the guard at the decision time, from the state's
    complete vehicle records and the same-time lane frame; sets cfg.network.c1_storage_capacity_guard (None first, as
    CX USG:15) and returns the RS metadata block (section 5.11).  Reads state_json only."""
    cfg.network.c1_storage_capacity_guard = None
    section = ((tuning or {}).get('c1_port') or {})['storage_capacity_guard']
    ev = load_segments(section, cfg)
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers import obs150_contract
    records = complete_records(state_json)
    obs = state_json['obs150']
    current = obs['frames']['current']
    frame = obs150_contract.load_frame(obs150_contract.resolve(obs, current['path']), current['sha256'],
                                       state_json['sim_sec'])
    lengths = {int(row[0]): float(row[5]) for row in frame['vehicles']}
    live = {owner: tuple(cfg.network.signal_live_phases(owner)) for owner in cfg.network.signals}
    meters = tuple(cfg.network.physical_ramp_branches['ramps'])
    if sorted(meters) != sorted(GUARD_METERS) or sorted(ev['meters']) != sorted(GUARD_METERS):
        raise ValueError('C1G meters differ from the eight physical ramp meters')
    core = storage_capacity_core(records, lengths, ev, live, meters, capacity_threshold=section['capacity_threshold'])
    cfg.network.c1_storage_capacity_guard = {'schema': GUARD_OBSERVED_SCHEMA, 'policy': copy.deepcopy(section),
                                             'signals': core['signals'], 'meters': core['meters'],
                                             'observed_sec': float(state_json['sim_sec'])}
    return {'evidence_sha256': section['segments_sha256'], 'observed_sec': float(state_json['sim_sec']),
            'frame_sha256': current['sha256'], 'full_segments': core['full'], 'full_by_kind': core['full_by_kind'],
            'signals': core['signals'], 'meters': core['meters'], 'minus_one_lanes': core['minus_one_lanes'],
            'equal_weights_zeroed': core['equal_weights_zeroed'], 'overlap_dropped': core['overlap_dropped'],
            'short_segment_count': core['short_segment_count'], 'detail': core['detail']}


def _guard_num(x):
    x = float(x)
    return x if math.isfinite(x) else ('+inf' if x > 0 else '-inf' if x < 0 else 'nan')


def storage_capacity_meta(coord, seed_projected):
    """E27 decision metadata (section 5.11): block receipts, LP inputs per receipt signal (phase rows only, before the
    guard rows), seed projection, block-0 reference inside the phase rows (stop 9)."""
    blocks = list(getattr(coord, 'blocks', [coord]))
    out = {'blocks': [], 'lp_inputs': [], 'seed_projected': bool(seed_projected), 'reference_in_phase_limits': {}}
    for k, b in enumerate(blocks):
        receipts = copy.deepcopy(getattr(b, 'c1_storage_capacity_receipt', []))
        out['blocks'].append(receipts)
        rows = {}
        n_phase = len(b.phase_rows)
        for r in receipts:
            owner = r['signal']
            ix = [j for j, a in enumerate(b.axes) if a['owner'] == owner and a['kind'] == 'green']
            G = b.G[:n_phase][:, ix]
            mask = np.any(G != 0, axis=1)
            lo, hi = b.glo[:n_phase][mask], b.ghi[:n_phase][mask]
            rows[owner] = {'axes': ix, 'green_vectors': [dict(b.green_vectors[j]) for j in ix],
                           'axis_scale': [float(b.axes[j]['scale']) for j in ix],
                           'G': [[float(x) for x in row] for row in G[mask]], 'glo': [_guard_num(x) for x in lo],
                           'ghi': [_guard_num(x) for x in hi], 'lower': [_guard_num(b.lower[j]) for j in ix],
                           'upper': [_guard_num(b.upper[j]) for j in ix]}
            if k == 0:
                out['reference_in_phase_limits'][owner] = bool(np.all(lo <= 0.) and np.all(hi >= 0.))
        out['lp_inputs'].append(rows)
    return out


def constrain_storage_capacity(coord):
    """One feasible pressure-progress halfspace per affected signal, no rollout.

    LP uses the actual command's existing phase/min/max/cycle/trust constraints.
    Conflicting full approaches cannot independently demand extra cycle time.
    Half of attainable improvement leaves room for millisecond writer rounding.
    """
    from scipy.optimize import linprog
    data = getattr(coord.cfg.network, 'c1_storage_capacity_guard', None)
    coord.c1_storage_capacity_receipt = []
    if not data:
        return
    for owner, weights in data['signals'].items():
        scale = max(map(abs, weights.values()), default=0.)
        if not scale:
            continue
        ix = [j for j, a in enumerate(coord.axes) if a['owner'] == owner and a['kind'] == 'green']
        w = np.array([sum(weights.get(owner+'_'+p, 0.)*factor for p, factor in coord.green_vectors[j].items())
                      *coord.axes[j]['scale']/scale for j in ix])
        if not ix or np.max(np.abs(w), initial=0) < 1e-10:
            coord.c1_storage_capacity_receipt.append(dict(signal=owner, status='no_green_redistribution_direction'))
            continue
        G = coord.G[:, ix]
        mask = np.any(G != 0, axis=1)
        G, lo, hi = G[mask], coord.glo[mask], coord.ghi[mask]
        matrix = np.concatenate((G[np.isfinite(hi)], -G[np.isfinite(lo)]))
        rhs = np.concatenate((hi[np.isfinite(hi)], -lo[np.isfinite(lo)]))
        result = linprog(-w, A_ub=matrix, b_ub=rhs,
                         bounds=list(zip(coord.lower[ix], coord.upper[ix])), method='highs')
        if not result.success:
            raise ValueError('Urban reserve actuator feasibility failed: '+owner)
        maximum = float(w@result.x)
        required = min(data['policy']['reserve_green_sec'], max(0., maximum)*.5)
        receipt = dict(signal=owner, attainable_pressure_sec=maximum,
                       required_pressure_sec=required, phase_weights=weights)
        if required < .01:
            receipt['status'] = 'no_attainable_reserve_progress'
        else:
            row = np.zeros(len(coord.axes)); row[ix] = w
            coord.G = np.vstack((coord.G, row))
            coord.glo = np.append(coord.glo, required)
            coord.ghi = np.append(coord.ghi, np.inf)
            receipt['status'] = 'constrained'
        coord.c1_storage_capacity_receipt.append(receipt)


def storage_capacity_seed(coord, reference, policy):
    """Project warm start only; preserve the previous applied trust anchor."""
    if coord.valid(coord.encode(reference)):
        return reference
    from evaluation.controllers.sdmpc import solve_qp
    z = coord.encode(reference)
    step, proof = solve_qp(np.zeros(len(z)), np.zeros(len(z)), 1.,
        coord.lower-z, coord.upper-z, coord.G, coord.glo-coord.G@z, coord.ghi-coord.G@z, policy)
    if not proof['success']:
        raise ValueError('Urban/ramp reserve has no executable operating seed')
    # Leave the active reserve face before the native writer rounds greens to
    # milliseconds. Physical min/max and consecutive changes stay constrained.
    step, proof = solve_qp(1.05*step, np.zeros(len(z)), 1.,
        coord.lower-z, coord.upper-z, coord.G, coord.glo-coord.G@z, coord.ghi-coord.G@z, policy)
    if not proof['success']:
        raise ValueError('Urban/ramp reserve rounding-margin projection failed')
    seed = coord.decode(z+step, reference)
    coord.validate(seed)
    return seed
