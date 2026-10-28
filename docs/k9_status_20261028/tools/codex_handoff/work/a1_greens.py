import csv,collections,sys,json
E='C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/tree/handoff/evidence/'
r=list(csv.DictReader(open(E+'decision_greens.csv',encoding='utf-8-sig')))
print(len(r))
for k in r[0].keys():
  vals=collections.Counter(x[k] for x in r)
  if len(vals)<40: print(k, dict(vals))
  else: print(k, len(vals),'distinct')
print(collections.Counter((x['condition'],x['kind']) for x in r))
