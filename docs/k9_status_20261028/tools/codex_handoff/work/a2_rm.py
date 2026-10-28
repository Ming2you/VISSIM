import csv,collections
E='C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/tree/handoff/evidence/'
r=list(csv.DictReader(open(E+'decision_greens.csv',encoding='utf-8-sig')))
secs=sorted({int(float(x['sim_sec'])) for x in r})
print('sim_secs',secs)
for cond in ['nc','joint','window','off','freeway_only','urban_only']:
  rm=[x for x in r if x['condition']==cond and x['kind']=='ramp_meter']
  ids=sorted({x['id'] for x in rm})
  print('==',cond,len(rm),'rows')
  for i in ids:
    xs=sorted([(int(float(x['sim_sec'])),float(x['green_sec'])) for x in rm if x['id']==i])
    g=[v for _,v in xs]
    c=collections.Counter(g)
    ctrl=[v for t,v in xs if t>=900]
    mean=sum(ctrl)/len(ctrl)
    below=sum(1 for v in ctrl if v<10)
    first=next((t for t,v in xs if v<10),None)
    last=max((t for t,v in xs if v<10),default=None)
    print(f"{i}: n={len(xs)} dist={dict(sorted(c.items()))} mean_ctrl(t>=900)={mean:.2f} n<10={below} first<10={first} last<10={last}")
