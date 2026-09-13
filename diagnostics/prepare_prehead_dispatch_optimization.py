"""Unapplied immutable-config index proposal. Every state check stays in place."""
from __future__ import annotations
import difflib
import hashlib
import json
from pathlib import Path
import types

ROOT=Path(__file__).resolve().parents[1]
PREHEAD='evaluation/controllers/native_input_prehead.py'
NATIVE='evaluation/controllers/native_internal_input.py'
PINS={PREHEAD:'d915c0e52fa69f5b8a89dcf3614d0132c5c5ea3a03f1e8650164ce911612acef',
      NATIVE:'f513f2bd7b6777f8c143710f990ea886dbdb9074575d99bfc88ba08ce7035a98'}


def replace_once(source, before, after):
    if source.count(before)!=1:raise ValueError('Proposal anchor changed: '+before[:90])
    return source.replace(before,after,1)


def proposed_sources():
    original={p:(ROOT/p).read_bytes() for p in PINS}
    if any(hashlib.sha256(b).hexdigest()!=PINS[p] for p,b in original.items()):
        raise ValueError('Pinned production source changed; review before regeneration')
    p=original[PREHEAD].decode('utf-8')
    old="""def _inputs(cfg):
    return {n:r for n,r in getattr(cfg.network,'native_internal_inputs',{}).get('inputs',{}).items() if r.get('kind')=='native_choice_prehead'}
"""
    new="""def prepare_dispatch_index(cfg):
    \"\"\"Derive only immutable configuration lookups after native validation.

    No candidate/cohort/stock/validation result is cached. The source dictionary
    reference survives deepcopy and pickle as an alias. Reconfigured/replaced
    inputs fall back to original lookups until this explicit builder runs again.
    Config is immutable throughout a candidate rollout, as for other model maps.
    \"\"\"
    source=getattr(cfg.network,'native_internal_inputs',{}).get('inputs',{})
    inputs={n:r for n,r in source.items() if r.get('kind')=='native_choice_prehead'}
    if not inputs:
        if hasattr(cfg.network,'native_prehead_dispatch_index'):
            del cfg.network.native_prehead_dispatch_index
        return
    cfg.network.native_prehead_dispatch_index={
        'source_inputs':source,'source_count':len(source),'inputs':inputs,
        'origins':{n:r['prehead_spec']['origin'] for n,r in inputs.items()},
        'movements':{n:{tag:b['movement'] for tag,b in r['prehead_spec']['branches'].items()}
                     for n,r in inputs.items()},
        'wn_movements':frozenset(m for r in inputs.values() for m in r['prehead_spec']['wn_movements'])}


def _dispatch_index(cfg):
    index=getattr(cfg.network,'native_prehead_dispatch_index',None)
    source=getattr(cfg.network,'native_internal_inputs',{}).get('inputs',{})
    if index is None or index['source_inputs'] is not source or index['source_count']!=len(source):
        return None
    return index


def _inputs(cfg):
    index=_dispatch_index(cfg)
    if index is not None:return index['inputs']
    return {n:r for n,r in getattr(cfg.network,'native_internal_inputs',{}).get('inputs',{}).items() if r.get('kind')=='native_choice_prehead'}
"""
    p=replace_once(p,old,new)
    p=replace_once(p,"    local=state.native_input_prehead_state;inputs=_inputs(cfg);grouped=defaultdict(float)\n",
      "    local=state.native_input_prehead_state;index=_dispatch_index(cfg)\n    inputs=index['inputs'] if index is not None else _inputs(cfg);grouped=defaultdict(float)\n")
    p=replace_once(p,"        spec=inputs[cohort['input']]['prehead_spec']\n        key=('queue',spec['branches'][cohort['route']]['movement']) if cohort['stage']=='queue' else ('storage',spec['origin'])\n",
      "        if index is None:\n            spec=inputs[cohort['input']]['prehead_spec']\n            key=('queue',spec['branches'][cohort['route']]['movement']) if cohort['stage']=='queue' else ('storage',spec['origin'])\n        else:\n            key=('queue',index['movements'][cohort['input']][cohort['route']]) if cohort['stage']=='queue' else ('storage',index['origins'][cohort['input']])\n")
    p=replace_once(p,"def _blocked(local,inputs,movement,step):\n    return sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='queue'\n",
      "def _blocked(local,inputs,movement,step,index=None):\n    if index is not None:\n        return sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='queue'\n            and index['movements'][c['input']][c['route']]==movement\n            and (not c['passed_first'] or c['ready']>step))\n    return sum(c['vehicles'] for c in local['cohorts'] if c['stage']=='queue'\n")
    p=replace_once(p,"def limit_intended(state,cfg,movement,available,intended,step):\n    inputs=_inputs(cfg)\n",
      "def limit_intended(state,cfg,movement,available,intended,step):\n    index=_dispatch_index(cfg)\n    inputs=index['inputs'] if index is not None else _inputs(cfg)\n")
    p=replace_once(p,"    blocked=_blocked(state.native_input_prehead_state,inputs,movement,step)\n",
      "    blocked=_blocked(state.native_input_prehead_state,inputs,movement,step,index)\n")
    p=replace_once(p,"def receive_accepted(state,cfg,movement,vehicles,step):\n    inputs=_inputs(cfg)\n",
      "def receive_accepted(state,cfg,movement,vehicles,step):\n    index=_dispatch_index(cfg)\n    inputs=index['inputs'] if index is not None else _inputs(cfg)\n")
    p=replace_once(p,"    if any(movement in r['prehead_spec']['wn_movements'] for r in inputs.values()):\n",
      "    if (movement in index['wn_movements'] if index is not None else\n            any(movement in r['prehead_spec']['wn_movements'] for r in inputs.values())):\n")
    p=replace_once(p,"    eligible_before=state.urban_movement_queue.get(movement,0.)+vehicles-_blocked(local,inputs,movement,step)\n",
      "    eligible_before=state.urban_movement_queue.get(movement,0.)+vehicles-_blocked(local,inputs,movement,step,index)\n")
    p=replace_once(p,"                or inputs[cohort['input']]['prehead_spec']['branches'][cohort['route']]['movement']!=movement):continue\n",
      "                or (index['movements'][cohort['input']][cohort['route']] if index is not None else\n                    inputs[cohort['input']]['prehead_spec']['branches'][cohort['route']]['movement'])!=movement):continue\n")
    n=original[NATIVE].decode('utf-8')
    anchor="        'expected_internal_demand_veh_h':expected_internal}\n    if tuning.get('prediction', {}).get('native_input_schedule', False):\n"
    n=replace_once(n,anchor,"        'expected_internal_demand_veh_h':expected_internal}\n    from evaluation.controllers.native_input_prehead import prepare_dispatch_index\n    prepare_dispatch_index(cfg)\n    if tuning.get('prediction', {}).get('native_input_schedule', False):\n")
    return {PREHEAD:p,NATIVE:n}


def candidate_module():
    source=proposed_sources()[PREHEAD]
    module=types.ModuleType('diagnostics._prehead_dispatch_candidate')
    exec(compile(source,'diagnostics/_prehead_dispatch_candidate.py','exec'),module.__dict__)
    return module


def candidate_native_module():
    source=proposed_sources()[NATIVE]
    module=types.ModuleType('diagnostics._native_dispatch_candidate')
    # Preserve the real helper's resource root while code stays in memory.
    module.__file__=str(ROOT/NATIVE)
    exec(compile(source,'diagnostics/_native_dispatch_candidate.py','exec'),module.__dict__)
    return module


def main():
    sources=proposed_sources();patch=''
    for p,after in sources.items():
        before=(ROOT/p).read_text(encoding='utf-8')
        patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+p,tofile='b/'+p))
    (ROOT/'diagnostics/prehead_dispatch_optimization.patch').write_text(patch,encoding='utf-8',newline='\n')
    (ROOT/'diagnostics/prehead_dispatch_optimization_manifest.json').write_text(json.dumps({
        'schema':'prehead-dispatch-optimization/v1','production_applied':False,'before_sha256':PINS,
        'after_lf_sha256':{p:hashlib.sha256(v.encode()).hexdigest() for p,v in sources.items()},
        'contract':'Immutable configured inputs only; every original _check/_blocked remains at its original call site. No validation-result or mutable-cohort cache.',
        'deferred':'Unrelated/zero accepted fastpaths are not included: invalid-state detection timing must not change.'},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
