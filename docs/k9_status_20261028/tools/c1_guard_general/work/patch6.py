p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
old = "                            part=part_of(c), plant_storage_key=l2o.get(c))"
new = """                            part=part_of(c), plant_storage_key=l2o.get(c),
                            plant_ramp_queue=[dict(key=q, max_veh=net.get('ramp_queue_max_veh_by_ramp', {}).get(q))
                                              for q in det.get('ramp_link_to_queues', {}).get(c, [])])"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
p = 'tools/inv_final.py'
s = open(p, encoding='utf-8').read()
# role names
s = s.replace("""def f1(x, nd=1):""", """ROLE_KO = {'controlled_phase': '현시', 'controlled_sc_midblock_native': '미드블록 SG(우리 현시 밖)',
           'controlled_sc_unmapped_sg': '현시 없는 SG', 'native_signal': 'native 신호', 'meter': '미터'}


def rk(x):
    return ROLE_KO.get(x, x)


def f1(x, nd=1):""", 1)
s = s.replace("other_detail=sorted({'%s(SG%s)' % (a['role'], a['sg']) for a in other}),", "other_detail=sorted({'%s SG%s' % (rk(a['role']), a['sg']) for a in other}),")
s = s.replace("""a['sc'], a['link'], a['lane'], a['sg'], f1(a['head_pos_m']), a['role'],
                (' (위 정지선 %s SC%s SG%s @%s m)' % (a['upstream_head']['role'],""", """a['sc'], a['link'], a['lane'], a['sg'], f1(a['head_pos_m']), rk(a['role']),
                (' (위 정지선 %s SC%s SG%s @%s m)' % (rk(a['upstream_head']['role']),""")
s = s.replace("""        t.append('| %s | %s SC%s SG%s @%s m | %s (@%s) |' % (b['approach'], u['role'],""", """        t.append('| %s | %s SC%s SG%s @%s m | %s (@%s) |' % (b['approach'], rk(u['role']),""")
# offramp landing lanes
s = s.replace("""c, o['road'], o['from_link'], f1(o['diverge_pos_m']), o['lanes'], f1(o['length_m']), o['to_link'], o['to_lane'], f1(o['landing_pos_m']),""",
              """c, o['road'], o['from_link'], f1(o['diverge_pos_m']), o['lanes'], f1(o['length_m']), o['to_link'],
            ('%d' % o['to_lane']) if o['lanes'] == 1 else '%d–%d' % (o['to_lane'], o['to_lane'] + o['lanes'] - 1), f1(o['landing_pos_m']),""")
s = s.replace("t = ['| 진출 커넥터 | 도로 | 갈림(링크 @m) | 차로·길이 m | 착지(링크:차로 @m) |", "t = ['| 진출 커넥터 | 도로 | 갈림(링크 @m) | 차로·길이 m | 착지(링크:차로 @m) |")
s = s.replace("""        t.append('| %s | %s | %s @%s | %d · %s | %s:%d @%s | %s | %s | %s |' % (""", """        t.append('| %s | %s | %s @%s | %d · %s | %s:%s @%s | %s | %s | %s |' % (""")
# meter plant key
s = s.replace("""            ','.join(m['plant_storage_key'] or []) or '–'))""", """            ', '.join('%s(%s)' % (q['key'], f1(q['max_veh'])) for q in m.get('plant_ramp_queue', [])) or '–'))""")
s = s.replace("| 접근에 착지하는 공급 | plant 저장 키 |', '|---|", "| 접근에 착지하는 공급 | plant 램프 대기 키(설정 최대 대) |', '|---|")
# dedupe direct feeders by connector
old = """                bylink[x['on_link']].append((x['landing_pos_m'], '%s(%s:%s @%s → %s @%s, %s m, %s대)' % (
                    c['link'], c['connector_from']['link'], c['connector_from']['lane'], f1(c['connector_from']['pos_m']),
                    ','.join(map(str, x['on_lanes'])), f1(x['landing_pos_m']), f1(x['landing_to_server_end_m']), f1(x['landing_to_server_end_m'] / SF)), bnd))"""
new = """                bylink[x['on_link']].append((c['link'], x, c, bnd))"""
assert old in s
s = s.replace(old, new, 1)
old = """        rows = sorted(set(bylink.get(g['link'], [])))
        t.append('| %s (%s) | %s | %s |' % (g['link'], g['sc'], ' · '.join(r[1] for r in rows) or '–', ' · '.join(r[2] for r in rows) or '–'))"""
new = """        agg = {}
        for cid, x, c, bnd in bylink.get(g['link'], []):
            e = agg.setdefault(cid, dict(c=c, x=x, lo=x['landing_to_server_end_m'], hi=x['landing_to_server_end_m'], bnd=bnd))
            e['lo'] = min(e['lo'], x['landing_to_server_end_m'])
            e['hi'] = max(e['hi'], x['landing_to_server_end_m'])
        cells, bnds = [], []
        for cid, e in sorted(agg.items(), key=lambda kv: (kv[1]['x']['landing_pos_m'], kv[0])):
            c, x = e['c'], e['x']
            rng = f1(e['lo']) if abs(e['hi'] - e['lo']) < 0.05 else '%s–%s' % (f1(e['lo']), f1(e['hi']))
            cells.append('%s(%s:%s @%s → %s @%s, %s m, %s대)' % (cid, c['connector_from']['link'], c['connector_from']['lane'],
                                                               f1(c['connector_from']['pos_m']), ','.join(map(str, x['on_lanes'])),
                                                               f1(x['landing_pos_m']), rng, f1(e['lo'] / SF)))
            bnds.append('%s: %s' % (cid, e['bnd']))
        t.append('| %s (%s) | %s | %s |' % (g['link'], g['sc'], ' · '.join(cells) or '–', ' · '.join(bnds) or '–'))"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
