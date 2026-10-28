# -*- coding: utf-8 -*-
import json, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
pat = re.compile(sys.argv[2], re.I)
hits = {}
def find(o, path, depth):
    if depth > 12: return
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'source_sha256': continue
            np_ = path + '/' + str(k)
            if pat.search(str(k)):
                key = re.sub(r'\[\d+\]', '[]', np_)
                if key not in hits:
                    hits[key] = (type(v).__name__, (len(v) if hasattr(v, '__len__') and not isinstance(v, str) else repr(v)[:80]))
            find(v, np_, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:4]):
            find(v, path + '[%d]' % i, depth + 1)
find(d, '', 0)
for k, v in sorted(hits.items()): print(k, v)
