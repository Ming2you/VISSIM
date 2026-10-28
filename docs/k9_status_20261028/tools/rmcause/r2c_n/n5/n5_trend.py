import json,glob
FE=['RM_C10639','RM_C10681','RM_C10490','RM_C10484']
def d(rows,name):
    v=[c['delta_veh_h'] for c in rows if c['candidate']==name]
    return min(v) if v else None
f=lambda x:('%+.4f'%x) if x is not None else '   —   '
print('T     vsl(b0/b1/b2)  ref10480 refFWE(39/81/90/84)   selected            FWE:t     FWE:r     84:t     90:t     81:t     39:t   10480:t  10480:r   FWW:t   n_cand')
for p in sorted(glob.glob('ext/n5_*.json')):
    r=json.load(open(p,encoding='utf-8'))
    a=r['audit']; rows=a['candidates']
    v0=r['vsl_non110'].get('FW_E__seg13',110); fb=[b['vsl_non110'].get('FW_E__seg13',110) for b in r['future_blocks']]
    rg=r['reference_meter_green']
    ref=[int(rg['rw_meter_green_'+m]) for m in FE]
    print(f"{r['T']:5d} {int(v0)}/{'/'.join(str(int(x)) for x in fb):8s} {int(rg['rw_meter_green_RM_C10480']):3d}   {str(ref):18s} {str(a['selected']):20s}",
          f(d(rows,'FW_E:tighten')),f(d(rows,'FW_E:release')),f(d(rows,'RM_C10484:tighten')),f(d(rows,'RM_C10490:tighten')),f(d(rows,'RM_C10681:tighten')),f(d(rows,'RM_C10639:tighten')),f(d(rows,'RM_C10480:tighten')),f(d(rows,'RM_C10480:release')),f(d(rows,'FW_W:tighten')), len(rows))
