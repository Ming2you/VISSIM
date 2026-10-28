import json
d = json.load(open(r'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_001950.json', encoding='utf-8'))
md = d['metadata']
for k in md:
    if 'stopline' in k.lower() or 'link_storage' in k.lower() or 'storage_veh' in k.lower():
        v = md[k]
        print(k, v if not isinstance(v, (dict, list)) else json.dumps(v)[:300])
