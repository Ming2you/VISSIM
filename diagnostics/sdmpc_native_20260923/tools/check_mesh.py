r"""How many freeway cells does each candidate mesh carry?

The mapping directories are named by parent-segment count (ver2n21 = 21), but the
lane plant pins its own geometry.json, and the refinement work went 21 -> 31. This
prints both so the two cannot be assumed equal.
"""
import collections
import io
import json
import os

SIM = r'D:\VISSIM-merge\sim3'


def load(rel):
    return json.load(io.open(os.path.join(SIM, rel.replace('/', os.sep)), encoding='utf-8-sig'))


def cells_of(doc):
    geo = doc.get('geometry', doc)
    cells = geo.get('cells') or []
    return geo, cells


plant = load('diagnostics/lane_plant_20260921/plant.json')
gsrc = plant['sources']['geometry']['path']
print('lane plant geometry source:\n   ', gsrc)
geo, cells = cells_of(load(gsrc))
print('    cells=%d  per road=%s  profile=%s'
      % (len(cells), dict(collections.Counter(c.get('road') for c in cells)),
         geo.get('geometry_profile')))

print('\nmapping segment counts:')
for name in sorted(os.listdir(os.path.join(SIM, 'evaluation'))):
    d = os.path.join(SIM, 'evaluation', name)
    if not name.startswith('real_world_modi_control') or not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.startswith('control_mapping') or not fn.endswith('.json'):
            continue
        try:
            doc = json.load(io.open(os.path.join(d, fn), encoding='utf-8-sig'))
        except Exception as exc:
            print('    %-46s <unreadable: %s>' % (name + '/' + fn, exc))
            continue
        segs = doc.get('segments') or []
        roads = collections.Counter(s.get('road') for s in segs if isinstance(s, dict))
        print('    %-52s segments=%-4d per road=%s' % (name + '/' + fn, len(segs), dict(roads)))

print('\nany geometry.json with 31 cells per road:')
hits = 0
for root, dirs, files in os.walk(os.path.join(SIM, 'diagnostics')):
    dirs[:] = [x for x in dirs if x not in ('__pycache__', '.git')]
    for fn in files:
        if fn != 'geometry.json':
            continue
        path = os.path.join(root, fn)
        try:
            _, cs = cells_of(json.load(io.open(path, encoding='utf-8-sig')))
        except Exception:
            continue
        per = collections.Counter(c.get('road') for c in cs)
        if any(v >= 31 for v in per.values()):
            print('    %-90s %s' % (os.path.relpath(path, SIM), dict(per)))
            hits += 1
            if hits >= 12:
                print('    ...')
                raise SystemExit(0)
if not hits:
    print('    (none)')
