import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
def size(x): return len(json.dumps(x))
def walk(x,path,depth,maxd):
    if depth>maxd: return
    if isinstance(x,dict):
        for k,v in x.items():
            t=type(v).__name__
            print('  '*depth+f'{path}/{k} [{t}] {size(v)}' + (f' len={len(v)}' if isinstance(v,(list,dict)) else f' = {str(v)[:80]}'))
            if isinstance(v,dict): walk(v,path+'/'+k,depth+1,maxd)
            elif isinstance(v,list) and v and isinstance(v[0],dict) and depth+1<=maxd:
                print('  '*(depth+1)+f'[0] keys: {list(v[0].keys())[:30]}')
walk(o,'',0,int(sys.argv[2]) if len(sys.argv)>2 else 1)
