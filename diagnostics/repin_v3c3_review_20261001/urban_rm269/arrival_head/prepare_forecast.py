"""Reuse the verified fixed-action harness for three bounded predictions."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
source=HERE.parent/'native_beta/forecast.py'
text=source.read_text(encoding='utf8')
def replace(a,b):
    global text
    assert text.count(a)==1,a
    text=text.replace(a,b)
replace("choices=['native_beta'], default='native_beta'","choices=['arrival_head'], default='arrival_head'")
replace("OUT = HERE / ('forecast2400_checked' if args.at == 2400 else 'forecast3300')","OUT = HERE / f'forecast{args.at}'")
replace("('SC16_S','SC16_S_SC109_')]","('SC16_S','SC16_S_SC109_'), ('SC101_S','SC101_S_SC1_')]")
replace("'SC16_S':'SC109_to_SC16'}","'SC16_S':'SC109_to_SC16', 'SC101_S':'SC1_to_SC101'}")
replace("scope='Same actual commands; pinned native destination priors for SC12/SC16 only, on top of previous queue-service candidate. No future inputs or fitting.'","scope='Same actual commands and all rates; only SC6S/SC101S current terminal-road cohort ETA and lane composition change. No future inputs, optimizer, native execution or fitted coefficients.'")
dest=HERE/'forecast.py';assert not dest.exists();compile(text,str(dest),'exec');dest.write_text(text,encoding='utf8')
plan=json.loads((HERE/'plan.json').read_bytes())
assert json.loads((HERE/'initialization_verification.json').read_bytes())['status']=='passed'
assert 'Ran 16 tests' in (HERE/'tests.log').read_text(encoding='utf8') and '\nOK' in (HERE/'tests.log').read_text(encoding='utf8')
for p in (source,dest,HERE/'check_initialization.py',Path(__file__),ROOT/'tests/test_partial_kinematic_cohort.py'):
    plan['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
plan.update(status='two_initializations_and16tests_passed',tests_passed=16)
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('Prepared3fixed forecasts after conservation and domain checks.')
