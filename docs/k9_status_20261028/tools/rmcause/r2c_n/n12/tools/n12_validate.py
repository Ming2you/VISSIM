"""N12 check: the static install-time capacities vs values the run itself recorded (read-only)."""
import json, sys
from pathlib import Path
caps = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
dec = json.loads(Path(sys.argv[2]).read_bytes().decode('utf-8-sig'))
meta = dec['metadata']
base = {r['movement']: r['cap_install_veh_h'] for r in caps['rows']}
t1 = {r['movement']: r.get('u4_t1_cap_veh_h') for r in caps['rows'] if r.get('u4_t1_cap_veh_h') is not None}
checks = []
for m, v in (meta['k9_w1']['before']).items():
    checks.append(('k9_w1.before', m, v, base.get(m)))
checks.append(('k92_w.before', 'SC109_W_SC108_to_E', meta['k92_w']['before'], base.get('SC109_W_SC108_to_E')))
for path, row in meta['route_choice_corridors'].items():
    for mg in row['route_choice_merges']:
        for name, v in zip((mg['keep'], mg['removed']), mg['old_capacities_veh_h']):
            if name in base:
                checks.append(('rcc.old_capacities ' + Path(path).name, name, v, base.get(name)))
ok = sum(1 for c in checks if c[3] is not None and abs(c[2] - c[3]) < 1e-9)
print(json.dumps({'run_recorded_checks': len(checks), 'equal_1e-9': ok,
                  'rows': [list(c) for c in checks]}, indent=1))
same_t1 = sum(1 for m, v in t1.items() if abs(v - base[m]) < 0.01)
print('U4 T1 (v3b-era replay) perimeter caps equal to the reconstruction (0.01):', same_t1, 'of', len(t1))
print('differ:', [(m, v, round(base[m], 2)) for m, v in t1.items() if abs(v - base[m]) >= 0.01])
