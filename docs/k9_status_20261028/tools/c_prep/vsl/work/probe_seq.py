# structure probe of diagnostics.sdmpc_prediction_sequence (keys/types only + VSL entries)
import json, sys
o = json.load(open(sys.argv[1], encoding='utf-8'))
s = o['diagnostics']['sdmpc_prediction_sequence']
print(type(s).__name__, list(s.keys()) if isinstance(s, dict) else len(s))
f = s.get('future')
print('future', type(f).__name__, (list(f.keys())[:10] if isinstance(f, dict) else len(f)))
if isinstance(f, list):
    for i, b in enumerate(f):
        print(i, type(b).__name__, list(b.keys())[:15] if isinstance(b, dict) else str(b)[:200])
        if isinstance(b, dict) and isinstance(b.get('vsl'), dict):
            print('   vsl FW_E seg13/14:', {k: v for k, v in b['vsl'].items() if k in ('FW_E__seg13','FW_E__seg14','FW_E__seg5','FW_E__seg2','FW_E')})
