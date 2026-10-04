"""Verify this bounded saved-state diagnostic; do not rerun dynamics."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
HELPER=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/replay_congested_component.py'

def read(p):return json.loads(p.read_text(encoding='utf8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (HERE/'verification.json').exists()
    s=read(HERE/'summary.json');p=read(HERE/'protocol.json');rows=read(HERE/'rows.json')
    for path,expected in s['pins'].items():assert digest(Path(path))==expected,path
    assert all(s['pins'][path]==expected for path,expected in p['pins'].items())
    assert HELPER.read_bytes()==(HERE/'helper_executed.py.txt').read_bytes()
    def functions(path):
        return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    before=functions(HERE/'helper_before.py.txt');after=functions(HELPER)
    assert all(after[k]==v for k,v in before.items())
    assert set(after)-set(before)=={'audit_recovery_subcell_balance'}
    assert len(rows)==s['samples']==420 and len(s['skipped'])==0
    assert s['saved_scalar_parity_count']==180 and s['saved_scalar_parity_error_max']==0
    assert s['mass_error_max']<1e-10 and s['initial_moment_error_max']<1e-9
    assert s['derivative_identity_error_max']<1e-4
    assert not s['screen_passed'] and not s['adopted'] and not s['gain_qualified']
    assert all(g['passed_screen']==(g['cell']==25) for g in s['groups'])
    assert all(g['zero']['rmse']<g['two_halves']['rmse'] for g in s['groups'])
    assert not any(r['baseline']['one_second_clipped'] or any(h['terms']['one_second_clipped'] for h in r['halves']) for r in rows)
    assert all(s[k]==0 for k in ('new_native','new_fzp_reads','autonomous_rollouts','fit'))
    for name in ('failed_protocol1.json','failed_helper1.py.txt','run.log','run2.log','README.md'):
        assert (HERE/name).is_file()
    result=dict(status='DIAGNOSTIC_VERIFIED_SUBDIVISION_NOT_ADOPTED',samples=420,groups=6,
        old_functions_unchanged=len(before),production_changed=False,coefficient_fit=False,
        autonomous_gain_test=False,native_runs=0,fzp_reads=0,goal='ACTIVE / NOT_QUALIFIED',
        pins=s['pins'],artifacts={x.name:digest(x) for x in HERE.iterdir() if x.is_file()})
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('pins','artifacts')}))

if __name__=='__main__':main()
