import json
G=r'D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
O=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29/obs150/vsl_cohorts_%06d.json'
g=json.load(open(G,encoding='utf-8'))
lk={c['cell']:c['lane_km'] for c in g['cells'] if c['road']=='FW_E'}
def dens(st,cells): return sum(st[c] for c in cells)/sum(lk[c] for c in cells)
def dd(rows,n):
    v=[c['delta_veh_h'] for c in rows if c['candidate']==n]; return min(v) if v else None
f=lambda x:('%+.4f'%x) if x is not None else 'n/a'
print('T | VSL90 blocks | obs rho 9-13(B1) 14-18 19-24(B2) 22-23 | pred end-horizon rho 16-18 19-24 (tangent0) | pred rampQ 10490/10484 end | FWE:t 90:t 84:t')
for T in range(900,2551,150):
    ob=json.load(open(O%T,encoding='utf-8'))['cohorts']['FW_E']; st=[sum(x.values()) for x in ob]
    r=json.load(open('ext/n5_%06d.json'%T,encoding='utf-8'))
    nb=(1 if r['vsl_non110'] else 0)+sum(1 for b in r['future_blocks'] if b['vsl_non110'])
    ph=r['tangent'][0]['phys']; tend=max(int(k.split('/')[1]) for k in ph)
    pd={int(k.split('/')[4]):-v for k,v in ph.items() if k.startswith(f'physical/{tend}/freeway_density/FW_E/')}
    pden=lambda cells: sum(pd[c]*lk[c] for c in cells)/sum(lk[c] for c in cells)
    q={k.split('/')[3]:-v for k,v in ph.items() if k.startswith(f'physical/{tend}/ramp_queue/')}
    rows=r['audit']['candidates']
    print(T,'|',nb,'|',round(dens(st,range(9,14)),1),round(dens(st,range(14,19)),1),round(dens(st,range(19,25)),1),round(dens(st,[22,23]),1),'|',tend,round(pden(range(16,19)),1),round(pden(range(19,25)),1),'|',round(q.get('RM_C10490',0),1),round(q.get('RM_C10484',0),1),'|',f(dd(rows,'FW_E:tighten')),f(dd(rows,'RM_C10490:tighten')),f(dd(rows,'RM_C10484:tighten')))
