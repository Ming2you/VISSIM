r"""What would re-pinning the SDMPC lane plant onto the 31-cell mesh require?

plant.json pins seven sources by sha256 against the 21-cell mesh and the older
source_dsd network. The new plant's refit lives under res10_20260922 on the
both_off_half network. This lists each pin, what it currently points at, and
whether a 31-cell counterpart already exists -- so the remaining work is a list,
not a guess.
"""
import collections
import io
import json
import os

SIM = r'D:\VISSIM-merge\sim3'
RES = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_20260922'


def load(rel):
    return json.load(io.open(os.path.join(SIM, rel.replace('/', os.sep)), encoding='utf-8-sig'))


def cell_count(rel):
    try:
        doc = load(rel)
    except Exception:
        return None
    geo = doc.get('geometry', doc)
    cells = geo.get('cells')
    if not cells:
        return None
    return dict(collections.Counter(c.get('road') for c in cells))


plant = load('diagnostics/lane_plant_20260921/plant.json')
print('plant.json pins (%d):\n' % len(plant['sources']))
for key, pin in plant['sources'].items():
    path = pin['path']
    extra = ''
    counts = cell_count(path)
    if counts:
        extra = '   cells=%s' % counts
    print('  %-18s %s%s' % (key, path, extra))

print('\n31-cell candidates under res10_20260922:')
root = os.path.join(SIM, RES.replace('/', os.sep))
for sub in sorted(os.listdir(root)):
    d = os.path.join(root, sub)
    if not os.path.isdir(d):
        continue
    files = sorted(f for f in os.listdir(d) if f.endswith('.json'))
    if not files:
        continue
    counts = cell_count(RES + '/' + sub + '/geometry.json') if 'geometry.json' in files else None
    print('  %-42s %-28s %s' % (sub, ('cells=%s' % counts) if counts else '', ', '.join(files[:6])))

print('\nboundary_literature_v1 (the fitted new plant):')
bl = os.path.join(root, 'boundary_literature_v1')
if os.path.isdir(bl):
    for f in sorted(os.listdir(bl)):
        print('   ', f)
