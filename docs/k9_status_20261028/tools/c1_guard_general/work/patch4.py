p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
old = """        up = prev_head(link, lane, h['pos'])
        start = up['pos'] if up else 0.0
        same_lane_heads = hb[link, lane]"""
new = """        # A head of the same SC within SAME_STOPLINE_M on the same lane is the same stop line (shared lane,
        # several SGs), not an upstream stop line.
        shared = [x for x in hb[link, lane] if x is not h and x['sc'] == h['sc'] and abs(x['pos'] - h['pos']) <= SAME_STOPLINE_M]
        up = None
        for x in hb[link, lane]:
            if x['pos'] < h['pos'] - EPS and x not in shared:
                up = x
        start = up['pos'] if up else 0.0
        same_lane_heads = hb[link, lane]"""
assert old in s
s = s.replace(old, new, 1)
s = s.replace("EPS = 1e-6\n", "EPS = 1e-6\nSAME_STOPLINE_M = 3.0   # design choice (not data-fitted): same-SC heads this close = one stop line\n", 1)
old2 = """                   heads_on_lane=len(same_lane_heads), part=part_of(link),"""
new2 = """                   heads_on_lane=len(same_lane_heads), part=part_of(link),
                   shared_stopline_sgs=sorted(x['sg'] for x in shared),"""
assert old2 in s
s = s.replace(old2, new2, 1)
open(p, 'w', encoding='utf-8').write(s)
print('patched4')
