r"""VERIFY_N2: build markdown tables from MY v2_metrics.json and compare with the authors' published numbers
(r2c_n/out/r2c_metrics.json is read only as the comparison target; none of its code is used)."""
import io
import json
import os

VN2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mine = json.load(io.open(os.path.join(VN2, 'out', 'v2_metrics.json'), encoding='utf-8'))['diffs']
theirs = json.load(io.open(os.path.join(os.path.dirname(VN2), 'out', 'r2c_metrics.json'), encoding='utf-8'))['pairs']
ROWS = [('M1', 'M1', '**① FW_E 본선 7링크 (주 지표)**'), ('MB', 'meterbound_FWE', 'FW_E 미터 대기 4개 합'),
        ('MB_10681', 'meterbound:RM_C10681', '└ RM_C10681 미터 대기'), ('ONR', 'onramp_FWE', 'FW_E 진입 램프 구역 4개 합'),
        ('M2', 'M2', '② 동측 국소 19링크'), ('FWW', 'fw_w_main', 'FW_W 본선 3링크'),
        ('UN_1099', 'unins_1099', '입력 1099 미삽입'), ('UN_1098', 'unins_1098', '입력 1098 미삽입'),
        ('OM', 'M3', '③ Ω635'), ('M4', 'M4', '**④ 전체 + 미삽입**'), ('OUTa', 'OUT_a', '**Ω 밖 (a) = ④ − ③**')]
PAIRS = [('r1', 'R1-NC3'), ('rm', 'RM-NC3'), ('va', 'VA-NC3')]
WIN = [('late_6300_8100', 'late_6300_8100', '늦은 창 6,300–8,100 s'), ('early_2700_4500', 'early_2700_4500', '이른 창 2,700–4,500 s'),
       ('full_900_9000', 'whole_900_9000', '전체 900–9,000 s')]
out = []
maxdiff = {}
for wm, wt, title in WIN:
    out.append('\n#### %s — 내 재계산 (괄호 = 내 값 − 보고 값)\n' % title)
    out.append('| 줄 (veh·h, 같은 시드 NC3 대비) | s31 R1 | s31 RM 팔 | s31 V-A | s41 R1 | s41 RM 팔 | s41 V-A |')
    out.append('|---|---:|---:|---:|---:|---:|---:|')
    for km, kt, label in ROWS:
        cells = []
        for s in ('31', '41'):
            for a, p in PAIRS:
                v = mine['%s-nc|s%s|%s|%s' % (a, s, wm, km)]
                t = theirs[p]['windows'][s][kt][wt]
                d = v - t
                key = (km, a)
                maxdiff[key] = max(maxdiff.get(key, 0.0), abs(d))
                cells.append('%+.1f (%+.1f)' % (v, d))
        out.append('| %s | %s |' % (label, ' | '.join(cells)))
md = '\n'.join(out)
summary = {'%s|%s' % k: round(v, 3) for k, v in sorted(maxdiff.items())}
with io.open(os.path.join(VN2, 'out', 'v2_compare.md'), 'w', encoding='utf-8') as f:
    f.write(md + '\n')
with io.open(os.path.join(VN2, 'out', 'v2_compare_maxdiff.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=1)
print(md)
print(json.dumps(summary))
