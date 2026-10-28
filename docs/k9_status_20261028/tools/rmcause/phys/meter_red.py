import csv,sys,collections
p=sys.argv[1]
ev=collections.defaultdict(list)
for r in csv.DictReader(open(p,encoding='utf-8')):
    if r['kind']=='meter': ev[int(r['no'])].append((int(float(r['time_s'])),r['value']))
T=9000; W=900
res={}
for no,lst in sorted(ev.items()):
    lst.sort()
    red=[0]*(T//W+1)
    state='GREEN'; t0=0
    for t,v in lst+[(T,'END')]:
        if state=='RED':
            for s in range(t0,t):
                red[s//W]+=1
        state=v; t0=t
    res[no]=[round(1-x/W,2) for x in red[:T//W]]
names={9101:'10480',9102:'10482',9103:'10646',9104:'10644',9105:'10639',9106:'10681',9107:'10490',9108:'10484'}
print('green share per 900 s window (0-900,...,8100-9000)')
for no,v in res.items(): print(no,names.get(no),v)
