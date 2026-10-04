"""List the top-level code roots referenced by the n31 config / plant / reference JSONs of a code root
(what a scratch copy of a frozen tree must contain).   python -B roots.py [--root R]   (read only, stdout only)"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
c.apply(_ap.parse_args())
ROOT = c.R
roots = set()
pat = re.compile(r'^(diagnostics|evaluation|outputs|network|plant|vendor|scripts|harness|tools|src|docs)[/\\]')
def walk(o):
    if isinstance(o, dict):
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
    elif isinstance(o, str) and pat.match(o):
        p = o.replace(chr(92), '/').split('/')
        roots.add('/'.join(p[:3]))
for f in ['diagnostics/sdmpc_n31_20260924/config_n31_v2.json', 'diagnostics/sdmpc_n31_20260924/plant_n31_v2.json',
          'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json']:
    walk(json.load(open(ROOT / f, encoding='utf-8-sig')))
print('\n'.join(sorted(roots)))
