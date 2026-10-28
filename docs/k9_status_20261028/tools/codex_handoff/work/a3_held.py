import csv,collections
E='C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/tree/handoff/evidence/'
r=list(csv.DictReader(open(E+'decision_greens.csv',encoding='utf-8-sig')))
for cond in ['joint','window','off','freeway_only','urban_only']:
  sig=[x for x in r if x['condition']==cond and x['kind']=='signal']
  rm=[x for x in r if x['condition']==cond and x['kind']=='ramp_meter']
  ts=sorted({int(float(x['sim_sec'])) for x in sig})
  tr=sorted({int(float(x['sim_sec'])) for x in rm})
  S={};R={}
  for x in sig: S.setdefault(int(float(x['sim_sec'])),{})[x['id']]=(x['p1'],x['p2'],x['p3'],x['p4'],x['offset'])
  for x in rm: R.setdefault(int(float(x['sim_sec'])),{})[x['id']]=x['green_sec']
  print('==',cond,'signal times',ts[0],ts[-1],len(ts),'rm times',tr[0],tr[-1],len(tr))
  held_sig=[];held_all=[]
  for a,b in zip(ts,ts[1:]):
    if S[a]==S[b]: held_sig.append(b)
    if S[a]==S[b] and R.get(a)==R.get(b): held_all.append(b)
  print(' signal-identical-to-previous at', held_sig)
  print(' signal+RM identical at', held_all)
  # distinct plans per SC
  d={sc:len({S[t][sc] for t in ts}) for sc in sorted(S[ts[0]])}
  print(' distinct per SC', d)
  # first row example
  print(' first time sample SC1', S[ts[0]].get('SC1'), ' second', S[ts[1]].get('SC1'))
