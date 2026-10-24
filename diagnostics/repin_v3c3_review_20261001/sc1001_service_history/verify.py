"""Verify this turn's saved evidence and limited source changes; no rollout."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def funcs(path):
    result={}
    def visit(node,prefix=''):
        for n in getattr(node,'body',[]):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                result[prefix+n.name]=ast.dump(n,include_attributes=False)
            elif isinstance(n,ast.ClassDef):visit(n,prefix+n.name+'.')
    visit(ast.parse(path.read_text(encoding='utf-8-sig')))
    return result


def main():
    before=json.loads((HERE/'before.json').read_bytes());changes={}
    for rel,expected in before.items():
        current=ROOT/rel;old=HERE/(current.name+'.before.txt')
        assert sha(old)==expected
        a,b=funcs(old),funcs(current)
        changes[rel]=dict(changed=sorted(k for k in a.keys() & b.keys() if a[k]!=b[k]),
                         added=sorted(b.keys()-a.keys()),removed=sorted(a.keys()-b.keys()))
        assert not changes[rel]['removed']
    pinned=json.loads((HERE/'source_pins.json').read_bytes())
    for rel,expected in pinned.items():assert sha(ROOT/rel)==expected,rel
    core=json.loads((HERE.parent/'sc1001_connection/verification.json').read_bytes())['unchanged_core_pins']
    for rel,expected in core.items():assert sha(ROOT/rel)==expected,rel
    test=(HERE/'tests_routes.log').read_text(encoding='utf-8-sig')
    assert 'Ran 23 tests' in test and test.rstrip().endswith('OK')
    a=json.loads((HERE/'assessment.json').read_bytes())
    assert a['source_only_change_traffic_exact'] and a['source_audit']['mismatch']==[]
    assert a['source_audit']['agreed_with_cached_past']==62
    assert len(a['source_audit']['unresolved'])==7
    assert a['physical_resource_max_exceedance']<1e-7
    result=dict(status='OBSERVATION_WIRING_VERIFIED_NOT_GAIN_QUALIFIED',changes=changes,
        source_pins=pinned,unchanged_core_pins=core,
        artifacts={p.name:sha(p) for p in (HERE/'assessment.json',HERE/'tests.log',HERE/'tests_routes.log',
            HERE/'pair.log',HERE/'pair_routes.log',HERE/'assess.py',Path(__file__))},
        observation_scope='Only validated current/past150s frames and head windows; 5s cached truth used separately to audit source identity.',
        capacity_interpretation='Demonstrated green-discharge floor, not saturation identified from queues; amber counts excluded.',
        checks=dict(unit_tests=23,completed450s=4,latest_pair_completed=2,optimizer=0,
            new_native=0,new_fzp_scans=0,coefficient_fit=0,push=0,full_rollout_AD=False,new_independent_rollout=False),
        active_processes_started_in_turn_remaining=0,
        goal='ACTIVE / NOT_QUALIFIED',production_default_enabled=False)
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],changes=changes),ensure_ascii=False))


if __name__=='__main__':main()
