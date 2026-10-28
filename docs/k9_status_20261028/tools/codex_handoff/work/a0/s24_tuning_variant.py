# Make ONE tuning variant in the a0 scratch code tree: runtime.decision_timeout_sec 1800 -> 2390 (< StallSec 2400).
# Only that byte span changes. Used to see what a timeout-only tuning change does to an offline decision.
import hashlib
D = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/'
src = open(D + 'optimized_config.json', 'rb').read()
old, new = b'"decision_timeout_sec": 1800', b'"decision_timeout_sec": 2390'
assert src.count(old) == 1
out = src.replace(old, new)
dst = D + 'optimized_config_t2390.json'
open(dst, 'xb').write(out)
print('src', hashlib.sha256(src).hexdigest(), len(src))
print('dst', hashlib.sha256(out).hexdigest(), len(out))
