"""Read-only audits of a copied handoff; outputs use relative names and hashes."""
import argparse, collections, csv, hashlib, json, re, sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET

CFG='diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
S7=[74,10699,2,10613,119,10702,24]
S19=S7+[10484,10490,10639,10681,10481,10483,10643,10682,129,31,68,70]
SEALED={37,59,61,67}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def save(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csvout(p,rows):
 if not rows:return
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def audit(root):
 out=root/'derived';out.mkdir(exist_ok=True);code=root/'code';cfg=load(code/CFG)
 summary=load(root/'analysis/comparison/summary.json'); metrics=[];runmeta=[];actions={};greenrows=[]
 for name,cr in summary['conditions'].items():
  assert summary['seed']not in SEALED
  cache=root/'analysis/comparison'/name/'area_metrics.json';m=load(cache);links=m['physical_link_residence']
  vals={'FW_E_7':sum(links[str(i)]['ttt_veh_h']for i in S7),'local_19':sum(links[str(i)]['ttt_veh_h']for i in S19),
        'Omega701':cr['ttt_veh_h'],'outside_Omega_residence':cr['components_veh_h']['outside'],
        'network_sampled_residence':sum(x['ttt_veh_h']for x in links.values())}
  parts=summary['reporting_partition']['parts'][name]
  for key in ['urban_roads','urban','onramps_E','onramps_W','offramps']:vals[key]=parts[key]
  vals['Omega_minus_W_mainline']=vals['Omega701']-parts['FW_W']
  for key,v in vals.items():metrics.append(dict(evidence_class='[측정]',condition=name,seed=29,start_s=0,end_s=8100,metric=key,veh_h=v,source=cache.relative_to(root).as_posix(),source_sha256=sha(cache)))
 for row in metrics:
  baseline=next(x['veh_h']for x in metrics if x['condition']=='nc'and x['metric']==row['metric'])
  row.update(baseline_veh_h=baseline,delta_veh_h=row['veh_h']-baseline,change_percent=100*(row['veh_h']/baseline-1),improvement_percent=100*(1-row['veh_h']/baseline))
 csvout(out/'metrics_0_8100.csv',metrics);save(out/'metrics_0_8100.json',metrics)
 for name in ['nc','joint','window','off','freeway_only','urban_only']:
  run=root/'raw'/name
  if name!='nc':run=run/'sdmpc'
  provfile=next(run.glob('run_provenance*.json'));prov=load(provfile);assert prov['seed']not in SEALED
  text=(run/'launch.log').read_text(encoding='utf-8-sig',errors='replace');times=[x for x in text.splitlines()if 'START 'in x or ' OK 'in x]
  db=next(run.rglob('*.db'));con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
  sr=dict(con.execute('select * from SIMULATIONRUN').fetchone());con.close()
  np=load(run/'native_network_performance.json');n=np['native'];horizon=np['to_sec']
  err=(run/'vissim_simulation_001.err').read_text(encoding='utf-8-sig',errors='replace')
  remains={i:int(q)for i,q in re.findall(r'Vehicle input (\d+):[^\n]*?remain: (\d+) vehicles',err)}
  record=dict(evidence_class='[읽음]',condition=name,seed=prov['seed'],created_at=prov['created_at'],launch_time_lines=times,sim_period_s=prov['sim_period_sec'],vissim_version=sr['VISSIMVER'],provenance=provfile.relative_to(root).as_posix(),provenance_sha256=sha(provfile),network_sha256=prov['files']['network']['sha256'],native_interval_s=[0,horizon],native_road_veh_h=n['TravTmTot']/3600,native_uninserted_wait_veh_h=n['DelayLatent']/3600,native_road_plus_uninserted_veh_h=(n['TravTmTot']+n['DelayLatent'])/3600,native_uninserted_end_vehicles=n['DemandLatent'],per_input_uninserted_end_warnings=remains,per_input_uninserted_wait_veh_h='모름',native_8100_baseline_comparison='모름: NC native cumulative interval ends at 9000')
  runmeta.append(record)
  action=next(run.glob('action_*.csv'));rows=list(csv.DictReader(action.open(encoding='utf-8-sig')))
  v=[x for x in rows if x['kind']=='vsl'];rm=[x for x in rows if x['kind']=='ramp_meter'];tsc=[x for x in rows if x['kind']=='signal']
  acts=dict(evidence_class='[측정]',source=action.relative_to(root).as_posix(),sha256=sha(action),vsl_rows=len(v),vsl_speeds=dict(collections.Counter(x['speed_kph']for x in v)),vsl_readbacks=dict(collections.Counter(x['readback']for x in v)),ramp_rows=len(rm),signal_rows=len(tsc),rm_values_by_id={},signal_unique_plans_by_id={})
  for k in sorted({x['id']for x in rm}):acts['rm_values_by_id'][k]=sorted({float(x['green_sec'])for x in rm if x['id']==k})
  for k in sorted({x['id']for x in tsc}):acts['signal_unique_plans_by_id'][k]=len({tuple(x[z]for z in ['p1_green','p2_green','p3_green','p4_green','offset'])for x in tsc if x['id']==k})
  for x in rm+tsc:
   greenrows.append(dict(evidence_class='[측정]',condition=name,sim_sec=x['sim_sec'],kind=x['kind'],id=x['id'],green_sec=x['green_sec'],p1=x['p1_green'],p2=x['p2_green'],p3=x['p3_green'],p4=x['p4_green'],offset=x['offset'],readback=x['readback']))
  actions[name]=acts
 save(out/'run_metadata.json',runmeta);save(out/'action_audit.json',actions);csvout(out/'decision_greens.csv',greenrows)
 network=next((root/'raw/joint/sdmpc/network').glob('*.inpx'));xml=ET.parse(network).getroot();demands=[]
 starts=[float(x.get('start'))for x in xml.findall('.//timeIntervalSet[@no="VEHICLEINPUT"]//timeInterval')]
 for v in xml.findall('.//vehicleInput'):
  for i,x in enumerate(v.findall('.//timeIntervalVehVolume')):
   start=float(x.get('timeInt').split()[-1])/1000
   demands.append(dict(evidence_class='[읽음]',input=int(v.get('no')),name=v.get('name'),link=int(v.get('link')),start_s=start,end_s=starts[i+1]if i+1<len(starts)else 8100,volume_veh_h=float(x.get('volume')),vehicle_composition=x.get('vehComp'),volume_type=x.get('volType'),continuation=x.get('cont')))
 csvout(out/'demand_34_inputs.csv',demands)
 speeds=[]
 for d in xml.findall('.//desSpeedDistribution'):
  for point in d.findall('.//speedDistributionDataPoint'):speeds.append(dict(evidence_class='[읽음]',distribution=d.get('no'),name=d.get('name'),cdf=float(point.get('fx')),speed_kph=float(point.get('x'))))
 csvout(out/'desired_speed_cdfs.csv',speeds)
 dsds=[]
 for d in xml.findall('.//desSpeedDecision'):
  for v in d.findall('.//vehClassDesSpeedDistribution'):
   dsds.append(dict(evidence_class='[읽음]',dsd=int(d.get('no')),name=d.get('name'),link_lane=d.get('lane'),position_m=float(d.get('pos')),vehicle_class=v.get('vehClass'),distribution=v.get('desSpeedDistr'),time_from=d.get('timeFrom'),time_to=d.get('timeTo')))
 csvout(out/'dsd_locations.csv',dsds)
 membership=load(code/cfg['control_area_objective']['membership_path']);save(out/'omega_membership_exact.json',membership)
 plant=load(code/cfg['freeway']['lane_plant']);ref=load(code/plant['sources']['reference_config']['path']);fw=ref['freeway']
 save(out/'plant_coefficients.json',dict(evidence_class='[읽음]',manifest_name=cfg['freeway']['lane_plant'],manifest_sha256=sha(code/cfg['freeway']['lane_plant']),reference_name=plant['sources']['reference_config']['path'],reference_sha256=sha(code/plant['sources']['reference_config']['path']),state_response=fw.get('state_response'),fd=fw.get('fd'),freeway_keys=list(fw),qualification=plant['qualification']))
 save(out/'scope_definitions.json',dict(evidence_class='[읽음]',FW_E_7=S7,local_19=S19,interval_s=[0,8100],seed=29,sealed_seeds_excluded=sorted(SEALED),sampled_residence_rule=summary['definition'],source_cache_hashes={name:sha(root/'analysis/comparison'/name/'area_metrics.json')for name in summary['conditions']},uninserted_wait_in_objective=False,full_network_plus_uninserted_paired_8100='모름'))
 print(json.dumps({'metric_rows':len(metrics),'inputs':len({x['input']for x in demands}),'joint_actions':actions['joint'],'joint_native':next(x for x in runmeta if x['condition']=='joint')},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();audit(a.bundle.resolve())
