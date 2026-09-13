"""Generate, never apply, the single-module selected-clock cache patch."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path('evaluation/controllers/signal_actuation_contract.py')


def proposed_source(source):
    body = (ROOT/'diagnostics/signal_clock_cache_proposal.py').read_text(encoding='utf-8')
    lines = body.splitlines(keepends=True)
    keep = {'clear', 'stats', '_uncached_clock', '_immutable', '_clock_key',
            '_validated_clock', '_finite_fraction', '_immutable_plan'}
    fragments = []
    for node in ast.parse(body).body:
        if isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id in
            {'MAX_CLOCKS','MAX_INTERVALS','MAX_PLAN_TREES','_PLAN_TREES','_CLOCKS','_STATS'} for t in node.targets):
            fragments.append(''.join(lines[node.lineno-1:node.end_lineno]))
        if isinstance(node, ast.FunctionDef) and node.name in keep:
            first = min([node.lineno]+[d.lineno for d in node.decorator_list])
            fragments.append(''.join(lines[first-1:node.end_lineno]))
    helper = '\n\n'.join(fragments).replace('original.', '').replace('def clear():', 'def clear_clock_cache():').replace('def stats():', 'def clock_cache_info():')
    anchor = 'def phase_fraction(control, cfg, spec, urban_step_index=None):'
    if source.count(anchor) != 1:
        raise ValueError('Canonical phase function changed')
    source = source.replace('from functools import lru_cache', 'from functools import lru_cache\nfrom collections import OrderedDict')
    source = source.replace(anchor, helper+'\n\n\n'+anchor)
    start = source.index('    validate_vector(net, signal, values)\n', source.index(anchor))
    end = source.index('    if window is None:\n', start)
    source = source[:start]+'''    cycle, offset, table = _validated_clock(control, cfg, signal, values, raw, contract)
    window = next((window for name, window in table if name == phase), None)
'''+source[end:]
    start = source.index('    total = 0.0\n', source.index(anchor))
    end = source.index('\n\n\ndef wrap_clock', start)
    source = source[:start]+'''    return _finite_fraction(cycle, offset, lo, hi, duration, start, end)'''+source[end:]
    return source


def run():
    path = ROOT/TARGET
    before = path.read_text(encoding='utf-8')
    manifest = json.loads((ROOT/'diagnostics/fixtures/signal_clock_dd13e08_manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['source_sha256']:
        raise ValueError('Frozen dd13e08 clock does not match current production source')
    after = proposed_source(before)
    compile(after, str(TARGET), 'exec')
    patch = ''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='a/'+TARGET.as_posix(),tofile='b/'+TARGET.as_posix()))
    output = ROOT/'diagnostics/signal_clock_cache.patch'
    output.write_text(patch,encoding='utf-8',newline='\n')
    result = {'source_sha256': manifest['source_sha256'],
        'after_lf_sha256': hashlib.sha256(after.encode('utf-8')).hexdigest(),
        'proposal_sha256': hashlib.sha256((ROOT/'diagnostics/signal_clock_cache_proposal.py').read_bytes()).hexdigest(),
        'patch_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'target':TARGET.as_posix(), 'applied':False,
        'selected':'validated clock + finite interval cache; finite-only arm not selected'}
    (ROOT/'diagnostics/signal_clock_cache_patch_manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    run()
