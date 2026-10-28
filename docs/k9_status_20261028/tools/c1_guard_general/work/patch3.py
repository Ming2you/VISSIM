p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
old_head = """            for ln in range(1, L[x]['lanes'] + 1):
                for t in out_c.get((x, ln), []):
                    if t['source_pos'] < p - EPS:
                        continue
                    h = lane_head.get(ln)"""
new_head = """            n_follow = 0
            for ln in range(1, L[x]['lanes'] + 1):
                for t in out_c.get((x, ln), []):
                    if t['source_pos'] < p - EPS:
                        continue
                    h = lane_head.get(ln)"""
assert old_head in s
s = s.replace(old_head, new_head, 1)
old_push = """                    heapq.heappush(pq, (c1 + L[c]['length_m'], t['link'], t['position']))
        return best"""
new_push = """                    n_follow += 1
                    heapq.heappush(pq, (c1 + L[c]['length_m'], t['link'], t['position']))
            if not lane_head and n_follow == 0 and not any(t['source_pos'] >= p - EPS for ln in range(1, L[x]['lanes'] + 1)
                                                           for t in out_c.get((x, ln), [])):
                lab = 'sink:' + x
                c2 = cost + L[x]['length_m'] - p
                if lab not in best or c2 < best[lab]:
                    best[lab] = c2
        return best"""
assert old_push in s
s = s.replace(old_push, new_push, 1)
a = s.index("        path = []\n        frontier = [(c, i, 0.0) for i in range(1, cl['lanes'] + 1)]")
b = s.index("        offramps[c] = dict(")
s = s[:a] + """        dd = dist_to_servers(c, 0.0)
        servers = set(dd)
        path = {k: v for k, v in sorted(dd.items())}
""" + s[b:]
s = s.replace("path=path, routes=routes_through(c))", "dist_from_diverge_to_first_stopline_m=path, routes=route_servers_chained(c))")
open(p, 'w', encoding='utf-8').write(s)
print('patched3')
