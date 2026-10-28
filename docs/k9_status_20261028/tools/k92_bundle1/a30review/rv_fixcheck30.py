"""ReviewDeclare A30: the driver's own a30_sha() and the C6 string test against the fixation file, with the expected
pin list standing in for KB/a30_pins.sha256 (G1 writes that file later).  Imports the driver module only; runs no
stage and writes nothing.

    python -B rv_fixcheck30.py
"""
import importlib.util
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
KB = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('k92t30', KB / 'a30decl' / 'k92t30.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
s = D.a30_sha()
print('a30_sha', s[:16])
exp = KB / 'a30decl' / 'a30_pins.expected.sha256'
n, bad, ps = D.pins_check(exp)
listed = exp.read_text(encoding='utf-8')
mine = ['%s *%s' % (D.sha(p), str(p).replace(chr(92), '/')) for p in (Path(D.__file__).resolve(), D.JUDGE)]
fixed = D.FIXED30.read_text(encoding='utf-8')
c6 = (ps is not None and not bad and all(m in listed for m in mine)
      and re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % ps, fixed) is not None)
print('C6_equivalent', c6, 'n', n, 'bad', len(bad), 'list_sha', ps[:16])
r1 = (KB.parent.parent / 'K8_PREDECLARATION_AMENDMENT_30_r1.md')
print('declare_sha_in_fixed_64', D.sha(r1) in fixed)
