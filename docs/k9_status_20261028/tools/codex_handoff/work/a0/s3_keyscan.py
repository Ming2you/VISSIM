# A0 step 3: scan key paths of a recorded action JSON (lists collapsed) to pre-declare excluded leaves
import json, re, sys
from collections import Counter
D = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
name = sys.argv[1]
out = sys.argv[2]
d = json.load(open(D + '/' + name, encoding='utf-8'))
cnt = Counter()
ex = {}
pathlike = Counter()
TIMEKEY = re.compile(r'(wall|elapsed|cpu|clock|perf|timestamp|created|started|finished|_at$|duration|seconds$|spawn|pid$|tmp|temp|host)', re.I)


def walk(x, p):
    if isinstance(x, dict):
        for k, v in x.items():
            walk(v, p + '/' + str(k))
    elif isinstance(x, list):
        for v in x[:]:
            walk(v, p + '/[]')
    else:
        cnt[p] += 1
        if p not in ex:
            ex[p] = repr(x)[:80]
        if isinstance(x, str) and re.match(r'^[A-Za-z]:[\\/]', x):
            pathlike[p] += 1


walk(d, '')
keys = sorted(cnt)
tl = [k for k in keys if TIMEKEY.search(k.split('/')[-1] if k.split('/')[-1] != '[]' else k)]
with open(out, 'w', encoding='utf-8') as f:
    f.write('# leaf paths: %d distinct, %d leaves\n' % (len(keys), sum(cnt.values())))
    f.write('## time-like key candidates (%d)\n' % len(tl))
    for k in tl:
        f.write('%d\t%s\t%s\n' % (cnt[k], k, ex[k]))
    f.write('## path-like string leaves (%d)\n' % len(pathlike))
    for k, v in sorted(pathlike.items()):
        f.write('%d\t%s\t%s\n' % (v, k, ex[k]))
    f.write('## all\n')
    for k in keys:
        f.write('%d\t%s\t%s\n' % (cnt[k], k, ex[k]))
print('distinct', len(keys), 'leaves', sum(cnt.values()), 'timelike', len(tl), 'pathlike', len(pathlike))
print('top', list(d.keys()) if isinstance(d, dict) else type(d))
