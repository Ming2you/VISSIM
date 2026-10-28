# vhr_tables.py - cell-by-cell transcription check of HANDOFF_RESULTS tables against OMEGA701_V3C3 / RAW_CHECK, and the % table.
import json, re

B = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff'
HR = open(f'{B}/HANDOFF_RESULTS.md', encoding='utf-8').read().splitlines()
OM = open(f'{B}/OMEGA701_V3C3.md', encoding='utf-8').read().splitlines()
RW = open(f'{B}/RAW_CHECK.md', encoding='utf-8').read().splitlines()


def num(s):
    s = s.replace('−', '-').replace('+', '').replace(',', '').strip()
    m = re.match(r'^[≈ ]*(-?\d+(?:\.\d+)?)', s)
    return float(m.group(1)) if m else None


def table(lines, start, stop):
    rows = {}
    for i in range(start - 1, stop):
        l = lines[i]
        if not l.startswith('|') or l.startswith('|---'):
            continue
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        rows[cells[0]] = (i + 1, cells[1:])
    return rows


def key(lbl):
    l = lbl
    for a, b in [('(우리 목적 영역, 635링크)', ''), ('(codex 목적 영역, 701링크)', ''), ('Ω701 − Ω635 (더한 66링크)', 'Ω701 − Ω635'),
                 ('④a 전체 링크', '④a'), ('④b 미삽입 (U9, NC3 앵커)', '④b'), ('④b 미삽입', '④b'), ('④ = ④a + ④b', '④'),
                 ('Ω 밖 (a) ④ − Ω635', 'Ω 밖 (a) Ω635 기준'), ('Ω 밖 (b) ④a − Ω635', 'Ω 밖 (b) Ω635 기준'),
                 ('Ω 밖 (a) ④ − Ω701', 'Ω 밖 (a) Ω701 기준'), ('Ω 밖 (b) ④a − Ω701', 'Ω 밖 (b) Ω701 기준'),
                 ('① FW_E 본선 7링크', '①'), ('② 국소 19링크', '②'), ('도시도로 (codex 분할)', '도시도로'),
                 ('④b 중 입력 1098 (FW_E 입구)', '1098'), ('④b 입력 1098 (FW_E 입구)', '1098'),
                 ('④b 중 입력 1099 (FW_W 입구)', '1099'), ('④b 입력 1099 (FW_W 입구)', '1099'),
                 ('④b 중 도시 입력 (1098·1099 밖)', '도시입력'), ('④b 도시 입력 합', '도시입력'), ('①', '①')]:
        l = l.replace(a, b)
    return l.strip()


def find(lines, pat):
    return next(i + 1 for i, l in enumerate(lines) if pat in l)


out = {'mismatch': [], 'checked': 0}
# HR §1.1 (lines 60-77) vs OM §4.2 (lines 220-242): 9 v3c3 columns
hr11 = table(HR, 60, 77); om42 = table(OM, 220, 242)
omk = {key(k): v for k, v in om42.items()}
for k, (ln, cells) in hr11.items():
    kk = key(k)
    if kk not in omk:
        continue
    o = omk[kk][1]
    for c in range(9):
        a, b = num(cells[c]), num(o[c])
        out['checked'] += 1
        if a is None or b is None or abs(a - b) > 0.051:
            out['mismatch'].append(dict(where=f'HR:{ln} vs OM:{omk[kk][0]}', row=kk, col=c, hr=cells[c], om=o[c]))
# HR §1.3 (95-104) vs OM §4.1 (191-213)
hr13 = table(HR, 95, 104); om41 = {key(k): v for k, v in table(OM, 191, 213).items()}
om_link66 = table(OM, 297, 307)
for k, (ln, cells) in hr13.items():
    kk = key(k)
    if kk not in om41:
        continue
    o = om41[kk][1]
    for c in range(9):
        a, b = num(cells[c]), num(o[c]); out['checked'] += 1
        if a is None or b is None or abs(a - b) > 0.051:
            out['mismatch'].append(dict(where=f'HR:{ln} vs OM:{om41[kk][0]}', row=kk, col=c, hr=cells[c], om=o[c]))
# percentages HR §1.2 from OM §6.2 levels (codex 0-8100) and RW §5.2
lv = {key(k): v for k, v in table(OM, 345, 367).items()}
cols = ['NC3 s31', 'J1 s31', 'V-A s31', 'NC3 s41', 'J1 s41', 'V-A s41', 'NC3 s43', 'J1 s43', 'V-A s43']
def L(row, run):
    return num(lv[row][1][cols.index(run)])
pct = {}
for arm in ['V-A', 'J1']:
    for s in ['s31', 's41', 's43']:
        for row in ['Ω635', 'Ω701', '④', '①', '도시도로']:
            a = L(row, f'{arm} {s}'); n = L(row, f'NC3 {s}')
            pct[f'{arm}-NC3 {s} {row}'] = round(100 * (a - n) / n, 2)
out['pct_from_om_levels'] = pct
# HR 1.2 parse
hr12 = table(HR, 85, 89)
for k, (ln, cells) in hr12.items():
    if k.startswith('V-A') or k.startswith('J1'):
        arm = 'V-A' if k.startswith('V-A') else 'J1'
        for ci, row in enumerate(['Ω635', 'Ω701', '④', '①', '도시도로']):
            vals = [num(x) for x in cells[ci].split('/')]
            for si, s in enumerate(['s31', 's41', 's43']):
                out['checked'] += 1
                if abs(vals[si] - pct[f'{arm}-NC3 {s} {row}']) > 0.0051:
                    out['mismatch'].append(dict(where=f'HR:{ln}', row=f'{arm} {row} {s}', hr=vals[si], recomputed=pct[f'{arm}-NC3 {s} {row}']))
json.dump(out, open(f'{B}/work/vhr/tables_check.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('checked', out['checked'], 'mismatch', len(out['mismatch']))
for m in out['mismatch'][:40]:
    print(m)
