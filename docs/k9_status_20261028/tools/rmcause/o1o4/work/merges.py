# merges per 900 s block (veh/h) at FW_E on-ramps and key crossings, W/N/V (read-only, fwe_scan outputs)
import json
R='C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/rmcause'
F={'W':json.load(open(R+'/o1o4/scan/w264_s29.json')),'N':json.load(open(R+'/phys/scan/cf_s29_none.json')),'V':json.load(open(R+'/o1o4/scan/vsl_s29.json'))}
out={}
for a,d in F.items():
    r={}
    for k in ['10639','10681','10490','10484']:
        r['merge_'+k]=[round(sum(d['merge'][k][w0:w0+15])*4) for w0 in range(0,150,15)]
    for X in ['300','4200','5300','6800','7700']:
        r['q'+X]=[round(sum(d['cross'][X][w0:w0+15])*4) for w0 in range(0,150,15)]
    r['div_10483']=[round(sum(d['div']['10483'][w0:w0+15])*4) for w0 in range(0,150,15)]
    r['ins_1098']=[round(sum(d['ins'][w0:w0+15])*4) for w0 in range(0,150,15)]
    out[a]=r
json.dump(out,open(R+'/o1o4/work/merges_900.json','w'),indent=1)
for k in out['W']:
    print(k.ljust(12), ' '.join(f"{out['W'][k][i]}/{out['N'][k][i]}/{out['V'][k][i]}".rjust(16) for i in range(1,9)))
