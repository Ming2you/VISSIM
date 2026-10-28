# -*- coding: utf-8 -*-
"""gd_usg.py (guard/general DATA, 2026-10-27 KST) — read-only: codex USG (urban storage guard) records in B decisions.

Usage: python -B gd_usg.py <out.json>
Reads only the PREFIX of each B decision file action_<T>.json (T = 900..9000 step 150, v3c3-s31/s41/s43) until the
object /metadata/joint_leader_selection/urban_storage_guard decodes (it sits ~0.4 MB into an ~80 MB file).
Keeps per decision: observed_sec, nonzero signal phase weights, all 210 lane observations (vehicles, capacity, fill,
crowded, all_receivers_full, pressure; receivers only where crowded or all full), block receipts (signal, status,
required/attainable). Light job (about 1 MB per file); no lock needed. Writes only <out.json>.
"""
import hashlib
import json
import os
import sys

B = {'s31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31',
     's41': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/decisions_sdmpc31_sdmpc9000_s41',
     's43': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/decisions_sdmpc31_sdmpc9000_s43'}
KEY = b'"urban_storage_guard": {'


def read_usg(fp):
    n = 1 << 20
    with open(fp, 'rb') as g:
        buf = b''
        while True:
            chunk = g.read(n)
            if not chunk:
                return None, len(buf)
            buf += chunk
            j = buf.find(b'"joint_leader_selection"')
            if j < 0:
                continue
            i = buf.find(KEY, j)
            if i < 0:
                continue
            try:
                s = buf[i + len(KEY) - 1:].decode('utf-8')
            except UnicodeDecodeError as e:
                s = buf[i + len(KEY) - 1:i + len(KEY) - 1 + e.start].decode('utf-8')
            try:
                u, _ = json.JSONDecoder().raw_decode(s)
                return u, len(buf)
            except json.JSONDecodeError:
                continue


def main():
    out = sys.argv[1]
    res = {}
    shas = {}
    for seed, d in B.items():
        rows = []
        for T in range(900, 9001, 150):
            fp = '%s/action_%06d.json' % (d, T)
            if not os.path.exists(fp):
                rows.append(dict(T=T, missing_file=True))
                continue
            u, nread = read_usg(fp)
            if u is None:
                rows.append(dict(T=T, missing_usg=True))
                continue
            o = u['observation']
            lanes = []
            for l in o['lanes']:
                e = dict(signal=l['signal'], phase=l['phase'], link=str(l['link']), lane=int(l['lane']), head=l['head_id'],
                         veh=l['vehicles'], cap=l['capacity_veh'], fill=l['fill_fraction'], crowded=l['crowded'],
                         all_full=l['all_receivers_full'], known=l['receiver_known'], pressure=l['pressure'])
                if l['crowded'] or l['all_receivers_full']:
                    e['receivers'] = [dict(connector=r['connector'], link=str(r['link']), lane=int(r['lane']), position=r['position'],
                                           veh=r['vehicles'], cap=r['capacity_veh'], fill=r['fill_fraction']) for r in l['receivers']]
                lanes.append(e)
            blocks = []
            for blk in u['blocks']:
                for r in (blk if isinstance(blk, list) else [blk]):
                    if isinstance(r, dict):
                        blocks.append(dict(signal=r.get('signal'), status=r.get('status'), required=r.get('required_pressure_sec'),
                                           attainable=r.get('attainable_pressure_sec')))
            sig = {s: {p: v for p, v in w.items() if v != 0} for s, w in o['signals'].items()}
            sig = {s: w for s, w in sig.items() if w}
            rows.append(dict(T=T, observed_sec=o['observed_sec'], policy=o['policy'], signals_nonzero=sig, lanes=lanes,
                             n_blocks=len(u['blocks']), receipts=blocks, prefix_bytes=nread))
        res[seed] = rows
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(dict(tool='gd_usg.py', tool_sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest(), runs=res), g,
                  ensure_ascii=False, sort_keys=True)
    os.replace(out + '.tmp', out)
    print(hashlib.sha256(open(out, 'rb').read()).hexdigest())
    for seed, rows in res.items():
        fired = [r['T'] for r in rows if r.get('signals_nonzero')]
        print(seed, len(rows), 'fired decisions', len(fired), fired[:10])


if __name__ == '__main__':
    main()
