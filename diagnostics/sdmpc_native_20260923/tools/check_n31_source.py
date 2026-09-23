r"""Which .inpx and which run does the 31-cell mesh come from?

The SDMPC lane plant pins a 21-cell geometry; the refit under res10_20260922 is
31-cell. Before deciding what "connect the controller to the new plant" costs, we
need the 31-cell mesh's own network identity and profile.
"""
import hashlib
import io
import json
import os

SIM = r'D:\VISSIM-merge\sim3'
RES = os.path.join(SIM, 'diagnostics', 'demand_sweep', 'user_native_20260914',
                   'metanet_calibration_v1', 'res10_20260922')

KNOWN = {}
for label, path in [
    ('source_dsd/baseline.inpx (lane plant pin)',
     os.path.join(SIM, 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/source_dsd/baseline.inpx')),
    ('modi_eval_userfix Ver2.inpx',
     os.path.join(SIM, 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx')),
    ('both_off_half prepared/network/baseline.inpx',
     r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\prepared\network\baseline.inpx'),
    ('both_off_half source/baseline.inpx',
     r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\source\baseline.inpx'),
]:
    if os.path.exists(path):
        KNOWN[hashlib.sha256(io.open(path, 'rb').read()).hexdigest()] = label


def name(sha):
    return KNOWN.get(sha, '(unrecognised)')


print('res10_20260922 contents:')
for entry in sorted(os.listdir(RES))[:24]:
    print('   ', entry)

print('\ngeometry_profile / network identity per observation set:')
seen = set()
for root, dirs, files in os.walk(RES):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    if 'geometry.json' not in files:
        continue
    doc = json.load(io.open(os.path.join(root, 'geometry.json'), encoding='utf-8-sig'))
    geo = doc.get('geometry', doc)
    profile = geo.get('geometry_profile') or doc.get('geometry_profile')
    key = json.dumps(profile, sort_keys=True) if profile else '(none)'
    if key in seen:
        continue
    seen.add(key)
    print('\n  from', os.path.relpath(root, SIM))
    if isinstance(profile, dict):
        for k, v in profile.items():
            print('      %-10s %s' % (k, str(v)[:120]))
    else:
        print('      profile:', str(profile)[:160])

print('\nany network sha256 recorded under res10_20260922:')
hits = {}
for root, dirs, files in os.walk(RES):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for fn in files:
        if not fn.endswith('.json'):
            continue
        try:
            text = io.open(os.path.join(root, fn), encoding='utf-8-sig').read()
        except Exception:
            continue
        for sha, label in KNOWN.items():
            if sha in text:
                hits.setdefault(label, os.path.relpath(os.path.join(root, fn), SIM))
for label, where in hits.items():
    print('   %-46s first seen in %s' % (label, where))
if not hits:
    print('   (no known network hash appears)')
