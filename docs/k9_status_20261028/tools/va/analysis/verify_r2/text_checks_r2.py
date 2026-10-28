# VerifyVA r2 text checks (light; reads documents only, no run data).
import json
import re
import sys

SP = r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
rep = open(SP + '/k92/va/analysis/VA_REPORT.md', encoding='utf-8').read().split('\n')
out = {}
blocks, cur, start = [], [], None
for i, l in enumerate(rep, 1):
    if l.startswith('>'):
        if not cur:
            start = i
        cur.append(l[2:] if l.startswith('> ') else l[1:])
    else:
        if cur:
            blocks.append((start, cur))
            cur = []
if cur:
    blocks.append((start, cur))
out['blocks'] = [(s, len(b)) for s, b in blocks]
srcN = open(SP + '/j1/J1_CAVEAT_ADDENDUM.md', encoding='utf-8').read().rstrip('\n').split('\n')
srcD = open(SP + '/k92/va/J1_CAVEAT_ADDENDUM_K92VA.md', encoding='utf-8').read().rstrip('\n').split('\n')
out['na_same'] = blocks[0][1] == srcN
out['da_same'] = blocks[1][1] == srcD
a22 = open(SP + '/K8_PREDECLARATION_AMENDMENT_22.md', encoding='utf-8').read().split('\n')
out['h8_eq_A22_409'] = blocks[2][1] == [a22[408]]
a34 = open(SP + '/K8_PREDECLARATION_AMENDMENT_34.md', encoding='utf-8').read().split('\n')
m = re.search(r'`(\[K9-2 V-A\][^`]*)`', a34[402])
out['below8_eq_A34_403'] = blocks[3][1] == [m.group(1)]
a24 = open(SP + '/K8_PREDECLARATION_AMENDMENT_24.md', encoding='utf-8').read().split('\n')
out['val10_eq_A24_191'] = blocks[4][1] == [a24[190]]
out['val6_eq_A24_187'] = blocks[5][1] == [a24[186]]
# addendum 2 file = amendment 34 lines 455-457 backtick text
ad = [re.search(r'`(- \[더함[^`]*)`', a34[k]).group(1) for k in (454, 455, 456)]
out['addendum2_eq_A34_455_457'] = srcD == ['# J1 단서 덧붙임 2 (K9-2 V-A, 트리 밖)', ''] + ad
# R12 banned / verdict strings in both docs (outside quote blocks)
ban = ['개선', '이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌', '악화', '유리', '불리', '우세', '이득', '손해']
for fn, key in ((SP + '/k92/va/analysis/VA_REPORT.md', 'report'), (SP + '/k92/va/validity/VALIDITY_VA.md', 'validity')):
    lines = open(fn, encoding='utf-8').read().split('\n')
    hits = [(i, w) for i, l in enumerate(lines, 1) if not l.startswith('>') for w in ban if w in l]
    out['ban_hits_' + key] = hits
    out['bare_seed_' + key] = [i for i, l in enumerate(lines, 1)
                               if not l.startswith('>') and not l.startswith('|')
                               and re.search(r'(?<![\w-])s(31|41|43|47)(?![\w])', re.sub(r'`[^`]*`', '', l))]
    out['cr_' + key] = open(fn, 'rb').read().count(b'\r')
print(json.dumps(out, ensure_ascii=False, indent=1))
