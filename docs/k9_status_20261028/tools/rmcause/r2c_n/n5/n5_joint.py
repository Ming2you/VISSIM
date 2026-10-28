import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
def show(x,path,depth,maxd):
    if isinstance(x,dict):
        for k,v in sorted(x.items(), key=lambda kv:-len(json.dumps(kv[1]))):
            s=len(json.dumps(v))
            if s<1000 and depth>0: continue
            print('  '*depth+f'{path}/{k} [{type(v).__name__}] {s}')
            if depth<maxd: show(v,path+'/'+k,depth+1,maxd)
show(o,'',0,int(sys.argv[2]))
