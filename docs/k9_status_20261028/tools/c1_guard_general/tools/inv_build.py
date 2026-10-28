# -*- coding: utf-8 -*-
"""inv_build.py (guard/general, 2026-10-27 KST) — build the storage inventory from read-only facts.

Usage: python -B inv_build.py <net_facts.json> <usg_b.json> <spacing.json|-> <out.json>
Inputs (all read-only): net_facts.json (inv_net.py on the v3c3 .inpx), the native clock plan and the deployed tuning
of GWT8 c20aff1d, the codex Omega701 membership and reporting partition, the codex USG observation of one B decision
(inv_usg_b.py), and optionally the FZP standstill-spacing summary (inv_spacing.py).
Writes only <out.json>. No VISSIM, no COM, no plant, no decision replay.
"""
import hashlib
import json
import math
import os
import sys
from collections import defaultdict

GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
PLAN = GWT8 + '/diagnostics/controller_confidence_20260913/local_native_clock_v2/native_clock_plan_local.json'
OUC = GWT8 + '/diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
DETMAP = GWT8 + '/evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
PARAMS = GWT8 + '/evaluation/parameters.json'
OMEGA = 'D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json'
PART = 'D:/VISSIM_handoff/20261024/derived/reporting_partition.json'
FW_E = ['74', '10699', '2', '10613', '119', '10702', '24']        # OMEGA701 S7 (codex FW_E mainline 7)
FW_W = ['26', '10771', '120']                                    # codex west mainline chain
METERS = {'RM_C10480': '10480', 'RM_C10482': '10482', 'RM_C10646': '10646', 'RM_C10644': '10644',
          'RM_C10639': '10639', 'RM_C10681': '10681', 'RM_C10490': '10490', 'RM_C10484': '10484'}
EPS = 1e-6
SAME_STOPLINE_M = 3.0   # design choice (not data-fitted): same-SC heads this close = one stop line


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def jl(p):
    return json.loads(open(p, 'rb').read().decode('utf-8-sig'))


def relflow(s):
    """'' -> 1.0 (VISSIM empty = 1), '2 0:x' -> x (one interval in this .inpx), plain number -> number."""
    s = (s or '').strip()
    if not s:
        return 1.0
    parts = s.split()
    if len(parts) == 2 and ':' in parts[1]:
        return float(parts[1].split(':', 1)[1])
    if len(parts) == 1:
        return float(parts[0])
    raise ValueError('relFlow form ' + s)


def main():
    nf_p, usg_p, sp_p, out = sys.argv[1:5]
    nf = jl(nf_p)
    L = nf['links']
    plan = jl(PLAN)
    ouc = jl(OUC)
    det = jl(DETMAP)
    params = jl(PARAMS)
    omega = jl(OMEGA)
    part = jl(PART)
    usg = jl(usg_p)
    spacing_fzp = None
    spacing_fzp_mean = None
    if sp_p != '-':
        sp = jl(sp_p)
        spacing_fzp = sp['recommended_spacing_m']
        spacing_fzp_mean = sp['all']['mean_d_m']   # added after seeing the scan (data after)
    s6 = float(params['network']['urban_avg_vehicle_length_m'])
    net = ouc['config_overrides']['network']
    controlled = [s[2:] for s in net['signals']]
    C = plan['controllers']
    never = set(plan.get('never_green_signal_groups', []))
    in701 = set(map(str, omega['inside_links']))
    onr = {str(k): v for k, v in part['onramp_roads'].items()}
    offr = set(map(str, part['offramp_links']))
    fwe, fww = set(FW_E), set(FW_W)

    def part_of(link):
        if link not in in701:
            return 'outside_omega701'
        if link in fwe:
            return 'fw_e_mainline'
        if link in fww:
            return 'fw_w_mainline'
        if link in onr:
            return 'onramp_' + onr[link]
        if link in offr:
            return 'offramp'
        return 'urban_road'

    def storage(length_m):
        r = {'len_m': length_m, 'veh_per_lane_6m': length_m / s6}
        if spacing_fzp:
            r['veh_per_lane_fzp'] = length_m / spacing_fzp
        if spacing_fzp_mean:
            r['veh_per_lane_fzp_mean'] = length_m / spacing_fzp_mean
        return r

    # ------------------------------------------------------------------ indices
    heads = nf['signal_heads']
    hb = defaultdict(list)            # (link, lane) -> heads sorted by pos
    for h in heads:
        hb[h['link'], h['lane']].append(h)
    for k in hb:
        hb[k].sort(key=lambda h: h['pos'])
    meter_sc = {}
    for sc in nf['signal_controllers']:
        nm = sc.get('name') or ''
        if nm.startswith('RW_SC_RM_C'):
            meter_sc[sc['no']] = nm[len('RW_SC_'):]
    out_c = defaultdict(list)         # (link, lane) -> outgoing connector lanes
    in_c = defaultdict(list)          # (link, lane) -> incoming connector lanes
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
    l2o = det.get('link_to_origins', {})
    storage_key_cap = net.get('urban_link_storage_veh', {})

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

    def describe_head(h):
        role, extra = head_role(h)
        d = {'head_no': h['no'], 'sc': h['sc'], 'sg': h['sg'], 'link': h['link'], 'lane': h['lane'],
             'pos_m': h['pos'], 'role': role, 'never_green': ('SC%s:%s' % (h['sc'], h['sg'])) in never}
        if role == 'meter':
            d['meter'] = extra
        if role == 'controlled_phase':
            d['phases'] = extra
        return d

    def next_head(link, lane, start):
        for h in hb.get((link, lane), []):
            if h['pos'] > start + EPS:
                return h
        return None

    def prev_head(link, lane, pos):
        best = None
        for h in hb.get((link, lane), []):
            if h['pos'] < pos - EPS:
                best = h
        return best

    # ------------------------------------------------------------------ (1) controlled approach lanes
    usg_lanes = {(str(x['link']), int(x['lane'])): x for x in usg['lanes']}
    approach = []
    for h in sorted(heads, key=lambda h: (int(h['sc']), h['link'], h['lane'])):
        if h['sc'] not in controlled:
            continue
        role, ph = head_role(h)
        link, lane = h['link'], h['lane']
        # A head of the same SC within SAME_STOPLINE_M on the same lane is the same stop line (shared lane,
        # several SGs), not an upstream stop line.
        shared = [x for x in hb[link, lane] if x is not h and x['sc'] == h['sc'] and abs(x['pos'] - h['pos']) <= SAME_STOPLINE_M]
        up = None
        for x in hb[link, lane]:
            if x['pos'] < h['pos'] - EPS and x not in shared:
                up = x
        start = up['pos'] if up else 0.0
        same_lane_heads = hb[link, lane]
        recv = []
        before = []
        for t in out_c.get((link, lane), []):
            if t['source_pos'] < h['pos'] - EPS:
                before.append(dict(connector=t['connector'], source_pos=t['source_pos'], to_link=t['link'],
                                   to_lane=t['lane']))
                continue
            nh = next_head(t['link'], t['lane'], t['position'])
            end = nh['pos'] if nh else L[t['link']]['length_m']
            r = dict(connector=t['connector'], source_pos=t['source_pos'], link=t['link'], lane=t['lane'],
                     landing_pos_m=t['position'], segment_end_m=end,
                     segment_end_kind=('head' if nh else 'link_end'),
                     segment_end_head=(describe_head(nh) if nh else None),
                     part=part_of(t['link']), storage=storage(max(0.0, end - t['position'])))
            recv.append(r)
        u = usg_lanes.get((link, lane))
        row = dict(sc='SC' + h['sc'], sg=h['sg'], role=role, phases=ph, never_green=('SC%s:%s' % (h['sc'], h['sg'])) in never,
                   head_no=h['no'], link=link, lane=lane, link_lanes=L[link]['lanes'], link_len_m=L[link]['length_m'],
                   is_connector=L[link]['is_connector'], head_pos_m=h['pos'], segment_start_m=start,
                   segment_start_kind=('upstream_head' if up else 'link_start'),
                   upstream_head=(describe_head(up) if up else None),
                   heads_on_lane=len(same_lane_heads), part=part_of(link),
                   shared_stopline_sgs=sorted(x['sg'] for x in shared),
                   storage=storage(h['pos'] - start), storage_from_link_start=storage(h['pos']),
                   receivers=recv, branches_before_head=before,
                   inputs_on_link=inputs_by_link.get(link, []),
                   plant_storage_key=l2o.get(link),
                   plant_storage_cap_veh={k: storage_key_cap.get(k) for k in (l2o.get(link) or [])},
                   plant_movements=[dict(movement=m['movement'], weight=m.get('weight'), source=m.get('source'),
                                         phase=(net['urban_movements'].get(m['movement']) or {}).get('phase'))
                                    for m in (det.get('link_to_movements', {}).get(link) or [])],
                   codex_usg=(dict(included=True, capacity_veh=u['capacity_veh'], phase=u['phase'],
                                   receivers=[(r['connector'], r['link'], r['lane'], r['capacity_veh']) for r in u['receivers']])
                              if u else dict(included=False)))
        approach.append(row)

    # lanes of controlled approach links without any head
    appr_links = sorted({r['link'] for r in approach if r['role'] == 'controlled_phase'}, key=lambda x: int(x))
    headless_lanes = []
    for link in appr_links:
        for lane in range(1, L[link]['lanes'] + 1):
            if (link, lane) in hb:
                continue
            outs = [dict(connector=t['connector'], source_pos=t['source_pos'], to_link=t['link'], to_lane=t['lane'],
                         to_part=part_of(t['link'])) for t in out_c.get((link, lane), [])]
            headless_lanes.append(dict(link=link, lane=lane, link_len_m=L[link]['length_m'], outgoing=outs,
                                       storage=storage(L[link]['length_m'])))

    # ------------------------------------------------------------------ routes
    routes = []
    for d in nf['routing_static']:
        tot = sum(relflow(r['relFlow']) for r in d['routes'])
        for r in d['routes']:
            seq = [d['link']] + r['linkSeq'] + [r['destLink']]
            routes.append(dict(decision=d['no'], route=r['no'], name=d['name'], rel=relflow(r['relFlow']),
                               share=(relflow(r['relFlow']) / tot if tot else None), seq=seq,
                               dec_pos=d['pos'], dest_pos=r['destPos']))

    def route_server(seq, i):
        """From seq[i] onward, the first head that a vehicle on this route meets (lane taken from the next
        connector's departure lanes when the head link is not the last element)."""
        for j in range(i, len(seq)):
            link = seq[j]
            if link in fwe or link in fww:
                if j > i:
                    return dict(kind='freeway', link=link)
            nxt = seq[j + 1] if j + 1 < len(seq) else None
            if nxt is not None and L.get(nxt, {}).get('is_connector') and L[nxt]['from_link'] == link:
                lanes = range(L[nxt]['from_lane'], L[nxt]['from_lane'] + L[nxt]['lanes'])
                dep = L[nxt]['from_pos']
            else:
                lanes = range(1, L[link]['lanes'] + 1)
                dep = L[link]['length_m'] + 1.0
            hs = [h for ln in lanes for h in hb.get((link, ln), []) if h['pos'] <= dep + EPS]
            if hs:
                return dict(kind='head', link=link, heads=sorted({(h['sc'], h['sg']) for h in hs}),
                            roles=sorted({head_role(h)[0] for h in hs}))
        return dict(kind='route_end_no_head', link=seq[-1])

    def routes_through(link):
        rows = []
        for r in routes:
            if link in r['seq']:
                i = r['seq'].index(link)
                srv = route_server(r['seq'], i)
                rows.append(dict(decision=r['decision'], route=r['route'], share=r['share'], server=srv))
        return rows

    # ------------------------------------------------------------------ (2) headless feeders by upstream walk
    # Link-level walk (vehicles change lanes on a link); lane detail kept in landings/exits.
    feeders = {}

    def frow(link):
        f = feeders.get(link)
        if f is None:
            f = dict(link=link, is_connector=L[link]['is_connector'], link_lanes=L[link]['lanes'],
                     link_len_m=L[link]['length_m'], from_m=None, to_m=0.0, part=part_of(link), servers=set(),
                     via=set(), exits=[], landings=[], boundaries=[], freeway_spill=None, min_depth=99,
                     inputs_on_link=inputs_by_link.get(link, []), plant_storage_key=l2o.get(link))
            if L[link]['is_connector']:
                f['connector_from'] = dict(link=L[link]['from_link'], lane=L[link]['from_lane'], pos_m=L[link]['from_pos'])
                f['connector_to'] = dict(link=L[link]['to_link'], lane=L[link]['to_lane'], pos_m=L[link]['to_pos'])
            feeders[link] = f
        return f

    def add_once(lst, item):
        if item not in lst:
            lst.append(item)

    def walk_conn(c, land_link, land_lane_first, land_pos, land_end, server, via, depth):
        """Connector c lands on land_link at land_pos; the landing link stretch toward the server ends at land_end."""
        cl = L[c]
        f = frow(c)
        c_heads = [h for i in range(1, cl['lanes'] + 1) for h in hb.get((c, i), [])]
        start = max([h['pos'] for h in c_heads], default=0.0)
        f['from_m'] = start if f['from_m'] is None else min(f['from_m'], start)
        f['to_m'] = cl['length_m']
        f['servers'].add(server)
        f['via'].add(via)
        f['min_depth'] = min(f['min_depth'], depth)
        add_once(f['landings'], dict(on_link=land_link, on_lanes=list(range(land_lane_first, land_lane_first + cl['lanes'])),
                                     landing_pos_m=land_pos, landing_to_server_end_m=land_end - land_pos,
                                     storage_landing_to_end=storage(max(0.0, land_end - land_pos))))
        if c_heads:
            add_once(f['boundaries'], dict(kind='head_on_connector', heads=[describe_head(h) for h in c_heads]))
            return
        fl = cl['from_link']
        if fl in fwe or fl in fww:
            f['freeway_spill'] = dict(road=('FW_E' if fl in fwe else 'FW_W'), link=fl, lane=cl['from_lane'],
                                      diverge_pos_m=cl['from_pos'])
            return
        walk_link(fl, cl['from_pos'], c, server, via, depth + 1)

    def walk_link(link, end_pos, exit_conn, server, via, depth):
        if depth > 25:
            raise ValueError('walk too deep at ' + link)
        lanes = range(1, L[link]['lanes'] + 1)
        hs = [h for ln in lanes for h in hb.get((link, ln), []) if h['pos'] <= end_pos + 2 * EPS]
        if hs:
            # departure lies after a stop line: the upstream server is that head (boundary on the connector row)
            add_once(frow(exit_conn)['boundaries'], dict(kind='upstream_stopline', link=link, departure_pos_m=end_pos,
                                                        heads=[describe_head(h) for h in sorted(hs, key=lambda h: h['lane'])]))
            return
        f = frow(link)
        f['from_m'] = 0.0
        f['to_m'] = max(f['to_m'], end_pos)
        f['servers'].add(server)
        f['via'].add(via)
        f['min_depth'] = min(f['min_depth'], depth)
        cl = L[exit_conn]
        add_once(f['exits'], dict(connector=exit_conn, departure_pos_m=end_pos,
                                  from_lanes=list(range(cl['from_lane'], cl['from_lane'] + cl['lanes'])), server=server))
        if inputs_by_link.get(link):
            add_once(f['boundaries'], dict(kind='vehicle_input', inputs=inputs_by_link[link]))
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
                walk_conn(ic['connector'], link, L[ic['connector']]['to_lane'], ic['to_pos'], end_pos, server, via, depth + 1)

    visited = set()

    def srv_name(h):
        role, ph = head_role(h)
        if role == 'meter':
            return 'meter:' + meter_sc[h['sc']]
        if role == 'controlled_phase':
            return 'SC%s:%s(SG%s)' % (h['sc'], '/'.join(ph), h['sg'])
        return '%s:SC%s:SG%s' % (role, h['sc'], h['sg'])

    approach_boundaries = []
    for r in approach:
        if r['role'] != 'controlled_phase':
            continue
        h = {'sc': r['sc'][2:], 'sg': r['sg']}
        server = srv_name(h)
        link, lane = r['link'], r['lane']
        via = 'approach:%s:%s' % (link, lane)
        lo = r['segment_start_m']
        # any connector landing on this link (any lane) inside [segment start of this lane, head]; lane changes allowed
        for ln in range(1, L[link]['lanes'] + 1):
            for ic in in_c.get((link, ln), []):
                if ic['to_pos'] > r['head_pos_m'] + EPS:
                    continue
                if ic['to_pos'] < lo - EPS:
                    add_once(approach_boundaries, dict(approach=via, connector=ic['connector'], landing_pos_m=ic['to_pos'],
                                                       upstream_head=r['upstream_head'],
                                                       note='lands upstream of a same-link upstream stopline'))
                    continue
                key = (ic['connector'], server)
                if key in visited:
                    continue
                visited.add(key)
                walk_conn(ic['connector'], link, L[ic['connector']]['to_lane'], ic['to_pos'], r['head_pos_m'], server, via, 1)

    # ------------------------------------------------------------------ path distances to servers (lane-blind)
    import heapq

    def server_label_of(h):
        return srv_name(h)

    def dist_to_servers(link, pos, limit=6000.0):
        """Shortest along-road distance from (link, pos) to each first stop line met downstream.
        Lane-blind: vehicles may change lanes on a link. A head on the link at or after pos ends that branch;
        a connector that departs a lane after that lane's head is served by the head (not followed)."""
        best = {}
        pq = [(0.0, link, pos)]
        done = set()
        while pq:
            cost, x, p = heapq.heappop(pq)
            if (x, round(p, 3)) in done or cost > limit:
                continue
            done.add((x, round(p, 3)))
            lane_head = {}
            for ln in range(1, L[x]['lanes'] + 1):
                hs = [h for h in hb.get((x, ln), []) if h['pos'] >= p - EPS]
                if hs:
                    lane_head[ln] = hs[0]
            for ln, h in lane_head.items():
                lab = server_label_of(h)
                c2 = cost + h['pos'] - p
                if lab not in best or c2 < best[lab]:
                    best[lab] = c2
            if L[x]['is_connector'] and not lane_head:
                tl = L[x]['to_link']
                c1 = cost + L[x]['length_m'] - p
                if tl in fwe or tl in fww:
                    lab = 'freeway_merge:' + ('FW_E' if tl in fwe else 'FW_W')
                    if lab not in best or c1 < best[lab]:
                        best[lab] = c1
                else:
                    heapq.heappush(pq, (c1, tl, L[x]['to_pos']))
                continue
            n_follow = 0
            for ln in range(1, L[x]['lanes'] + 1):
                for t in out_c.get((x, ln), []):
                    if t['source_pos'] < p - EPS:
                        continue
                    h = lane_head.get(ln)
                    if h is not None and t['source_pos'] >= h['pos'] - EPS:
                        continue
                    c = t['connector']
                    c1 = cost + t['source_pos'] - p
                    ch = [hh for i in range(1, L[c]['lanes'] + 1) for hh in hb.get((c, i), [])]
                    if ch:
                        hh = min(ch, key=lambda z: z['pos'])
                        lab = server_label_of(hh)
                        c2 = c1 + hh['pos']
                        if lab not in best or c2 < best[lab]:
                            best[lab] = c2
                        continue
                    if t['link'] in fwe or t['link'] in fww:
                        lab = 'freeway_merge:' + ('FW_E' if t['link'] in fwe else 'FW_W')
                        c2 = c1 + L[c]['length_m']
                        if lab not in best or c2 < best[lab]:
                            best[lab] = c2
                        continue
                    n_follow += 1
                    heapq.heappush(pq, (c1 + L[c]['length_m'], t['link'], t['position']))
            if not lane_head and n_follow == 0 and not any(t['source_pos'] >= p - EPS for ln in range(1, L[x]['lanes'] + 1)
                                                           for t in out_c.get((x, ln), [])):
                lab = 'sink:' + x
                c2 = cost + L[x]['length_m'] - p
                if lab not in best or c2 < best[lab]:
                    best[lab] = c2
        return best

    def route_servers_chained(link):
        """Routes passing `link`; a route that ends before any head is continued by the routing decisions
        placed on its destination link at or after the destination point (product of shares)."""
        rows = []

        def follow(r, i, chain, share, depth):
            srv = route_server(r['seq'], i)
            if srv['kind'] == 'route_end_no_head' and depth < 4:
                dl, dp = r['seq'][-1], r['dest_pos']
                nexts = [d for d in nf['routing_static'] if d['link'] == dl and d['pos'] >= dp - 1.0]
                if nexts:
                    for d in nexts:
                        for r2 in [x for x in routes if x['decision'] == d['no']]:
                            follow(r2, 0, chain + ['%s:%s' % (r2['decision'], r2['route'])],
                                   (share or 0) * (r2['share'] or 0), depth + 1)
                    return
            rows.append(dict(chain=chain, share_product=share, server=srv))

        for r in routes:
            if link in r['seq']:
                follow(r, r['seq'].index(link), ['%s:%s' % (r['decision'], r['route'])], r['share'], 0)
        return rows

    # meters: pre-head connector storage + upstream approach
    meters = {}
    for name, c in METERS.items():
        cl = L[c]
        mh = [h for i in range(1, cl['lanes'] + 1) for h in hb.get((c, i), [])]
        server = 'meter:' + name
        lanes_rows = []
        for h in sorted(mh, key=lambda h: h['lane']):
            lanes_rows.append(dict(lane=h['lane'], head_no=h['no'], head_pos_m=h['pos'], sc=h['sc'], sg=h['sg'],
                                   prehead=storage(h['pos']), posthead=storage(cl['length_m'] - h['pos'])))
        f_link, f_lane, f_pos = cl['from_link'], cl['from_lane'], cl['from_pos']
        ups = prev_head(f_link, f_lane, f_pos + 2 * EPS)
        a = ups['pos'] if ups else 0.0
        walk_link(f_link, f_pos, c, server, 'meter:' + name, 1)
        road = 'FW_E' if cl['to_link'] in fwe else ('FW_W' if cl['to_link'] in fww else None)
        meters[name] = dict(connector=c, road=road, lanes=cl['lanes'], length_m=cl['length_m'],
                            from_link=f_link, from_lane=f_lane, diverge_pos_m=f_pos,
                            merge_link=cl['to_link'], merge_pos_m=cl['to_pos'], heads=lanes_rows,
                            approach_segment=dict(link=f_link, lanes=[f_lane + i for i in range(cl['lanes'])],
                                                  from_m=a, to_m=f_pos, storage=storage(f_pos - a),
                                                  start_kind=('upstream_head' if ups else 'link_start'),
                                                  upstream_head=(describe_head(ups) if ups else None)),
                            part=part_of(c), plant_storage_key=l2o.get(c),
                            plant_ramp_queue=[dict(key=q, max_veh=net.get('ramp_queue_max_veh_by_ramp', {}).get(q))
                                              for q in det.get('ramp_link_to_queues', {}).get(c, [])])

    # off-ramps: downstream walk from each diverge to first heads (topology), with routes
    offramps = {}
    for c in sorted(offr, key=int):
        cl = L[c]
        road = 'FW_E' if cl['from_link'] in fwe else ('FW_W' if cl['from_link'] in fww else None)
        dd = dist_to_servers(c, 0.0)
        servers = set(dd)
        path = {k: v for k, v in sorted(dd.items())}
        offramps[c] = dict(road=road, from_link=cl['from_link'], from_lane=cl['from_lane'], diverge_pos_m=cl['from_pos'],
                           to_link=cl['to_link'], to_lane=cl['to_lane'], landing_pos_m=cl['to_pos'], lanes=cl['lanes'],
                           length_m=cl['length_m'], in_omega701=c in in701, topology_servers=sorted(servers),
                           dist_from_diverge_to_first_stopline_m=path, routes=route_servers_chained(c))

    # finalize feeders
    frows = []
    for link, f in sorted(feeders.items(), key=lambda kv: int(kv[0])):
        if f['from_m'] is None:
            continue
        f['servers'] = sorted(f['servers'])
        f['via'] = sorted(f['via'])
        f['storage'] = storage(max(0.0, f['to_m'] - f['from_m']))
        ex = {}
        for e in f['exits']:
            k = (e['connector'], e['departure_pos_m'])
            ex.setdefault(k, dict(connector=e['connector'], departure_pos_m=e['departure_pos_m'],
                                  from_lanes=e['from_lanes'], servers=[]))
            if e['server'] not in ex[k]['servers']:
                ex[k]['servers'].append(e['server'])
        f['exits'] = sorted(ex.values(), key=lambda e: (e['departure_pos_m'], e['connector']))
        d0 = dist_to_servers(link, f['from_m'])
        own = f['to_m'] - f['from_m']
        f['dist_from_start_to_server_m'] = {k: v for k, v in sorted(d0.items()) if k in f['servers'] or k.startswith('freeway_merge')}
        f['dist_from_end_to_server_m'] = {k: v - own for k, v in f['dist_from_start_to_server_m'].items()}
        rr = route_servers_chained(link)
        f['routes'] = rr
        agg = defaultdict(float)
        for r in rr:
            srv = r['server']
            key = (srv['kind'] if srv['kind'] != 'head' else
                   'head:' + srv['link'] + ':' + ','.join('SC%s/SG%s' % x for x in srv['heads']))
            agg[key] += 1
        f['route_server_counts'] = dict(agg)
        frows.append(f)

    for name, m in meters.items():
        a = m['approach_segment']
        m['approach_segment']['dist_from_start_to_meter_head_m'] = dist_to_servers(a['link'], a['from_m']).get('meter:' + name)

    res = dict(tool='inv_build.py', spacing_6m=s6, spacing_fzp=spacing_fzp, spacing_fzp_mean=spacing_fzp_mean,
               sources={'net_facts_sha256': sha(nf_p), 'inpx_sha256': nf['inpx_sha256'], 'plan_sha256': sha(PLAN),
                        'tuning_sha256': sha(OUC), 'detector_mapping_sha256': sha(DETMAP), 'parameters_sha256': sha(PARAMS),
                        'omega701_sha256': sha(OMEGA), 'partition_sha256': sha(PART), 'usg_b_sha256': sha(usg_p),
                        'usg_b_source_sha256': usg['source_sha256'],
                        'spacing_sha256': (sha(sp_p) if sp_p != '-' else None)},
               controlled_signals=['SC' + s for s in controlled],
               plan_phase_order={('SC' + s): C[s]['native_clock_basis'].get('phase_order') for s in controlled},
               plan_phase_signal_groups={('SC' + s): C[s]['phase_signal_groups'] for s in controlled},
               plan_midblock_sgs={('SC' + s): C[s].get('midblock_native_signal_groups', []) for s in controlled},
               never_green=sorted(never),
               approach_lanes=approach, approach_link_lanes_without_head=headless_lanes,
               feeders=frows, approach_boundaries=approach_boundaries, meters=meters, offramps=offramps,
               fw_e=FW_E, fw_w=FW_W, routes_count=len(routes))
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False, indent=1, sort_keys=True, default=list)
    os.replace(tmp, out)
    print('approach', len(approach), 'headless lanes', len(headless_lanes), 'feeders', len(frows), 'meters', len(meters),
          'offramps', len(offramps), 'routes', len(routes))
    print(sha(out))


if __name__ == '__main__':
    main()
