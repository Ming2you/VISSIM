r"""VERIFY_N2: FW_E seg5 / seg10 space-mean speed per 300 s bin from v2_scan zone accumulators (fresh code).
Chain position = offset(link) + pos; offsets from the .inpx connector end points; connector length = max POS seen
in the FZP (approximation, < 1 m). Zone start = most upstream chain position of the zone's DSDs (seg5 DSD 51-58,
seg10 DSD 59-66, seg15 DSD 67-73 as listed in the stage-1 zone policy text of the reports)."""
import io
import json
import os
import xml.etree.ElementTree as ET

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
INPX = r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3nc\prepared\network\baseline_s41_v3c3nc.inpx'
CHAIN = ['74', '10699', '2', '10613', '119', '10702', '24']
ZONES = {'seg5': [51, 52, 53, 54, 55, 56, 57, 58], 'seg10': [59, 60, 61, 62, 63, 64, 65, 66], 'seg15': [67, 68, 69, 71, 72, 73]}


def main():
    root = ET.parse(INPX).getroot()
    ends = {}
    for lk in root.iter('link'):
        fe, te = lk.find('fromLinkEndPt'), lk.find('toLinkEndPt')
        if fe is not None and lk.get('no') in CHAIN:
            ends[lk.get('no')] = (fe.get('lane').split()[0], float(fe.get('pos')), te.get('lane').split()[0], float(te.get('pos')))
    meta = json.load(io.open(os.path.join(OUT, 'scan_nc_s41.json')))
    clen = meta['chain_maxpos']
    off = {'74': 0.0}
    for i in (1, 3, 5):
        c = CHAIN[i]
        f, fp, to, tp = ends[c]
        assert f == CHAIN[i - 1] and to == CHAIN[i + 1]
        off[c] = off[f] + fp
        off[to] = off[c] + clen[c] - tp
    dsd = {}
    for d in root.iter('desSpeedDecision'):
        dsd[int(d.get('no'))] = (d.get('lane').split()[0], float(d.get('pos')))
    zstart = {}
    for z, ids in ZONES.items():
        ps = [off[dsd[i][0]] + dsd[i][1] for i in ids if dsd[i][0] in off]
        zstart[z] = min(ps)
    res = {'offsets': off, 'zone_start_m': zstart, 'speeds': {}}
    for tag in ('nc_s31', 'r1_s31', 'rm_s31', 'va_s31', 'nc_s41', 'r1_s41', 'rm_s41', 'va_s41'):
        z = np.load(os.path.join(OUT, 'scan_%s.npz' % tag), allow_pickle=True)
        pos = np.array([off[l] for l in z['zone_link']]) + (z['zone_bucket'] + 0.5) * 10.0
        for zn, a, e in (('seg5', zstart['seg5'], zstart['seg10']), ('seg10', zstart['seg10'], zstart['seg15'])):
            m = (pos >= a) & (pos < e)
            sp = {}
            for b in range(3, 30):
                mb = m & (z['zone_bin'] == b)
                n = z['zone_n'][mb].sum()
                sp[b * 300] = round(float(z['zone_vsum'][mb].sum() / n), 1) if n else None
            res['speeds']['%s|%s' % (tag, zn)] = sp
    with io.open(os.path.join(OUT, 'v2_speed.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print(json.dumps({'offsets': off, 'zone_start_m': zstart}))
    for s in ('41', '31'):
        for zn in ('seg5', 'seg10'):
            print('s' + s, zn)
            for b in range(900, 9000, 300):
                print('  %5d ' % b + ' '.join('%6s' % res['speeds']['%s_s%s|%s' % (a, s, zn)][b] for a in ('nc', 'r1', 'rm', 'va')))


if __name__ == '__main__':
    main()
