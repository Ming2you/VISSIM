"""VERIFY_VP: make the one-ablation re-run spec (verifier, 2026-10-27 KST).  Copies the producer P1 spec of one state
and keeps only one ablation (vp_probe.py always adds 'null').  Everything else (mode, owner, zone head, state,
max_parallel, the ablation's own values) is byte-for-value the same.

    python -B vv_make_spec.py <producer spec.json> <ablation name> <out spec.json>"""
import json
import os
import sys
from pathlib import Path

src, name, outp = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
with open(src, 'r', encoding='utf-8-sig') as f:
    s = json.load(f)
s['ablations'] = {name: s['ablations'][name]}
outp.parent.mkdir(parents=True, exist_ok=True)
tmp = outp.with_name(outp.name + '.tmp%d' % os.getpid())
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(s, f, ensure_ascii=False, indent=1)
os.replace(tmp, outp)
print('VV_MAKE_SPEC', outp, list(s['ablations']))
