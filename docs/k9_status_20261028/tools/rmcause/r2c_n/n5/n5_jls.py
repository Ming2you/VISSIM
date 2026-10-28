import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
j=o['metadata']['joint_leader_selection']
print(type(j).__name__, len(json.dumps(j)))
for k,v in sorted(j.items(), key=lambda kv:-len(json.dumps(kv[1]))):
    s=len(json.dumps(v))
    print(k, type(v).__name__, s, (str(v)[:120] if s<200 else ''))
mna=j.get('meter_neighbor_audit')
if mna:
    print('=== MNA keys', list(mna.keys()))
    for k,v in mna.items():
        if k not in ('candidates','budget_audits'): print(k, v)
    print('n candidates', len(mna['candidates']))
    print(json.dumps(mna['candidates'][:3],indent=0)[:1500])
    for a in mna['budget_audits']:
        print('--audit', {k:v for k,v in a.items() if k!='candidates'})
md=o['metadata']
print('--- metadata top keys by size')
for k,v in sorted(md.items(), key=lambda kv:-len(json.dumps(kv[1])))[:25]:
    print(k, type(v).__name__, len(json.dumps(v)))
