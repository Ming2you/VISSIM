"""Read-only: list JSON pointers in a tuning file whose string value matches patterns."""
import json, sys
path = sys.argv[1]; pats = sys.argv[2:]
d = json.load(open(path, encoding='utf-8'))
def walk(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, p + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, p + '/' + str(i))
    else: yield p, o
for p, v in walk(d):
    if isinstance(v, str) and any(s in v for s in pats):
        print(p, '=', v)
