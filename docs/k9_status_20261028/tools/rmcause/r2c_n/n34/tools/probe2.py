# N34 probe (read-only): JSON paths in one decision whose key or string value mentions a pattern
import json, sys, re, collections
p, pat = sys.argv[1], re.compile(sys.argv[2])
d = json.load(open(p, encoding='utf-8-sig'))
hits = collections.Counter(); ex = {}
def walk(x, path):
    if isinstance(x, dict):
        for k, v in x.items():
            q = path + '/' + (re.sub(r'\d+', '#', k) if not pat.search(k) else k)
            if pat.search(k):
                hits[q] += 1; ex.setdefault(q, v if not isinstance(v, (dict, list)) else type(v).__name__)
            walk(v, q)
    elif isinstance(x, list):
        for i, v in enumerate(x[:400]):
            walk(v, path + '[]')
walk(d, '')
for k, n in sorted(hits.items()):
    print(n, k, str(ex[k])[:80])
