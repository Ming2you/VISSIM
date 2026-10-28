import json,re
G=r'D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
O=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/obs150/vsl_cohorts_%06d.json'
g=json.load(open(G,encoding='utf-8'))
lk={c['cell']:c['lane_km'] for c in g['cells'] if c['road']=='FW_E'}
cells=list(range(8,27))
print('cell   '+' '.join(f'{c:>5d}' for c in cells))
print('lanekm '+' '.join(f'{lk[c]:5.2f}' for c in cells))
res={}
for T in [1350,1500,1650,1800,1950,2100]:
    ob=json.load(open(O%T,encoding='utf-8'))['cohorts']['FW_E']
    st=[sum(x.values()) for x in ob]
    print(f'obs@{T}  '+' '.join(f'{st[c]/lk[c]:5.1f}' for c in cells), ' 90-tagged cells:', [i for i,x in enumerate(ob) if any(k!="110.0" and v>0.5 for k,v in x.items())])
    r=json.load(open('ext/n5_%06d.json'%T,encoding='utf-8'))
    ph=r['tangent'][0]['phys']
    times=sorted({int(k.split('/')[1]) for k in ph})
    for t in times:
        d={int(k.split('/')[4]):-v for k,v in ph.items() if k.startswith(f'physical/{t}/freeway_density/FW_E/')}
        q={k.split('/')[3]:-v for k,v in ph.items() if k.startswith(f'physical/{t}/ramp_queue/')}
        print(f' pred{T}->{t} '+' '.join(f'{d.get(c,float("nan")):5.1f}' for c in cells), ' rampQ', {k[4:]:round(v,1) for k,v in q.items()})
