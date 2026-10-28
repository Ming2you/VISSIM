# vb_frz_extra.py — 두 FRZ 트리에서 FREEZE.json 표에 없는 파일이 어느 폴더에 있는지 셈 (파일 이름만, 읽기만)
import os, json, collections
for r in ['D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258',
          'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410']:
    man = set(json.load(open(r + '/FREEZE.json', encoding='utf-8'))['files'])
    root = '\\\\?\\' + r.replace('/', '\\')
    extra = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), root).replace('\\', '/')
            if rel not in man and rel != 'FREEZE.json':
                extra.append(rel)
    c = collections.Counter(x.split('/')[-2] for x in extra)
    print(r[-32:], len(extra), dict(c))
