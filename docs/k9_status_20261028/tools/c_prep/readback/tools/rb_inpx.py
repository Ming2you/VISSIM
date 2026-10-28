# -*- coding: utf-8 -*-
"""rb_inpx.py (c_port/readback, 2026-10-27 KST) - read-only inpx facts for the 8 ramp meters.

Usage: python -B rb_inpx.py <inpx> <out.json>
Writes only <out.json>. Per meter connector: polyline length, lane count, from/to link ends, signal heads of
SC 9101-9108 SG 1 (lane, pos, name), length after head and storage after head = (len - head) / 6.0 m
(N34 definition, N34_FLOWS.md:194). Also compares heads with the N34 HEAD table (n34_fzp_scan.py, inpx 3de889f0).
"""
import hashlib
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

METER_CONN = [10480, 10482, 10646, 10644, 10639, 10681, 10490, 10484]
N34_HEAD = {(10639, 1): 314.83469380887993, (10681, 1): 290.72003141146473, (10681, 2): 290.72003141146473,
            (10490, 1): 272.6035592816065, (10484, 1): 377.1107628548054, (10480, 1): 145.641195575947,
            (10482, 1): 374.11967822309003, (10482, 2): 374.2173333514973, (10646, 1): 304.45039540874615,
            (10644, 1): 814.7799217676458}
N34_STORAGE = {10490: 16.0, 10484: 27.5, 10681: 24.5, 10639: 15.6}  # N34_FLOWS.md:194 (vehicles)


def main():
    inpx, out = sys.argv[1], sys.argv[2]
    raw = open(inpx, 'rb').read()
    root = ET.fromstring(raw)
    links = {}
    for ln in root.iter('link'):
        no = int(ln.get('no'))
        pts = [(float(q.get('x')), float(q.get('y'))) for q in ln.iter('linkPolyPoint')]
        L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
        lanes_el = ln.find('lanes')
        nl = len(lanes_el.findall('lane')) if lanes_el is not None else None
        fr = ln.find('fromLinkEndPt')
        to = ln.find('toLinkEndPt')
        links[no] = {'poly_len': L, 'n_pts': len(pts), 'lanes': nl,
                     'from': fr.get('lane') if fr is not None else None, 'from_pos': float(fr.get('pos')) if fr is not None else None,
                     'to': to.get('lane') if to is not None else None, 'to_pos': float(to.get('pos')) if to is not None else None}
    heads = []
    for sh in root.iter('signalHead'):
        sg = sh.get('sg') or ''
        if not sg.startswith('910'):
            continue
        lane = sh.get('lane') or ''
        lk, li = lane.split()
        heads.append({'no': int(sh.get('no')), 'name': sh.get('name'), 'sc': int(sg.split()[0]), 'sg': int(sg.split()[1]),
                      'link': int(lk), 'lane': int(li), 'pos': float(sh.get('pos'))})
    meters = {}
    for c in METER_CONN:
        lk = links.get(c)
        hs = [h for h in heads if h['link'] == c]
        per_lane = {}
        for h in hs:
            after = lk['poly_len'] - h['pos']
            n34 = N34_HEAD.get((c, h['lane']))
            per_lane[str(h['lane'])] = {'head_pos': h['pos'], 'sc': h['sc'], 'sg': h['sg'], 'head_no': h['no'], 'name': h['name'],
                                        'after_head_m': after, 'storage_after_head_veh': after / 6.0,
                                        'n34_head_pos': n34, 'head_minus_n34': (h['pos'] - n34) if n34 is not None else None}
        meters[str(c)] = {'poly_len': lk['poly_len'], 'n_pts': lk['n_pts'], 'lanes': lk['lanes'], 'from': lk['from'],
                          'from_pos': lk['from_pos'], 'to': lk['to'], 'to_pos': lk['to_pos'], 'heads': per_lane,
                          'n34_storage_veh': N34_STORAGE.get(c)}
    res = {'tool': 'rb_inpx.py', 'inpx': inpx, 'sha256': hashlib.sha256(raw).hexdigest(), 'meters': meters,
           'heads_9101_9108': heads}
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g, indent=1)
    os.replace(tmp, out)
    for c, m in meters.items():
        print(c, 'len %.2f lanes %s' % (m['poly_len'], m['lanes']),
              {k: ('sc%d head %.3f after %.1f stor %.1f d34 %s' % (v['sc'], v['head_pos'], v['after_head_m'], v['storage_after_head_veh'],
                                                                 None if v['head_minus_n34'] is None else round(v['head_minus_n34'], 6)))
               for k, v in m['heads'].items()}, 'n34_stor', m['n34_storage_veh'])


if __name__ == '__main__':
    main()
