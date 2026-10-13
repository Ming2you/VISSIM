"""One composition of two diagnosed physical stages; no new rate fitting."""
import ast,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert not (HERE/'plan.json').exists()
staging=H/'connector_stage';lateral=H/'lateral_access';core=ROOT/'evaluation/controllers/route_choice_corridor.py';flow=ROOT/'evaluation/controllers/urban_flow_accounting.py'
for folder in (staging,lateral):
    restoration=read(folder/'restoration.json')
    if 'files' in restoration:
        for rec in restoration['files']:
            assert sha(Path(rec['file']))==rec['restored_sha256']
            assert sha(Path(rec['candidate_archive']))==rec['candidate_sha256']
assert core.read_bytes()==(lateral/'route_choice_corridor.before.py').read_bytes()
candidate=(staging/'route_choice_corridor.candidate.py.preserved').read_text(encoding='utf8')
other=(lateral/'route_choice_corridor.candidate.py.preserved').read_text(encoding='utf8')
def funcs(s):return {n.name:n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
cfuncs=funcs(candidate);lfuncs=funcs(other)
replacements=[]
for name in ('_known_local_queue_advance','known_legsplit_requests','known_legsplit_commit'):
    node=cfuncs[name];replacements.append((node.lineno-1,node.end_lineno,ast.get_source_segment(other,lfuncs[name])))
lines=candidate.splitlines()
for start,end,new in sorted(replacements,reverse=True):lines[start:end]=new.splitlines()
candidate='\n'.join(lines)+'\n'
additions='\n\n'.join(ast.get_source_segment(other,lfuncs[name]) for name in ('_known_lane_occupancy','_known_ramp_lane_share','_known_lateral_advance','_known_ramp_lane_debit'))
anchor='def _known_local_queue_prepare(cfg, cohort):';assert candidate.count(anchor)==1
candidate=candidate.replace(anchor,additions+'\n\n\n'+anchor)
configure=ast.get_source_segment(other,lfuncs['configure_known_legsplit'])
block=configure[configure.index("    lateral = tuning"):configure.index('    initialize_known_legsplit')]
anchor='    initialize_known_legsplit(state, cfg, raw)';assert candidate.count(anchor)==1
candidate=candidate.replace(anchor,block+anchor)
ast.parse(candidate)
for p in (core,flow):(HERE/(p.stem+'.before.py')).write_bytes(p.read_bytes())
core.write_text(candidate,encoding='utf8');flow.write_bytes((staging/'urban_flow_accounting.candidate.py.preserved').read_bytes())
for folder,name in ((staging,'connector_stage'),(lateral,'lateral_access')):
    target=ROOT/f'tests/test_known_wout_{name}.py';assert not target.exists()
    target.write_bytes((folder/f'test_known_wout_{name}.py.preserved').read_bytes())
config=read(staging/'config.json');rate=read(lateral/'past_fit.json')['rate_per_sec']
config['urban']['known_wout_lateral_access']={'rate_per_sec':rate};save(HERE/'config.json',config)
forecast=(staging/'forecast.py').read_text(encoding='utf8').replace("choices=['connector_stage'], default='connector_stage'","choices=['connector_lane'], default='connector_lane'")
forecast=forecast.replace("comparable=copy.deepcopy(spec);comparable.pop('connector_queue_gate')", "comparable=copy.deepcopy(spec);comparable.pop('connector_queue_gate')\n            assert comparable.pop('lateral_access_rate_per_sec')==read(H/'lateral_access/past_fit.json')['rate_per_sec']")
forecast=forecast.replace("No new coefficient and no lateral-rate candidate.","Connecting-lane access uses the already pinned past-only rate; no new fit or multiplier.")
(HERE/'forecast.py').write_text(forecast,encoding='utf8')
inputs=[core,flow,HERE/'forecast.py',HERE/'config.json',lateral/'past_fit.json',H/'connector_attribution/assessment.json',
        ROOT/'tests/test_known_wout_connector_stage.py',ROOT/'tests/test_known_wout_lateral_access.py',H.parent/'urban260/verify.py']
plan=dict(status='prepared_before_validation',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    candidate='finite connector queues plus explicit current-lane RM eligibility and conservative adjacent-space exchange',
    baseline='../sc1_supply/config.json',max_fixed_predictions=3,new_native=0,new_full_selections=0,new_fitted_coefficients=0,
    rate_per_sec=rate,rate_source='../lateral_access/past_fit.json',rate_training_times=[1800,1950,2100,2250],
    source_pins={str(p):sha(p) for p in inputs},
    reason='Completed native ordinal-ID attribution: first150 selected initial wrong-lane entries1 versus model12.51, and noninitial9 versus21.38; actual initial connecting24 vs model18.60. A single total entry coefficient cannot correct both groups.',
    preserve=['initial owned stock and current routes','network/FW80 urban90/seed29','Omega701 TTT','450s and3blocks','terminal OFF','active frozen queue'],
    gate='One composition, no rate sweep. Check arrival timing, lane residuals, W_out/ramp wait and total cost plus unused-state check. No full AD/native or promotion unless physically useful. Small net signs are not fitted.',
    limitations=['Effective lateral rate is an aggregate approximation, not resolved VISSIM gaps.','2400/3300 already used for development; not independent out-of-sample qualification.'])
save(HERE/'plan.json',plan)
print('Prepared one structural composition, existing rate',rate,'maximum three fixed predictions')
