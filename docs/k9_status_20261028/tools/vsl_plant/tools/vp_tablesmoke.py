"""Pipeline test of vp_analyze tables on the smoke job output (smoke state only, synthetic VISSIM frames).
Prints only whether each table step ran and the stop-rule hit count; no plant value.
python -B vp_tablesmoke.py <smoke_job_dir> <out.json>"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402
import vp_analyze as A  # noqa: E402

jd = Path(sys.argv[1])
frames, N, SV = [], [], []
t = 1700.1
while t <= 7700.0:
    frames.append(round(t, 1))
    N.append([2.0] * 31)
    SV.append([180.0] * 31)
    t += 5.0
synthetic = {'frames': frames, 'N': N, 'SV': SV}
A.job_dirs = lambda kind: [jd]
A.frames_scan = lambda label: synthetic
res = {}
ok = {}
try:
    res['AB'] = A.probe_ab()
    ok['probe_ab'] = True
except Exception as e:
    ok['probe_ab'] = repr(e)
try:
    res['P1'] = A.p1_states()
    ok['p1_states'] = True
except Exception as e:
    ok['p1_states'] = repr(e)
try:
    res['P1_params'] = A.p1_params(res.get('P1') or {}, None)
    res['P1_FZP'] = {}
    md = A.md_tables(res)
    ok['md'] = len(md) > 1000
except Exception as e:
    ok['md'] = repr(e)
out = {'ok': ok, 'AB_stops': (res.get('AB') or {}).get('stops'), 'P1_stops': (res.get('P1') or {}).get('stops'),
       'AB_states': len((res.get('AB') or {}).get('states') or []), 'P1_states': len((res.get('P1') or {}).get('states') or [])}
C.write_json(sys.argv[2], out)
print(json.dumps({'ok': ok, 'AB_stops_n': len(out['AB_stops'] or []), 'P1_stops_n': len(out['P1_stops'] or []),
                  'AB_stops': out['AB_stops'], 'P1_stops': out['P1_stops']}, ensure_ascii=False)[:3000])
