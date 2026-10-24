"""Independent count-by-frame integration; no controller/model imports."""
import argparse,collections,json,time
from pathlib import Path
S7={74,10699,2,10613,119,10702,24}
S19=S7|{10484,10490,10639,10681,10481,10483,10643,10682,129,31,68,70}
def integrate(p,end,inside):
 previous_t=0.;previous=collections.Counter();current_t=None;counts=collections.Counter();area=collections.Counter();rows=frames=0
 def commit(t,n):
  nonlocal previous_t,previous,frames
  dt=t-previous_t
  for k in set(previous)|set(n):area[k]+=(previous[k]+n[k])*dt/2/3600
  previous_t=t;previous=n.copy();frames+=1
 # Numeric rows and column identifiers are ASCII; preserve arbitrary header bytes.
 with p.open(encoding='latin-1',errors='strict')as f:
  for line in f:
   if line.startswith('$VEHICLE:'):
    fields=line.strip().split(':',1)[1].split(';');ti=fields.index('SIMSEC');li=fields.index('LANE\\LINK\\NO');break
  else:raise ValueError('Missing FZP header')
  for line in f:
   if not line.strip()or line.startswith('*'):continue
   parts=line.split(';',4);t=float(parts[ti])
   if t>end:break
   if current_t is not None and t!=current_t:commit(current_t,counts);counts=collections.Counter()
   current_t=t;counts[int(parts[li])]+=1;rows+=1
 if current_t is None:raise ValueError('Empty FZP')
 commit(current_t,counts)
 for k,n in previous.items():area[k]+=n*(end-previous_t)/3600
 return dict(rows=rows,frames=frames,last_sec=previous_t,tail_sec=end-previous_t,FW_E_7=sum(area[k]for k in S7),local_19=sum(area[k]for k in S19),Omega701=sum(area[k]for k in inside),whole_observed=sum(area.values()),definition='trapezoid counts from empty t=0; observed timestamps; hold last inventory through 8100; never convert residual to exit')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--bundle',type=Path,required=True);x=a.parse_args();b=x.bundle
 membership=json.loads((b/'derived/omega_membership_exact.json').read_text(encoding='utf-8-sig'));inside=set(map(int,membership['inside_links']));start=time.time()
 cache=b/'derived/independent_fzp_counts.json';out=json.loads(cache.read_text(encoding='utf-8'))if cache.exists()else{}
 for key,rel in [('nc','raw/nc'),('joint','raw/joint/sdmpc'),('window','raw/window/sdmpc'),('off','raw/off/sdmpc')]:
  if key in out:continue
  p=next((b/rel/'vissim_eval').glob('*.fzp'));out[key]=integrate(p,8100,inside);out[key]['file']=p.relative_to(b).as_posix();print(key,out[key],flush=True)
 out['seconds']=time.time()-start
 cache.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
