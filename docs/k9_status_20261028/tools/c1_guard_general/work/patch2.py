p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
# insert path/route helpers before meters section
anchor = '    # meters: pre-head connector storage + upstream approach'
s = s.replace(anchor, open('work/patch_paths_body.txt', encoding='utf-8').read() + anchor, 1)
# replace finalize
a = s.index('    # finalize feeders')
b = s.index('    res = dict(tool=')
s = s[:a] + open('work/patch_fin_body.txt', encoding='utf-8').read() + s[b:]
open(p, 'w', encoding='utf-8').write(s)
print('patched2')
