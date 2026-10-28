# A0 step 2: what absolute paths do recorded state / action JSON carry?
import json, re, sys
D = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
pat = re.compile(r'[A-Za-z]:[\\/][^"\n]{3,200}')
for name in sys.argv[1:]:
    txt = open(D + '/' + name, encoding='utf-8').read()
    d = json.loads(txt)
    print('==', name, 'bytes', len(txt), 'top keys', list(d.keys())[:60] if isinstance(d, dict) else type(d))
    found = {}
    for m in pat.findall(txt):
        k = m[:120]
        found[k] = found.get(k, 0) + 1
    for k, v in sorted(found.items(), key=lambda x: -x[1])[:40]:
        print('  ', v, k)
