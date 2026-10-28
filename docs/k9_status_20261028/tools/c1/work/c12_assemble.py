# -*- coding: utf-8 -*-
"""c12_assemble.py (K8 amendment C1-2 Declare, 2026-10-27 KST) - builds the amendment from its template.

Usage: python -B c12_assemble.py <SP> <template.md> <out.md>
Three quote blocks are copied byte-exact from pinned source documents (sha256 checked before use):
  {D98_BLOCK}    GD/GUARD_DESIGN_DRAFT.md r2 lines 370-442 (section 3.1-3.6), one row (D98-5, line 394) replaced
                 by the wording fix of GG/GENERAL_GUARD_DESIGN.md r1 section 3.8; every line prefixed with '> '.
  {THREAD_BLOCK} GG/GENERAL_GUARD_DESIGN.md r1 line 658 as is (already a '> ' quote line).
  {FWE33_BLOCK}  fwe_decomp/FWE_DECOMP.md r2 line 260 as is (already a '> ' quote line).
A pure-CRLF source is read with the CR of each line end removed (line endings only). Checks: each source sha256,
the replaced row's original text, the thread line equals GD r2 line 450, every block line
except the replaced row equals its source line. Writes <out.md> with exclusive create (LF), prints sha256.
"""
import hashlib
import json
import sys

SRC = {
    'gd': ('c_port/c1/guard/GUARD_DESIGN_DRAFT.md', '553227cddc6e15e66a08beb3c2dee0bc0d7437a8035a736614a5a175e1f2ee0e'),
    'gg': ('c_port/c1/guard/general/GENERAL_GUARD_DESIGN.md', 'cffbef23ad1c185174bb5639e7e062ab4f525b1924a9d35f36a83caaf85596b0'),
    'fd': ('fwe_decomp/FWE_DECOMP.md', '7f58ab3e624719bcdba2e7b91bc2516a2d58174cf269d70f338a5c6336a291e1'),
}
OLD_D985 = ('| D98-5 | 같은 상태에서 C1·C1G 팔의 S⁰ = Ω 팔 S⁰ (비트 같음). M·H·가드 키는 투영을 바꾸지 않아야 함 '
            '| 실제 확인(가드 RS 줄이 투영 앞에 있지 않음을 확인) |')
NEW_D985 = ('| D98-5 | 같은 상태에서 C1·C1G 팔의 S⁰ = Ω 팔 S⁰ (비트 같음). M·H·가드 키는 투영을 바꾸지 않아야 함. '
            '가드 RS 줄(E23)은 투영 입력(`detector_mapping`·`state_json`)을 읽기만 하고 바꾸지 않음을 확인 '
            '| 실제 확인 `[C1-2 고침: 일반형 설계 r1 §3.8, 원래 셋째 칸 "실제 확인(가드 RS 줄이 투영 앞에 있지 않음을 확인)"]` |')


CRLF = []


def lines_of(sp, key):
    path, digest = SRC[key]
    raw = open(sp + '/' + path, 'rb').read()
    got = hashlib.sha256(raw).hexdigest()
    if got != digest:
        raise SystemExit('source sha256 differs: %s %s' % (path, got))
    text = raw.decode('utf-8')
    if '\r' in text:
        # A pure-CRLF source is read with the CR of each line end removed (line endings only, text unchanged).
        if text.count('\r\n') != text.count('\n') or text.count('\r') != text.count('\n'):
            raise SystemExit('mixed line endings in source: ' + path)
        text = text.replace('\r\n', '\n')
        CRLF.append(path)
    return text.split('\n')


def main():
    sp, tpl, out = sys.argv[1], sys.argv[2], sys.argv[3]
    gd, gg, fd = lines_of(sp, 'gd'), lines_of(sp, 'gg'), lines_of(sp, 'fd')
    d98 = gd[369:442]                       # lines 370..442 (1-based)
    if not d98[0].startswith('### 3.1 정의') or not d98[-1].startswith('- 이것은 첫 행(첫 스텝 뒤)이고'):
        raise SystemExit('D98 range anchor differs')
    idx = [i for i, l in enumerate(d98) if l.startswith('| D98-5 |')]
    if len(idx) != 1 or d98[idx[0]] != OLD_D985 or idx[0] != 394 - 370:
        raise SystemExit('D98-5 row differs from the expected original text')
    block = list(d98)
    block[idx[0]] = NEW_D985
    for i, (a, b) in enumerate(zip(block, d98)):
        if i != idx[0] and a != b:
            raise SystemExit('unexpected change at block line %d' % i)
    d98_block = '\n'.join(('> ' + l) if l else '>' for l in block)
    thread = gg[657]
    if not thread.startswith('> **정정 (D-K9-99, 2026-10-27)**') or thread != gd[449]:
        raise SystemExit('thread erratum line differs (GG r1 :658 vs GD r2 :450)')
    fwe = fd[259]
    if not fwe.startswith('> **C1 FW_E 기준 줄 (데이터 전 보고 칸, D-K9-106)**'):
        raise SystemExit('FWE_DECOMP section 3.3 line differs')
    t = open(tpl, 'rb').read().decode('utf-8')
    if '\r' in t:
        raise SystemExit('CR in template')
    for k in ('{D98_BLOCK}', '{THREAD_BLOCK}', '{FWE33_BLOCK}'):
        if t.count(k) != 1:
            raise SystemExit('placeholder count differs: ' + k)
    t = t.replace('{D98_BLOCK}', d98_block).replace('{THREAD_BLOCK}', thread).replace('{FWE33_BLOCK}', fwe)
    if '{' in t and any(x in t for x in ('{D98', '{THREAD', '{FWE33')):
        raise SystemExit('placeholder left')
    raw = t.encode('utf-8')
    with open(out, 'xb') as fh:
        fh.write(raw)
    print(json.dumps({'out': out, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                      'lines': t.count('\n'), 'd98_lines': len(block), 'd98_replaced_line_in_source': 394,
                      'thread_source_line': 658, 'fwe_source_line': 260, 'crlf_sources_read_as_lf': CRLF},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
