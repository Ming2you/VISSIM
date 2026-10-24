"""Create a one-file unapplied patch; no runtime module import or test execution."""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'evaluation/controllers/native_input_prehead.py'
BEFORE_SHA256 = 'd915c0e52fa69f5b8a89dcf3614d0132c5c5ea3a03f1e8650164ce911612acef'
NAMES = ('_inputs', '_check', '_blocked', 'receive_accepted')
FIXTURE = ROOT / 'diagnostics/fixtures/prehead_call_local_dd13e08.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_source():
    raw = (ROOT / SOURCE).read_bytes()
    if sha(raw) != BEFORE_SHA256:
        raise ValueError('Pre-head source differs from the reviewed baseline')
    return raw.decode('utf-8')


def functions(source):
    lines = source.splitlines(keepends=True)
    nodes = {n.name:n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
    return {name:''.join(lines[nodes[name].lineno-1:nodes[name].end_lineno]) for name in NAMES}


def proposed_source():
    source = original_source()
    old = "def _check(state,cfg):\n    local=state.native_input_prehead_state;inputs=_inputs(cfg);grouped=defaultdict(float)\n"
    new = "def _check(state,cfg,inputs=None):\n    local=state.native_input_prehead_state\n    if inputs is None:inputs=_inputs(cfg)\n    grouped=defaultdict(float)\n"
    if source.count(old) != 1:
        raise ValueError('Pre-head check anchor differs')
    result = source.replace(old,new,1)
    received = functions(result)['receive_accepted']
    if received.count('    _check(state,cfg)') != 1:
        raise ValueError('Pre-head accepted validation anchor differs')
    changed = received.replace('    _check(state,cfg)',
        '    # This call already filtered inputs; retain every validation and sum.\n    _check(state,cfg,inputs)',1)
    return result.replace(received,changed,1)


def main():
    original, after = original_source(), proposed_source()
    # The fixture contains only four exact original functions, not a controller copy.
    pieces = functions(original)
    fixture = ('"""Four exact dd13e08 pre-head functions; never regenerated after application."""\n'
               'from collections import defaultdict\nimport math\nEPS=1e-8\n\n' + '\n\n'.join(pieces.values()))
    fixture_raw = fixture.encode('utf-8')
    if FIXTURE.exists():
        if FIXTURE.read_bytes() != fixture_raw:
            raise ValueError('Frozen original function fixture differs; refuse regeneration')
    else:
        FIXTURE.write_bytes(fixture_raw)
    patch = ''.join(difflib.unified_diff(original.splitlines(True),after.splitlines(True),
        fromfile='a/'+SOURCE,tofile='b/'+SOURCE))
    target = ROOT / 'diagnostics/prehead_call_local_reuse.patch'
    target.write_text(patch,encoding='utf-8',newline='\n')
    manifest = {'schema':'prehead-call-local-reuse/v1','production_applied':False,
        'source':SOURCE,'before_sha256':BEFORE_SHA256,'after_lf_sha256':sha(after.encode()),
        'patch_sha256':sha(target.read_bytes()),'fixture':FIXTURE.relative_to(ROOT).as_posix(),
        'fixture_sha256':sha(fixture_raw),'original_functions':{k:sha(v.encode()) for k,v in pieces.items()},
        'scope':'One extra _inputs scan is avoided only at receive_accepted final _check. No inter-call or cfg cache.',
        'tests_status':'prepared_not_run_parent_requested_baseline_window',
        'new_model_evaluations':0}
    path = ROOT / 'diagnostics/prehead_call_local_reuse_manifest.json'
    path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
