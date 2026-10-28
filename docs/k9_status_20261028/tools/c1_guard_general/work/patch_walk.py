p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
a = s.index('    # ------------------------------------------------------------------ (2) headless feeders by upstream walk')
b = s.index('    # meters: pre-head connector storage + upstream approach')
new = open('work/patch_walk_body.txt', encoding='utf-8').read()
s = s[:a] + new + s[b:]
s = s.replace("""        walk_up(f_link, [f_lane + i for i in range(cl['lanes'])], f_pos, server, 'meter:' + name, 1, frozenset())""",
              """        walk_link(f_link, f_pos, c, server, 'meter:' + name, 1)""")
a = s.index('    # finalize feeders')
b = s.index('    res = dict(tool=')
fin = open('work/patch_fin_body.txt', encoding='utf-8').read()
s = s[:a] + fin + s[b:]
s = s.replace("feeders=frows, meters=meters, offramps=offramps,",
              "feeders=frows, approach_boundaries=approach_boundaries, meters=meters, offramps=offramps,")
open(p, 'w', encoding='utf-8').write(s)
print('patched')
