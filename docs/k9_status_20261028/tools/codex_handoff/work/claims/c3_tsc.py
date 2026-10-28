# R_CLAIMS c3: TSC per-SC offset changes, green sums, distance from freeway_only constant plan (read only)
import csv, collections, statistics as st
E='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence/'
r=list(csv.DictReader(open(E+'decision_greens.csv',encoding='utf-8-sig')))
def S(cond):
    d=collections.defaultdict(dict)
    for x in r:
        if x['condition']==cond and x['kind']=='signal':
            d[x['id']][int(x['sim_sec'])]=tuple(float(x[k]) for k in ['p1','p2','p3','p4','offset'])
    return d
base=S('freeway_only')
for cond in ['joint','off','window','urban_only']:
    d=S(cond); print('=====',cond)
    tot_off_ch=0; tot=0
    for sc in sorted(d):
        ts=sorted(t for t in d[sc] if t<8100)
        offs=[d[sc][t][4] for t in ts]; gs=[sum(d[sc][t][:4]) for t in ts]
        ch=[abs(b-a) for a,b in zip(offs,offs[1:])]
        nch=sum(1 for c in ch if c>1e-9); tot_off_ch+=nch; tot+=len(ch)
        b=base[sc][900]
        dg=[sum(abs(d[sc][t][k]-b[k]) for k in range(4)) for t in ts]
        print(f'  {sc:7s} offset changes {nch}/{len(ch)} median|d|={st.median(ch):6.2f}  green-sum range {min(gs):6.2f}-{max(gs):6.2f} (fw_only const {sum(b[:4]):.1f}) mean L1 green dist to fw_only plan {st.mean(dg):6.2f}')
    print('  total offset changes',tot_off_ch,'/',tot)
