import json, sys
p = sys.argv[1]
j = json.load(open(p, encoding='utf-8-sig'))
s = j['selection']
print('options:', {k: v for k, v in j['options'].items() if not isinstance(v, (dict, list))})
for k, v in s.items():
    if isinstance(v, (dict, list)):
        print(k, type(v).__name__, len(v))
    else:
        print(k, '=', v)
print('policy:', {k: v for k, v in s['policy'].items() if not isinstance(v, (dict, list))})
print('local_rows[0] keys', list(s['local_rows'][0].keys()))
print('gradient_rows[0]', {k: v for k, v in s['gradient_rows'][0].items()})
print('pfo keys', list(s['pfo_warm_start'].keys()))
print('pfo local_rows[0] keys', list(s['pfo_warm_start']['local_rows'][0].keys()))
