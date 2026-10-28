# -*- coding: utf-8 -*-
"""fwe_inventory_md.py - render out/inventory.json + out/pins_existing.json into out/INVENTORY.md (read-only, light)."""
import hashlib, json, os

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
D = SP + '/fwe_decomp/out'


def sh(p):
    h = hashlib.sha256(); h.update(open(p, 'rb').read()); return h.hexdigest()


def short(p):
    return p.replace(SP + '/', 'SP/').replace('D:/VISSIM_handoff/20261024/', 'H/')


def main():
    inv = json.load(open(D + '/inventory.json', encoding='utf-8'))
    pins = json.load(open(D + '/pins_existing.json', encoding='utf-8'))
    L = []
    L.append('# INVENTORY — D-K9-106 팔·파일·캐시 목록 (fwe_inventory.py 출력을 옮긴 표)')
    L.append('')
    L.append('- 만든 도구: `fwe_decomp/tools/fwe_inventory.py`(sha256 `%s`), 이 표: `fwe_inventory_md.py`(`%s`). 원본 JSON: `out/inventory.json`(`%s`).' % (
        sh(SP + '/fwe_decomp/tools/fwe_inventory.py'), sh(SP + '/fwe_decomp/tools/fwe_inventory_md.py'), sh(D + '/inventory.json')))
    L.append('- 시드는 폴더 이름이 아니라 provenance(`run.json` 또는 `run_provenance_*.json`)의 `/seed` 에서 읽었습니다 [실행].')
    L.append('- FZP sha256 은 FZP 를 다시 읽지 않고, 기존 캐시가 그 경로를 스캔할 때 적은 값을 경로로 맞춰 옮겼습니다. "일치(n)" = 캐시 n 개의 값이 모두 같음. 크기·수정 시각은 이번에 읽은 값입니다 [실행].')
    L.append('- 열지 않은 것: `sealed`, 봉인 시드 37/59/61/67 이름, v3c3-s47·s53 캐시(`nc_s47.json`·`nc_s53.json`), `raw/historical_vsl_s43`(범위 밖) [실행 이름 거르기].')
    L.append('- 줄임: SP = scratchpad/k8, H = `D:/VISSIM_handoff/20261024`.')
    L.append('')
    L.append('## 1. 팔 × 시드 (런 파일)')
    L.append('')
    L.append('| 팔 | 망 | seed (provenance) | provenance sha256 | FZP (bytes, 수정 KST) | FZP sha256 (캐시) | inpx sha256 | 결정 폴더 action CSV 수 · 목록 sha256 | signal_readback.csv sha256 | 미터 LDP 수 |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    for r in inv['runs']:
        f = r['fzp'] or {}
        dec = r.get('decisions') or {}
        rb = (dec.get('signal_readback') or {}).get('sha256') if dec else None
        L.append('| %s | %s | %s | `%s` | `%s` (%s, %s) | %s `%s` | `%s` | %s | %s | %d |' % (
            r['arm'], r['net'], r['provenance']['seed'], (r['provenance']['sha256'] or '-')[:16] + '…',
            short(f.get('path', '-')), f.get('bytes'), f.get('mtime_kst'), r['fzp_sha256_status'],
            (r['fzp_sha256_cached'][0] if r['fzp_sha256_cached'] else '-'),
            ((r.get('inpx') or {}).get('sha256') or '-')[:16] + ('…' if (r.get('inpx') or {}).get('sha256') else ''),
            ('%d · `%s…`' % (dec['n_action_csv'], dec['action_csv_manifest_sha256'][:16])) if dec else '-',
            ('`%s…`' % rb[:16]) if rb else '-', len(r.get('meter_ldp') or [])))
    L.append('')
    L.append('## 2. 기존 캐시 (팔별, 경로로 맞춤)')
    L.append('')
    L.append('| 팔 | seed | 캐시 종류 | 파일 | 파일 sha256 |')
    L.append('|---|---|---|---|---|')
    for r in inv['runs']:
        for c in sorted(r['caches'], key=lambda c: c['kind']):
            L.append('| %s | %s | %s | `%s` | `%s` |' % (r['arm'], r['provenance']['seed'], c['kind'], short(c['file']), c['file_sha256']))
    L.append('')
    L.append('- 경로가 이 표의 런과 맞지 않은 캐시: ' + '; '.join('`%s` (%s)' % (short(c['file']), c['fzp']) for c in inv['caches_not_matched_to_inventory_runs']))
    L.append('')
    L.append('## 3. 기존 도구·정의·문서·결과 표 sha256 (`out/pins_existing.json`, `out/pins_existing.sha256`)')
    L.append('')
    for g, ps in pins['groups'].items():
        L.append('### ' + g)
        L.append('')
        L.append('| 파일 | bytes | sha256 |')
        L.append('|---|---:|---|')
        for p in ps:
            L.append('| `%s` | %s | `%s` |' % (short(p['path']), p.get('bytes', '-'), p.get('sha256', 'MISSING')))
        L.append('')
    open(D + '/INVENTORY.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print('done', len(L))


if __name__ == '__main__':
    main()
