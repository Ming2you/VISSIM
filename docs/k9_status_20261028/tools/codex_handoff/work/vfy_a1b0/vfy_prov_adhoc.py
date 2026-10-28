import json, os
a=json.load(open('D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json',encoding='utf-8-sig'))
b=json.load(open('D:/VISSIM_handoff/20261024/raw/joint/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json',encoding='utf-8-sig'))
print(list(a.keys()))
def collect(x, out, p=''):
    if isinstance(x,dict):
        if 'sha256' in x and 'path' in x and isinstance(x['path'],str):
            out.append((x['path'].replace('/', os.sep), x['sha256'], p))
        for k,v in x.items(): collect(v,out,p+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): collect(v,out,p+'/%d'%i)
ra=[];rb=[]; collect(a,ra); collect(b,rb)
def rel(path):
    s=path.split('frozen'+os.sep,1)[-1]
    return s.split(os.sep,1)[-1] if os.sep in s else s
ma={rel(p):h for p,h,_ in ra}; mb={rel(p):h for p,h,_ in rb}
common=set(ma)&set(mb)
diff=[k for k in common if ma[k]!=mb[k]]
print('n_a',len(ma),'n_b',len(mb),'common',len(common),'diff',len(diff), diff[:10])
print('only_a', sorted(set(ma)-set(mb))[:10]); print('only_b', sorted(set(mb)-set(ma))[:10])
