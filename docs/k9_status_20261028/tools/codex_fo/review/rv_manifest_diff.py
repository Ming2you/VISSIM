import json,sys
fo=r'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954\FREEZE.json'
b1=r'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410\FREEZE.json'
F=json.load(open(fo,encoding='utf-8')); B=json.load(open(b1,encoding='utf-8'))
ff=F['files']; bf=B['files']
k=next(iter(ff)); print('example entry', k, ff[k])
only_fo=sorted(set(ff)-set(bf)); only_b=sorted(set(bf)-set(ff))
def h(v): return v.get('sha256') if isinstance(v,dict) else v
chg=sorted(x for x in set(ff)&set(bf) if h(ff[x])!=h(bf[x]))
print('only_fo',only_fo); print('only_b',only_b); print('changed',len(chg))
for x in chg: print('  ',x)
for key in ['git','exclusions','plan_subtrees','plan_subtree_files']:
    a=F[key]; b=B[key]
    if a!=b: print('DIFF',key, json.dumps(a)[:600], '\n   vs', json.dumps(b)[:600])
    else: print('same',key)
# also other attribute diffs (size)
sz=[x for x in set(ff)&set(bf) if isinstance(ff[x],dict) and ff[x]!=bf[x] and x not in chg]
print('attr-only diffs',len(sz), sz[:5])
