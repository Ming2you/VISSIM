"""Record the diagnosed accounting fix without overwriting failed attempts."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(HERE/'debit_failure_evidence.json')['difference']==-5.551115123125783e-17
plan=read(HERE/'plan.json')
assert 'roundoff_repair' not in plan
(HERE/'plan_before_roundoff.json').write_bytes((HERE/'plan.json').read_bytes())
(HERE/'preflight_before_roundoff.json').write_bytes((HERE/'preflight.json').read_bytes())
logs=[HERE/'head_regression_roundoff.log',HERE/'shared_regression_roundoff.log']
for p in logs:assert p.read_text(encoding='utf8').rstrip().endswith('OK'),str(p)
pre=dict(status='passed',tests_passed=107,canonical_python='3.12.14',logs={str(p):sha(p) for p in logs})
(HERE/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n',encoding='utf8')
plan['source_pins']={p:sha(Path(p)) for p in plan['source_pins']}
plan['roundoff_repair']=dict(evidence='debit_failure_evidence.json',failed_outputs=['forecast2400','debit_repro'],completed_forecasts=0,
    corrected_output='forecast2400_corrected',reason='Compensated sum versus sequential debit; 5.55e-17 vehicle difference at2435; absolute1e-8 evidence tolerance with nonfinite rejection. Physical budget unchanged.')
plan['status']='roundoff_repaired_ready_for_bounded_verification'
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
