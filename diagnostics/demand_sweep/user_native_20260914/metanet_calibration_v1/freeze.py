"""Seal parameters, data definitions and model dependencies before test extraction."""
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path
import boundary_factory
import canonical_harness
import extract_observations
import evaluate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    target=HERE/'FREEZE.json'
    if target.exists() or (HERE/'seed17_observations').exists():
        raise ValueError('Freeze must precede test observation extraction and cannot be overwritten')
    parameters=HERE/'fit_v2/parameters.json'
    fit=json.loads(parameters.read_text(encoding='utf-8'))
    protocol=boundary_factory.PROTOCOL
    train=HERE/'seed13_observations'
    if fit['training_seed']!=13: raise ValueError('Training seed must be 13')
    for name,digest in fit['code_sha256'].items():
        if sha(HERE/name)!=digest: raise ValueError('Fitting code changed: '+name)
    for name,digest in fit['input_sha256'].items():
        if sha(train/name)!=digest: raise ValueError('Fitting observations changed: '+name)
    model=canonical_harness.load_base_model(train/'geometry.json')
    if model.provenance!=fit['model_provenance']:
        raise ValueError('Physical model provenance changed after fitting')
    test_network=HERE.parent/'east080_seed17_v1/prepared/network/baseline.inpx'
    if sha(test_network)!=protocol['test_network_sha256']:
        raise ValueError('Unexpected test network')
    paths=set(HERE.glob('*.py'))|{HERE/'PROTOCOL.json',parameters,train/'manifest.json',test_network}
    paths.update(train/name for name in json.loads((train/'manifest.json').read_text(encoding='utf-8'))['files'])
    paths.update(ROOT/name for name in model.provenance['model_files'])
    paths.add(ROOT/model.provenance['baseline_config'])
    paths.add(extract_observations.OFF_INVENTORY)
    for module in list(sys.modules.values()):
        value=getattr(module,'__file__',None)
        if value:
            p=Path(value).resolve()
            if p.is_relative_to(ROOT) and p.suffix=='.py': paths.add(p)
    # Include lazy-loaded physical/config modules as well as the observed imports.
    for folder in ('evaluation/controllers','vendor/NumSim-mine/src'):
        paths.update((ROOT/folder).rglob('*.py'))
    files={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(paths)}
    value={'schema':'metanet-unseen-seed-freeze/v1',
        'frozen_at':datetime.datetime.now().astimezone().isoformat(),
        'python':sys.version,'platform':platform.platform(),
        'parameters_sha256':sha(parameters),'files':files,
        'test_observations_present_at_freeze':False,
        'scope':'All fit, evaluation and physical model definitions fixed before reading/extracting seed17 traffic. Test native completion receipt was checked only for successful run completion. No test-based retuning permitted.',
        'test_cutoffs_s':protocol['test_cutoffs_sec'],
        'display_examples_cutoffs_s':[1350,3600,7200]}
    with target.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,ensure_ascii=False)
    evaluate.check_freeze(target,parameters)
    print(json.dumps({'freeze':str(target),'files':len(files),'frozen_at':value['frozen_at'],'parameters_sha256':sha(parameters)}))

if __name__=='__main__': main()
