# Structure-only probe of /metadata/joint_leader_selection and siblings (key names/types only, no values).
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
m = d.get('metadata', {})
print('metadata keys containing sdmpc/joint/held/audit/vsl/price:', [k for k in m if any(s in k for s in ('sdmpc','joint','held','audit','vsl','price','operating','dual','policy'))])
j = m.get('joint_leader_selection')
print('jls type', type(j).__name__)
if isinstance(j, dict):
    for k, v in j.items():
        t = type(v).__name__; n = len(v) if isinstance(v,(list,dict)) else ''
        print(' jls/', k, t, n)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            print('    [0] keys:', list(v[0].keys()))
        if isinstance(v, dict):
            print('    keys:', list(v.keys())[:40])
