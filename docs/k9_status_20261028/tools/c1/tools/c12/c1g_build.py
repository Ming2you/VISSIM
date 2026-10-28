"""c1g_build.py -- evidence builder of the C1-2 general storage-capacity guard (K8 amendment C1-2
dfe9809b7212bdc7..., sections 5.1-5.10, 8.1; rule file c1g_guard_rule.json 93827138...).  Scratch tool (never committed;
the commit builder build_c1_evidence.py guard copies this logic at C1-G).

    python -B c1g_build.py <inpx> <plan json> <tuning json> <out evidence> <out null evidence>

Inputs: ONLY the v3c3 network (.inpx, sha256 3de889f0...), the native clock plan (8e28f983...) and the deployed tuning
OUC (c8e3ee2c...); each sha256 is checked (SystemExit when different).  The `part` field uses builder constants
(amendment C1-2 section 13.2: B0 Omega701 inside 701 = codex omega_membership_exact 701, the chains, on-/off-ramps).
No run data.  The comparison files inventory.json / segments.json / gr_check.json are NOT read here (P0-17 (b)-(g)
compare them; amendment C1-2 section 5.10 [review r1] builder inputs).  Outputs are written exclusively (never
overwritten) in the PN data() serialisation (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + newline).

Port of the inventory walk (guard/general/tools inv_net.py 3D polyline length, inv_build.py approach lanes / feeder walk
/ meters / landings, gd_scan.py build_segments ids) for the A / F / M / MA / L table (D5 left out); new here: codex
receivers R (CX USG:68-76 exact span), cells, edges, stops, attribution sub-graphs, overlap pairs / groups, meters.

Server name rule (P0-17 (d), fixed with pin A): inventory server labels 'SC<n>:<p>[/<p>..](SG<g>)' -> one key
'SC<n>_<p>' per phase; 'meter:<name>' -> '<name>'; other labels (native / midblock / sink / freeway_merge) -> none.
Cut points (amendment C1-2 section 5.4): link start and end, every head position on the lane, every connector landing
on the lane, every connector departure from the lane; points closer than 1e-6 m merge (the first kept).
"""
import hashlib
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

sys.dont_write_bytecode = True

NETWORK_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
PLAN_SHA256 = '8e28f983e12d67d5244b4865d43482ef324729e12e4af87962ee60513704a012'
TUNING_SHA256 = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
GUARD_RULE_SHA256 = '938271380735313d5d2c1efde51423430cfe080c4c8c08c1e39c185e6d5806da'
SCHEMA = 'c1g-storage-segments/v1'
SPACING_M = 6.0
MIN_SOURCE_CAPACITY_VEH = 2.0
SPILL_RULE = {'top_window_m': 12.0, 'stop_speed_kph': 5.0, 'max_clear_gap_m': 20.0,
              'bottom_reach': 'max(20.0, 0.2 * length_m)', 'short_length_m': 12.0}
EPS = 1e-6
OVERLAP_M = 0.05
SAME_STOPLINE_M = 3.0          # inv_build.py: same-SC heads this close on one lane = one stop line
FW_E = ('74', '10699', '2', '10613', '119', '10702', '24')
FW_W = ('26', '10771', '120')
METERS = {'RM_C10480': '10480', 'RM_C10482': '10482', 'RM_C10646': '10646', 'RM_C10644': '10644',
          'RM_C10639': '10639', 'RM_C10681': '10681', 'RM_C10490': '10490', 'RM_C10484': '10484'}
ONRAMPS_E = ('10639', '10681', '10490', '10484')
ONRAMPS_W = ('10480', '10482', '10646', '10644')
OFFRAMPS_ALL = ('10479', '10481', '10483', '10491', '10638', '10643', '10645', '10682')
# B0 Omega701 membership 9bb740b3... /inside_links (= codex omega_membership_exact.json efdfaeb1... /inside_links),
# sorted by int; sha256 of ' '.join = OMEGA701_LIST_SHA256 (checked at import)
OMEGA701_INSIDE = '''
2 17 18 19 21 24 26 29 30 31 32 37 39 40 43 46 47 52 56 57 58 61 62 63 66 68 69 70 71 72 74 75 78 91 97 100 118
119 120 121 122 124 126 127 128 129 136 138 141 164 166 168 170 172 173 174 176 178 182 183 187 189 194 196 197
199 200 201 209 213 217 222 223 224 225 236 240 242 245 247 249 251 254 255 256 257 259 265 268 270 308 309 314
316 317 321 322 324 325 326 327 328 329 332 336 337 340 341 343 353 354 355 358 359 360 364 367 374 378 379 382
383 385 387 403 404 407 408 409 410 411 412 413 416 417 420 421 422 423 424 425 426 427 459 461 462 467 469
10023 10024 10025 10029 10032 10049 10103 10104 10105 10106 10107 10108 10109 10110 10112 10114 10116 10117
10118 10119 10121 10124 10127 10129 10130 10133 10134 10135 10139 10144 10149 10153 10172 10175 10179 10180
10181 10182 10183 10184 10185 10186 10187 10188 10189 10190 10191 10192 10193 10194 10195 10196 10199 10200
10201 10202 10204 10206 10208 10209 10210 10211 10212 10213 10214 10215 10216 10218 10220 10221 10223 10224
10225 10229 10231 10232 10233 10234 10235 10236 10238 10239 10240 10242 10243 10244 10245 10247 10248 10249
10251 10252 10255 10256 10257 10258 10259 10260 10261 10263 10265 10268 10269 10270 10271 10272 10273 10274
10275 10276 10277 10278 10280 10281 10282 10284 10286 10287 10288 10289 10290 10291 10292 10293 10294 10296
10299 10300 10301 10302 10303 10304 10305 10308 10309 10310 10311 10314 10315 10316 10317 10318 10319 10322
10323 10324 10325 10328 10329 10330 10331 10332 10333 10334 10335 10336 10337 10339 10340 10342 10343 10345
10346 10347 10348 10349 10350 10354 10355 10356 10357 10358 10359 10360 10364 10365 10366 10367 10368 10369
10370 10372 10373 10374 10375 10376 10377 10378 10379 10380 10381 10382 10385 10388 10391 10392 10393 10394
10395 10396 10397 10398 10401 10402 10403 10404 10407 10408 10409 10411 10413 10414 10415 10416 10417 10419
10420 10421 10422 10423 10424 10426 10429 10430 10434 10435 10436 10459 10463 10464 10465 10466 10480 10481
10482 10483 10484 10485 10489 10490 10491 10492 10493 10494 10495 10496 10497 10498 10499 10500 10501 10502
10503 10504 10505 10506 10507 10508 10509 10512 10513 10514 10515 10516 10517 10518 10519 10520 10521 10522
10523 10524 10525 10526 10527 10528 10529 10530 10531 10532 10534 10535 10536 10537 10539 10540 10541 10542
10544 10545 10546 10547 10550 10553 10554 10555 10556 10557 10558 10559 10560 10561 10562 10563 10564 10565
10566 10567 10568 10569 10570 10571 10572 10573 10574 10575 10578 10579 10582 10583 10584 10585 10586 10588
10590 10591 10592 10593 10595 10596 10598 10599 10600 10601 10602 10603 10604 10605 10608 10609 10610 10611
10612 10613 10614 10615 10617 10618 10619 10621 10622 10623 10624 10625 10627 10628 10629 10631 10632 10633
10634 10635 10636 10637 10638 10639 10640 10641 10643 10644 10646 10647 10648 10649 10650 10651 10652 10653
10654 10655 10656 10657 10658 10659 10660 10661 10662 10663 10664 10665 10666 10667 10668 10669 10670 10671
10672 10673 10674 10675 10676 10677 10678 10679 10680 10681 10682 10683 10684 10685 10686 10687 10688 10690
10691 10693 10696 10697 10698 10699 10700 10701 10702 10703 10771 10772 10774 10776 10777 10778 121008402
1210006903 1210008202 1210008203 1210008303 1210008401 1210008402 1210008501 1210008603 1210008703 1210009402
1210009403 1210009502 1210009503 1210009600 1210009700 1210012001 1210012101 1210012103 1210012600 1210012700
1210014303 1210015600 1210018202 1210018302 1210018401 1210018504 1210019201 1210021204 1220000102 1220000201
1220000300 1220000402 1220000502 1220000600 1220000704 1220006403 1220006503 1220006803 1220006903 1220007001
1220007004 1220007101 1220007104 1220007200 1220007300 1220007401 1220007402 1220007501 1220007502 1220008201
1220008202 1220008203 1220008301 1220008302 1220008303 1220008401 1220008402 1220008501 1220008502 1220008601
1220008602 1220008603 1220008701 1220008702 1220008703 1220009402 1220009403 1220009502 1220009503 1220009600
1220009700 1220011001 1220011003 1220011101 1220011103 1220011200 1220011403 1220011503 1220012001 1220012002
1220012003 1220012101 1220012102 1220012103 1220012402 1220012502 1220012600 1220012700 1220013100 1220013600
1220014000 1220014100 1220014201 1220014203 1220014303 1220015000 1220015100 1220015600 1220016001 1220018201
1220018202 1220018301 1220018302 1220018401 1220018402 1220018403 1220018404 1220018501 1220018502 1220018503
1220018504 1220019201 1220021201 1220021203 1220021204 1220021801 1220021802 1220021803 1220042300 1220043200
1220043300 1220044500
'''
OMEGA701_LIST_SHA256 = '336c2ffeedbb766c964ad339d1d2eeea95bc2500eda9c4c740f6fff33106fc67'


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def data(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def omega_inside():
    links = OMEGA701_INSIDE.split()
    if sha256_bytes(' '.join(links).encode()) != OMEGA701_LIST_SHA256 or len(links) != 701:
        raise SystemExit('builder constant OMEGA701_INSIDE differs from its pin')
    return frozenset(links)


def part_of(link, inside):
    if link not in inside:
        return 'outside'
    if link in FW_E:
        return 'FW_E'
    if link in FW_W:
        return 'FW_W'
    if link in ONRAMPS_E:
        return 'onramps_E'
    if link in ONRAMPS_W:
        return 'onramps_W'
    if link in OFFRAMPS_ALL:
        return 'offramps'
    return 'urban_roads'


def server_keys_of_inventory_label(label):
    """P0-17 (d) rule: inventory label -> evidence server names (list, possibly empty)."""
    if label.startswith('meter:'):
        return [label[len('meter:'):]]
    if label.startswith('SC') and ':' in label and '(SG' in label:
        sc, rest = label.split(':', 1)
        phases = rest.split('(SG', 1)[0]
        return ['%s_%s' % (sc, p) for p in phases.split('/')]
    return []


# ================================================================================================ network
def plen(node):
    pts = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
           for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def parse_inpx(raw):
    root = ET.fromstring(raw)
    links = {}
    for ln in root.find('links').findall('link'):
        no = ln.get('no')
        fr, to = ln.find('fromLinkEndPt'), ln.find('toLinkEndPt')
        row = {'no': no, 'lanes': len(ln.findall('./lanes/lane')), 'length_m': plen(ln), 'is_connector': fr is not None}
        if fr is not None:
            fl, fi = fr.get('lane').split()
            tl, ti = to.get('lane').split()
            row.update(from_link=fl, from_lane=int(fi), from_pos=float(fr.get('pos')),
                       to_link=tl, to_lane=int(ti), to_pos=float(to.get('pos')))
        links[no] = row
    heads = []
    for h in root.find('signalHeads').findall('signalHead'):
        lk, li = h.get('lane').split()
        sc, sg = h.get('sg').split()
        heads.append({'no': h.get('no'), 'link': lk, 'lane': int(li), 'pos': float(h.get('pos')), 'sc': sc, 'sg': sg})
    scs = [{'no': c.get('no'), 'name': c.get('name')} for c in root.find('signalControllers').findall('signalController')]
    inputs = [{'no': vi.get('no'), 'link': vi.get('link')} for vi in root.find('vehicleInputs').findall('vehicleInput')]
    return {'links': links, 'signal_heads': heads, 'signal_controllers': scs, 'vehicle_inputs': inputs}


# ================================================================================================ inventory port
def inventory(nf, plan, tuning, meters_map=None, fw_e=FW_E, fw_w=FW_W):
    """inv_build.py main() (approach lanes, feeder walk, meters) with the parts the segment table needs.
    meters_map / fw_e / fw_w default to the v3c3 constants (the synthetic self-test passes its own)."""
    meters_map = METERS if meters_map is None else meters_map
    L = nf['links']
    net = tuning['config_overrides']['network']
    controlled = [s[2:] for s in net['signals']]
    C = plan['controllers']
    heads = nf['signal_heads']
    hb = defaultdict(list)
    for h in heads:
        hb[h['link'], h['lane']].append(h)
    for k in hb:
        hb[k].sort(key=lambda h: h['pos'])
    meter_sc = {}
    for sc in nf['signal_controllers']:
        nm = sc.get('name') or ''
        if nm.startswith('RW_SC_RM_C'):
            meter_sc[sc['no']] = nm[len('RW_SC_'):]
    out_c, in_c = defaultdict(list), defaultdict(list)
    for c, l in L.items():
        if not l['is_connector']:
            continue
        for i in range(l['lanes']):
            out_c[l['from_link'], l['from_lane'] + i].append(dict(
                connector=c, conn_lane=i + 1, source_pos=l['from_pos'], link=l['to_link'],
                lane=l['to_lane'] + i, position=l['to_pos']))
            in_c[l['to_link'], l['to_lane'] + i].append(dict(
                connector=c, conn_lane=i + 1, from_link=l['from_link'], from_lane=l['from_lane'] + i,
                from_pos=l['from_pos'], to_pos=l['to_pos']))
    inputs_by_link = defaultdict(list)
    for vi in nf['vehicle_inputs']:
        inputs_by_link[vi['link']].append(vi['no'])
    fwe, fww = set(fw_e), set(fw_w)

    def sg2phase(sc):
        c = C.get(sc)
        m = defaultdict(list)
        if c:
            for p, g in c['phase_signal_groups'].items():
                for x in g:
                    m[str(x)].append(p)
        return m

    def head_role(h):
        sc, sg = h['sc'], h['sg']
        if sc in meter_sc:
            return 'meter', meter_sc[sc]
        if sc in controlled:
            c = C[sc]
            if sg in map(str, c.get('midblock_native_signal_groups', [])):
                return 'controlled_sc_midblock_native', None
            ph = sg2phase(sc).get(sg)
            if ph:
                return 'controlled_phase', ph
            return 'controlled_sc_unmapped_sg', None
        return 'native_signal', None

    def prev_head(link, lane, pos):
        best = None
        for h in hb.get((link, lane), []):
            if h['pos'] < pos - EPS:
                best = h
        return best

    approach = []
    for h in sorted(heads, key=lambda h: (int(h['sc']), h['link'], h['lane'])):
        if h['sc'] not in controlled:
            continue
        role, ph = head_role(h)
        link, lane = h['link'], h['lane']
        shared = [x for x in hb[link, lane] if x is not h and x['sc'] == h['sc'] and abs(x['pos'] - h['pos']) <= SAME_STOPLINE_M]
        up = None
        for x in hb[link, lane]:
            if x['pos'] < h['pos'] - EPS and x not in shared:
                up = x
        start = up['pos'] if up else 0.0
        approach.append(dict(sc='SC' + h['sc'], sg=h['sg'], role=role, phases=ph, head_no=h['no'], link=link, lane=lane,
                             head_pos_m=h['pos'], segment_start_m=start))
    feeders = {}

    def frow(link):
        f = feeders.get(link)
        if f is None:
            f = dict(link=link, link_lanes=L[link]['lanes'], from_m=None, to_m=0.0, servers=set(), landings=[],
                     freeway_spill=None)
            feeders[link] = f
        return f

    def add_once(lst, item):
        if item not in lst:
            lst.append(item)

    visited = set()

    def walk_conn(c, land_link, land_lane_first, land_pos, land_end, server, depth):
        cl = L[c]
        f = frow(c)
        c_heads = [h for i in range(1, cl['lanes'] + 1) for h in hb.get((c, i), [])]
        start = max([h['pos'] for h in c_heads], default=0.0)
        f['from_m'] = start if f['from_m'] is None else min(f['from_m'], start)
        f['to_m'] = cl['length_m']
        f['servers'].add(server)
        add_once(f['landings'], dict(on_link=land_link, on_lanes=list(range(land_lane_first, land_lane_first + cl['lanes'])),
                                     landing_pos_m=land_pos, landing_to_server_end_m=land_end - land_pos))
        if c_heads:
            return
        fl = cl['from_link']
        if fl in fwe or fl in fww:
            f['freeway_spill'] = dict(road=('FW_E' if fl in fwe else 'FW_W'), link=fl, lane=cl['from_lane'],
                                      diverge_pos_m=cl['from_pos'])
            return
        walk_link(fl, cl['from_pos'], c, server, depth + 1)

    def walk_link(link, end_pos, exit_conn, server, depth):
        if depth > 25:
            raise SystemExit('walk too deep at ' + link)
        lanes = range(1, L[link]['lanes'] + 1)
        hs = [h for ln in lanes for h in hb.get((link, ln), []) if h['pos'] <= end_pos + 2 * EPS]
        if hs:
            return
        f = frow(link)
        f['from_m'] = 0.0
        f['to_m'] = max(f['to_m'], end_pos)
        f['servers'].add(server)
        seen_c = set()
        for ln in lanes:
            for ic in in_c.get((link, ln), []):
                if ic['to_pos'] > end_pos + EPS or ic['connector'] in seen_c:
                    continue
                seen_c.add(ic['connector'])
                key = (ic['connector'], server)
                if key in visited:
                    continue
                visited.add(key)
                walk_conn(ic['connector'], link, L[ic['connector']]['to_lane'], ic['to_pos'], end_pos, server, depth + 1)

    def srv_name(sc, sg):
        h = {'sc': sc, 'sg': sg}
        role, ph = head_role(h)
        if role == 'meter':
            return 'meter:' + meter_sc[sc]
        if role == 'controlled_phase':
            return 'SC%s:%s(SG%s)' % (sc, '/'.join(ph), sg)
        return '%s:SC%s:SG%s' % (role, sc, sg)

    for r in approach:
        if r['role'] != 'controlled_phase':
            continue
        server = srv_name(r['sc'][2:], r['sg'])
        link, lo = r['link'], r['segment_start_m']
        for ln in range(1, L[link]['lanes'] + 1):
            for ic in in_c.get((link, ln), []):
                if ic['to_pos'] > r['head_pos_m'] + EPS or ic['to_pos'] < lo - EPS:
                    continue
                key = (ic['connector'], server)
                if key in visited:
                    continue
                visited.add(key)
                walk_conn(ic['connector'], link, L[ic['connector']]['to_lane'], ic['to_pos'], r['head_pos_m'], server, 1)
    meters = {}
    for name, c in meters_map.items():
        cl = L[c]
        mh = sorted([h for i in range(1, cl['lanes'] + 1) for h in hb.get((c, i), [])], key=lambda h: h['lane'])
        f_link, f_lane, f_pos = cl['from_link'], cl['from_lane'], cl['from_pos']
        ups = prev_head(f_link, f_lane, f_pos + 2 * EPS)
        a = ups['pos'] if ups else 0.0
        walk_link(f_link, f_pos, c, 'meter:' + name, 1)
        meters[name] = dict(connector=c, heads=[dict(lane=h['lane'], head_pos_m=h['pos'], head_no=h['no']) for h in mh],
                            approach=dict(link=f_link, lanes=[f_lane + i for i in range(cl['lanes'])], from_m=a, to_m=f_pos))
    frows = [f for _, f in sorted(feeders.items(), key=lambda kv: int(kv[0])) if f['from_m'] is not None]
    return dict(approach=approach, feeders=frows, meters=meters, hb=hb, out_c=out_c, in_c=in_c, head_role=head_role,
                meter_sc=meter_sc, controlled=controlled)


# ================================================================================================ build
def build(inpx_raw, plan_raw, tuning_raw, check_sha=True, meters_map=None, fw_e=FW_E, fw_w=FW_W):
    if check_sha:
        for name, raw, want in (('network', inpx_raw, NETWORK_SHA256), ('plan', plan_raw, PLAN_SHA256),
                                ('tuning', tuning_raw, TUNING_SHA256)):
            if sha256_bytes(raw) != want:
                raise SystemExit('builder input %s sha256 differs from its pin' % name)
    inside = omega_inside()
    nf = parse_inpx(inpx_raw)
    plan = json.loads(plan_raw.decode('utf-8-sig'))
    tuning = json.loads(tuning_raw.decode('utf-8-sig'))
    meters_map = METERS if meters_map is None else meters_map
    inv = inventory(nf, plan, tuning, meters_map, fw_e, fw_w)
    L = nf['links']
    hb, out_c, head_role = inv['hb'], inv['out_c'], inv['head_role']
    fw = set(fw_e) | set(fw_w)

    seg = []                                             # gd_scan.build_segments order, D5 left out

    def add(sid, kind, link, lane, start, end, **extra):
        cap = (end - start) / SPACING_M
        row = {'id': sid, 'kind': kind, 'link': link, 'lane': int(lane), 'start_m': float(start), 'end_m': float(end),
               'capacity_veh': cap, 'short': cap < MIN_SOURCE_CAPACITY_VEH}
        row.update(extra)
        seg.append(row)
    for a in inv['approach']:
        if a['role'] != 'controlled_phase':
            continue
        add('A:%s:%s:%s' % (a['link'], a['lane'], a['sg']), 'A', a['link'], a['lane'], a['segment_start_m'],
            a['head_pos_m'], _phases=['%s_%s' % (a['sc'], p) for p in a['phases']], _head_no=a['head_no'])
    for f in inv['feeders']:
        for ln in range(1, f['link_lanes'] + 1):
            add('F:%s:%s' % (f['link'], ln), 'F', f['link'], ln, f['from_m'], f['to_m'])
    for name, m in inv['meters'].items():
        for h in m['heads']:
            add('M:%s:%s' % (name, h['lane']), 'M', m['connector'], h['lane'], 0.0, h['head_pos_m'], _meter=name)
        a = m['approach']
        for ln in a['lanes']:
            add('MA:%s:%s' % (name, ln), 'MA', a['link'], ln, a['from_m'], a['to_m'], _meter=name)
    for f in inv['feeders']:
        if not f['freeway_spill']:
            continue
        ends = {}
        for l in f['landings']:
            for ln in l['on_lanes']:
                k = (l['on_link'], int(ln))
                e = float(l['landing_pos_m']) + float(l['landing_to_server_end_m'])
                ends[k] = (float(l['landing_pos_m']), max(e, ends.get(k, (0, 0))[1]))
        for (lk, ln), (a0, e) in sorted(ends.items()):
            add('L:%s:%s:%s' % (f['link'], lk, ln), 'L', lk, ln, a0, e, _offramp=f['link'])
    # ---------------------------------------------------------------- receivers (codex CX USG:68-76, exact span)
    stops = defaultdict(list)
    for h in nf['signal_heads']:
        stops[h['link'], h['lane']].append(h['pos'])
    by_lane = defaultdict(list)
    for s in seg:
        by_lane[s['link'], s['lane']].append(s)
    span_id = {}
    receiver_items = 0
    new_r = []
    for s in [x for x in seg if x['kind'] == 'A']:
        items = []
        for t in out_c[s['link'], s['lane']]:
            if t['source_pos'] < s['end_m'] - 1e-6:
                continue
            tgt, tl, start = t['link'], t['lane'], t['position']
            future = [p for p in stops[tgt, tl] if p > start + 1e-6]
            end = min(future, default=L[tgt]['length_m'])
            if end <= start + 1e-6:
                continue
            key = None
            for k, rid in span_id.items():
                if k[0] == tgt and k[1] == tl and abs(k[2] - start) <= EPS and abs(k[3] - end) <= EPS:
                    key = k
            if key is None:
                existing = [x for x in by_lane[tgt, tl]
                            if abs(x['start_m'] - start) <= EPS and abs(x['end_m'] - end) <= EPS]
                if existing:
                    rid = sorted(existing, key=lambda x: x['id'])[0]['id']
                else:
                    rid = 'R:%s:%s:%.3f' % (tgt, tl, start)
                    new_r.append((rid, tgt, tl, start, end))
                key = (tgt, tl, start, end)
                span_id[key] = rid
            items.append({'connector': t['connector'], 'segment': span_id[key]})
            receiver_items += 1
        s['_receiver_items'] = items
    for rid, tgt, tl, start, end in new_r:
        add(rid, 'R', tgt, tl, start, end)
    ids = [s['id'] for s in seg]
    if len(set(ids)) != len(ids):
        raise SystemExit('segment ids are not unique')
    segd = {s['id']: s for s in seg}
    # ---------------------------------------------------------------- cells
    landings_on = defaultdict(list)
    departures_from = defaultdict(list)
    for c, l in L.items():
        if not l['is_connector']:
            continue
        for i in range(l['lanes']):
            landings_on[l['to_link'], l['to_lane'] + i].append(l['to_pos'])
            departures_from[l['from_link'], l['from_lane'] + i].append(l['from_pos'])
    cells, cell_of_lane = {}, {}
    for link in sorted(L, key=int):
        length = L[link]['length_m']
        for lane in range(1, L[link]['lanes'] + 1):
            pts = [0.0, length] + list(stops[link, lane]) + landings_on[link, lane] + departures_from[link, lane]
            pts = sorted(min(max(float(p), 0.0), length) for p in pts)
            kept = []
            for p in pts:
                if not kept or p > kept[-1] + EPS:
                    kept.append(p)
            if kept[-1] < length - EPS:
                kept.append(length)
            if len(kept) < 2:
                raise SystemExit('lane without length: %s %s' % (link, lane))
            row = []
            for i in range(len(kept) - 1):
                cid = 'C:%s:%s:%d' % (link, lane, i)
                cap = (kept[i + 1] - kept[i]) / SPACING_M
                cells[cid] = {'id': cid, 'link': link, 'lane': lane, 'start_m': kept[i], 'end_m': kept[i + 1],
                              'short': cap < MIN_SOURCE_CAPACITY_VEH, 'judge': None, 'next': [], 'stop': None}
                row.append(cid)
            cell_of_lane[link, lane] = row

    def cell_ending_at(link, lane, pos):
        for cid in cell_of_lane.get((link, lane), []):
            if abs(cells[cid]['end_m'] - pos) <= EPS:
                return cid
        return None

    def cell_holding_end(link, lane, pos):
        """section 5.4: the bottom cell of s = the cell holding the downstream end of s (start < pos <= end); a
        segment end that is not a cut point of its lane lies strictly inside one cell."""
        for cid in cell_of_lane.get((link, lane), []):
            c = cells[cid]
            if c['start_m'] + EPS < pos <= c['end_m'] + EPS:
                return cid
        return None

    def cell_departing_at(link, lane, pos):
        row = cell_of_lane.get((link, lane), [])
        for cid in row:
            c = cells[cid]
            if c['start_m'] + EPS < pos <= c['end_m'] + EPS:
                return cid
        return row[0] if row and pos <= cells[row[0]]['start_m'] + EPS else None

    def cell_landing_at(link, lane, pos):
        row = cell_of_lane.get((link, lane), [])
        for cid in row:
            c = cells[cid]
            if c['start_m'] - EPS <= pos < c['end_m'] - EPS:
                return cid
        return row[-1] if row else None
    # judges: the shortest containing segment (A L F M MA R), tie smallest id
    for (link, lane), row in cell_of_lane.items():
        segs = by_lane.get((link, lane), []) + [s for s in seg if s['kind'] == 'R' and s['link'] == link
                                                 and s['lane'] == lane and s not in by_lane.get((link, lane), [])]
        if not segs:
            continue
        for cid in row:
            c = cells[cid]
            inn = [s for s in segs if s['start_m'] <= c['start_m'] + EPS and c['end_m'] <= s['end_m'] + EPS]
            if inn:
                c['judge'] = sorted(inn, key=lambda s: (s['end_m'] - s['start_m'], s['id']))[0]['id']
    # edges
    edge_set = set()

    def edge(u, v, kind):
        if u and v and (u, v) not in edge_set:
            edge_set.add((u, v))
            cells[u]['next'].append([v, kind])
    for (link, lane), row in cell_of_lane.items():
        for a, b in zip(row, row[1:]):
            edge(a, b, 'lane')
    for c, l in sorted(L.items(), key=lambda kv: int(kv[0])):
        if not l['is_connector']:
            continue
        for i in range(l['lanes']):
            dep = cell_departing_at(l['from_link'], l['from_lane'] + i, l['from_pos'])
            crow = cell_of_lane[c, i + 1]
            land = cell_landing_at(l['to_link'], l['to_lane'] + i, l['to_pos'])
            if dep is None or land is None:
                raise SystemExit('connector %s lane %d has no departure / landing cell' % (c, i + 1))
            edge(dep, crow[0], 'connector')
            edge(crow[-1], land, 'connector')
    for (link, lane), row in sorted(cell_of_lane.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
        other = cell_of_lane.get((link, lane + 1), [])
        for cid in row:
            c = cells[cid]
            for oid in other:
                o = cells[oid]
                if abs(o['start_m'] - c['start_m']) <= EPS and abs(o['end_m'] - c['end_m']) <= EPS:
                    edge(cid, oid, 'lane_change')
                    edge(oid, cid, 'lane_change')
    for c in cells.values():
        c['next'].sort()
    # stops
    head_cells = defaultdict(list)                     # server -> [(cell, head lane segment id)]
    for (link, lane), hs in hb.items():
        for h in hs:
            role, ph = head_role(h)
            cid = cell_ending_at(link, lane, h['pos'])
            if cid is None:
                raise SystemExit('no cell ends at head %s' % h['no'])
            st = cells[cid]['stop'] or {'kind': None, 'servers': [], 'heads': []}
            st['heads'].append(h['no'])
            if role == 'controlled_phase':
                keys = ['SC%s_%s' % (h['sc'], p) for p in ph]
                st['kind'] = 'phase'
                st['servers'] = sorted(set(st['servers']) | set(keys))
                aid = 'A:%s:%s:%s' % (link, lane, h['sg'])
                for k in keys:
                    head_cells[k].append((cid, aid))
            elif role == 'meter':
                st['kind'] = 'meter' if st['kind'] != 'phase' else st['kind']
                st['servers'] = sorted(set(st['servers']) | {inv['meter_sc'][h['sc']]})
                head_cells[inv['meter_sc'][h['sc']]].append((cid, 'M:%s:%s' % (inv['meter_sc'][h['sc']], lane)))
            else:
                if st['kind'] is None:
                    st['kind'] = {'controlled_sc_midblock_native': 'midblock_head',
                                  'controlled_sc_unmapped_sg': 'unmapped_head'}.get(role, 'native_head')
            cells[cid]['stop'] = st
    for cid, c in cells.items():
        if c['stop'] is not None:
            c['stop']['heads'] = sorted(c['stop']['heads'], key=int)
            continue
        if c['link'] in fw:
            c['stop'] = {'kind': 'freeway', 'servers': [], 'heads': []}
        elif cell_of_lane[c['link'], c['lane']][-1] == cid and not any(k == 'connector' for _, k in c['next']):
            c['stop'] = {'kind': 'sink', 'servers': [], 'heads': []}
    for k in head_cells:
        head_cells[k] = sorted(set(head_cells[k]))
    # ---------------------------------------------------------------- sources, attribution sub-graphs
    for s in seg:
        s['source'] = s['kind'] in ('A', 'L', 'F', 'MA') and not s['short']
    head_lane_of = {}
    for k, rows in head_cells.items():
        for cid, sid in rows:
            head_lane_of[k, cid] = sid
    attribution = []
    for s in sorted(seg, key=lambda x: x['id']):
        if not s['source'] or s['kind'] not in ('F', 'L', 'MA'):
            continue
        bottom = cell_holding_end(s['link'], s['lane'], s['end_m'])
        if bottom is None:
            raise SystemExit('source %s has no bottom cell' % s['id'])
        excluded_heads = set()
        if s['kind'] == 'F':
            for cid in cell_of_lane.get((s['link'], s['lane']), []) + [x for ln in range(1, L[s['link']]['lanes'] + 1)
                                                                      for x in cell_of_lane[s['link'], ln]]:
                st = cells[cid]['stop']
                if st and st['kind'] == 'phase':
                    excluded_heads.add(cid)                       # same-link head exclusion (section 5.4)
        fwd, q = {bottom}, deque([bottom])
        while q:
            u = q.popleft()
            if cells[u]['stop'] is not None:
                continue
            for v, _k in cells[u]['next']:
                if v not in fwd:
                    fwd.add(v)
                    q.append(v)
        targets = []
        for cid in sorted(fwd):
            st = cells[cid]['stop']
            if not st or cid in excluded_heads:
                continue
            for srv in st['servers']:
                if s['kind'] == 'MA' and srv != s['_meter']:
                    continue
                if (srv, cid) in head_lane_of:
                    targets.append((srv, cid))
        preds = defaultdict(list)
        for u in fwd:
            if cells[u]['stop'] is not None:
                continue
            for v, _k in cells[u]['next']:
                if v in fwd:
                    preds[v].append(u)
        for srv, h in targets:
            back, q = {h}, deque([h])
            while q:
                v = q.popleft()
                for u in preds.get(v, ()):
                    if u not in back:
                        back.add(u)
                        q.append(u)
            sub = sorted(back & fwd)
            subset = set(sub)
            edges = sorted([u, v] for u in sub if cells[u]['stop'] is None
                           for v, _k in cells[u]['next'] if v in subset)
            attribution.append({'segment': s['id'], 'server': srv, 'start_cell': bottom, 'head_cell': h,
                                'head_lane_segment': head_lane_of[srv, h], 'cells': sub, 'edges': edges})
    attribution.sort(key=lambda a: (a['segment'], a['server'], a['head_cell']))
    # ---------------------------------------------------------------- overlaps
    pairs = []
    for (link, lane), _row in sorted(cell_of_lane.items(), key=lambda kv: (int(kv[0][0]), kv[0][1])):
        segs = sorted([s for s in seg if s['link'] == link and s['lane'] == lane], key=lambda s: s['id'])
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                a, b = segs[i], segs[j]
                if min(a['end_m'], b['end_m']) - max(a['start_m'], b['start_m']) > OVERLAP_M:
                    pairs.append(sorted([a['id'], b['id']]))
    pairs.sort()
    servers_all = sorted(set(head_cells))
    groups = {}
    for srv in servers_all:
        members = {s['id'] for s in seg if s['kind'] == 'A' and srv in s['_phases']}
        members |= {a['segment'] for a in attribution if a['server'] == srv}
        adj = defaultdict(set)
        for a, b in pairs:
            if a in members and b in members:
                adj[a].add(b)
                adj[b].add(a)
        seen, comps = set(), []
        for m in sorted(members):
            if m in seen or not adj[m]:
                continue
            comp, q = set(), deque([m])
            while q:
                x = q.popleft()
                if x in comp:
                    continue
                comp.add(x)
                q.extend(adj[x] - comp)
            seen |= comp
            comps.append(sorted(comp))
        if comps:
            groups[srv] = sorted(comps)
    # ---------------------------------------------------------------- assemble
    srv_by_seg = defaultdict(set)
    for a in attribution:
        srv_by_seg[a['segment']].add(a['server'])
    out_segments = []
    for s in sorted(seg, key=lambda x: x['id']):
        if s['kind'] == 'A':
            servers = list(s['_phases'])
        elif s['kind'] in ('M', 'MA'):
            servers = [s['_meter']]
        elif s['kind'] in ('F', 'L'):
            servers = sorted(srv_by_seg.get(s['id'], ()))
        else:
            servers = []
        row = {'id': s['id'], 'kind': s['kind'], 'link': s['link'], 'lane': s['lane'], 'start_m': s['start_m'],
               'end_m': s['end_m'], 'capacity_veh': s['capacity_veh'], 'short': s['short'], 'source': s['source'],
               'servers': servers}
        if s['kind'] == 'A':
            row['receivers'] = [it['segment'] for it in s['_receiver_items']]
            row['receiver_connectors'] = [it['connector'] for it in s['_receiver_items']]
            row['head_no'] = s['_head_no']
        row['part'] = part_of(s['link'], inside)
        out_segments.append(row)
    meters_out = {}
    for name in sorted(meters_map):
        meters_out[name] = {'connector': meters_map[name], 'head_cells': [c for c, _ in head_cells.get(name, [])],
                            'M': sorted(s['id'] for s in seg if s['kind'] == 'M' and s['_meter'] == name),
                            'MA': sorted(s['id'] for s in seg if s['kind'] == 'MA' and s['_meter'] == name)}
    counts = defaultdict(int)
    for s in seg:
        counts[s['kind']] += 1
    doc = {'schema': SCHEMA, 'network_sha256': NETWORK_SHA256, 'plan_sha256': PLAN_SHA256,
           'tuning_sha256': TUNING_SHA256, 'spacing_m': SPACING_M, 'min_source_capacity_veh': MIN_SOURCE_CAPACITY_VEH,
           'spill_rule': dict(SPILL_RULE), 'guard_rule_sha256': GUARD_RULE_SHA256, 'null_test': False,
           'counts': {k: counts[k] for k in ('A', 'L', 'F', 'M', 'MA', 'R')},
           'receiver_items': receiver_items,
           'segments': out_segments,
           'cells': [cells[c] for c in sorted(cells)],
           'attribution': attribution, 'overlap_pairs': pairs, 'overlap_groups': groups, 'meters': meters_out}
    return doc


def null_of(doc):
    """amendment C1-2 section 5.10: the same file, null_test true, every source false, attribution [], meter MA []."""
    import copy
    n = copy.deepcopy(doc)
    n['null_test'] = True
    for s in n['segments']:
        s['source'] = False
    n['attribution'] = []
    for m in n['meters'].values():
        m['MA'] = []
    return n


def main():
    if len(sys.argv) != 6:
        raise SystemExit(__doc__)
    inpx, plan, tuning, out, out_null = sys.argv[1:6]
    raw = [open(p, 'rb').read() for p in (inpx, plan, tuning)]
    doc = build(*raw)
    b = data(doc)
    bn = data(null_of(doc))
    for path, payload in ((out, b), (out_null, bn)):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'xb') as f:
            f.write(payload)
    print('C1G_BUILD evidence sha256=%s bytes=%d null sha256=%s bytes=%d counts=%s receivers=%d cells=%d attribution=%d'
          % (sha256_bytes(b), len(b), sha256_bytes(bn), len(bn), doc['counts'], doc['receiver_items'], len(doc['cells']),
             len(doc['attribution'])))


if __name__ == '__main__':
    main()
