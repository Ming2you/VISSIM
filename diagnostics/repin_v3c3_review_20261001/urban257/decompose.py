"""Read-only4200s urban/ramp stock-time decomposition from saved observations."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,bisect,ctypes,ctypes.wintypes,csv,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
END=4200
RUNS={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
      'current':Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc')}
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected'
PINS={}
REFERENCE_SUMMARY=None
def read(p):
 b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 HERE.mkdir(parents=True,exist_ok=True)
 assert not (HERE/'summary.json').exists()
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
 k.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
 membership=physical_membership_from_ledger(read(I/'scenario/control_area_membership_213a5d.json'))
 geo=read(I/'port_gain/geometry.json')
 mainline={str(x['link']):road for road,seq in geo['chains'].items() for x in seq}
 on={str(b['connector']) for b in geo['boundaries'] if b['kind']=='ramp'}
 off={str(b['connector']) for b in geo['boundaries'] if b['kind']=='offramp'}
 links=sorted(membership,key=int); index={s:i for i,s in enumerate(links)}
 times=np.array([0,1]+list(range(150,END+1,150)),float)
 data={};lanes={};raw_frames={};commands={};provs={}
 for arm,run in RUNS.items():
  name=f'sdmpc31_{"nc" if arm=="nc" else "sdmpc"}9000_s29'
  provs[arm]=read(run/f'run_provenance_{name}.json')
  n=np.zeros((len(times),len(links)),int);st=n.copy();lanes[arm]={};raw_frames[arm]={}
  commands[arm]={}
  for j,t in enumerate(times[1:],1):
   d=run/f'decisions_{name}';s=read(d/f'state_{int(t):06d}.json');v=s['vehicle_records']
   assert s['sim_sec']==t==v['paused_at_sim_sec']==v['capture_sim_sec_before']==v['capture_sim_sec_after']
   assert v['complete'] and not v['unobservable_count'];rows=v['records'];raw_frames[arm][int(t)]=rows
   assert len(rows)==v['record_count']==s['total_vehicles']==len({x['veh_no'] for x in rows})
   bylink=Counter(str(x['link_no']) for x in rows)
   assert dict(bylink)=={str(l):c for l,c in v['full_network_link_counts'].items() if c}
   for x in rows:
    link=str(x['link_no']);c=index[link];n[j,c]+=1;st[j,c]+=bool(x['stopped'])
    lane=f"{link}:{x['lane_no']}";entry=lanes[arm].setdefault(lane,dict(n=[0]*len(times),stopped=[0]*len(times)))
    entry['n'][j]+=1;entry['stopped'][j]+=bool(x['stopped'])
   a=d/f'action_{int(t):06d}.csv'
   if a.exists():
    raw=a.read_bytes();PINS[str(a)]=hashlib.sha256(raw).hexdigest()
    commands[arm][int(t)]=[r for r in csv.DictReader(raw.decode('utf-8-sig').splitlines()) if r['kind']!='vsl']
  data[arm]=dict(n=n,stopped=st)
 for t in (1,150,300,450,600,750,900):assert raw_frames['nc'][t]==raw_frames['current'][t]
 for key in ('network','demand_profile','control_mapping','signal_group_plan','generated_vbs_config'):
  assert provs['nc']['files'][key]['sha256']==provs['current']['files'][key]['sha256']
 net=Path(provs['current']['files']['network']['path']);PINS[str(net)]=hashlib.sha256(net.read_bytes()).hexdigest()
 assert PINS[str(net)]==provs['current']['files']['network']['sha256']
 tree=ET.parse(net); desc={x.get('no'):dict(name=x.get('name',''),lanes=len(x.findall('./lanes/lane')),from_link=x.find('fromLinkEndPt').attrib if x.find('fromLinkEndPt') is not None else None,to_link=x.find('toLinkEndPt').attrib if x.find('toLinkEndPt') is not None else None) for x in tree.findall('./links/link')}
 def integral(x):return ((x[1:]+x[:-1])*.5*np.diff(times)[:,None]/3600).sum(axis=0)
 totals={a:{k:integral(x) for k,x in v.items()} for a,v in data.items()}
 table=[]
 for l,i in index.items():
  category='outside' if not membership[l] else mainline.get(l) or ('on_ramp_connector' if l in on else 'off_ramp_connector' if l in off else 'urban_and_other_inside')
  row=dict(link=l,inside=membership[l],category=category,**desc.get(l,{}))
  for a in RUNS:
   row[a+'_ttt']=float(totals[a]['n'][i]);row[a+'_stopped_time']=float(totals[a]['stopped'][i]);row[a+'_end_n']=int(data[a]['n'][-1,i]);row[a+'_end_stopped']=int(data[a]['stopped'][-1,i])
  row['delta']=row['current_ttt']-row['nc_ttt'];row['delta_stopped']=row['current_stopped_time']-row['nc_stopped_time'];table.append(row)
 table.sort(key=lambda r:r['delta'],reverse=True)
 categories={}
 for cat in sorted({r['category'] for r in table}):
  rows=[r for r in table if r['category']==cat];categories[cat]={k:sum(r[k] for r in rows) for k in ('nc_ttt','current_ttt','delta','delta_stopped','nc_end_n','current_end_n')}
 inside_nonfw=[r for r in table if r['inside'] and r['category'] not in ('FW_E','FW_W')]
 expected=(read(REFERENCE_SUMMARY)['comparison_veh_h']['Omega_other']['delta_control_minus_nc']
           if REFERENCE_SUMMARY is not None else 100.60416666666674)
 assert abs(sum(r['delta'] for r in inside_nonfw)-expected)<1e-8
 summary=dict(end_sec=END,method='150s instantaneous native saved observations; trapezoid; not completed9000',categories=categories,top_increases=inside_nonfw[:25],top_reductions=sorted(inside_nonfw,key=lambda r:r['delta'])[:12],source_sha256=PINS)
 save(HERE/'summary.json',summary);save(HERE/'links.json',table);save(HERE/'lanes.json',dict(times=times.tolist(),arms=lanes));save(HERE/'commands.json',commands)
 np.savez_compressed(HERE/'stocks.npz',times=times,links=np.array(links),**{a+'_'+k:x for a,v in data.items() for k,x in v.items()})
 # Small current key-link records for targeted position/queue checks; no other raw data duplicated.
 focus={r['link'] for r in inside_nonfw[:12]}|on|off
 save(HERE/'focus_records.json',{a:{str(t):[r for r in rows if str(r['link_no']) in focus] for t,rows in ts.items()} for a,ts in raw_frames.items()})
 print(json.dumps(dict(categories=categories,top_increases=inside_nonfw[:15],top_reductions=summary['top_reductions'][:7]),ensure_ascii=False))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--end',type=int,default=END)
 parser.add_argument('--current-run',type=Path,default=RUNS['current'])
 parser.add_argument('--out',type=Path,default=HERE)
 parser.add_argument('--reference-summary',type=Path)
 args=parser.parse_args();assert 900<=args.end<=9000 and args.end%150==0
 END,HERE=args.end,args.out.resolve();RUNS['current']=args.current_run.resolve()
 REFERENCE_SUMMARY=args.reference_summary
 main()
