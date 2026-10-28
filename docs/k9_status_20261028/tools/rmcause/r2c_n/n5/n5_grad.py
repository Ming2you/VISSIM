import json,glob
M=['RM_C10681','RM_C10490','RM_C10484','RM_C10480']
print('T vsl | per meter: ref | dTotal/dz(b0,b1,b2) | dFW_E/dz(b0) dPASSIVE/dz(b0) dUrban/dz(b0) dFW_W(b0)  [tangent point 0]')
for p in sorted(glob.glob('ext/n5_*.json')):
    r=json.load(open(p,encoding='utf-8'))
    if not r['tangent']: continue
    t=r['tangent'][0]; own=r['owners']; ax=r['meter_axes']
    cj=t['cost_jac_meter']
    v0=r['vsl_non110'].get('FW_E__seg13',110)
    out=[]
    for m in M:
        idx=[k for k,a in enumerate(ax) if a['key']==m]
        ref=ax[idx[0]]['ref']
        tot=[sum(row[k] for row in cj) for k in idx]
        k0=idx[0]
        fwe=cj[own.index('FW_E')][k0]; pas=cj[own.index('PASSIVE_OMEGA')][k0]; fww=cj[own.index('FW_W')][k0]
        urb=sum(cj[i][k0] for i,o in enumerate(own) if o.startswith('SC'))
        out.append(f"{m[4:]}:g{int(ref)} T[{tot[0]:+.3f},{tot[1]:+.3f},{tot[2]:+.3f}] E{fwe:+.3f} P{pas:+.3f} U{urb:+.3f} W{fww:+.3f}")
    print(r['T'], int(v0), ' | '.join(out))
