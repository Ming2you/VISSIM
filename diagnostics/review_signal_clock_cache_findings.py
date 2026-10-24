"""Independent small cache-key counterexamples; no endpoint/model solve."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from diagnostics.test_signal_clock_cache import fixture,outcome
from diagnostics import signal_clock_cache_proposal as candidate
from evaluation.controllers import signal_actuation_contract as original,offset_promotion

ROOT=Path(__file__).resolve().parents[1]


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='diagnostics/signal_clock_cache_peer_findings.json')
    args=parser.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to((ROOT/'diagnostics').resolve()):raise ValueError('Output must stay under diagnostics')
    if output.exists():raise FileExistsError('Preserve earlier peer evidence; provide a new --output')
    paths=[Path(original.__file__),ROOT/'diagnostics/signal_clock_cache_proposal.py']
    before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    runtime,action=fixture();cfg=deepcopy(runtime[0]);signal='SC1004';spec={'phase':signal+'_p3'}
    cfg.network.signal_actuation_contract['offset_writer']='test_only'
    first,second=offset_promotion.FORCED_ARM_DIAGNOSTIC_KEYS
    a=action.copy();a.diagnostics={second:10.}
    b=action.copy();b.diagnostics={first:None,second:10.}
    differences=[]
    for step in range(30):
        candidate.clear()
        candidate.validated_clock(a,cfg,spec,step)
        expected=outcome(original.phase_fraction,b,cfg,spec,step)
        actual=outcome(candidate.validated_clock,b,cfg,spec,step)
        if expected!=actual:differences.append({'step':step,'original':expected,'cached':actual})
    cases=[{'name':'test_only_missing_vs_present_none','written_offset_original_a':original.written_offset_sec(a,cfg,signal),
        'written_offset_original_b':original.written_offset_sec(b,cfg,signal),'different_public_results':differences,
        'first_diagnostics':a.diagnostics,'second_diagnostics':b.diagnostics}]
    class BadFloatZero(int):
        def __float__(self):return float('nan')
    cfg.network.signal_actuation_contract['offset_writer']='experiment'
    a=action.copy();a.offsets[signal]=0.
    b=action.copy();b.offsets[signal]=BadFloatZero(0)
    candidate.clear();candidate.validated_clock(a,cfg,spec,0)
    cases.append({'name':'custom_numeric_key_equal_to_cached_builtin','original':outcome(original.phase_fraction,b,cfg,spec,0),
        'cached':outcome(candidate.validated_clock,b,cfg,spec,0),
        'scope':'Explicit proposal custom-type bypass claim only. Ordinary production actions use built-in floats.'})
    after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    report={'schema':'signal-clock-cache-peer-findings/v1','code_review':True,'bounded_functions_only':True,
        'sources':before,'source_changes':[p for p,h in before.items() if after[p]!=h],'cases':cases}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
