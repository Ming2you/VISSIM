# -*- coding: utf-8 -*-
"""inv_final.py (guard/general, 2026-10-27 KST) — assemble inventory.json and render INVENTORY.md tables.

Usage: python -B inv_final.py <inv_build.json> <spacing.json> <occ.json> <narrative.md> <out_json> <out_md>
The narrative file holds the hand-written Korean text with {{TABLE:name}} and {{VAL:name}} slots.
Writes only <out_json> and <out_md>. Read-only otherwise.
"""
import hashlib
import json
import os
import sys
from collections import defaultdict

KEY_SEGMENTS = [
    # FW_E off-ramp chains
    ('F:10481:1', 'FW_E 진출 10481 차로 1'), ('F:10481:2', 'FW_E 진출 10481 차로 2'),
    ('A:127:1:2', '127 차로 1 (SC1001 p3)'), ('A:127:2:2', '127 차로 2 (SC1001 p3)'), ('A:127:3:5', '127 차로 3 (SC1001 p4)'),
    ('F:10483:1', 'FW_E 진출 10483'), ('F:124:1', '124 차로 1'), ('MA:RM_C10480:1', 'RM_C10480 접근 124 차로 1'),
    ('M:RM_C10480:1', 'RM_C10480 머리 앞'),
    ('F:10682:1', 'FW_E 진출 10682'), ('F:121:1', '121 차로 1'), ('M:RM_C10646:1', 'RM_C10646 머리 앞'),
    ('F:10643:1', 'FW_E 진출 10643 차로 1'), ('F:10643:2', 'FW_E 진출 10643 차로 2'), ('F:126:1', '126 차로 1'), ('F:126:2', '126 차로 2'),
    ('A:71:1:2', '71 차로 1 (SC1004 p3)'), ('A:71:2:2', '71 차로 2 (SC1004 p3)'), ('A:71:3:2', '71 차로 3 (SC1004 p3)'),
    ('A:71:4:5', '71 차로 4 (SC1004 p4)'), ('A:71:5:5', '71 차로 5 (SC1004 p4)'),
    # FW_E meters
    ('M:RM_C10484:1', 'RM_C10484 머리 앞'), ('MA:RM_C10484:1', 'RM_C10484 접근 31 차로 1'),
    ('M:RM_C10490:1', 'RM_C10490 머리 앞'), ('MA:RM_C10490:1', 'RM_C10490 접근 129 차로 1'), ('D5:129:1', '129 차로 1 국소 239.4–300.0 m'),
    ('M:RM_C10639:1', 'RM_C10639 머리 앞'), ('MA:RM_C10639:1', 'RM_C10639 접근 70 차로 1'),
    ('M:RM_C10681:1', 'RM_C10681 머리 앞 차로 1'), ('M:RM_C10681:2', 'RM_C10681 머리 앞 차로 2'),
    ('MA:RM_C10681:1', 'RM_C10681 접근 68 차로 1'), ('MA:RM_C10681:2', 'RM_C10681 접근 68 차로 2'),
    # FW_W (monitor only)
    ('F:10491:1', 'FW_W 진출 10491'), ('F:129:1', '129 차로 1'), ('F:10638:1', 'FW_W 진출 10638 차로 1'), ('F:10638:2', 'FW_W 진출 10638 차로 2'),
    ('F:70:1', '70 차로 1'), ('F:70:2', '70 차로 2'),
]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def jl(p):
    return json.loads(open(p, 'rb').read().decode('utf-8-sig'))


ROLE_KO = {'controlled_phase': '현시', 'controlled_sc_midblock_native': '미드블록 SG(우리 현시 밖)',
           'controlled_sc_unmapped_sg': '현시 없는 SG', 'native_signal': 'native 신호', 'meter': '미터'}


def rk(x):
    return ROLE_KO.get(x, x)


def f1(x, nd=1):
    if x is None:
        return '–'
    return ('%.' + str(nd) + 'f') % x


def main():
    b_p, sp_p, occ_p, nar_p, out_j, out_m = sys.argv[1:7]
    inv = jl(b_p)
    sp = jl(sp_p)
    occ = jl(occ_p)
    S6 = inv['spacing_6m']
    SF = sp['recommended_spacing_m']
    if abs((inv['spacing_fzp'] or 0) - SF) > 1e-12:
        raise SystemExit('build spacing differs from spacing file')
    A = inv['approach_lanes']
    tables = {}
    vals = {}

    # ---------------- signals summary
    sig = []
    for sc in inv['controlled_signals']:
        rows = [a for a in A if a['sc'] == sc]
        ph = [a for a in rows if a['role'] == 'controlled_phase']
        other = [a for a in rows if a['role'] != 'controlled_phase']
        inc = [a for a in ph if a['codex_usg']['included']]
        links = sorted({a['link'] for a in ph}, key=int)
        sig.append(dict(sc=sc, live=inv['plan_phase_order'][sc], phase_head_lanes=len(ph), other_heads=len(other),
                        other_detail=sorted({'%s SG%s' % (rk(a['role']), a['sg']) for a in other}),
                        codex_included=len(inc), approach_links=links,
                        parts=sorted({a['part'] for a in ph})))
    t = ['| SC | 살아 있는 현시(계획 순서) | 현시 머리 차로 | codex USG 가 보는 차로 | 우리 현시 밖 머리 | 접근 링크 | 분할 |', '|---|---|---:|---:|---|---|---|']
    for r in sig:
        t.append('| %s | %s | %d | %d | %s | %s | %s |' % (r['sc'], '·'.join(r['live']), r['phase_head_lanes'], r['codex_included'],
                                                         (', '.join(r['other_detail']) + ' (%d)' % r['other_heads']) if r['other_heads'] else '0',
                                                         ' · '.join(r['approach_links']), ', '.join(r['parts'])))
    tables['signals'] = '\n'.join(t)
    vals['n_phase_lanes'] = sum(r['phase_head_lanes'] for r in sig)
    vals['n_codex_lanes'] = sum(r['codex_included'] for r in sig)
    vals['n_heads_controlled'] = len(A)

    # ---------------- approach groups per (sc, link)
    groups = defaultdict(list)
    for a in A:
        if a['role'] == 'controlled_phase':
            groups[(a['sc'], a['link'])].append(a)
    grows = []
    for (sc, link), rows in sorted(groups.items(), key=lambda kv: (int(kv[0][0][2:]), int(kv[0][1]))):
        rows.sort(key=lambda a: a['lane'])
        lanes_txt = ', '.join('%d:SG%s/%s' % (a['lane'], a['sg'], '/'.join(a['phases'])) for a in rows)
        hp = [a['head_pos_m'] for a in rows]
        st = sorted({round(a['segment_start_m'], 1) for a in rows})
        s6 = [a['storage']['veh_per_lane_6m'] for a in rows]
        sf = [a['storage']['veh_per_lane_fzp'] for a in rows]
        sm = [a['storage']['veh_per_lane_fzp_mean'] for a in rows]
        recv = []
        for a in rows:
            for r in a['receivers']:
                recv.append('%s→%s:%d(%s)' % (r['connector'], r['link'], r['lane'], f1(r['storage']['veh_per_lane_6m'])))
        g = dict(sc=sc, link=link, link_lanes=rows[0]['link_lanes'], link_len_m=rows[0]['link_len_m'], lanes=[a['lane'] for a in rows],
                 sgs=sorted({a['sg'] for a in rows}), phases=sorted({p for a in rows for p in a['phases']}),
                 head_pos_m=[min(hp), max(hp)], segment_start_m=st, lane_storage_6m=[min(s6), max(s6)], lane_storage_fzp=[min(sf), max(sf)],
                 lane_storage_fzp_mean=[min(sm), max(sm)], link_sum_storage_fzp_mean=sum(sm),
                 link_sum_storage_6m=sum(s6), link_sum_storage_fzp=sum(sf), codex_included=all(a['codex_usg']['included'] for a in rows),
                 codex_included_lanes=[a['lane'] for a in rows if a['codex_usg']['included']], part=rows[0]['part'],
                 plant_storage_key=rows[0]['plant_storage_key'], plant_storage_cap_veh=rows[0]['plant_storage_cap_veh'],
                 receivers=sorted(set(recv)), upstream_head=[a['upstream_head'] for a in rows if a['upstream_head']],
                 shared_stopline=[(a['lane'], a['sg'], a['shared_stopline_sgs']) for a in rows if a['shared_stopline_sgs']],
                 lanes_text=lanes_txt)
        grows.append(g)
    def rg(v):
        return f1(v[0]) if abs(v[1] - v[0]) < 0.05 else '%s–%s' % (f1(v[0]), f1(v[1]))
    t = ['| SC | 링크(차로, 길이 m) | 차로:SG/현시 | 머리 m | 구간 시작 m | 차로 저장 대 (6 m / 중앙 %s / 평균 %s) | 링크 합 (6 m / 중앙 / 평균) | codex USG | Ω701 분할 | plant 저장 키(설정 대) |' % (f1(SF, 2), f1(inv['spacing_fzp_mean'], 2)),
         '|---|---|---|---|---|---|---|---|---|---|']
    for g in grows:
        cap = '; '.join('%s %s' % (k, f1(v)) for k, v in (g['plant_storage_cap_veh'] or {}).items()) or '–'
        t.append('| %s | %s (%d, %s) | %s | %s | %s | %s / %s / %s | %s / %s / %s | %s | %s | %s |' % (
            g['sc'], g['link'], g['link_lanes'], f1(g['link_len_m']), g['lanes_text'], rg(g['head_pos_m']),
            '/'.join(f1(x) for x in g['segment_start_m']), rg(g['lane_storage_6m']), rg(g['lane_storage_fzp']), rg(g['lane_storage_fzp_mean']),
            f1(g['link_sum_storage_6m']), f1(g['link_sum_storage_fzp']), f1(g['link_sum_storage_fzp_mean']),
            ('예' if g['codex_included'] else ('일부 ' + ','.join(map(str, g['codex_included_lanes'])) if g['codex_included_lanes'] else '아니오')),
            g['part'], cap))
    tables['approach_groups'] = '\n'.join(t)
    vals['n_approach_groups'] = len(grows)

    # receivers table
    t = ['| SC | 접근 링크 | 받는 쪽 (커넥터→착지 링크:차로(저장 대, 6 m)) |', '|---|---|---|']
    for g in grows:
        t.append('| %s | %s | %s |' % (g['sc'], g['link'], ' · '.join(g['receivers']) or '–'))
    tables['receivers'] = '\n'.join(t)

    # not-phase heads
    t = ['| SC | 링크:차로 | SG | 머리 m | 역할 | 영구 적색 | codex USG |', '|---|---|---|---|---|---|---|']
    for a in A:
        if a['role'] != 'controlled_phase' or not a['codex_usg']['included']:
            t.append('| %s | %s:%d | %s | %s | %s%s | %s | %s |' % (
                a['sc'], a['link'], a['lane'], a['sg'], f1(a['head_pos_m']), rk(a['role']),
                (' (위 정지선 %s SC%s SG%s @%s m)' % (rk(a['upstream_head']['role']), a['upstream_head']['sc'], a['upstream_head']['sg'], f1(a['upstream_head']['pos_m'])) if a['upstream_head'] else '')
                + ((' (같은 정지선 SG ' + ','.join(a['shared_stopline_sgs']) + ')') if a['shared_stopline_sgs'] else ''),
                '예' if a['never_green'] else '–', '포함' if a['codex_usg']['included'] else '빠짐'))
    tables['other_heads'] = '\n'.join(t)

    # headless lanes on approach links
    t = ['| 링크:차로 | 링크 길이 m | 나가는 커넥터 → 링크 |', '|---|---|---|']
    for h in inv['approach_link_lanes_without_head']:
        t.append('| %s:%d | %s | %s |' % (h['link'], h['lane'], f1(h['link_len_m']), ' · '.join('%s→%s' % (o['connector'], o['to_link']) for o in h['outgoing'])))
    tables['headless_lanes'] = '\n'.join(t)

    # ---------------- feeders
    F = inv['feeders']
    vals['n_feeders'] = len(F)
    vals['n_feeders_links'] = sum(1 for f in F if not f['is_connector'])
    vals['n_feeders_conn'] = sum(1 for f in F if f['is_connector'])
    vals['n_feeders_in701'] = sum(1 for f in F if f['part'] != 'outside_omega701')
    vals['n_feeders_out701'] = sum(1 for f in F if f['part'] == 'outside_omega701')
    Fby = {f['link']: f for f in F}

    def srvtxt(f, key='dist_from_end_to_server_m'):
        return ' · '.join('%s %s m (%s대)' % (k, f1(v), f1(v / SF)) for k, v in f[key].items() if not k.startswith('sink'))

    for c in ('10481', '10483', '10643', '10682', '10491', '10638'):
        f = Fby[c]
        vals['chain_' + c] = ' · '.join('%s %s m(%s대)' % (k, f1(v), f1(v / SF)) for k, v in f['dist_from_end_to_server_m'].items()
                                        if not k.startswith('sink') and not k.startswith('freeway'))
    vals['d5_len'] = f1(299.99 - 239.38)
    vals['d5_veh_fzp'] = f1((299.99 - 239.38) / SF)
    vals['d5_veh_6'] = f1((299.99 - 239.38) / S6)

    # offramps
    t = ['| 진출 커넥터 | 도로 | 갈림(링크 @m) | 차로·길이 m | 착지(링크:차로 @m) | Ω701 | 처음 만나는 정지선(갈림에서 m) | 경로(결정:경로 몫 → 서버) |', '|---|---|---|---|---|---|---|---|']
    order = sorted(inv['offramps'].items(), key=lambda kv: (kv[1]['road'] != 'FW_E', int(kv[0])))
    for c, o in order:
        rt = ' · '.join('%s %s → %s' % ('>'.join(r['chain']), f1(r['share_product'], 3),
                                         (r['server']['link'] + ':' + ','.join('SC%s/SG%s' % tuple(x) for x in r['server']['heads'])) if r['server']['kind'] == 'head'
                                         else ('끝 ' + r['server']['link'] + '(정지선 없음)')) for r in o['routes'])
        t.append('| %s | %s | %s @%s | %d · %s | %s:%s @%s | %s | %s | %s |' % (
            c, o['road'], o['from_link'], f1(o['diverge_pos_m']), o['lanes'], f1(o['length_m']), o['to_link'],
            ('%d' % o['to_lane']) if o['lanes'] == 1 else '%d–%d' % (o['to_lane'], o['to_lane'] + o['lanes'] - 1), f1(o['landing_pos_m']),
            '안' if o['in_omega701'] else '밖',
            ' · '.join('%s %s' % (k, f1(v)) for k, v in o['dist_from_diverge_to_first_stopline_m'].items()), rt))
    tables['offramps'] = '\n'.join(t)

    # shared / key feeder links
    keyl = ['129', '127', '124', '121', '70', '126', '31', '68', '69', '32', '37', '75']
    t = ['| 링크 | 차로·길이 m | 구간 m | 차로 저장 대 (6 m / FZP) | 들어오는 커넥터(출발 → 착지 차로 @m) | 나가는 곳(출발 m, 차로 → 서버) | 입력 | 끝(정지선)까지 m (FZP 대) | 경로 몫 → 서버 |', '|---|---|---|---|---|---|---|---|---|']
    for k in keyl:
        f = Fby.get(k)
        if f is None:
            continue
        ins = []
        for c in F:
            if c['is_connector']:
                for x in c['landings']:
                    if x['on_link'] == k:
                        s = '%s(%s:%s → %s @%s)' % (c['link'], c['connector_from']['link'], c['connector_from']['lane'],
                                                    ','.join(map(str, x['on_lanes'])), f1(x['landing_pos_m']))
                        if s not in ins:
                            ins.append(s)
        ex = ' · '.join('%s @%s %s → %s' % (e['connector'], f1(e['departure_pos_m']), ','.join(map(str, e['from_lanes'])), '/'.join(e['servers'])) for e in f['exits'])
        rr = defaultdict(float)
        for r in f['routes']:
            s = r['server']
            lab = (s['link'] + ':' + ','.join('SC%s/SG%s' % tuple(x) for x in s['heads'])) if s['kind'] == 'head' else ('끝 ' + s.get('link', '?'))
            rr[lab] += 1
        t.append('| %s | %d · %s | %s–%s | %s / %s | %s | %s | %s | %s | %s |' % (
            k, f['link_lanes'], f1(f['link_len_m']), f1(f['from_m']), f1(f['to_m']), f1(f['storage']['veh_per_lane_6m']), f1(f['storage']['veh_per_lane_fzp']),
            ' · '.join(ins) or '–', ex, ','.join(f['inputs_on_link']) or '–', srvtxt(f), ' · '.join('%s ×%d' % (a, b) for a, b in rr.items())))
    tables['shared_links'] = '\n'.join(t)

    # direct feeders of approach links (connectors landing on controlled approach links)
    appr_links = {g['link'] for g in grows}
    t = ['| 접근 링크 | 공급 커넥터(출발 링크:차로 @m → 착지 차로 @m, 착지→머리 m, FZP 대) | 상류 경계 |', '|---|---|---|']
    bylink = defaultdict(list)
    for c in F:
        if not c['is_connector']:
            continue
        for x in c['landings']:
            if x['on_link'] in appr_links:
                bnd = ','.join(sorted({('정지선 ' + '/'.join(sorted({'SC%s:SG%s' % (h['sc'], h['sg']) for h in b['heads']}))) if b['kind'] in ('upstream_stopline', 'head_on_connector')
                                       else b['kind'] for b in c['boundaries']})) or (('고속도로 ' + c['freeway_spill']['road']) if c['freeway_spill'] else '상류 계속')
                bylink[x['on_link']].append((c['link'], x, c, bnd))
    for g in grows:
        pass
    seen = set()
    for g in grows:
        if g['link'] in seen:
            continue
        seen.add(g['link'])
        agg = {}
        for cid, x, c, bnd in bylink.get(g['link'], []):
            e = agg.setdefault(cid, dict(c=c, x=x, lo=x['landing_to_server_end_m'], hi=x['landing_to_server_end_m'], bnd=bnd))
            e['lo'] = min(e['lo'], x['landing_to_server_end_m'])
            e['hi'] = max(e['hi'], x['landing_to_server_end_m'])
        cells, bnds = [], []
        for cid, e in sorted(agg.items(), key=lambda kv: (kv[1]['x']['landing_pos_m'], kv[0])):
            c, x = e['c'], e['x']
            rng = f1(e['lo']) if abs(e['hi'] - e['lo']) < 0.05 else '%s–%s' % (f1(e['lo']), f1(e['hi']))
            cells.append('%s(%s:%s @%s → %s @%s, %s m, %s대)' % (cid, c['connector_from']['link'], c['connector_from']['lane'],
                                                               f1(c['connector_from']['pos_m']), ','.join(map(str, x['on_lanes'])),
                                                               f1(x['landing_pos_m']), rng, f1(e['lo'] / SF)))
            bnds.append('%s: %s' % (cid, e['bnd']))
        t.append('| %s (%s) | %s | %s |' % (g['link'], g['sc'], ' · '.join(cells) or '–', ' · '.join(bnds) or '–'))
    tables['direct_feeders'] = '\n'.join(t)

    # boundaries: midblock / upstream stoplines on approach links
    t = ['| 접근 | 상류 머리 | 커넥터(착지 m) |', '|---|---|---|']
    for b in inv['approach_boundaries']:
        u = b['upstream_head']
        t.append('| %s | %s SC%s SG%s @%s m | %s (@%s) |' % (b['approach'], rk(u['role']), u['sc'], u['sg'], f1(u['pos_m']), b['connector'], f1(b['landing_pos_m'])))
    tables['approach_boundaries'] = '\n'.join(t)

    # feeders summary by depth / part
    cnt = defaultdict(int)
    for f in F:
        cnt[(f['part'], 'connector' if f['is_connector'] else 'link', min(f['min_depth'], 6))] += 1
    t = ['| 분할 | 종류 | 접근에서 깊이(1 = 바로 붙음, 6 = 6 이상) | 수 |', '|---|---|---|---:|']
    for k in sorted(cnt):
        t.append('| %s | %s | %s | %d |' % (k[0], k[1], k[2], cnt[k]))
    tables['feeder_counts'] = '\n'.join(t)

    # ---------------- meters
    M = inv['meters']
    t = ['| 미터 | 도로 | 커넥터(차로, 길이 m) | 갈림(링크:차로 @m) → 합류(링크 @m) | 머리 m | 머리 앞 저장 대/차로 (6 m / FZP) | 머리 뒤 m | 접근 구간(링크:차로, m) | 접근 저장 대/차로 (6 m / FZP) | 접근 시작~머리 m | 접근에 착지하는 공급 | plant 램프 대기 키(설정 최대 대) |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    morder = sorted(M.items(), key=lambda kv: (kv[1]['road'] != 'FW_E', kv[0]))
    for name, m in morder:
        a = m['approach_segment']
        ins = []
        for c in F:
            if c['is_connector']:
                for x in c['landings']:
                    if x['on_link'] == a['link'] and any(l in a['lanes'] for l in x['on_lanes']):
                        s = '%s(@%s, %s)' % (c['link'], f1(x['landing_pos_m']), ('FW ' + c['freeway_spill']['road']) if c['freeway_spill'] else c['connector_from']['link'])
                        if s not in ins:
                            ins.append(s)
        h = m['heads']
        t.append('| %s | %s | %s (%d, %s) | %s:%d @%s → %s @%s | %s | %s / %s | %s | %s:%s, %s–%s | %s / %s | %s | %s | %s |' % (
            name, m['road'], m['connector'], m['lanes'], f1(m['length_m']), m['from_link'], m['from_lane'], f1(m['diverge_pos_m']),
            m['merge_link'], f1(m['merge_pos_m']), '/'.join(f1(x['head_pos_m']) for x in h), f1(h[0]['prehead']['veh_per_lane_6m']),
            f1(h[0]['prehead']['veh_per_lane_fzp']), f1(h[0]['posthead']['len_m']), a['link'], ','.join(map(str, a['lanes'])), f1(a['from_m']), f1(a['to_m']),
            f1(a['storage']['veh_per_lane_6m']), f1(a['storage']['veh_per_lane_fzp']), f1(a['dist_from_start_to_meter_head_m']), ' · '.join(ins) or '–',
            ', '.join('%s(%s)' % (q['key'], f1(q['max_veh'])) for q in m.get('plant_ramp_queue', [])) or '–'))
    tables['meters'] = '\n'.join(t)

    # ---------------- spacing
    al = sp['all']
    t = ['| 묶음 | 쌍 수 | d 중앙 m | d 평균 m | d 5–95 % m | 간격(d − 앞차 길이) 중앙 m | 앞차 길이 평균 m | d > 15 m 몫 |', '|---|---:|---:|---:|---|---:|---:|---:|']

    def sprow(name, s):
        if not s.get('pairs'):
            return '| %s | 0 | – | – | – | – | – | – |' % name
        return '| %s | %d | %s | %s | %s–%s | %s | %s | %s |' % (name, s['pairs'], f1(s['d_pct']['0.5'], 2), f1(s['mean_d_m'], 2), f1(s['d_pct']['0.05'], 2),
                                                             f1(s['d_pct']['0.95'], 2), f1(s['gap_pct']['0.5'], 2), f1(s['mean_leader_len_m'], 2), f1(s['share_d_over_15m'], 3))
    t.append(sprow('전체', al))
    beh = {'1': '도시 주행 행태 1 (W74, ax 1.5 m)', '2': '행태 2 (W99, cc0 1.5 m)', '3': '고속도로 행태 3 (W99, cc0 1.5 m)'}
    for k, s in sp['by_link_behaviour'].items():
        t.append(sprow(beh.get(k, '행태 ' + k), s))
    for k, s in sp['by_leader_length'].items():
        t.append(sprow({'leader_len_lt_7m': '앞차 길이 < 7 m', 'leader_len_ge_7m': '앞차 길이 ≥ 7 m'}[k], s))
    tables['spacing'] = '\n'.join(t)
    t = ['| 링크 | 쌍 수 | d 중앙 m | d 평균 m | 간격 중앙 m |', '|---|---:|---:|---:|---:|']
    for k, s in sp['by_focus_link'].items():
        if s.get('pairs', 0) >= 50:
            t.append('| %s | %d | %s | %s | %s |' % (k, s['pairs'], f1(s['d_pct']['0.5'], 2), f1(s['mean_d_m'], 2), f1(s['gap_pct']['0.5'], 2)))
    tables['spacing_links'] = '\n'.join(t)
    vals['spacing_fzp'] = f1(SF, 2)
    vals['spacing_ratio'] = f1(SF / S6, 3)
    vals['spacing_pairs'] = '{:,}'.format(al['pairs'])

    # ---------------- occupancy (data after)
    O = {s['id']: s for s in occ['segments']}
    runs = occ['runs']
    RL = {'VA_s31': 'V-A v3c3-s31', 'VA_s41': 'V-A v3c3-s41', 'VA_s43': 'V-A v3c3-s43',
          'B_s31': 'B v3c3-s31', 'B_s41': 'B v3c3-s41', 'B_s43': 'B v3c3-s43'}
    runs = [r for r in ('VA_s31', 'VA_s41', 'VA_s43', 'B_s31', 'B_s41', 'B_s43') if r in runs]
    hdr = ' | '.join(RL[r] for r in runs)
    t1 = ['| 구간 | 길이 m | 용량 대 (6 m / 중앙 / 평균) | ' + hdr + ' |', '|---|---:|---|' + '---|' * len(runs)]
    t2 = ['| 구간 | ' + hdr + ' |', '|---|' + '---|' * len(runs)]
    for sid, lab in KEY_SEGMENTS:
        s = O.get(sid)
        if s is None:
            continue
        c1, c2 = [], []
        for r in runs:
            e = s['runs'][r]
            c1.append('%d · %s / %s / %s' % (e['max_veh'], f1(e.get('max_fill_6m'), 2), f1(e.get('max_fill_fzp_mean'), 2), f1(e.get('max_fill_len'), 2)))
            c2.append('%d/%d/%d/%d · %d' % (e.get('n_ge_1.0_6m', 0), e.get('n_ge_1.0_fzp', 0), e.get('n_ge_1.0_fzp_mean', 0),
                                            e.get('n_ge_1.0_len', 0), e.get('n_ge_0.9_6m', 0)))
        t1.append('| %s `%s` | %s | %s / %s / %s | %s |' % (lab, sid, f1(s['len_m']), f1(s['cap_veh']['6m']), f1(s['cap_veh']['fzp']),
                                                         f1(s['cap_veh']['fzp_mean']), ' | '.join(c1)))
        t2.append('| %s | %s |' % (lab, ' | '.join(c2)))
    tables['occ_key'] = '\n'.join(t1)
    tables['occ_key_counts'] = '\n'.join(t2)
    G = occ['groups']
    t = ['| 묶음(링크 단위) | 용량 대 (6 m / 중앙 / 평균) | ' + hdr + ' |', '|---|---|' + '---|' * len(runs)]
    for gid, lab in [('SC1001:127', '127 (SC1001 동쪽행, 3차로)'), ('SC1004:71', '71 (SC1004 서쪽 접근, 5차로)'), ('F:124', '124 (3차로)'),
                     ('F:121', '121 (4차로)'), ('F:126', '126 (2차로)'), ('F:129', '129 (3차로)'), ('F:70', '70 (2차로)'), ('F:31', '31 (3차로)'),
                     ('F:68', '68 (4차로)')]:
        g = G.get(gid)
        if g is None:
            continue
        cells = []
        for r in runs:
            e = g['runs'][r]
            cells.append('%d · %s / %s · ≥1.0: %d/%d/%d' % (e['max_veh'], f1(e.get('max_fill_6m'), 2), f1(e.get('max_fill_len'), 2),
                                                        e.get('n_ge_1.0_6m', 0), e.get('n_ge_1.0_fzp_mean', 0), e.get('n_ge_1.0_len', 0)))
        t.append('| %s | %s / %s / %s | %s |' % (lab, f1(g['cap_veh']['6m']), f1(g['cap_veh']['fzp']), f1(g['cap_veh']['fzp_mean']), ' | '.join(cells)))
    tables['occ_groups'] = '\n'.join(t)
    # decisions with any >= 1.0, by rule, excluding segments shorter than 2 vehicles (FZP median)
    raw = occ['raw_counts']
    rawu = occ['raw_used_m']
    ids = occ['segment_ids']
    segs = {s['id']: s for s in occ['segments']}
    capf = {i: segs[i]['cap_veh']['fzp'] for i in ids}
    lens = {i: segs[i]['len_m'] for i in ids}
    kind = {i: segs[i]['kind'] for i in ids}
    sp6, spm, spa = occ['spacings']['6m'], occ['spacings']['fzp'], occ['spacings']['fzp_mean']
    short = [s for s in occ['segments'] if s['cap_veh']['fzp'] is not None and s['cap_veh']['fzp'] < 2.0]
    vals['n_short_segments'] = len(short)
    vals['n_short_approach'] = sum(1 for s in short if s['kind'] == 'approach_lane')
    t = ['| 팔·시드 | 결정 수 | 머리 차로 (6 m / 중앙 / 평균 / 길이) | 공급 차로 (같은 순서) | 미터 머리 앞 (같은 순서) | 미터 접근 (같은 순서) |', '|---|---:|---|---|---|---|']
    dec_out = {}
    for r in runs:
        rows = raw[r]
        urows = {row[0]: row[1:] for row in rawu[r]}

        def n_any(kd):
            out = []
            for rule in ('6m', 'fzp', 'fzp_mean', 'len'):
                n = 0
                for row in rows:
                    T, c = row[0], row[1:]
                    u = urows[T]
                    hit = False
                    for j, i in enumerate(ids):
                        if kind[i] != kd or capf[i] is None or capf[i] < 2.0 or lens[i] <= 0:
                            continue
                        if rule == 'len':
                            f = u[j] / lens[i]
                        else:
                            f = c[j] / (lens[i] / {'6m': sp6, 'fzp': spm, 'fzp_mean': spa}[rule])
                        if f >= 1.0 - 1e-9:
                            hit = True
                            break
                    n += hit
                out.append(n)
            return out
        a, f_, m_, ma = n_any('approach_lane'), n_any('feeder_lane'), n_any('meter_prehead_lane'), n_any('meter_approach_lane')
        dec_out[r] = dict(decisions=len(rows), approach=a, feeder=f_, meter_prehead=m_, meter_approach=ma)
        t.append('| %s | %d | %s | %s | %s | %s |' % (RL[r], len(rows), '/'.join(map(str, a)), '/'.join(map(str, f_)), '/'.join(map(str, m_)), '/'.join(map(str, ma))))
    tables['occ_decisions'] = '\n'.join(t)
    # which segments (cap >= 2) reach >= 1.0 under the length rule, counts over 6 runs
    t = ['| 구간 | 종류 | 길이 m | ≥ 1.0 결정 수 6런 합 (6 m / 중앙 / 평균 / 길이) | 최대 점유 (길이) |', '|---|---|---:|---|---:|']
    rows_ = []
    for s in occ['segments']:
        if s['cap_veh']['fzp'] is None or s['cap_veh']['fzp'] < 2.0:
            continue
        tot = [sum(s['runs'][r].get('n_ge_1.0_' + k, 0) for r in runs) for k in ('6m', 'fzp', 'fzp_mean', 'len')]
        if any(tot):
            rows_.append((tot[3], tot, s))
    rows_.sort(key=lambda x: (-x[0], -x[1][2]))
    vals['n_long_hit_len'] = sum(1 for x in rows_ if x[1][3] > 0)
    vals['n_long_hit_6m'] = sum(1 for x in rows_ if x[1][0] > 0)
    for _, tot, s in rows_[:25]:
        t.append('| `%s` | %s | %s | %s | %s |' % (s['id'], s['kind'], f1(s['len_m']), '/'.join(map(str, tot)),
                                               f1(max(s['runs'][r].get('max_fill_len', 0) for r in runs), 2)))
    tables['occ_long_hits'] = '\n'.join(t)
    t = ['| 구간 | 길이 m | 용량 대 (중앙) | 6런 합 ≥ 1.0 결정 수 (중앙) |', '|---|---:|---:|---:|']
    for s in sorted(short, key=lambda s: -sum(s['runs'][r].get('n_ge_1.0_fzp', 0) for r in runs))[:15]:
        t.append('| `%s` | %s | %s | %d |' % (s['id'], f1(s['len_m']), f1(s['cap_veh']['fzp'], 2), sum(s['runs'][r].get('n_ge_1.0_fzp', 0) for r in runs)))
    tables['occ_short'] = '\n'.join(t)
    k127 = O['A:127:1:2']['runs']
    vals['b127_max'] = ' · '.join('%s %d대 (%s / %s / %s)' % (RL[r], k127[r]['max_veh'], f1(k127[r]['max_fill_6m'], 2), f1(k127[r]['max_fill_fzp_mean'], 2),
                                                              f1(k127[r]['max_fill_len'], 2)) for r in ('B_s31', 'B_s41', 'B_s43'))
    vals['gap_m'] = f1(occ['length_rule']['gap_m'], 2)
    vals['spacing_mean'] = f1(spa, 2)
    vals['spacing_mean_ratio'] = f1(sp6 / spa, 3)

    # ---------------- assemble json
    out = dict(schema='c1g-general-inventory/v1', created_kst=__import__('time').strftime('%Y-%m-%d %H:%M KST'),
               spacing_scan_lock_acquired_kst=sp.get('lock', {}).get('acquired_kst'),
               note='Inventory only. No thresholds, no verdicts. Occupancy numbers are exploratory (data after).',
               spacing=dict(codex_and_ours_m=S6, fzp_m=SF, fzp_mean_m=inv['spacing_fzp_mean'], fzp_summary={k: sp[k] for k in ('definition', 'frames', 'rows', 'all', 'by_link_behaviour',
                                                                                           'by_leader_length', 'by_focus_link', 'recommended_rule', 'fzp_name', 'fzp_sha256')}),
               signals=sig, approach_lane_groups=grows, approach_lanes=A,
               approach_link_lanes_without_head=inv['approach_link_lanes_without_head'],
               approach_boundaries=inv['approach_boundaries'], feeders=F, offramps=inv['offramps'], meters=M,
               plan_phase_order=inv['plan_phase_order'], plan_phase_signal_groups=inv['plan_phase_signal_groups'],
               plan_midblock_sgs=inv['plan_midblock_sgs'], never_green=inv['never_green'], fw_e=inv['fw_e'], fw_w=inv['fw_w'],
               occupancy_existing_states=dict(runs=runs, spacings=occ['spacings'], length_rule=occ['length_rule'], decisions_any_ge_1_cap_ge_2=dec_out,
                                              key_segments={sid: O[sid] for sid, _ in KEY_SEGMENTS if sid in O},
                                              groups={k: v for k, v in G.items()}, short_segments=[s['id'] for s in short],
                                              state_sha16=occ['state_sha16']),
               sources=dict(inv['sources'], spacing_json_sha256=sha(sp_p), occupancy_json_sha256=sha(occ_p), build_json_sha256=sha(b_p)))
    tmp = out_j + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g, ensure_ascii=False, indent=1, sort_keys=True, default=list)
    os.replace(tmp, out_j)
    vals['inventory_sha'] = sha(out_j)

    nar = open(nar_p, encoding='utf-8').read()
    for k, v in tables.items():
        nar = nar.replace('{{TABLE:%s}}' % k, v)
    for k, v in vals.items():
        nar = nar.replace('{{VAL:%s}}' % k, str(v))
    left = [x for x in ('{{TABLE:', '{{VAL:') if x in nar]
    if left:
        import re
        raise SystemExit('unfilled slots: ' + ', '.join(sorted(set(re.findall(r'\{\{(?:TABLE|VAL):[a-z_0-9]+\}\}', nar)))))
    tmp = out_m + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        g.write(nar)
    os.replace(tmp, out_m)
    print('json', vals['inventory_sha'])
    print('md', sha(out_m))


if __name__ == '__main__':
    main()
