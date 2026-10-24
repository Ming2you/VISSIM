"""Independent tiny immutable-value guard checks; no model/benchmark execution."""
import gc
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import weakref

from diagnostics import signal_clock_cache_proposal as proposal

ROOT=Path(__file__).resolve().parents[1]


def main():
    paths=[ROOT/'diagnostics/signal_clock_cache_proposal.py',ROOT/'diagnostics/signal_clock_cache.patch',
           ROOT/'evaluation/controllers/signal_actuation_contract.py']
    before={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    expected_patch='d75097744dad4214dc60ed42ef10b5ca18df00d41e1a93771afe68e0a6eb451f'
    assert before['diagnostics/signal_clock_cache.patch']==expected_patch
    checks=[]
    proposal.clear()
    tree=tuple([('p3',((2,'g',0.,1.),))])
    references=sys.getrefcount(tree)
    assert proposal._immutable_plan(tree)
    assert sys.getrefcount(tree)==references+1
    assert proposal._PLAN_TREES[id(tree)] is tree
    checks.append('Registry holds one direct strong reference to the exact verified tuple')
    with patch.object(proposal,'_immutable',wraps=proposal._immutable) as proof:
        assert proposal._immutable_plan(tree)
        assert proof.call_count==0
        replacement=tuple([('p3',((2,'g',0.,1.),))])
        assert replacement==tree and replacement is not tree
        assert proposal._immutable_plan(replacement)
        assert proof.call_count==1
    checks.append('Equal new tuple receives a new complete proof; same proved object reuses it')
    class TupleSubclass(tuple):pass
    class NumericSubclass(int):pass
    bads=[TupleSubclass(tree),(TupleSubclass((1,)),),(['mutable'],),({'mutable':True},),
          ((NumericSubclass(0),),),((float('nan'),),),((float('inf'),),)]
    for value in bads:
        assert proposal._immutable_plan(value) is False
        assert id(value) not in proposal._PLAN_TREES
    checks.append('Tuple subclasses, nested mutable leaves, numeric subclasses and nonfinite leaves rejected before hashing')
    deep=['mutable']
    for _ in range(200):deep=(deep,)
    assert not proposal._immutable_plan(deep)
    assert id(deep) not in proposal._PLAN_TREES
    checks.append('A mutable leaf 200 tuples deep is detected; no shallow-only proof')
    identifier=id(tree)
    del tree
    assert id(proposal._PLAN_TREES[identifier])==identifier
    for i in range(1000):
        fresh=tuple([i,'fresh'])
        assert id(fresh)!=identifier
    checks.append('The retained object remains alive, preventing its ID from being reused by a new tuple')
    proposal.clear()
    with patch.object(proposal,'MAX_PLAN_TREES',2):
        first=tuple(['first']);assert proposal._immutable_plan(first)
        assert proposal._immutable_plan(tuple(['second']))
        assert proposal._immutable_plan(tuple(['third']))
        assert len(proposal._PLAN_TREES)==2 and id(first) not in proposal._PLAN_TREES
        with patch.object(proposal,'_immutable',wraps=proposal._immutable) as proof:
            assert proposal._immutable_plan(first)
            assert proof.call_count==1
    checks.append('Bounded eviction drops identity proof; a surviving evicted tuple is checked again')
    class Owner:pass
    owner=Owner();owner.plan=tuple([('p3',((2,'g',0.,1.),))]);reference=weakref.ref(owner)
    assert proposal._immutable_plan(owner.plan)
    assert not proposal._immutable_plan((owner,))
    del owner;gc.collect();assert reference() is None
    checks.append('Retaining a plan does not retain its cfg/control owner; owner-containing tuple cannot be registered')
    assert all(type(value) is tuple and id(value)==key for key,value in proposal._PLAN_TREES.items())
    proposal.clear();assert not proposal._PLAN_TREES and not proposal._CLOCKS
    checks.append('Clear releases both bounded caches; registry keys agree with retained object identity')
    after={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output=ROOT/'diagnostics/signal_clock_tuple_guard_independent_review.json'
    if output.exists():raise FileExistsError('Preserve prior independent result')
    report={'schema':'signal-clock-tuple-guard-peer/v1','passed':True,'checks':checks,
        'scope':'Small pure guard calls only. No endpoint, solver, VISSIM or timing benchmark.',
        'source_sha256':before,'source_changes':[p for p,h in before.items() if after[p]!=h]}
    assert not report['source_changes']
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
