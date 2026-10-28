# b_report_build.py - assemble CH/b/B_REPORT.md from b_report_src.md + generated table pieces. New 2026-10-27 KST. Read only
# toward every input; writes CH/b/B_REPORT.md (+ .sha256). Checks: no placeholder left, none of the 8 verdict words
# (va_report_build.py FORBIDDEN), no sealed-seed names. Copy to D: is done separately.
import hashlib, os, re, subprocess, sys

CH = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff'
CW = CH + '/work'
FORBIDDEN = ('개선', '이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌')
SEALED = ('s37', 's59', 's61', 's67', 'seed37', 'seed59', 'seed61', 'seed67')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def sections(path):
    txt = open(path, encoding='utf-8').read()
    parts = re.split(r'(?m)^(?=#### )', txt)
    return [p for p in parts if p.startswith('#### ')]


T = sections(CW + '/b/b_report_tables.md')
Lsec = sections(CW + '/b/b_report_lines.md')
t1 = [p for p in T if p.startswith('#### 주 표 T1')]
t2 = [p for p in T if p.startswith('#### 보조 표 T2')]
t0 = [p for p in T if p.startswith('#### 참고 표 T0')]
la = [p for p in Lsec if p.startswith('#### 링크 66') or p.startswith('#### 도시도로')]
chk = [p for p in Lsec if p.startswith('#### 점검')]
lb = [p for p in Lsec if p not in la and p not in chk]
assert len(t1) == 2 and len(t2) == 2 and len(t0) == 1 and len(la) == 2 and len(chk) == 1 and len(lb) == 5, (len(t1), len(t2), len(t0), len(la), len(chk), len(lb))

art = [
    ('입력 V', CW + '/vhr_b/v3c3_all.json'), ('입력 O', CW + '/omega_b/omega701_v3c3.json'), ('입력 P', CW + '/omega_b/omega701_per_link.csv'),
    ('입력 top66', CW + '/omega_b/top66.json'),
    ('입력 M s31', CW + '/rawcheck_b/s31/metrics_out.json'), ('입력 M s41', CW + '/rawcheck_b/s41/metrics_out.json'),
    ('입력 M s43', CW + '/rawcheck_b/s43/metrics_out.json'),
    ('표 JSON', CW + '/b/b_report_tables.json'), ('표 조각', CW + '/b/b_report_tables.md'), ('줄 조각', CW + '/b/b_report_lines.md'),
    ('도구 b_report_tables.py', CW + '/b/b_report_tables.py'), ('도구 b_report_lines.py', CW + '/b/b_report_lines.py'),
    ('조립 원문 b_report_src.md', CW + '/b/b_report_src.md'), ('조립 b_report_build.py', CW + '/b/b_report_build.py'),
    ('실행기 b_analyze.ps1 (v2)', CW + '/b/b_analyze.ps1'), ('발사 b_analyze_launch_wmi.ps1 (v2)', CW + '/b/b_analyze_launch_wmi.ps1'),
    ('실행 기록 v1', CW + '/b/ana_full.state.txt'), ('실행 기록 v2', CW + '/b/ana_full2.state.txt'),
]
shatab = ['| 무엇 | 경로 (CW = `CH/work`) | sha256 |', '|---|---|---|']
for name, p in art:
    shatab.append('| %s | `%s` | `%s` |' % (name, p.replace(CW, 'CW'), sha(p)))
chk_pins = subprocess.run(['sha256sum', '-c', 'b/PINS_B.sha256'], cwd=CH, capture_output=True, text=True)
ok = sum(1 for l in chk_pins.stdout.splitlines() if l.endswith(': OK'))
bad = [l for l in chk_pins.stdout.splitlines() if not l.endswith(': OK')]
shatab.append('')
shatab.append('- 조립 때 다시 셈: `sha256sum -c b/PINS_B.sha256` OK %d줄, OK 아닌 줄 %d. COMPARE_RULE_B `%s…`, PINS_B `%s…`, PRE_B_CONCURRENT `%s…`.' % (
    ok, len(bad), sha(CH + '/b/COMPARE_RULE_B.md')[:8], sha(CH + '/b/PINS_B.sha256')[:8], sha(CH + '/b/PRE_B_CONCURRENT.md')[:8]))

src = open(CW + '/b/b_report_src.md', encoding='utf-8').read()
out = (src.replace('{{T1}}', '\n'.join(t1).rstrip()).replace('{{T2}}', '\n'.join(t2).rstrip()).replace('{{T0}}', '\n'.join(t0).rstrip())
       .replace('{{LINES_A}}', '\n'.join(la).rstrip()).replace('{{LINES_B}}', '\n'.join(lb).rstrip())
       .replace('{{CHECKS}}', '\n'.join(chk).rstrip()).replace('{{SHA}}', '\n'.join(shatab)))
assert '{{' not in out
hits = [w for w in FORBIDDEN if w in out]
seal = [w for w in SEALED if re.search(r'(?<![0-9A-Za-z])' + w + r'(?![0-9])', out)]
if hits or seal or bad or ok != 54:
    print('STOP forbidden', hits, 'sealed', seal, 'pins bad', bad, 'ok', ok)
    sys.exit(2)
dst = CH + '/b/B_REPORT.md'
with open(dst, 'w', encoding='utf-8', newline='\n') as f:
    f.write(out)
h = sha(dst)
with open(dst + '.sha256', 'w', encoding='utf-8', newline='\n') as f:
    f.write('%s *B_REPORT.md\n' % h)
print('B_REPORT.md', h, 'lines', out.count('\n'), 'pins ok', ok)
