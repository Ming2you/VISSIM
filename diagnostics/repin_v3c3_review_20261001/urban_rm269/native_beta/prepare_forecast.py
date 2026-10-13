"""Derive a finite diagnostic from the already reviewed same-command harness."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE.parent/'sc6_queue/forecast_first150.py'
text=source.read_text(encoding='utf8')
def replace(a,b):
    global text
    assert text.count(a)==1, a
    text=text.replace(a,b)
replace("ap.add_argument('--variant', choices=['baseline', 'queue', 'service'], required=True)", "ap.add_argument('--variant', choices=['native_beta'], default='native_beta')")
replace("assert (args.at == 2400 and args.variant in ('queue', 'service')) or (args.at == 3300 and args.variant in ('baseline', 'service'))", "assert args.at in (2400,3300)")
replace("OUT = HERE / f'forecast{args.at}_{args.variant}_first150'", "OUT = HERE / ('forecast2400_checked' if args.at == 2400 else 'forecast3300')")
replace("assert args.at == 3300\n", "")
replace("assert not point.aborted and len(point.states) == 1 and visits is None", "save(name+'.rollout_status.json', dict(aborted=point.aborted, states=len(point.states), expected_depth=depth, visits=visits))\n                assert not point.aborted and len(point.states) == depth\n                assert visits == list(range(depth)) if depth == 3 else visits is None")
replace("tuning = H / 'config_candidate.json' if args.variant == 'baseline' else HERE / ('config.json' if args.variant == 'queue' else 'service_config.json')", "tuning = HERE / 'config.json'")
replace("read(HERE / 'service_plan.json')", "read(HERE / 'plan.json')")
replace("[('SC6_S', 'SC6_S_SC12_'), ('SC6_E', 'SC6_E_SC104_')]", "[('SC6_S', 'SC6_S_SC12_'), ('SC6_E', 'SC6_E_SC104_'), ('SC12_S','SC12_S_SC16_'), ('SC16_S','SC16_S_SC109_')]")
replace("origins = {'SC6_S': 'SC12_to_SC6', 'SC6_E': 'SC104_to_SC6'}", "origins = {'SC6_S': 'SC12_to_SC6', 'SC6_E': 'SC104_to_SC6', 'SC12_S':'SC16_to_SC12', 'SC16_S':'SC109_to_SC16'}")
replace("response = point.control_area_response", "response = point.control_area_response\n                import gzip\n                with gzip.open(OUT/(name+'.response.json.gz'),'wt',encoding='utf8') as f:\n                    json.dump(response,f,allow_nan=False)")
replace("scope='Same actual commands; corrected initial queue/causal past service only. Control-gain qualification requires native comparison.'", "scope='Same actual commands; pinned native destination priors for SC12/SC16 only, on top of previous queue-service candidate. No future inputs or fitting.'")
dest=HERE/'forecast.py'
assert not dest.exists()
compile(text,str(dest),'exec')
dest.write_text(text,encoding='utf8')
plan=json.loads((HERE/'plan.json').read_bytes())
plan.update(status='initialization_and_8_tests_passed', tests_passed=8,
    diagnostic_failures=[dict(stage='first2400_initialization_import',reason='Sandbox denied reading canonical NumPy; no model prediction started.',preserved_output='init2400',resolution='Canonical environment with authorized read access, new output init2400_checked.')])
for p in (source,dest,HERE/'check_initialization.py',HERE/'test_native_beta.py'):
    plan['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Bounded forecast prepared: two450 + one150; no optimizer/native.')
