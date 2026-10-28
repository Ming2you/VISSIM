import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def walk(o, path, depth):
    if depth > 3: return
    if isinstance(o, dict):
        for k, v in o.items():
            t = type(v).__name__
            n = len(v) if isinstance(v, (dict, list, str)) else ''
            print('  '*depth + f'{path}/{k} [{t} {n}]')
            if isinstance(v, dict) and depth < 3:
                walk(v, path+'/'+k, depth+1)
walk(d, '', 0)
