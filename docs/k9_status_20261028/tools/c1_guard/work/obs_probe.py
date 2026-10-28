"""Read-only: decision-time observables for 10491 / 129 lane 1 / 26 lane 1 in existing state JSONs (V-A, B)."""
import json, sys, hashlib
RUNS = {
    'VA': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_{s}/decisions_sdmpc31_v3c3_k92va_{s}',
    'B': 'D:/VISSIM_runs/20261026_codex_b_v3c3/{s}/sdmpc/decisions_sdmpc31_sdmpc9000_{s}',
}
TS = (1800, 2100, 2400, 2700, 3000, 3300)
out = {}
for arm, pat in RUNS.items():
    for s in ('s31', 's41', 's43'):
        for T in TS:
            p = pat.format(s=s) + '/state_%06d.json' % T
            d = json.load(open(p, encoding='utf-8'))
            recs = d['vehicle_records']['records']
            def cnt(link, lane=None, lo=None, hi=None):
                rows = [r for r in recs if str(r['link_no']) == link and (lane is None or r['lane_no'] == lane)
                        and (lo is None or r['position_m'] >= lo) and (hi is None or r['position_m'] <= hi)]
                return [len(rows), sum(1 for r in rows if r['stopped'])]
            lo_ = d['local_observation']
            qc = (lo_.get('queue_counters') or {}).get('counters', {})
            det = d['obs150']['detectors']
            out[f'{arm}|{s}|{T}'] = dict(
                c10491=cnt('10491'),
                l129_lane1=cnt('129', 1), l129_lane1_from_landing=cnt('129', 1, 239.38),
                l26_lane1_3200_3700=cnt('26', 1, 3200, 3700), l26_lane1_all=cnt('26', 1),
                qc_127_2012=qc.get('2012'), qc_129_200122=qc.get('200122'),
                qc_26_200141=qc.get('200141'), qc_26_200142=qc.get('200142'),
                tail_m={k: lo_['link_queue_tail_pos_m'].get(k) for k in ('127', '129', '10491', '26')},
                src_FW_W_150s=sum(det.get(k, 0) for k in ('960282', '960283', '960284')),
                off_entry_10491_150s=det.get('960225'))
p = sys.argv[1]
open(p, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
print(hashlib.sha256(open(p, 'rb').read()).hexdigest())
for k, v in out.items():
    print(k, 'c10491', v['c10491'], '129L1', v['l129_lane1'], '129L1>=239', v['l129_lane1_from_landing'],
          '26L1[3200,3700]', v['l26_lane1_3200_3700'], 'QC2012', v['qc_127_2012'], 'QC200122', v['qc_129_200122'],
          'QC200141', v['qc_26_200141'], 'QC200142', v['qc_26_200142'], 'src150', v['src_FW_W_150s'], 'off10491', v['off_entry_10491_150s'])
