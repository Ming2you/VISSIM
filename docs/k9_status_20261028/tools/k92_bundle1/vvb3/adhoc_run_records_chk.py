import json,sys,os
sys.path.insert(0,'.'); import vvb3_recalc as R
nc=lambda s: os.path.normcase(os.path.normpath(s))
want={'off':{'VB-31':('config_n31_v2.json','d0f9ef39'),'VB-43':('config_n31_v2_stopline_observed_full_k91.json','5f0d0e40'),'VB-41':('config_n31_v2_stopline_observed_full_k91.json','5f0d0e40'),'VB-41w':('config_n31_v2_stopline_observed_full_k91.json','5f0d0e40')},
      'b1':{'VB-31':('config_n31_v2_k92b1.json','c8e3ee2c'),'VB-43':('config_n31_v2_stopline_observed_full_k91_k92b1.json','65cac7ea'),'VB-41':('config_n31_v2_stopline_observed_full_k91_k92b1.json','65cac7ea'),'VB-41w':('config_n31_v2_stopline_observed_full_k91_k92b1.json','65cac7ea')}}
bad_t=bad_p=n=ctl_bad=hooked_bad=0
for arm in ('off','b1'):
  for c in R.CHAINS:
    ts=c['off'] if arm=='off' else c['times']
    for i,T in enumerate(ts):
      P=R.dec_paths(c['key'],arm,T); rr=R.jload(P['run']); n+=1
      nm,sh=want[arm][c['chain']]
      if not (rr['tuning'].endswith(nm) and rr['tuning_sha256'].startswith(sh)): bad_t+=1; print('tuning',c['chain'],arm,T,rr['tuning'])
      exp = (None if T==1 else str(R.rr_dir(c['run'])/('action_%06d.json'%(T-150)))) if i==0 else str(P['dec']/('action_%06d.json'%ts[i-1]))
      got=rr.get('previous')
      ok=(got is None) if exp is None else (got is not None and nc(got)==nc(exp))
      if not ok: bad_p+=1; print('prev',c['chain'],arm,T,got,exp)
      if rr.get('controller')!=('no-control' if T<900 else 'wu-link'): ctl_bad+=1
      if rr.get('hooked') is not True: hooked_bad+=1
print('decisions',n,'tuning_bad',bad_t,'prev_bad',bad_p,'controller_bad',ctl_bad,'hooked_bad',hooked_bad)
v9=json.load(open(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/stages/V9.json',encoding='utf-8')); print({k:v for k,v in v9.items() if k in ('n_compared','equal')})
st=[l for l in open(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/steps.jsonl',encoding='utf-8') if 'V9' in l]; print(st[-1][:200])
