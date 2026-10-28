"""Merge work/R2C_RESULT.tmpl.md + work/result_tables.md (+ sha list) -> r2c_n/R2C_RESULT.md.  Read only elsewhere."""
import hashlib, io, os, re, sys
sys.dont_write_bytecode = True
R2C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


blocks, cur = {}, None
for line in io.open(os.path.join(R2C, 'work', 'result_tables.md'), encoding='utf-8').read().split('\n'):
    if line.startswith('@@TABLE '):
        cur = line.split(' ', 1)[1].strip()
        blocks[cur] = []
    elif cur:
        blocks[cur].append(line)
blocks = {k: '\n'.join(v).rstrip('\n') for k, v in blocks.items()}
files = ['PRE_R2C.md', 'tools/r2c_scan.py', 'tools/r2c_metrics.py', 'tools/run_py.ps1',
         'scans/r1_s31/scan.json', 'scans/r1_s31/uninserted.json', 'scans/r1_s41/scan.json', 'scans/r1_s41/uninserted.json',
         'out/r2c_scan_log.json', 'out/r2c_metrics.json', 'out/r2c_tables.md', 'out/r2c_bins300.csv', 'out/r2c_zone300.csv',
         'work/poll_r2c.ps1', 'work/r2c_report_extract.py', 'work/r2c_report_extract.json', 'work/make_result_tables.py',
         'work/result_tables.md', 'work/R2C_RESULT.tmpl.md', 'work/merge_result.py']
lines = ['| 파일 (`rmcause/r2c_n/`) | sha256 |', '|---|---|']
for f in files:
    lines.append('| `%s` | `%s` |' % (f, sha(os.path.join(R2C, *f.split('/')))))
lines.append('')
lines.append('- 이 문서 자체의 sha256 은 `rmcause/LOG.md` 와 D: 사본 폴더의 `SHA256SUMS.txt` 에 적습니다.')
lines.append('- D: 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/r2c_n/` (이 문서 + out/·scans/·logs/·work/ 사본).')
blocks['sha'] = '\n'.join(lines)
t = io.open(os.path.join(R2C, 'work', 'R2C_RESULT.tmpl.md'), encoding='utf-8').read()
used = set()


def rep(m):
    k = m.group(1)
    used.add(k)
    return blocks[k]


out = re.sub(r'^@@INSERT (\S+)$', rep, t, flags=re.M)
missing = set(blocks) - used
if missing or '@@' in out:
    raise SystemExit('unused blocks %s or leftover marker' % missing)
io.open(os.path.join(R2C, 'R2C_RESULT.md'), 'w', encoding='utf-8', newline='\n').write(out)
print('ok', sha(os.path.join(R2C, 'R2C_RESULT.md')))
