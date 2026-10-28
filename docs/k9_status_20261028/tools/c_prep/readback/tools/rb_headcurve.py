# -*- coding: utf-8 -*-
"""rb_headcurve.py (c_port/readback, 2026-10-27 KST) - RB_RULE_ADD1: add the codex head-service-curve column to the K7 lane table.

Usage: python -B rb_headcurve.py <discharge.json> <config_json> <out.json>
Reads only; writes <out.json>. curve value per lane = 360 * physical_ramp_head_service_veh_per_cycle[RM_C<meter>][g] / lanes.
"""
import hashlib
import json
import os
import sys


def main():
    dp, cp, out = sys.argv[1], sys.argv[2], sys.argv[3]
    d = json.load(open(dp, encoding='utf-8'))
    raw = open(cp, 'rb').read()
    cfg = json.loads(raw)
    curve = cfg['physical_ramp_head_service_veh_per_cycle'] if 'physical_ramp_head_service_veh_per_cycle' in cfg else None
    if curve is None:
        # nested search (key position not assumed)
        def find(o):
            if isinstance(o, dict):
                if 'physical_ramp_head_service_veh_per_cycle' in o:
                    return o['physical_ramp_head_service_veh_per_cycle']
                for v in o.values():
                    r = find(v)
                    if r is not None:
                        return r
            return None
        curve = find(cfg)
    lanes_cfg = cfg['actuation']['real_world_ramp_metering'].get('meter_lanes', {})
    res = {'tool': 'rb_headcurve.py', 'discharge': [dp, hashlib.sha256(open(dp, 'rb').read()).hexdigest()],
           'config': [cp, hashlib.sha256(raw).hexdigest()], 'curve': curve, 'groups': {}}
    for grp, gd in d['groups'].items():
        rows = []
        for t in gd['lane_table']:
            key = 'RM_C' + t['meter']
            nl = int(lanes_cfg.get(key, 1))
            cv = curve.get(key, {}).get(str(t['g'])) if curve else None
            cl = (360.0 * float(cv) / nl) if cv is not None else None
            rows.append({'meter': t['meter'], 'lane': t['lane'], 'g': t['g'], 'primary': t['primary'],
                         'primary_median': t['primary_median'], 'model_table_vph_lane': t['model_table_vph_lane'],
                         'head_curve_vph_lane': cl,
                         'ratio_head_curve': (t['primary_median'] / cl) if (cl and t['primary_median'] is not None) else None})
        res['groups'][grp] = rows
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(res, g, indent=1)
    os.replace(out + '.tmp', out)
    for grp, rows in res['groups'].items():
        for r in rows:
            if r['primary']:
                print(grp, r['meter'], r['lane'], 'g%d' % r['g'], 'P', r['primary'], 'med', r['primary_median'], 'tbl', r['model_table_vph_lane'],
                      'curve', r['head_curve_vph_lane'], 'r', None if r['ratio_head_curve'] is None else round(r['ratio_head_curve'], 3))


if __name__ == '__main__':
    main()
