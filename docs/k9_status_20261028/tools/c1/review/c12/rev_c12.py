# -*- coding: utf-8 -*-
"""rev_c12.py (K8 amendment C1-2 ReviewDeclare, 2026-10-27 KST) - read-only checks behind the review's [실행] claims.

Usage: python -B rev_c12.py <out_json>
Reads only: the v3c3 network (.inpx of the V-A v3c3-s31 run), inventory.json, segments.json, the B0 Omega701
membership (probe tree), the codex handoff copy (membership exact, reporting partition), three T=900 state files and
their lane frames (format, sha256, time, vehicle-id sets only; no values), the V-A v3c3-s31 run action CSV (VSL rows),
the Declare and review rule files, and the amendment texts. Writes only <out_json> (exclusive create).
No VISSIM, no COM, no replay, no plant, no lock (light reads, seconds).
"""
import collections
import csv
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
C1D = SP + '/c_port/c1'
GG = C1D + '/guard/general'
INPX = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/network/sdmpc31_sdmpc31_v3c3_k92va_s31.inpx'
SEG = 'D:/VISSIM-merge/k8_gate_trees/c1/guard_general/data/segments.json'
B0M = 'D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_5cdc6eb1/diagnostics/b0_v3c3/omega701/membership.json'
HOM = 'D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json'
HOP = 'D:/VISSIM_handoff/20261024/derived/reporting_partition.json'
STATES = {
    'va_s31_T900': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/state_000900.json',
    'b_s31_T900': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31/state_000900.json',
    'robs_s31_T900': 'D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31/decisions_sdmpc31_v3c3_nc_s31/state_000900.json',
}
B_ACTION = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31/action_000900.json'
VA_RUN_CSV = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/action_sdmpc31_v3c3_k92va_s31.csv'
MA = {'124': ([1], '10480'), '32': ([1, 2], '10482'), '31': ([1], '10484'), '129': ([1], '10490'),
      '70': ([1], '10639'), '69': ([1], '10644'), '121': ([1], '10646'), '68': ([1, 2], '10681')}
FWE7 = ['74', '10699', '2', '10613', '119', '10702', '24']
FWW3 = ['26', '10771', '120']


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def jload(path):
    return json.loads(open(path, 'rb').read().decode('utf-8-sig'))


def main():
    out = sys.argv[1]
    res = {'schema': 'c12-review/v1', 'inputs': {}}
    for k, p in [('inpx', INPX), ('segments', SEG), ('inventory', GG + '/inventory.json'), ('b0_membership', B0M),
                 ('ho_membership_exact', HOM), ('ho_partition', HOP), ('va_run_csv', VA_RUN_CSV),
                 ('b_action_900', B_ACTION)]:
        res['inputs'][k] = sha(p)
    inv = jload(GG + '/inventory.json')
    seg = [s for s in jload(SEG)['segments'] if s['kind'] != 'special']
    # 1. receivers: exact spans vs existing segments
    by = collections.defaultdict(list)
    for s in seg:
        by[(str(s['link']), int(s['lane']))].append(s)
    spans, entries, exact_entries = [], 0, 0
    for a in [x for x in inv['approach_lanes'] if x['phases']]:
        for r in a['receivers']:
            entries += 1
            k = (str(r['link']), int(r['lane']))
            lo, hi = r['landing_pos_m'], r['segment_end_m']
            if any(abs(s['from_m'] - lo) <= 1e-6 and abs(s['to_m'] - hi) <= 1e-6 for s in by[k]):
                exact_entries += 1
            if not any(sp[0] == k and abs(sp[1] - lo) <= 1e-6 and abs(sp[2] - hi) <= 1e-6 for sp in spans):
                spans.append((k, lo, hi))
    near = sum(1 for sp in spans if any(abs(s['from_m'] - sp[1]) <= 0.01 and abs(s['to_m'] - sp[2]) <= 0.01
                                        for s in by[sp[0]]))
    coll = {}
    for d in (1, 3):
        c = collections.Counter('R:%s:%s:%.*f' % (sp[0][0], sp[0][1], d, sp[1]) for sp in spans)
        coll[str(d)] = sorted(k for k, v in c.items() if v > 1)
    res['receivers'] = dict(entries=entries, unique_spans=len(spans), entries_with_exact_existing_segment=exact_entries,
                            unique_spans_within_1cm_of_existing=near, id_collisions_by_decimals=coll,
                            short_spans=sum(1 for sp in spans if (sp[2] - sp[1]) / 6.0 < 2.0),
                            evidence_segments_if_exact=1141 + len(spans))
    # 2. meter approach lanes: cut points and the cell ending at the meter connector departure; M cell length
    root = ET.parse(INPX).getroot()
    links = {x.get('no'): x for x in root.findall('./links/link')}
    cuts = collections.defaultdict(list)
    for c, node in links.items():
        s, e = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if s is None or e is None:
            continue
        src, first = s.get('lane').split()
        tgt, land = e.get('lane').split()
        for i in range(len(node.findall('./lanes/lane'))):
            if src in MA and int(first) + i in MA[src][0]:
                cuts[(src, int(first) + i)].append(('dep', c, float(s.get('pos'))))
            if tgt in MA and int(land) + i in MA[tgt][0]:
                cuts[(tgt, int(land) + i)].append(('land', c, float(e.get('pos'))))
    for h in root.findall('./signalHeads/signalHead'):
        l, ln = h.get('lane').split()
        if l in MA and int(ln) in MA[l][0]:
            cuts[(l, int(ln))].append(('head', h.get('no'), float(h.get('pos'))))
    ma = {}
    for (l, ln), pts in sorted(cuts.items()):
        conn = MA[l][1]
        dep = [p for p in pts if p[0] == 'dep' and p[1] == conn][0][2]
        lower = max([0.0] + [p[2] for p in pts if p[2] < dep - 1e-9])
        ma['%s:%s' % (l, ln)] = dict(meter_connector=conn, departure_m=round(dep, 4), cell=[round(lower, 4), round(dep, 4)],
                                     cell_len_m=round(dep - lower, 3), cell_short=(dep - lower) / 6.0 < 2.0,
                                     cuts=sorted([[p[0], p[1], round(p[2], 4)] for p in pts], key=lambda x: x[2]))
    mcell = {s['id']: dict(len_m=round(s['to_m'] - s['from_m'], 3), short=(s['to_m'] - s['from_m']) / 6.0 < 2.0)
             for s in seg if s['kind'] == 'meter_prehead_lane'}
    landings_on_meter_connectors = []
    meter_conns = {v[1] for v in MA.values()}
    for c, node in links.items():
        e = node.find('toLinkEndPt')
        if e is not None and e.get('lane').split()[0] in meter_conns:
            landings_on_meter_connectors.append(c)
    res['meter_paths'] = dict(ma_last_cells=ma, m_cells=mcell, connectors_landing_on_meter_connectors=landings_on_meter_connectors,
                              any_short_ma_last_cell=any(v['cell_short'] for v in ma.values()),
                              any_short_m_cell=any(v['short'] for v in mcell.values()))
    # 3. partition sets (v3c3)
    b0, ho, part = jload(B0M), jload(HOM), jload(HOP)
    ia, ib = set(map(str, b0['inside_links'])), set(map(str, ho['inside_links']))
    res['partition'] = dict(b0_inside=len(ia), ho_inside=len(ib), equal=ia == ib,
                            offramps_inside=[o for o in part['offramp_links'] if o in ia],
                            offramps_outside=[o for o in part['offramp_links'] if o not in ia],
                            onramps_inside={o: r for o, r in part['onramp_roads'].items() if o in ia},
                            fwe7_inside=all(x in ia for x in FWE7), fww3_inside=all(x in ia for x in FWW3))
    # 4. frames: location, encoding, sha, time, id sets (no values)
    fr = {}
    for name, p in STATES.items():
        st = jload(p)
        obs = st['obs150']
        cur = obs['frames']['current']
        fp = obs['directory'].replace('\\', '/') + '/' + cur['path']
        raw = open(fp, 'rb').read()
        text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
        f = json.loads(text)
        ids = {v['veh_no'] for v in st['vehicle_records']['records']}
        fr[name] = dict(state_sim_sec=st['sim_sec'], obs_sim_sec=obs['sim_sec'], relative_path_form=cur['path'].startswith('lane_observations/'),
                        bom=raw[:2].hex(), sha_match=hashlib.sha256(raw).hexdigest() == cur['sha256'], schema=f['schema'],
                        complete=f['complete'], time_s=f['time_s'], row_width=sorted({len(r) for r in f['vehicles']}),
                        records_complete=st['vehicle_records']['complete'], id_sets_equal=ids == {r[0] for r in f['vehicles']})
    res['frames'] = fr
    # 5. codex head ids vs inventory head numbers (P0-17 c key)
    L = jload(B_ACTION)['metadata']['joint_leader_selection']['urban_storage_guard']['observation']['lanes']
    hid = {(str(l['link']), int(l['lane']), str(l['head_id'])) for l in L}
    ours = {(str(x['link']), int(x['lane']), str(x['head_no'])) for x in inv['approach_lanes']
            if x['phases'] and x['codex_usg'].get('included')}
    res['codex_head_key'] = dict(codex=len(hid), inventory_included=len(ours), equal=hid == ours)
    # 6. RF10 rule on the V-A v3c3-s31 run CSV (fwe_r3.py vsl_decisions form) vs the per-decision-CSV form
    t_fwe, t_any, dsd, ids = set(), set(), set(), collections.Counter()
    with open(VA_RUN_CSV, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            if r['kind'] != 'vsl':
                continue
            ids[r['id'][:8]] += 1
            if float(r['speed_kph']) < 110:
                t_any.add(int(float(r['sim_sec'])))
                if r['id'].startswith('RW_FW_E'):
                    t_fwe.add(int(float(r['sim_sec'])))
                    dsd.add(int(r['dsd_no']))
    res['rf10_va_s31'] = dict(fwe_lt110_decisions=len(t_fwe), first=min(t_fwe), last=max(t_fwe), any_lt110=len(t_any),
                             dsd=sorted(dsd), vsl_row_id_prefixes=dict(ids))
    # 7. rule file differences (Declare -> review)
    old = jload(C1D + '/work/c12_superseded/c1g_guard_rule_cebd6f05.json')
    new = jload(C1D + '/declared_c1_2/c1g_guard_rule.json')
    diff = []

    def walk(a, b, p):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                if k not in a or k not in b:
                    diff.append(p + '/' + k)
                else:
                    walk(a[k], b[k], p + '/' + k)
        elif a != b:
            diff.append(p)
    walk(old, new, '')
    res['rule_diff'] = dict(old_sha256=sha(C1D + '/work/c12_superseded/c1g_guard_rule_cebd6f05.json'),
                            new_sha256=sha(C1D + '/declared_c1_2/c1g_guard_rule.json'), changed_paths=diff)
    # 8. verbatim quote boxes of the Declare text (line-level)
    A = open(SP + '/K8_PREDECLARATION_AMENDMENT_C1_2_r1.md', encoding='utf-8').read().split('\n')
    def rd(p):
        return open(p, 'rb').read().decode('utf-8').replace('\r\n', '\n').split('\n')
    GD = rd(C1D + '/guard/GUARD_DESIGN_DRAFT.md')
    GGD = rd(GG + '/GENERAL_GUARD_DESIGN.md')
    FD = rd(SP + '/fwe_decomp/FWE_DECOMP.md')
    q = [(l[2:] if l.startswith('> ') else l[1:]) for l in A[127:200]]
    res['quotes'] = dict(d98_lines=len(q), d98_diff_lines=[370 + i for i, (x, y) in enumerate(zip(q, GD[369:442])) if x != y],
                         thread_equal=A[216] == GGD[657], fwe_equal=A[601] == FD[259])
    raw = json.dumps(res, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with open(out, 'x', encoding='utf-8', newline='\n') as fh:
        fh.write(raw)
    print(hashlib.sha256(raw.encode('utf-8')).hexdigest())


if __name__ == '__main__':
    main()
