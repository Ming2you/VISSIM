import json, csv, statistics
d=json.load(open('meter_inv_all.json',encoding='utf-8'))
OWN={'RM_C10480':'FW_W','RM_C10482':'FW_W','RM_C10646':'FW_W','RM_C10644':'FW_W','RM_C10639':'FW_E','RM_C10681':'FW_E','RM_C10490':'FW_E','RM_C10484':'FW_E'}
out={}
print('== run-level')
for lab,r in d['runs'].items():
    m=r['meta']
    print(lab, 'joint',r['joint_files'],'runner rows',r['runner_meter_rows'],'distinct',len(r['runner_meter_distinct']), 'readback',{k.split('|')[1]+'/'+k.split('|')[2]:0 for k in r['signal_readback_meter']}.keys().__len__())
    print('  readback states', sorted({(k.split('|')[1],k.split('|')[2]) for k in r['signal_readback_meter']}), 'n', sum(r['signal_readback_meter'].values()))
    print('  meta', {k:v for k,v in m.items() if not k.startswith('allowed')})
    print('  allowed', {k:v for k,v in m.items() if k.startswith('allowed')})
    print('  pfo',r['pfo_status'],'cen',r['central_candidate_status'])
    for k in ('final_nuf_residual','final_np_residual','raw_nuf_residual_veh_h_each_iteration','raw_np_residual_veh_each_iteration'):
        v=r[k]; print('  ',k, {x:round(v[x],1) if isinstance(v[x],float) else v[x] for x in ('n','min','median','max','n_pos')})
    print('  dual nonzero dec',r['decisions_with_nonzero_dual'],'meter price nonzero',r['meter_price_gradient_nonzero_entries'])
print('== per meter')
hdr=['run','meter','own','pfo_b0 neg/0/pos','pfo_b0 med','pfo_b0 min','pfo_all max','cen_eff_b0 med','cen_eff_b0 min','cen_eff_all max','n>0.5','step absmax','pred med','pred max','>g9','>g8','sel b0/b1/b2','written']
rows=[]
for lab,r in d['runs'].items():
    for mid,pm in r['per_meter'].items():
        p=pm['pfo_own_b0']; c=pm['cen_eff_b0']; pa=pm['pfo_own_all']; ca=pm['cen_eff_all']; st=pm['cen_step_all']; pr=pm['pred_merge']
        sel=pm['selected_green_counts']
        rows.append([lab,mid,OWN[mid],'%d/%d/%d'%(p['n_neg'],p['n_zero'],p['n_pos']),'%.2e'%p['median'],'%.3g'%p['min'],'%.2g'%pa['max'],'%.2e'%c['median'],'%.3g'%c['min'],'%.2g'%ca['max'],pm['n_pfo_own_gt_0.5']+pm['n_cen_eff_gt_0.5'],'%.1e'%max(abs(st['min']),abs(st['max'])),round(pr['median']),round(pr['max']),pm['n_pred_merge_gt_svc_g9'],pm['n_pred_merge_gt_svc_g8'],';'.join('%s:%d'%(k,v) for k,v in sel.items()),';'.join('%s:%d'%(k,v) for k,v in pm['written_csv_counts'].items())])
w=csv.writer(open('per_meter_summary.csv','w',encoding='utf-8',newline=''))
w.writerow(hdr); w.writerows(rows)
for r in rows: print(' | '.join(str(x) for x in r))
