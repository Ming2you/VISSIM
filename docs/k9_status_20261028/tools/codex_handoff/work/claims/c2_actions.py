# R_CLAIMS c2: RM green distributions, held decisions, TSC variety from decision_greens.csv (read only)
import csv, collections, statistics as st
E='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence/'
r=list(csv.DictReader(open(E+'decision_greens.csv',encoding='utf-8-sig')))
conds=['nc','joint','window','off','freeway_only','urban_only']
for c in conds:
    rm=[x for x in r if x['condition']==c and x['kind']=='ramp_meter']
    sg=[x for x in r if x['condition']==c and x['kind']=='signal']
    trm=sorted({int(float(x['sim_sec'])) for x in rm}); tsg=sorted({int(float(x['sim_sec'])) for x in sg})
    print(f'===== {c}: RM rows {len(rm)} times {len(trm)} [{trm[0] if trm else None}..{trm[-1] if trm else None}] ; SG rows {len(sg)} times {len(tsg)} [{tsg[0] if tsg else None}..{tsg[-1] if tsg else None}]')
    print('   RM readback', dict(collections.Counter(x['readback'] for x in rm)), ' SG readback', dict(collections.Counter(x['readback'] for x in sg)))
    R=collections.defaultdict(dict)
    for x in rm: R[x['id']][int(float(x['sim_sec']))]=float(x['green_sec'])
    for i in sorted(R):
        ser=R[i]; ctrl=[(t,g) for t,g in sorted(ser.items()) if 900<=t<8100]
        g=[v for _,v in ctrl]
        if not g: continue
        dist=dict(sorted(collections.Counter(g).items()))
        below=[t for t,v in ctrl if v<10]
        ch=sum(1 for a,b in zip(g,g[1:]) if a!=b)
        # by hour blocks
        blocks={}
        for lo in range(900,8100,1800):
            gg=[v for t,v in ctrl if lo<=t<lo+1800]; blocks[f'{lo}-{lo+1800}']=round(st.mean(gg),2) if gg else None
        pre=[v for t,v in sorted(ser.items()) if t<900]; post=[v for t,v in sorted(ser.items()) if t>=8100]
        print(f'   {i}: n_ctrl={len(g)} dist={dist} mean={st.mean(g):.2f} n<10={len(below)} first<10={below[0] if below else "-"} last<10={below[-1] if below else "-"} changes={ch} pre900={sorted(set(pre))} at8100={post} block_means={blocks}')
    if sg:
        S=collections.defaultdict(dict)
        for x in sg: S[int(float(x['sim_sec']))][x['id']]=tuple(x[k] for k in ['p1','p2','p3','p4','offset'])
        ids=sorted(S[tsg[0]])
        print('   SC count', len(ids))
        same=[t2 for t1,t2 in zip(tsg,tsg[1:]) if S[t1]==S[t2]]
        same_any=[(t2,sum(1 for i in ids if S[t1].get(i)==S[t2].get(i))) for t1,t2 in zip(tsg,tsg[1:]) if any(S[t1].get(i)==S[t2].get(i) for i in ids)]
        # RM equality at same times
        RMt=collections.defaultdict(dict)
        for x in rm: RMt[int(float(x['sim_sec']))][x['id']]=x['green_sec']
        same_rm=[t for t in same if RMt.get(t)==RMt.get(tsg[tsg.index(t)-1])]
        print(f'   all-17-SC plan identical to previous decision at: {same}  (with RM also identical: {same_rm})')
        print(f'   partial SC repeats (time, #SC equal): {[x for x in same_any if x[1]<len(ids)]}')
        uniq={i:len({S[t][i] for t in tsg}) for i in ids}
        uniq_ctrl={i:len({S[t][i] for t in tsg if t<8100}) for i in ids}
        print('   unique plans per SC (all rows)', uniq)
        print('   unique plans per SC (900..7950)', uniq_ctrl)
        # value ranges
        for k_i,k in enumerate(['p1','p2','p3','p4','offset']):
            vals=[float(S[t][i][k_i]) for t in tsg for i in ids if S[t][i][k_i]!='']
            if vals: print(f'   {k}: min={min(vals):.3f} max={max(vals):.3f} n_zero={sum(1 for v in vals if v==0)} n={len(vals)}')
        if len({S[t][i] for t in tsg for i in ids})<=40:
            for i in ids: print('     const plan', i, S[tsg[0]][i])
            break_flag=True
        # last row equals?
        print('   row at 8100 equals row at 7950 for all SC:', S.get(8100)==S.get(7950))
