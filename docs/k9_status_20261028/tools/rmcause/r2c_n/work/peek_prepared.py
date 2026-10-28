import json, re, sys
p = r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\prepared\prepared.json'
d = json.load(open(p, encoding='utf-8-sig'))
print(list(d.keys()))
for k in ('rule_policy', 'demand_variant', 'network_variant', 'speed_variant', 'rule_variant'):
    if k in d:
        print(k, '=', json.dumps(d[k], ensure_ascii=False)[:3000])
s = open(p, encoding='utf-8-sig').read()
print('count s31_v3c3rm', s.count('s31_v3c3rm'), 'count baseline_s31_v3c3rm', s.count('baseline_s31_v3c3rm'))
for m in sorted(set(re.findall(r'"([^"]*s31_v3c3rm[^"]*)"', s))):
    print('  ', m[:220])
