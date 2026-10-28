import json, csv
d=json.load(open('meter_inv_all.json',encoding='utf-8'))
OWN={'RM_C10480':'FW_W','RM_C10482':'FW_W','RM_C10646':'FW_W','RM_C10644':'FW_W','RM_C10639':'FW_E','RM_C10681':'FW_E','RM_C10490':'FW_E','RM_C10484':'FW_E'}
LAN={'RM_C10482':2,'RM_C10681':2}
order=['RM_C10639','RM_C10681','RM_C10490','RM_C10484','RM_C10480','RM_C10482','RM_C10646','RM_C10644']
runs=['VA:v3c3-s31','VA:v3c3-s41','VA:v3c3-s43','J1:v3c3-s31r','J1:v3c3-s41','J1:v3c3-s43']
def f(x):
    if x==0: return '0'
    a=abs(x)
    if a<1e-12: return '%.0e'%x
    if a<1e-3: return '%.1e'%x
    return '%.3f'%x if a<1 else '%.2f'%x
print('### T1 block0 effective gradient (central: own+ext+price) neg/~0/pos · median · min ; any-block max positive ; max|step|')
for mid in order:
    cells=[]
    for r in runs:
        pm=d['runs'][r]['per_meter'][mid]; c=pm['cen_eff_b0']; ca=pm['cen_eff_all']; st=pm['cen_step_all']
        cells.append('%d/%d/%d · %s · %s ; %s ; %s'%(c['n_neg'],c['n_zero'],c['n_pos'],f(c['median']),f(c['min']),f(ca['max']),f(max(abs(st['min']),abs(st['max'])))))
    print('| %s (%s, %d차로) | %s |'%(mid,OWN[mid],LAN.get(mid,1),' | '.join(cells)))
print()
print('### T2 PFO own gradient block0 neg/~0/pos · min ; any-block max')
for mid in order:
    cells=[]
    for r in runs:
        pm=d['runs'][r]['per_meter'][mid]; p=pm['pfo_own_b0']; pa=pm['pfo_own_all']
        cells.append('%d/%d/%d · %s ; %s'%(p['n_neg'],p['n_zero'],p['n_pos'],f(p['min']),f(pa['max'])))
    print('| %s | %s |'%(mid,' | '.join(cells)))
print()
print('### T3 predicted merge (T..T+450) median/max vs svc g9/g8 ; decisions > g9 / > g8')
for mid in order:
    cells=[]
    for r in runs:
        pm=d['runs'][r]['per_meter'][mid]; p=pm['pred_merge']
        cells.append('%d / %d ; %d / %d'%(round(p['median']),round(p['max']),pm['n_pred_merge_gt_svc_g9'],pm['n_pred_merge_gt_svc_g8']))
    s9=LAN.get(mid,1)*3.69*360; s8=LAN.get(mid,1)*3.24*360
    print('| %s | %.1f / %.1f | %s |'%(mid,s9,s8,' | '.join(cells)))
print()
print('### T4 dNUF/dz (scaled /1000 veh/h) block0 max |.|')
for mid in order:
    cells=[]
    for r in runs:
        pm=d['runs'][r]['per_meter'][mid]; a=pm['dNUF_scaled_b0']
        cells.append(f(max(abs(a['min']),abs(a['max']))))
    print('| %s | %s |'%(mid,' | '.join(cells)))
# top positive rows
rows=list(csv.DictReader(open('meter_rows_all.csv',encoding='utf-8')))
print()
print('### top positive gradients (any block) per run')
for r in runs:
    rr=[x for x in rows if x['run']==r]
    def v(x,k):
        try: return float(x[k])
        except: return -1e9
    best=max(rr,key=lambda x:max(v(x,'pfo_own_g_any_block_max'),v(x,'cen_eff_any_block_max')))
    print(r,best['T'],best['meter'],'pfo',best['pfo_own_g_any_block_max'],'cen',best['cen_eff_any_block_max'],'step',best['cen_step_any_absmax'],'pred',best['pred_merge_T_T450'])
# sel green and csv check
bad=[x for x in rows if not (x['sel_green_b0']=='10.0' and x['csv_green_sec']=='10.0' and x['csv_rate_vph']=='900.0')]
print('rows not 10/900:',len(bad),'of',len(rows))
print('future-block non-10:',sum(1 for x in rows if x['sel_green_b1'] not in ('','10.0') or x['sel_green_b2'] not in ('','10.0')))
print('json ramp_metering values', sorted({(x['meter'],x['json_ramp_metering'],x['csv_group_rate_vph']) for x in rows}))
for r in runs:
    rb=d['runs'][r]['signal_readback_meter']; print(r,'readback',rb if len(str(rb))<300 else sum(rb.values()))
