"""ReviewDeclare A31: the driver's own a31_sha() and the C6 text test against the fixation file and the expected pin
list (the G1 copy KB/a31_pins.sha256 does not exist yet, so the expected file stands in).  Reads only."""
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KB = HERE.parent
AD31 = KB / 'a31decl'
spec = importlib.util.spec_from_file_location('rv_k92t31', str(AD31 / 'k92t31.py'))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
out = {}
out['a31_sha'] = D.a31_sha()
exp = AD31 / 'a31_pins.expected.sha256'
n, bad, s = D.pins_check(exp)
listed = exp.read_text(encoding='utf-8')
fixed = D.FIXED31.read_text(encoding='utf-8')
# the driver as launched by KI/launch.ps1: Path(__file__) = KI/../a31decl/k92t31.py, resolved
drv = (KB / 'impl' / '..' / 'a31decl' / 'k92t31.py').resolve()
mine = ['%s *%s' % (D.sha(p), str(p).replace('\\', '/')) for p in (drv, D.JUDGE31, D.UNIT31)]
out['C6_same_meaning'] = (s is not None and not bad and all(m in listed for m in mine)
                          and re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % s, fixed) is not None)
out['pins'] = {'n': n, 'bad': len(bad), 'sha256': s}
declare = (D.SP / 'K8_PREDECLARATION_AMENDMENT_31_r1.md')
dsha = D.sha(declare)
out['declare_sha_64_absent_in_fixed'] = re.search(r'(?<![0-9a-f])%s(?![0-9a-f])' % dsha, fixed) is None
out['declare_prefix16_present'] = dsha[:16] in fixed
out['ok'] = bool(out['C6_same_meaning'] and out['declare_sha_64_absent_in_fixed'] and n == 133)
print(json.dumps(out, sort_keys=True))
