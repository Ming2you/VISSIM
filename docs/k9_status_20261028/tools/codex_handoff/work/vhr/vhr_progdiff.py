import json, sys, re
T=int(sys.argv[1]); t6=f'{T:06d}'
P={'mine':f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/runs/T{t6}/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_{t6}.joint.progress.jsonl',
   'record':f'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_{t6}.joint.progress.jsonl',
   'a0_env_hsw':f'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/env_hsw/T{t6}/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_{t6}.joint.progress.jsonl'}
def clean(o):
    if isinstance(o,dict): return {k:clean(v) for k,v in o.items() if not (k.endswith('sec') or k.endswith('seconds') or k=='elapsed')}
    if isinstance(o,list): return [clean(v) for v in o]
    return o
L={k:[clean(json.loads(l)) for l in open(p,encoding='utf-8')] for k,p in P.items()}
out={}
for a,b in [('mine','record'),('mine','a0_env_hsw'),('a0_env_hsw','record')]:
    x,y=L[a],L[b]; diffs=[i+1 for i,(u,v) in enumerate(zip(x,y)) if u!=v]
    out[f'{a}~{b}']=dict(n=(len(x),len(y)),first=diffs[:5],count=len(diffs),first_pair=(x[diffs[0]-1],y[diffs[0]-1]) if diffs else None)
print(json.dumps(out,indent=0)[:3000])
