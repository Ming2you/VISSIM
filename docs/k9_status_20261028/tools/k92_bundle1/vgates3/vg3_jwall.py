"""VerifyGates 2 — J job wall-clock pairs recomputed (amendment 24 :328, amendment 30 section 8: threshold 1.0158).
Pairs = the 11 SAF H3 OBS jobs of J-a (TL3 v3c3-s31 GRID9 + TL3m s43 / s47 900): A = OUTK/ja (SAF-K91), B = OUTK/jb
(SAF-K92b1), same label.  Clean pair = the four counts of both vissim_counts.json are known and 0.  Ratio = summary
wall_sec B / A.  PASS iff the median of the clean ratios <= 1.05 / 1.033718118959995; no clean pair -> INCOMPLETE;
IQR (inclusive quartiles) reported only.  Then vs OUTK/judge/jwall.json.  Output OUTV/jwall.json."""
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

LABELS = ['TL3_%d_SAF_OBS_H3' % T for T in V.GRID9] + ['TL3_900_s43_SAF_OBS_H3', 'TL3_900_s47_SAF_OBS_H3']


def main():
    rows = []
    for lab in LABELS:
        a = V.OUTK / 'ja' / 'sa' / 'jobs' / V.LABEL / lab
        b = V.OUTK / 'jb' / 'sa' / 'jobs' / V.LABEL / lab
        sa_, sb = V.rjson(a / 'summary.json') or {}, V.rjson(b / 'summary.json') or {}
        va, vb = V.rjson(a / 'vissim_counts.json') or {}, V.rjson(b / 'vissim_counts.json') or {}
        counts = [va.get('vissim_count_pre'), va.get('vissim_count_post'), vb.get('vissim_count_pre'),
                  vb.get('vissim_count_post')]
        clean = all(isinstance(x, int) and not isinstance(x, bool) and x == 0 for x in counts)
        wa, wb = sa_.get('wall_sec'), sb.get('wall_sec')
        ratio = (wb / wa) if (V.is_num(wa) and V.is_num(wb) and wa > 0) else None
        order = (V.is_num(va.get('end')) and V.is_num(vb.get('start')) and va['end'] <= vb['start'])
        rows.append({'label': lab, 'clean': clean, 'ratio': ratio, 'ok': [sa_.get('ok'), sb.get('ok')],
                     'order_A_then_B': order})
    ratios = [r['ratio'] for r in rows if r['clean'] and r['ratio'] is not None]
    if not ratios:
        verdict, med, iqr = 'INCOMPLETE', None, None
    else:
        med = statistics.median(ratios)
        q = statistics.quantiles(ratios, n=4, method='inclusive') if len(ratios) > 1 else [ratios[0]] * 3
        iqr = q[2] - q[0]
        verdict = 'PASS' if med <= V.WALL_LIMIT else 'FAIL'
    rec = V.rjson(V.OUTK / 'judge' / 'jwall.json') or {}
    rr = {r.get('label'): r for r in rec.get('rows') or []}
    ratio_mism = [r['label'] for r in rows if r['ratio'] is not None and (
        rr.get(r['label'], {}).get('ratio') is None or abs(rr[r['label']]['ratio'] - r['ratio']) > 1e-12)]
    clean_mism = [r['label'] for r in rows if rr.get(r['label'], {}).get('clean') != r['clean']]
    out = {'schema': 'vg3-jwall/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)), 'verdict': verdict,
           'limit': V.WALL_LIMIT, 'n_pairs': len(rows), 'n_clean': len(ratios), 'median': med,
           'iqr_inclusive_report_only': iqr, 'all_ok_true': all(r['ok'] == [True, True] for r in rows),
           'all_order_A_then_B': all(r['order_A_then_B'] for r in rows), 'rows': rows,
           'recorded': {'sha256': V.sha_file(V.OUTK / 'judge' / 'jwall.json'), 'verdict': rec.get('verdict'),
                        'median': rec.get('median'), 'n_clean': rec.get('n_clean'), 'limit': rec.get('limit')},
           'ratio_mismatch': ratio_mism, 'clean_mismatch': clean_mism}
    out['agree_all'] = (rec.get('verdict') == verdict and not ratio_mism and not clean_mism
                        and rec.get('n_clean') == len(ratios) and rec.get('median') is not None and med is not None
                        and abs(rec['median'] - med) <= 1e-12 and rec.get('limit') == V.WALL_LIMIT)
    V.wjson(V.OUTV / 'jwall.json', out)
    print('VG3_JWALL verdict=%s clean=%d/%d median=%s iqr=%s agree=%s' % (verdict, len(ratios), len(rows), med, iqr,
                                                                       out['agree_all']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
