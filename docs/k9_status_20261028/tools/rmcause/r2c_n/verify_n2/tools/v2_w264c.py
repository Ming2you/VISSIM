import json
G = json.load(open(r'D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json', encoding='utf-8'))
fe = {c['cell']: c for c in G['cells'] if c['road'] == 'FW_E'}
for T in (1500, 1650, 1800, 1950):
    c = json.load(open(r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/obs150/vsl_cohorts_%06d.json' % T, encoding='utf-8'))
    co = c['cohorts']['FW_E']
    n = [sum(x.values()) for x in co]
    lk = fe[22]['lane_km'] + fe[23]['lane_km']
    tags = sorted(set(k for x in co for k in x))
    tag90 = [i for i, x in enumerate(co) if any(k.startswith('90') and v > 0 for k, v in x.items())]
    print(T, len(co), round((n[22] + n[23]) / lk, 1), round(fe[22]['start_m']), round(fe[23]['end_m']), tags, tag90[:3], tag90[-1:] if tag90 else None)
