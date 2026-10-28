# Structure-only probe: top-level keys, diagnostics.sdmpc_prediction_sequence structure, coordinate order for FW_E (key names only).
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print('top keys', list(d.keys())[:30])
dg = d.get('diagnostics', {})
print('diagnostics keys (first 40)', list(dg.keys())[:40] if isinstance(dg, dict) else type(dg))
sps = dg.get('sdmpc_prediction_sequence') if isinstance(dg, dict) else None
print('sps type', type(sps).__name__, list(sps.keys())[:20] if isinstance(sps, dict) else '')
if isinstance(sps, dict) and 'future' in sps:
    f = sps['future']; print('future type', type(f).__name__, len(f))
    if isinstance(f, list) and f: print(' future[0] keys', list(f[0].keys())[:20] if isinstance(f[0], dict) else type(f[0]))
j = d['metadata']['joint_leader_selection']
fe = [ (c['kind'], c['key'], c['block']) for c in j['coordinates'] if c['owner']=='FW_E']
print('FW_E coords', len(fe), fe)
print('cs keys', list(j['control_sequence'].keys()))
