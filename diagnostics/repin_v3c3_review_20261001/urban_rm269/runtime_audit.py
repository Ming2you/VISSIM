"""Read completed decision timing receipts; no large action JSON, FZP or COM."""
from pathlib import Path
import collections, hashlib, json, re, statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUNS={
 'expanded036_r2':'D:/VISSIM_runs/20260930_expanded036_s29_9000_r2',
 'ctg':'D:/VISSIM_runs/20260930_ctg_s29_9000',
 'fixed90':'D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000',
 'rm233_235':'D:/VISSIM_runs/20261005_rm233_235_fixed90_s29_9000',
 'shared124':'D:/VISSIM_runs/20261005_shared124_fixed90_s29_9000',
 'min2':'D:/VISSIM_runs/20261006_min2_storage90_fixed90_s29_9000',
 'storage40':'D:/VISSIM_runs/20261006_urban_storage40_fixed90_s29_9000',
 'head47':'D:/VISSIM_runs/20261007_goal8_head47right_verified_s29_8100',
 'prevention':'D:/VISSIM_runs/20261007_goal8_prevention_s29_8100',
 'coupling268':'E:/VISSIM_runs/20261008_coupling268_window_s29_8100',
}

def mean(rows,key):
 vals=[r[key] for r in rows if isinstance(r.get(key),(int,float))]
 return statistics.mean(vals) if vals else None

def main():
 result={};pins={}
 for label,path in RUNS.items():
  run=Path(path)/'sdmpc'
  dirs=list(run.glob('decisions_*'))
  if len(dirs)!=1:
   result[label]={'unavailable_decision_dirs':len(dirs)};continue
  folder=dirs[0];rows=[]
  for file in sorted(folder.glob('action_*.decision_budget.json')):
   t=int(file.name.split('_')[1].split('.')[0]);raw=file.read_bytes();budget=json.loads(raw)
   if t<900 or t>6150 or not budget.get('output_completed'):continue
   pins[str(file)]=hashlib.sha256(raw).hexdigest()
   progress=folder/f'action_{t:06d}.joint.progress.jsonl'
   if not progress.exists():continue
   raw=progress.read_bytes();events=[json.loads(s) for s in raw.decode('utf-8-sig').splitlines() if s.strip()]
   pins[str(progress)]=hashlib.sha256(raw).hexdigest()
   r=dict(time=t,wall_sec=budget['wall_sec'],main_process_cpu_sec=budget['cpu_sec'],
    load_sec=budget.get('inclusive_scopes',{}).get('load_and_model_prepare',{}).get('wall_sec'),
    finalize_sec=budget.get('inclusive_scopes',{}).get('final_action_validation_and_output',{}).get('wall_sec'))
   counts=collections.Counter(e['stage'] for e in events)
   r.update(candidate_caps=counts['sdmpc_candidate_start'],pfo_accepted=counts['sdmpc_pfo_step_accepted'],
     sdmpc_accepted=counts['sdmpc_step_accepted'],completed=bool(counts['sdmpc_completed']),
     scalar_predictions=0,derivative_predictions=0,scalar_batch_wall=0.,derivative_batch_wall=0.,uncached_tangent_wall=0.)
   pending=None;tangent=None
   for e in events:
    stage=e['stage']
    if stage=='sdmpc_pfo_start':r['pfo_max_iterations']=e.get('max_iterations')
    if stage=='sdmpc_pfo_done':r.update(pfo_wall=e.get('seconds'),pfo_converged=e.get('converged'))
    if stage=='sdmpc_surrogate_batch_start':pending=e
    if stage=='sdmpc_surrogate_batch_done' and pending is not None:
     kind='derivative' if pending.get('derivative_predictions') else 'scalar'
     r[kind+'_predictions']+=e.get('predictions',pending.get('predictions',0))
     r[kind+'_batch_wall']+=e['elapsed_sec']-pending['elapsed_sec'];pending=None
    if stage=='sdmpc_tangent_start':tangent=e['elapsed_sec']
    if stage=='sdmpc_tangent_done' and tangent is not None:
     # The saved "seconds" can be a cached receipt: use new elapsed interval.
     r['uncached_tangent_wall']+=e['elapsed_sec']-tangent;tangent=None
    if stage=='sdmpc_meter_neighbors_start':r['meter_start']=e['elapsed_sec']
    if stage=='sdmpc_meter_neighbors_done':r['meter_wall']=e['elapsed_sec']-r['meter_start']
   r['action_json_mb']=sum((folder/f'action_{t:06d}{suffix}').stat().st_size for suffix in ['.json','.joint.json'] if (folder/f'action_{t:06d}{suffix}').exists())/1e6
   rows.append(r)
  keys=['wall_sec','load_sec','finalize_sec','pfo_wall','meter_wall','derivative_batch_wall','scalar_batch_wall','uncached_tangent_wall','candidate_caps','pfo_accepted','sdmpc_accepted','scalar_predictions','derivative_predictions','action_json_mb']
  result[label]={'folder':str(folder),'decisions':len(rows),'first':rows[0]['time'] if rows else None,'last':rows[-1]['time'] if rows else None,
     'means':{k:mean(rows,k) for k in keys},'rows':rows,
     'PFO_max':sorted(set(r['pfo_max_iterations'] for r in rows if 'pfo_max_iterations' in r)),
     'PFO_converged_count':sum(r.get('pfo_converged',False) for r in rows)}
  print(label,json.dumps({k:v for k,v in result[label].items() if k not in ['folder','rows']}))
 payload={'runs':result,'source_sha256':pins,'limitations':['Matched decision timestamps900..6150; distinct states/configs and machine contention are not controlled.','Per-batch wall times include worker launch/serialization; PFO and meter stages INCLUDE their batches, so must not sum categories.','CPU receipt excludes worker CPU; cached tangent receipt seconds are not charged again.','Accepted step counts are not convergence; PFO max and SDMPC cap-local iterations are separate.']}
 (HERE/'runtime_audit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
