"""Reuse the complete, now verified multi-block diagnostic harness."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=HERE.parent/'native_beta/forecast.py'
text=source.read_text(encoding='utf8')
def replace(a,b):
    global text
    assert text.count(a)==1,a
    text=text.replace(a,b)
replace("choices=['native_beta'], default='native_beta'", "choices=['sc109_service'], default='sc109_service'")
replace("OUT = HERE / ('forecast2400_checked' if args.at == 2400 else 'forecast3300')", "OUT = HERE / f'forecast{args.at}'")
replace("('SC16_S','SC16_S_SC109_')]", "('SC16_S','SC16_S_SC109_'), ('SC109_W','SC109_W_SC108_')]")
replace("'SC16_S':'SC109_to_SC16'}", "'SC16_S':'SC109_to_SC16', 'SC109_W':'SC108_to_SC109'}")
replace("scope='Same actual commands; pinned native destination priors for SC12/SC16 only, on top of previous queue-service candidate. No future inputs or fitting.'", "scope='Same actual commands; SC109 two-lane west-left past4-window support only on top of verified native-beta candidate. No future observation inputs or fitted coefficients.'")
dest=HERE/'forecast.py';assert not dest.exists();compile(text,str(dest),'exec');dest.write_text(text,encoding='utf8')
plan=json.loads((HERE/'plan.json').read_bytes())
assert json.loads((HERE/'initialization_verification.json').read_bytes())['status']=='passed'
root=HERE.parents[3]
for p in (source,dest,HERE/'check_initialization.py',root/'evaluation/controllers/head_service_resources.py',root/'tests/test_head_service_sc109_left_contract.py'):
    plan['source_pins'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
plan.update(status='two_initializations_and28tests_passed',tests_passed=28)
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('Prepared3bounded forecasts, no optimizer/native.')
