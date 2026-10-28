"""c1g_recount.py -- independent recount of the C1-2 storage-capacity guard observation (K8 amendment C1-2
dfe9809b7212bdc7..., sections 5.2-5.7; P0-18 (b)(c), probe r2 stop 6, G-K2 (f)).

It does NOT import c1_port nor any controller / harness module: it reads the state file, its same-time lane frame and
the evidence file only, and recounts with its own code (per-segment linear scans, depth-first path search).

    python -B c1g_recount.py <state.json> <evidence.json> <inputs.json> <out.json>
    inputs.json = {"evidence_sha256": ..., "live_phases": {signal: [phases]} (cfg.network.signals order),
                   "meters": [8 names], "capacity_threshold": 1.0}

Library: recount_state(state_path, evidence, live_phases, meters, threshold) -> dict with the runtime detail keys;
compare(runtime, recount) -> list of differences (integers / booleans / id lists equal, weights relative 1e-12).
Vehicle order on a lane = (position, vehicle number) ascending.  The frame is read from /obs150/directory joined with
/obs150/frames/current/path, UTF-16 (BOM) or UTF-8, its sha256 must equal the state's pin, time_s = sim_sec,
complete true, 15-field rows."""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOP, SLOW, GAP, SHORT_LEN = 12.0, 5.0, 20.0, 12.0


def _text(raw):
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def read_state(state_path):
    raw = Path(state_path).read_bytes()
    st = json.loads(raw.decode('utf-8-sig'))
    vr = st.get('vehicle_records') or {}
    recs = vr.get('records')
    if vr.get('complete') is not True or not isinstance(recs, list):
        raise ValueError('recount: incomplete vehicle records')
    if vr.get('record_count') != len(recs):
        raise ValueError('recount: record count differs')
    cur = st['obs150']['frames']['current']
    fpath = Path(st['obs150']['directory']) / Path(*cur['path'].split('/'))
    fraw = fpath.read_bytes()
    if hashlib.sha256(fraw).hexdigest() != cur['sha256']:
        raise ValueError('recount: frame sha256 differs from the state pin')
    frame = json.loads(_text(fraw))
    if frame.get('schema') != 'lane-plant-frame/v1' or frame.get('complete') is not True \
            or frame.get('time_s') != st['sim_sec']:
        raise ValueError('recount: frame schema / complete / time differs')
    lengths = {}
    for row in frame['vehicles']:
        if len(row) != 15:
            raise ValueError('recount: frame row width')
        lengths[int(row[0])] = float(row[5])
    return st, recs, lengths, hashlib.sha256(raw).hexdigest()


def _spill(vehicles, start, end, lengths):
    length = end - start
    first = None
    for i, (p, veh, spd) in enumerate(vehicles):
        if p > start + TOP:
            break
        if spd < SLOW:
            first = i
            break
    if first is None:
        return False
    if length <= SHORT_LEN:
        return True
    tail = vehicles[first][0]
    i = first + 1
    while i < len(vehicles):
        p, veh, _spd = vehicles[i]
        if p - lengths[veh] - tail > GAP:
            break
        tail = p
        i += 1
    return tail >= end - max(GAP, 0.2 * length)


def recount(records, lengths, ev, live_phases, meters, threshold=1.0):
    segs = {s['id']: s for s in ev['segments']}
    cells = {c['id']: c for c in ev['cells']}
    lane_rows = {}
    for r in records:
        lane_rows.setdefault((str(r['link_no']), int(r['lane_no'])), []).append(
            (float(r['position_m']), int(r['veh_no']), float(r['speed_kph'])))
    n, sp, fl = {}, {}, {}
    for sid, s in segs.items():
        start, end = float(s['start_m']), float(s['end_m'])
        inside = sorted(v for v in lane_rows.get((str(s['link']), int(s['lane'])), ()) if start <= v[0] <= end)
        for v in inside:
            if v[1] not in lengths:
                raise ValueError('recount: no frame length for a counted vehicle')
        n[sid] = len(inside)
        sp[sid] = _spill(inside, start, end, lengths)
        cnt = n[sid] / s['capacity_veh'] >= threshold
        fl[sid] = cnt if (s['kind'] == 'R' and s['short']) else (cnt or sp[sid])

    def ok(cid):
        c = cells[cid]
        if c['short']:
            return True
        return c['judge'] is not None and fl[c['judge']]
    blocked = {}
    for sid, s in segs.items():
        if s['kind'] == 'A':
            rec = s['receivers']
            blocked[sid] = len(rec) > 0 and all(fl[x] for x in rec)
    scores, minus, attributed = {}, [], {}
    trig = {m: [] for m in meters}
    for sid in sorted(blocked):
        s = segs[sid]
        if not s['source']:
            continue
        if blocked[sid]:
            v = -1.0
            minus.append(sid)
        elif fl[sid] and len(s['receivers']) > 0:
            v = max(1.0, n[sid] / s['capacity_veh'])
        else:
            v = 0.0
        for srv in s['servers']:
            scores.setdefault(srv, {})[sid] = v
    by_seg = {}
    for e in ev['attribution']:
        by_seg.setdefault(e['segment'], []).append(e)
    touched = set()
    for sid in sorted(by_seg):
        s = segs[sid]
        if not (s['source'] and fl[sid]):
            continue
        heads = {}
        for e in by_seg[sid]:
            touched.update(e['cells'])
            nxt = {}
            for a, b in e['edges']:
                nxt.setdefault(a, set()).add(b)
            goal = e['head_cell']
            found = False
            if ok(e['start_cell']):
                stack, seen = [e['start_cell']], set()
                while stack:
                    u = stack.pop()
                    if u in seen:
                        continue
                    seen.add(u)
                    if u == goal:
                        found = True
                        break
                    for v in sorted(nxt.get(u, ())):
                        if v not in seen and ok(v):
                            stack.append(v)
            if found:
                heads.setdefault(e['server'], set()).add(e['head_lane_segment'])
        for srv in sorted(heads):
            attributed.setdefault(sid, []).append(srv)
            if srv in trig:
                trig[srv].append(sid)
                continue
            if all(blocked.get(h, False) for h in heads[srv]):
                v = 0.0
            else:
                v = max(1.0, n[sid] / s['capacity_veh'])
            scores.setdefault(srv, {})[sid] = v
    groups = ev.get('overlap_groups') or {}
    weights, dropped = {}, []
    for srv in sorted(scores):
        pos = {sid: v for sid, v in scores[srv].items() if v > 0}
        neg = [v for v in scores[srv].values() if v < 0]
        parts = []
        left = set(pos)
        for g in groups.get(srv, []):
            members = [m for m in g if m in pos]
            if not members:
                continue
            top = max(pos[m] for m in members)
            winner = sorted(m for m in members if pos[m] == top)[0]
            parts.append(top)
            dropped.extend([srv, m] for m in members if m != winner)
            left -= set(members)
        parts.extend(pos[m] for m in left)
        weights[srv] = math.fsum(sorted(parts) + neg)
    signals, zeroed = {}, []
    for owner, live in live_phases.items():
        w = {'%s_%s' % (owner, p): weights.get('%s_%s' % (owner, p), 0.0) for p in live}
        if w and max(w.values()) - min(w.values()) <= 1e-12:
            if any(x != 0.0 for x in w.values()):
                zeroed.append(owner)
            w = dict.fromkeys(w, 0.0)
        signals[owner] = w
    full = sorted(k for k, v in fl.items() if v)
    kinds = {}
    for k in full:
        kinds[segs[k]['kind']] = kinds.get(segs[k]['kind'], 0) + 1
    return {'counts': {k: n[k] for k in sorted(n) if n[k]}, 'spill': sorted(k for k, v in sp.items() if v),
            'full': full, 'full_by_kind': kinds,
            'cells_full': sorted(c for c in touched if not cells[c]['short'] and ok(c)),
            'attributed': {k: attributed[k] for k in sorted(attributed)},
            'scores': {k: [[sid, scores[k][sid]] for sid in sorted(scores[k])] for k in sorted(scores)},
            'weights_before_equal_zero': {k: weights[k] for k in sorted(weights)},
            'signals': signals, 'equal_weights_zeroed': zeroed, 'minus_one_lanes': minus,
            'overlap_dropped': sorted(dropped),
            'meters': {m: {'triggered': bool(trig[m]), 'sources': sorted(trig[m])} for m in meters}}


def recount_state(state_path, ev, live_phases, meters, threshold=1.0):
    st, recs, lengths, sha = read_state(state_path)
    out = recount(recs, lengths, ev, live_phases, meters, threshold)
    out['state_sha256'] = sha
    out['frame_sha256'] = st['obs150']['frames']['current']['sha256']
    out['sim_sec'] = st['sim_sec']
    return out


def _rel(a, b):
    return abs(a - b) <= 1e-12 * max(abs(a), abs(b), 1e-300) or a == b


def compare(runtime, rc):
    """runtime = the runtime observation (RS metadata block or storage_capacity_core output: top keys + 'detail')."""
    det = runtime.get('detail') or {}
    diffs = []
    for key in ('counts', 'spill', 'cells_full', 'attributed'):
        if det.get(key) != rc[key]:
            diffs.append(key)
    full_rt = runtime.get('full_segments', runtime.get('full'))
    if full_rt != rc['full']:
        diffs.append('full')
    for key in ('equal_weights_zeroed', 'minus_one_lanes', 'meters'):
        if runtime.get(key) != rc[key]:
            diffs.append(key)
    if [list(x) for x in runtime.get('overlap_dropped', [])] != rc['overlap_dropped']:
        diffs.append('overlap_dropped')
    sc_rt = det.get('scores') or {}
    if set(sc_rt) != set(rc['scores']):
        diffs.append('scores_servers')
    else:
        for k in sc_rt:
            a, b = sc_rt[k], rc['scores'][k]
            if [x[0] for x in a] != [x[0] for x in b] or not all(_rel(x[1], y[1]) for x, y in zip(a, b)):
                diffs.append('scores:' + k)
    wb = det.get('weights_before_equal_zero') or {}
    if set(wb) != set(rc['weights_before_equal_zero']) or not all(
            _rel(wb[k], rc['weights_before_equal_zero'][k]) for k in wb):
        diffs.append('weights_before_equal_zero')
    sg = runtime.get('signals') or {}
    if list(sg) != list(rc['signals']):
        diffs.append('signals_order')
    for o in rc['signals']:
        a, b = sg.get(o, {}), rc['signals'][o]
        if list(a) != list(b) or not all(_rel(a[k], b[k]) for k in b):
            diffs.append('signals:' + o)
    return diffs


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    state, evp, inp, out = sys.argv[1:5]
    raw = Path(evp).read_bytes()
    params = json.loads(Path(inp).read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest() != params['evidence_sha256']:
        raise SystemExit('evidence sha256 differs')
    ev = json.loads(raw.decode('utf-8'))
    res = recount_state(state, ev, params['live_phases'], params['meters'], params.get('capacity_threshold', 1.0))
    with open(out, 'x', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print('C1G_RECOUNT ok full=%d attributed=%d' % (len(res['full']), len(res['attributed'])))


if __name__ == '__main__':
    main()
