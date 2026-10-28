import json,sys
sys.path.insert(0,'o1o4/work')
import tails as T
exec(open('o1o4/work/tails_variants.py',encoding='utf-8').read().split('def run')[0].split("D={t")[0])
D={t:json.load(open(f'phys/scan/{t}.json',encoding='utf-8')) for t in target}
C={t:T.grids(d) for t,d in D.items()}
def run(gap,b1zone,b2zone,sm,tmax=9000):
    score=0; rows={}
    for t,d in D.items():
        cong=C[t]; nb=d['nb']; nw=d['nw']
        b1=[];b2=[]
        for w in range(nw):
            if w*60>=tmax: break
            row=cong[w]
            for lst,(a,e) in ((b1,b1zone),(b2,b2zone)):
                seeds=[b for b in range(nb) if row[b] and a<=(b+0.5)*100<e]
                if not seeds: continue
                b=min(seeds) if sm=='min' else max(seeds)
                while True:
                    nxt=None
                    for g in range(1,gap+2):
                        if b-g>=0 and row[b-g]: nxt=b-g; break
                    if nxt is None: break
                    b=nxt
                lst.append((w,b*100))
        r=(min(x for _,x in b1) if b1 else None, sum(1 for _,x in b1 if x<4500), min(x for _,x in b2) if b2 else None, sum(1 for _,x in b2 if x<6800))
        rows[t]=r; score+=sum(1 for i in range(4) if r[i]==target[t][i])
    return score,rows
best=[]
for gap in (0,1,2):
  for b1z in ((4200,5300),(4800,5200),(4900,5100),(5000,5100),(4900,5200),(4600,5300)):
    for b2z in ((7500,7700),(7600,7700),(7400,7700)):
      for sm in ('min','max'):
        s,rows=run(gap,b1z,b2z,sm); best.append((s,gap,b1z,b2z,sm,rows))
best.sort(key=lambda x:-x[0])
for b in best[:6]: print(b[:5])
s,g,b1z,b2z,sm,rows=best[0]
for t in target:
    if rows[t]!=target[t]: print('MISMATCH',t, rows[t], target[t])
