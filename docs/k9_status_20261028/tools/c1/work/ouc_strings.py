"""Read-only: OUC .json strings (runtime part, codex prepare_next.py:61-63 rule) intersected with docs
that mention the Omega635 membership / base route contract / support document paths (git grep list)."""
import json, sys
BS = chr(92)
cfg = json.load(open(sys.argv[1], encoding='utf-8'))
runtime = dict(cfg)
for k in ('_repin', 'notes', '_n31_note', '_canonical', '_canon_note', '_ver2_note', 'description'):
    runtime.pop(k, None)


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


s = sorted({v.replace(BS, '/') for v in strings(runtime) if v.endswith('.json')})
refs = {l.strip() for l in open(sys.argv[2], encoding='utf-8') if l.strip()}
print('runtime .json strings:', len(s))
for v in s:
    if v in refs:
        print('REF', v)
