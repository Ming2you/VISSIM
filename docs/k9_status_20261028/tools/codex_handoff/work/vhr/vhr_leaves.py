# leaf-level comparison of action/joint JSON: mine vs a0 env_hsw vs record, numeric leaves only, timing keys removed
import json, re, sys
from collections import Counter
T=int(sys.argv[1]); t6=f'{T:06d}'
D={'mine':f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/runs/T{t6}/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
   'a0':f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/env_hsw/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
   'rec':'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'}
TIM=re.compile(r'(sec|seconds|elapsed|wall|time|_at|timestamp|created)$',re.I)
def leaves(o,p=''):
    if isinstance(o,dict):
        for k,v in o.items():
            if TIM.search(k): continue
            yield from leaves(v,p+'/'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from leaves(v,p+f'[{i}]')
    else: yield p,o
out={}
for fn in [f'action_{t6}.joint.json', f'action_{t6}.json']:
    L={k:dict(leaves(json.load(open(f'{d}/{fn}',encoding='utf-8')))) for k,d in D.items()}
    for a,b in [('mine','a0'),('mine','rec'),('a0','rec')]:
        x,y=L[a],L[b]; keys=set(x)|set(y)
        num=[k for k in keys if isinstance(x.get(k),(int,float)) and isinstance(y.get(k),(int,float)) and not isinstance(x.get(k),bool) and x.get(k)!=y.get(k)]
        oth=[k for k in keys if k not in num and x.get(k)!=y.get(k)]
        cat=Counter(re.sub(r'\[\d+\]','[]',k).split('/')[1] if k.count('/')>1 else k for k in num)
        out[f'{fn}|{a}~{b}']=dict(leaves=(len(x),len(y)),numeric_diff=len(num),other_diff=len(oth),numeric_top=cat.most_common(6),
                                   numeric_examples=[(k,x.get(k),y.get(k)) for k in sorted(num)[:4]],other_examples=[k for k in sorted(oth)[:6]])
json.dump(out,open(f'leaves_T{t6}.json','w'),indent=1,default=str)
for k,v in out.items(): print(k, v['leaves'], 'num', v['numeric_diff'], 'other', v['other_diff'], v['numeric_top'][:4]); print('   ', v['numeric_examples'][:2]); print('   ', v['other_examples'][:4])
