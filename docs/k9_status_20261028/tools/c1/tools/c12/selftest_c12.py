"""selftest_c12.py -- synthetic self-test of the C1-2 guard pieces (K8 amendment C1-2 section 8.1; development and
pin A).  Synthetic data only: a small hand-written network (.inpx XML), plan and tuning; synthetic vehicle records and
frame lengths.  No run data, no VISSIM, no decision.

    python -B selftest_c12.py <tree root with the patched c1_port.py> <out.json>

Cases: builder (segments, receivers, cells, edges, stops, attribution, overlap, null evidence), runtime core vs the
independent recount (counts, boundaries, spill S0 / S, short receiver count rule, -1 and the overlap rule, attribution
through full / short cells only, both end cells, same-link exclusion, meter approach-chain trigger, equal weights
zeroed), C1P key checks (G-K3 list), load_segments checks, E28 floor + RV-2 lowering + G-A7, AST of the two codex
functions (only the names / attributes differ), key-off identity of apply_tuning / operating_bounds."""
import ast
import copy
import hashlib
import json
import math
import sys
import traceback
import types
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TREE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TREE))
import c1g_build as B  # noqa: E402
import c1g_recount as R  # noqa: E402
from evaluation.controllers import c1_port as P  # noqa: E402

CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# ------------------------------------------------------------------------------------------------ synthetic network
def link_xml(no, lanes, length, conn=None):
    pts = '<linkPolyPoint x="0" y="0" zOffset="0"/><linkPolyPoint x="%r" y="0" zOffset="0"/>' % float(length)
    lane_xml = ''.join('<lane/>' for _ in range(lanes))
    ends = ''
    if conn:
        ends = '<fromLinkEndPt lane="%s %d" pos="%r"/><toLinkEndPt lane="%s %d" pos="%r"/>' % conn
    return '<link no="%s">%s<geometry><linkPolyPts>%s</linkPolyPts></geometry><lanes>%s</lanes></link>' % (
        no, ends, pts, lane_xml)


def synthetic():
    links = [link_xml('10', 1, 60.0), link_xml('11', 1, 60.0), link_xml('20', 1, 30.0), link_xml('21', 1, 9.0),
             link_xml('30', 1, 5.0, ('10', 1, 60.0, '20', 1, 0.0)),
             link_xml('31', 1, 4.0, ('11', 1, 60.0, '21', 1, 0.0)),
             link_xml('40', 2, 48.0),
             link_xml('41', 1, 3.0, ('40', 1, 48.0, '10', 1, 0.0)),
             link_xml('42', 1, 3.0, ('40', 2, 48.0, '11', 1, 0.0)),
             link_xml('50', 1, 36.0),
             link_xml('51', 1, 30.0, ('50', 1, 36.0, '60', 1, 10.0)),
             link_xml('60', 1, 100.0)]
    heads = ('<signalHead no="1" lane="10 1" pos="60.0" sg="9 1"/><signalHead no="2" lane="11 1" pos="60.0" sg="9 2"/>'
             '<signalHead no="3" lane="51 1" pos="24.0" sg="9101 1"/>')
    scs = '<signalController no="9" name="SC9"/><signalController no="9101" name="RW_SC_RM_C51"/>'
    xml = ('<network><links>%s</links><signalHeads>%s</signalHeads><signalControllers>%s</signalControllers>'
           '<vehicleInputs/></network>') % (''.join(links), heads, scs)
    plan = {'controllers': {'9': {'phase_signal_groups': {'p1': ['1'], 'p2': ['2']},
                                  'midblock_native_signal_groups': []}}}
    tuning = {'config_overrides': {'network': {'signals': ['SC9']}}}
    doc = B.build(xml.encode(), json.dumps(plan).encode(), json.dumps(tuning).encode(), check_sha=False,
                  meters_map={'RM_C51': '51'}, fw_e=('60',), fw_w=())
    return doc


LIVE = {'SC9': ('p1', 'p2')}
METERS = ('RM_C51',)


def veh(no, link, lane, pos, speed=0.0):
    return {'veh_no': no, 'link_no': int(link), 'lane_no': lane, 'position_m': float(pos), 'speed_kph': float(speed)}


def queue(link, lane, start, end, n, first_no, speed=0.0, length=4.5):
    """n stopped vehicles evenly from end down to start (front positions)."""
    rows, lens = [], {}
    step = (end - start) / max(n, 1)
    for i in range(n):
        no = first_no + i
        rows.append(veh(no, link, lane, end - i * step, speed))
        lens[no] = length
    return rows, lens


def both(doc, records, lengths):
    rt = P.storage_capacity_core(records, lengths, doc, LIVE, METERS, capacity_threshold=1.0)
    rc = R.recount(records, lengths, doc, LIVE, METERS, 1.0)
    return rt, rc, R.compare(rt, rc)


# ------------------------------------------------------------------------------------------------ cases
@case('builder_segments_receivers')
def _(doc):
    ids = sorted(s['id'] for s in doc['segments'])
    want = ['A:10:1:1', 'A:11:1:2', 'F:40:1', 'F:40:2', 'F:41:1', 'F:42:1', 'F:50:1', 'M:RM_C51:1', 'MA:RM_C51:1',
            'R:20:1:0.000', 'R:21:1:0.000']
    a10 = [s for s in doc['segments'] if s['id'] == 'A:10:1:1'][0]
    return ids == want and a10['receivers'] == ['R:20:1:0.000'] and a10['servers'] == ['SC9_p1']


@case('builder_cells_cover_lanes')
def _(doc):
    by = {}
    for c in doc['cells']:
        by.setdefault((c['link'], c['lane']), []).append(c)
    ok = True
    for rows in by.values():
        rows.sort(key=lambda c: c['start_m'])
        ok &= rows[0]['start_m'] == 0.0 and all(abs(a['end_m'] - b['start_m']) <= 1e-9 for a, b in zip(rows, rows[1:]))
    return ok and len(by) == 13


@case('builder_attribution_entries')
def _(doc):
    pairs = sorted({(a['segment'], a['server']) for a in doc['attribution']})
    return pairs == [('F:40:1', 'SC9_p1'), ('F:40:1', 'SC9_p2'), ('F:40:2', 'SC9_p1'), ('F:40:2', 'SC9_p2'),
                     ('F:50:1', 'RM_C51'), ('MA:RM_C51:1', 'RM_C51')]


@case('null_evidence')
def _(doc):
    n = B.null_of(doc)
    recs, lens = queue('10', 1, 0.0, 60.0, 12, 1)
    rt = P.storage_capacity_core(recs, lens, n, LIVE, METERS)
    return n['null_test'] and not n['attribution'] and all(v == 0. for v in rt['signals']['SC9'].values())


@case('count_boundary_no_tolerance')
def _(doc):
    recs = [veh(1, '20', 1, 30.0), veh(2, '20', 1, 30.0 + 1e-9), veh(3, '20', 1, 0.0), veh(4, '20', 1, -1e-9)]
    lens = {i: 4.5 for i in range(1, 5)}
    rt, rc, d = both(doc, recs, lens)
    return rt['detail']['counts'].get('R:20:1:0.000') == 2 and not d


@case('count_full_ge_one')
def _(doc):
    recs, lens = queue('10', 1, 0.0, 59.0, 10, 1, speed=30.0)       # 10 vehicles / (60 / 6) = 1.0, moving
    rt, rc, d = both(doc, recs, lens)
    recs2, lens2 = queue('10', 1, 0.0, 59.0, 9, 1, speed=30.0)
    rt2, rc2, d2 = both(doc, recs2, lens2)
    return 'A:10:1:1' in rt['full'] and 'A:10:1:1' not in rt2['full'] and not d and not d2


@case('spill_chain_reaches_bottom')
def _(doc):
    recs = [veh(1, '10', 1, 5.0, 0.0), veh(2, '10', 1, 22.0, 0.0), veh(3, '10', 1, 39.0, 0.0), veh(4, '10', 1, 52.0, 0.0)]
    lens = {i: 4.5 for i in range(1, 5)}
    rt, rc, d = both(doc, recs, lens)
    recs2 = [veh(1, '10', 1, 5.0, 0.0), veh(2, '10', 1, 22.0, 0.0), veh(3, '10', 1, 49.6, 0.0)]   # gap 23.1 > 20
    rt2, rc2, d2 = both(doc, recs2, {1: 4.5, 2: 4.5, 3: 4.5})
    return 'A:10:1:1' in rt['detail']['spill'] and 'A:10:1:1' not in rt2['detail']['spill'] and not d and not d2


@case('spill_needs_slow_vehicle_in_top_12m')
def _(doc):
    recs = [veh(1, '10', 1, 13.0, 0.0), veh(2, '10', 1, 30.0, 0.0), veh(3, '10', 1, 47.0, 0.0), veh(4, '10', 1, 58.0, 0.0)]
    rt, rc, d = both(doc, recs, {i: 4.5 for i in range(1, 5)})
    return 'A:10:1:1' not in rt['detail']['spill'] and not d


@case('short_receiver_count_only')
def _(doc):
    # R:21 (9 m, 1.5 veh) is short: one stopped vehicle at its top is S0 but not full by count
    recs = [veh(1, '21', 1, 1.0, 0.0)]
    rt, rc, d = both(doc, recs, {1: 4.5})
    recs2 = [veh(1, '21', 1, 1.0, 0.0), veh(2, '21', 1, 8.0, 0.0)]
    rt2, rc2, d2 = both(doc, recs2, {1: 4.5, 2: 4.5})
    return 'R:21:1:0.000' not in rt['full'] and 'R:21:1:0.000' in rt2['full'] and not d and not d2


@case('minus_one_when_receivers_full')
def _(doc):
    recs, lens = queue('20', 1, 0.0, 29.0, 5, 1)                      # receiver R:20 full (5 / 5)
    rt, rc, d = both(doc, recs, lens)
    return rt['minus_one_lanes'] == ['A:10:1:1'] and rt['detail']['weights_before_equal_zero'].get('SC9_p1') == -1. \
        and not d


@case('head_score_and_equal_zero')
def _(doc):
    r1, l1 = queue('10', 1, 0.0, 59.0, 12, 1)                         # A:10 full 1.2, receivers present
    rt, rc, d = both(doc, r1, l1)
    w = rt['signals']['SC9']
    return abs(w['SC9_p1'] - 1.2) < 1e-12 and w['SC9_p2'] == 0. and not d


@case('equal_live_weights_zeroed')
def _(doc):
    r1, l1 = queue('10', 1, 0.0, 59.0, 10, 1)
    r2, l2 = queue('11', 1, 0.0, 59.0, 10, 100)
    l1.update(l2)
    rt, rc, d = both(doc, r1 + r2, l1)
    # A:11 has a receiver R:21 -> score 1 each; equal -> zeroed
    return rt['equal_weights_zeroed'] == ['SC9'] and set(rt['signals']['SC9'].values()) == {0.} and not d


@case('feeder_attribution_needs_full_cells_both_ends')
def _(doc):
    r1, l1 = queue('40', 1, 0.0, 47.0, 8, 1)                          # F:40:1 full (8 / 8)
    rt, rc, d = both(doc, r1, l1)                                     # head lane A:10 not full -> no path
    r2, l2 = queue('10', 1, 0.0, 59.0, 10, 50)
    l2.update(l1)
    rt2, rc2, d2 = both(doc, r1 + r2, l2)
    return 'F:40:1' not in rt['detail']['attributed'] and rt2['detail']['attributed'].get('F:40:1') == ['SC9_p1'] \
        and abs(rt2['signals']['SC9']['SC9_p1'] - 2.0) < 1e-12 and not d and not d2


@case('meter_trigger_needs_approach_chain')
def _(doc):
    m, lm = queue('51', 1, 0.0, 23.0, 4, 1)                           # M full (4 / 4)
    rt, rc, d = both(doc, m, lm)
    a, la = queue('50', 1, 0.0, 35.0, 6, 50)                          # MA / F:50 full (6 / 6)
    la.update(lm)
    rt2, rc2, d2 = both(doc, m + a, la)
    return (not rt['meters']['RM_C51']['triggered'] and rt2['meters']['RM_C51']['triggered']
            and rt2['meters']['RM_C51']['sources'] == ['F:50:1', 'MA:RM_C51:1'] and not d and not d2)


@case('frame_length_missing_valueerror')
def _(doc):
    try:
        P.storage_capacity_core([veh(1, '20', 1, 3.0)], {}, doc, LIVE, METERS)
    except ValueError:
        return True
    return False


GOOD = {'segments_name': 'c1g_storage_segments_v3c3.json', 'segments_sha256': 'a' * 64, 'unit': 'lane',
        'full_rule': 'count_or_spill', 'capacity_threshold': 1.0, 'min_source_capacity_veh': 2.0,
        'feeder_attribution': 'cell_chain_max', 'landing_sources': True, 'short_receiver_rule': 'count',
        'reserve_green_sec': 2.0, 'meter_rule': 'approach_chain_or_m4'}


def rejects(value):
    try:
        P.check_value('storage_capacity_guard', value)
    except ValueError:
        return True
    return False


@case('check_value_accepts_declared')
def _(doc):
    P.check_value('storage_capacity_guard', dict(GOOD))
    return list(GOOD) == list(P.GUARD_KEYS)


@case('check_value_rejects_g_k3_list')
def _(doc):
    bad = []
    for k, v in (('unit', 'link'), ('full_rule', 'count'), ('feeder_attribution', 'first_server'),
                 ('meter_rule', 'm4_or'), ('short_receiver_rule', 'spill'), ('landing_sources', False),
                 ('reserve_green_sec', 2.5), ('reserve_green_sec', 0), ('capacity_threshold', 1.2),
                 ('capacity_threshold', True), ('min_source_capacity_veh', -1), ('segments_sha256', 'A' * 64),
                 ('segments_name', 'x/y.json'), ('capacity_threshold', float('nan'))):
        v2 = dict(GOOD, **{k: v})
        bad.append(rejects(v2))
    extra = dict(GOOD, extra=1)
    missing = dict(GOOD)
    del missing['unit']
    return all(bad) and rejects(extra) and rejects(missing)


@case('validate_requires_storage_release_guard')
def _(doc):
    try:
        P.validate({'storage_capacity_guard': dict(GOOD)})
    except ValueError as e:
        return 'requires storage_release_guard' in str(e)
    return False


@case('load_segments_checks')
def _(doc):
    name = 'c1g_storage_segments_v3c3.json'
    raw = B.data(dict(doc, network_sha256=P.NETWORK_SHA256))
    sha = hashlib.sha256(raw).hexdigest()
    import os
    import time
    tmp = OUT.parent / ('selftest_root_%d_%d' % (os.getpid(), time.time_ns()))
    folder = tmp / P.C1_DIRS['c1']
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / name
    old_root = P.ROOT
    P.ROOT = tmp
    out = []
    try:
        path.write_bytes(raw)
        sec = dict(GOOD, segments_sha256=sha)
        cfg = types.SimpleNamespace(network=types.SimpleNamespace(urban_avg_vehicle_length_m=6.0))
        P._GUARD_CACHE.clear()
        out.append(P.load_segments(sec, cfg)['doc']['schema'] == P.GUARD_SCHEMA)
        for mutate in (lambda c, s: setattr(c.network, 'urban_avg_vehicle_length_m', 6.5),
                       lambda c, s: s.update(min_source_capacity_veh=3.0),
                       lambda c, s: s.update(segments_sha256='b' * 64)):
            c2 = types.SimpleNamespace(network=types.SimpleNamespace(urban_avg_vehicle_length_m=6.0))
            s2 = dict(sec)
            mutate(c2, s2)
            P._GUARD_CACHE.clear()
            try:
                P.load_segments(s2, c2)
                out.append(False)
            except ValueError:
                out.append(True)
        bad_spill = dict(doc, network_sha256=P.NETWORK_SHA256, spill_rule=dict(doc['spill_rule'], top_window_m=10.0))
        raw2 = B.data(bad_spill)
        path.write_bytes(raw2)
        P._GUARD_CACHE.clear()
        try:
            P.load_segments(dict(sec, segments_sha256=hashlib.sha256(raw2).hexdigest()), cfg)
            out.append(False)
        except ValueError:
            out.append(True)
    finally:
        P.ROOT = old_root
        path.unlink()
        P._GUARD_CACHE.clear()
    return all(out)


CX_USG = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/evaluation/controllers/urban_storage_guard.py')


@case('codex_functions_ast_equal_but_names')
def _(doc):
    text = CX_USG.read_bytes().decode('utf-8').replace('\r\n', '\n')
    cx = {n.name: n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
    ours = {n.name: n for n in ast.parse((TREE / 'evaluation/controllers/c1_port.py').read_text(encoding='utf-8')).body
            if isinstance(n, ast.FunctionDef)}

    def norm(node, new_name):
        d = ast.dump(node)
        return d.replace("name='%s'" % new_name, "name='X'")
    a = norm(cx['constrain'], 'constrain').replace("'urban_storage_guard'", "'A'").replace(
        "attr='urban_storage_receipt'", "attr='B'")
    b = norm(ours['constrain_storage_capacity'], 'constrain_storage_capacity').replace(
        "'c1_storage_capacity_guard'", "'A'").replace("attr='c1_storage_capacity_receipt'", "attr='B'")
    c = norm(cx['operating_seed'], 'operating_seed')
    d = norm(ours['storage_capacity_seed'], 'storage_capacity_seed')
    return a == b and c == d


class Spec(dict):
    pass


def bounds_cfg(prev, table_greens, triggered_m4, guard_trig):
    ramps = {'RM_X': {'service_by_green_veh_h': {str(g): float(g) for g in table_greens}}}
    net = types.SimpleNamespace(physical_ramp_branches={'ramps': ramps, 'allow_zero_green': False,
                                                        'minimum_green_sec': 2.0, 'cycle_sec': 10.0,
                                                        'max_green_change_sec': 2.0},
                                ramp_operating_green_floors={'RM_X': 2.0})
    if guard_trig is not None:
        net.c1_storage_capacity_guard = {'meters': {'RM_X': {'triggered': guard_trig, 'sources': ['MA:RM_X:1']}}}
    return types.SimpleNamespace(network=net)


@case('e28_floor_rv2_ga7')
def _(doc):
    import evaluation.controllers.physical_ramp_branches as PRB
    original = PRB.configure_operating_bounds
    res = []
    try:
        for prev, table, trig, guard, want in ((7., [0, 2, 3, 4, 5, 6, 7, 8, 10], False, True, 8.),
                                              (7., [0, 2, 3, 4, 5, 6, 7, 8, 10], False, False, 2.),
                                              (7., [0, 2, 3, 4, 5, 6, 7, 8, 10], False, None, 2.),
                                              (10., [0, 2, 3, 4, 5, 6, 7, 8, 10], False, True, 10.),
                                              (4., [0, 2, 3, 4, 5, 6, 7, 8, 9, 10], False, True, 6.),
                                              (7., [0, 2, 3, 4, 5, 6, 7, 8, 10], True, True, 8.)):
            cfg = bounds_cfg(prev, table, trig, guard)

            def fake(state, cfg, reference, _prev=prev, _trig=trig):
                floor = max(2.0, min(10.0, _prev + 2.0)) if _trig else 2.0
                cfg.network.ramp_operating_green_floors = {'RM_X': floor}
                return {'ramps': {'RM_X': {'previous_green_sec': _prev, 'minimum_green_sec': floor,
                                           'triggered': _trig, 'lanes': []}}}
            PRB.configure_operating_bounds = fake
            r = P.operating_bounds(None, cfg, None)
            ev = r['ramps']['RM_X']
            ok = cfg.network.ramp_operating_green_floors['RM_X'] == want
            if guard is None:
                ok &= 'guard_triggered' not in ev
            else:
                ok &= ev['guard_triggered'] is guard and ev['guard_sources'] == (['MA:RM_X:1'] if guard else [])
            res.append(ok)
    finally:
        PRB.configure_operating_bounds = original
    return all(res)


@case('apply_tuning_key_off_identity')
def _(doc):
    t = {'a': 1}
    out, meta = P.apply_tuning(t)
    return out is t and meta == {}


def main():
    doc = synthetic()
    rows, ok = [], True
    for name, fn in CASES:
        try:
            r = fn(copy.deepcopy(doc))
            good = r is True or (isinstance(r, str) and r.startswith('skip'))
            rows.append({'name': name, 'ok': good, 'result': r if not isinstance(r, bool) else None})
        except Exception:  # noqa: BLE001
            good = False
            rows.append({'name': name, 'ok': False, 'error': traceback.format_exc()[-1500:]})
        ok &= good
    res = {'schema': 'c1-2-selftest/v1', 'tree': TREE.name, 'c1_port_sha256': hashlib.sha256(
        (TREE / 'evaluation/controllers/c1_port.py').read_bytes()).hexdigest(), 'cases': rows, 'n': len(rows),
        'n_ok': sum(1 for r in rows if r['ok']), 'ok': ok}
    with open(OUT, 'x', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print('SELFTEST_C12 %d/%d ok=%s' % (res['n_ok'], res['n'], ok))
    for r in rows:
        if not r['ok']:
            print('FAIL', r['name'], (r.get('error') or '')[-600:])


if __name__ == '__main__':
    main()
