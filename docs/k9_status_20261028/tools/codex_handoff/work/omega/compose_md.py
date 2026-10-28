# Compose OMEGA701_V3C3.md from md_template.txt + generated tables (numbers come only from the tool outputs).
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUTMD = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'OMEGA701_V3C3.md')
T = json.load(io.open(os.path.join(HERE, 'tables.json'), encoding='utf-8'))
D = json.load(io.open(os.path.join(HERE, 'omega701_v3c3.json'), encoding='utf-8'))
TOP = json.load(io.open(os.path.join(HERE, 'top66.json'), encoding='utf-8'))
EX = json.load(io.open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8-sig'))
REASON = {d['link']: d['reasons'] for d in EX['controlled_intersection_expansion']['added_links']}


def f1(x):
    return ('%+.1f' % x).replace('-', '−')


# runs table
NAMES = {'va': 'V-A', 'j1': 'J1', 'nc3': 'NC3', 'lnc': 'LNC (64cf-s29 NC)'}
lines = ['| 꼬리표 | 팔 · 시드 | FZP (읽기만) | FZP sha256 앞 16 | 행 수 | 프레임 (첫–끝 s) | 0.10 s 행 | 스캔 s |',
         '|---|---|---|---|---:|---|---:|---:|']
for tag, m in D['scan_meta'].items():
    arm = tag.split('_')[0]
    seed = 'v3c3-s%s' % tag.split('_s')[-1] if arm != 'lnc' else '64cf-s29'
    lines.append('| %s | %s %s | `%s` | `%s` | %d | %d (%.1f–%.1f) | %d | %.1f |' % (
        tag, NAMES[arm], seed, m['fzp'], m['fzp_sha256'][:16], m['rows'], m['frames'], m['first_sec'], m['last_sec'],
        m['skip_rows_0p10'], m['scan_sec']))
T['T_RUNS'] = '\n'.join(lines)
# inpx / err sha
lines = ['| 꼬리표 | 망 .inpx sha256 앞 16 | .err sha256 앞 16 | 런 끝 remain (입력: 대) | 차로변경 제거 (전체 / Ω635 밖 / Ω701 밖) |',
         '|---|---|---|---|---|']
for tag, m in D['scan_meta'].items():
    if tag.startswith('lnc'):
        continue
    rm = D['remains'][tag]
    rv = D['removals'][tag]
    lines.append('| %s | `%s` | `%s` | %s | %d / %d / %d |' % (
        tag, m['inpx_sha256'][:16], m['err_sha256'][:16], ', '.join('%s: %d' % kv for kv in rm.items()) or '없음',
        rv['all'], rv['outside635'], rv['outside701']))
T['T_INPX'] = '\n'.join(lines)
# LNC check
c = D['checks']['lnc_vs_codex']
lines = ['| 항목 (64cf-s29 NC, codex 꼴 0–8100) | 이 도구 (LNC) | codex 값 | 차 |', '|---|---:|---:|---:|']
for k, nm in (('FW_E_7', '① FW_E 7링크 (`independent_fzp_counts.json` nc)'), ('local_19', '② 국소 19'),
              ('Omega701', 'Ω701'), ('whole_observed', '④a 망 전체'),
              ('part_FW_W', '서측 본선 (`summary.json` parts.nc.FW_W)'), ('part_onramps_E', '동측 진입 커넥터'),
              ('part_onramps_W', '서측 진입 커넥터'), ('part_urban_roads', '도시도로'), ('part_offramps', '진출램프'),
              ('part_outside', 'Ω701 밖'), ('omega701_minus_west', 'Ω701 − 서측 본선 (`without_west_mainline.json`)')):
    a, b, dd = c[k]
    lines.append('| %s | %.6f | %.6f | %.1e |' % (nm, a, b, dd))
lines.append('| 행 수 (≤ 8100 s) / 프레임 | %d / %d | %d / %d | 0 / 0 |' % (
    c['rows_le_8100'][0], c['frames'][0], c['rows_le_8100'][1], c['frames'][1]))
T['T_LNC'] = '\n'.join(lines)
T['LNC_OMEGA635'] = '%.2f' % c['lnc_omega635_codex_8100']
T['LNC_D66'] = '%.2f' % (c['Omega701'][0] - c['lnc_omega635_codex_8100'])
# set checks
sc = D['checks']['sets']
T['T_SETS'] = '\n'.join('- `%s` = %s' % (k, v) for k, v in sc.items())
# top 66 table
lines = ['| 링크 | 소속 까닭 (`omega_membership_exact.json` added_links) | NC3 수준 s31/s41/s43 | V-A − NC3 s31/s41/s43 | J1 − NC3 s31/s41/s43 |',
         '|---|---|---|---|---|']
for l, d, lv in TOP['rows'][:8]:
    lines.append('| %d | %s | %s | %s | %s |' % (
        l, ', '.join(REASON.get(str(l), [])), ' / '.join('%.1f' % x for x in lv),
        ' / '.join(f1(d['VA-NC3|s%d' % s]) for s in (31, 41, 43)),
        ' / '.join(f1(d['J1-NC3|s%d' % s]) for s in (31, 41, 43))))
tot = {k: sum(r[1][k] for r in TOP['rows']) for k in TOP['rows'][0][1]}
lines.append('| 66링크 합 | — | — | %s | %s |' % (' / '.join(f1(tot['VA-NC3|s%d' % s]) for s in (31, 41, 43)),
                                                  ' / '.join(f1(tot['J1-NC3|s%d' % s]) for s in (31, 41, 43))))
T['T_TOP66'] = '\n'.join(lines)
# artifacts sha
arts = ['omega701_recount.py', 'build_tables.py', 'compose_md.py', 'md_template.txt', 'top66.py', 'probe_sets.py',
        'run_omega.ps1', 'check_fzp_copy.py', 'selftest/test_small.py', 'omega701_v3c3.json', 'omega701_per_link.csv',
        'omega701_pairs.csv', 'omega701_levels.csv', 'verify_vs_va_report.csv', 'tables.json', 'top66.json',
        'cache/scan_log.json', 'state_scan.json', 'state_metrics.json']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


lines = ['| 파일 (`codex_handoff/work/omega/` 아래) | 바이트 | sha256 |', '|---|---:|---|']
for a in arts:
    p = os.path.join(HERE, a)
    lines.append('| `%s` | %d | `%s` |' % (a, os.path.getsize(p), sha(p)))
for tag in D['scan_meta']:
    for ext in ('.npz', '.json'):
        p = os.path.join(HERE, 'cache', tag + ext)
        lines.append('| `cache/%s%s` | %d | `%s` |' % (tag, ext, os.path.getsize(p), sha(p)))
T['T_ARTS'] = '\n'.join(lines)
src = io.open(os.path.join(HERE, 'md_template.txt'), encoding='utf-8').read()
for k, v in T.items():
    src = src.replace('{{' + k + '}}', v)
left = [x for x in src.split('{{')[1:]]
if left:
    raise SystemExit('unfilled placeholders: %s' % [x.split('}}')[0] for x in left])
for bad in ('이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌', '우월', '성공', '실패했'):
    if bad in src:
        raise SystemExit('verdict-like word: ' + bad)
tmp = OUTMD + '.tmp'
with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
    f.write(src)
os.replace(tmp, OUTMD)
print('written', OUTMD, os.path.getsize(OUTMD), sha(OUTMD))
