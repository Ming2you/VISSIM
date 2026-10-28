import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def find(o, key, path, out, depth=0):
    if depth > 12: return
    if isinstance(o, dict):
        for k, v in o.items():
            if key in k:
                out.append(path + '/' + k)
            find(v, key, path + '/' + k, out, depth+1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            find(v, key, path + f'[{i}]', out, depth+1)
for key in sys.argv[2:]:
    out = []
    find(d, key, '', out)
    print(key, len(out))
    for x in out[:25]: print('   ', x)
