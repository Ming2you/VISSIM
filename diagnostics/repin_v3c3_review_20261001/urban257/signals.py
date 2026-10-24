"""Bounded read-only native signal and saved detector diagnosis, through4200."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import csv, ctypes, hashlib, json, sys, re
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.validate_native_signal_record import parse_ldp_columns
RUNS={'nc':Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
      'current':Path('D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000/sdmpc')}
read=lambda p:json.loads(p.read_bytes())
def save(name,x): (HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
 # Correct diagnostic category labels only; no changed observations or totals.
 rows=read(HERE/'links.json');summary=read(HERE/'summary.json')
 for r in rows:
  if not r['inside']:r['category']='outside'
 cats={}
 for cat in sorted({r['category'] for r in rows}):
  cats[cat]={key:sum(r[key] for r in rows if r['category']==cat) for key in ('nc_ttt','current_ttt','delta','delta_stopped','nc_end_n','current_end_n')}
 assert abs(cats['outside']['delta']-50)<1e-8
 assert abs(sum(v['delta'] for c,v in cats.items() if c not in ('outside','FW_E','FW_W'))-100.604166666667)<1e-8
 summary['categories']=cats;save('links.json',rows);save('summary.json',summary)
 out={};audits={}
 groups={1001:list(range(1,9)),1004:list(range(1,9)),9106:[1]}
 addresses={'40_left':('1001:3',[960164]),'52_straight':('1004:6',[960203,960204,960205]),
  '52_left':('1004:1',[960206]),'46_straight':('1004:4',[960208,960209,960210]),
  '10681_head':('9106:1',[960217,960218])}
 for arm,run in RUNS.items():
  name='sdmpc31_'+('nc' if arm=='nc' else 'sdmpc')+'9000_s29';d=run/('decisions_'+name)
  # The live LDP writer buffers its tail. Validate only a complete historical
  # prefix shared by all three controllers; never flush or truncate live files.
  frames={t:{} for t in range(1,4051)};pins={}
  for sc,sgs in groups.items():
   p=run/'vissim_eval'/f'{name}_{sc}_001.ldp';raw=p.read_bytes();prefix=[]
   for line in raw.splitlines(keepends=True):
    if re.match(rb'\s*\d+\.',line) and float(line[:7])>4050:break
    prefix.append(line)
   b=b''.join(prefix);parsed=parse_ldp_columns(b,sc,sgs,1,4050)
   for t,v in parsed['frames'].items():frames[t].update(v)
   pins[str(p)]={'prefix_sha256':hashlib.sha256(b).hexdigest(),'prefix_bytes':len(b),'read_file_bytes':len(raw)}
  record={'start_sec':1,'end_sec':4050,'complete':True,'pins':pins,'excluded_live_tail_after_sec':4050};rows=[]
  for t in range(150,4201,150):
   s=read(d/f'state_{t:06d}.json');o=s['obs150'];assert o['window']=={'start_s':t-150,'end_s':t}
   row={'end':t}
   for label,(key,detectors) in addresses.items():
    row[label]={'head_crossings':sum(o['detectors'][str(x)] for x in detectors),
      'native_seconds':dict(Counter(frames[i][key] for i in range(t-149,t+1))) if t<=4050 else None}
   row['10681_arrival']=sum(o['detectors'][str(x)] for x in [960276,960277]);rows.append(row)
  out[arm]={'native_coverage':record,'windows':rows,
   '10681_states_3151_4050':dict(Counter(frames[i]['9106:1'] for i in range(3151,4051)))}
  if arm=='current':
   for t in range(2700,4051,150):
    p=d/f'action_{t:06d}.joint.progress.jsonl';entries=[json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
    small=[]
    for entry in entries:
     if 'candidates' in entry and isinstance(entry['candidates'],list):
      selected=[r for r in entry['candidates'] if isinstance(r,dict) and r.get('candidate','').startswith('RM_C10681:')]
      if selected:small.append({'stage':entry.get('stage'),'selected':entry.get('selected'),'rows':selected})
    audits[t]=small
 save('native_signals_and_flows.json',out);save('rm10681_audits.json',audits)
 for a,v in out.items():
  print(a,'10681 states',v['10681_states_3151_4050'])
  for row in v['windows']:
   if row['end']>=2850:print(a,row)
 print('RM audits',audits)
if __name__=='__main__':main()
