import difflib, io, sys
R = r'D:\VISSIM_runs\20261001_v3c3'
out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
for s in (31, 41):
    for f in ('rule_policy.json', 'prepared.json'):
        a = open(r'%s\s%d_v3c3rm\prepared\%s' % (R, s, f), encoding='utf-8').read().splitlines()
        b = open(r'%s\s%d_v3c3rm10681\prepared\%s' % (R, s, f), encoding='utf-8').read().splitlines()
        d = list(difflib.unified_diff(a, b, 's%d_v3c3rm/prepared/%s' % (s, f), 's%d_v3c3rm10681/prepared/%s' % (s, f), n=0, lineterm=''))
        out.write('\n'.join(d) + '\n')
        adds = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
        dels = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
        print('s%d %s: -%d +%d lines' % (s, f, dels, adds))
out.close()
