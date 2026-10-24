"""Verify arriving FZP files against the SHA-256 evidence committed in 00abbab.
Hash semantics copied exactly from diagnostics/control_comparison_20260922/compare.py:raw_frames.
"""
import hashlib, json, sys, os
from pathlib import Path

EXPECT = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv)>1 else None
RUNS = {
 'none': Path('D:/VISSIM_runs/20260922_both_off_half/fw080_urban090_nc9000/run/vissim_eval/baseline_001.fzp'),
 'rm'  : Path('D:/VISSIM_runs/20260922_fw080_urban090_controls/rm/run/vissim_eval/baseline_001.fzp'),
 'vsl' : Path('D:/VISSIM_runs/20260922_fw080_urban090_controls/vsl/run/vissim_eval/baseline_001.fzp'),
 'both': Path('D:/VISSIM_runs/20260922_fw080_urban090_controls/both/run/vissim_eval/baseline_001.fzp'),
}

def scan(path):
    digest=hashlib.sha256(); prefix=hashlib.sha256(); rows=0; last=None; frames=0
    with path.open('rb') as f:
        for raw in f:
            digest.update(raw)
            if not raw[:1].isdigit(): continue
            t=float(raw.split(b';',1)[0])
            if t!=last:
                if last is not None: frames+=1
                last=t
            rows+=1
            if t<900: prefix.update(raw)
    if last is not None: frames+=1
    return dict(sha256=digest.hexdigest(), prefix_before900_sha256=prefix.hexdigest(),
                rows=rows, frames=frames, last_sec=last)

for arm,p in RUNS.items():
    if not p.exists():
        print(f"{arm:5} : 미도착"); continue
    size=p.stat().st_size
    got=scan(p)
    exp=(EXPECT or {}).get(arm)
    if exp is None:
        print(f"{arm:5} : {size/2**30:.2f}GB rows={got['rows']} frames={got['frames']} last={got['last_sec']} sha={got['sha256'][:16]}")
    else:
        ok=all(got[k]==exp[k] for k in ('sha256','prefix_before900_sha256','rows','frames'))
        marks=[f"{k}={'OK' if got[k]==exp[k] else 'MISMATCH'}" for k in ('sha256','prefix_before900_sha256','rows','frames','last_sec')]
        print(f"{arm:5} : {'VERIFIED' if ok else 'FAILED  '} {size/2**30:.2f}GB  " + " ".join(marks))
