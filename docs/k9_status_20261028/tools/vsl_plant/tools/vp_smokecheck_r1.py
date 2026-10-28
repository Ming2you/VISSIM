"""Pipeline check of one smoke job (booleans only; the smoke state is never a result).
python -B vp_smokecheck.py <job_dir> <out.json>"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402
import vp_analyze as A  # noqa: E402

jd = Path(sys.argv[1])
probe = C.read_json(jd / 'probe.json') or {}
T = int(probe['spec']['state']['T'])
out = {'errors': probe.get('errors'), 'checks': {k: v for k, v in (probe.get('checks') or {}).items()
                                                 if isinstance(v, bool)}, 'hooks': {}, 'reach': {}, 'identical': {}}
base = None
for lab in sorted((probe.get('evaluations') or {})):
    h, why = A.hook_for(jd, probe, lab)
    ok, why2 = A.hook_ok(h, T) if h else (False, why)
    out['hooks'][lab] = {'ok': ok, 'why': why or why2}
    if lab == 'EXEC_scalar':
        base = h
        out['map'] = A.map_ok(h)
for lab, applied in (probe.get('ablations') or {}).items():
    h, _ = A.hook_for(jd, probe, lab)
    name = lab[len('ABL_'):]
    out['reach'][lab] = A.reach(applied, h, name)
    out['identical'][lab] = bool(h and base and h['blocks'] == base['blocks'])
C.write_json(sys.argv[2], out)
print(json.dumps(out, ensure_ascii=False, indent=1))
