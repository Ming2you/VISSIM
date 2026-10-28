p = 'tools/inv_final.py'
s = open(p, encoding='utf-8').read()
a = s.index('    # ---------------- occupancy (data after)')
b = s.index('    # ---------------- assemble json')
s = s[:a] + open('work/patch_occ_render.txt', encoding='utf-8').read() + s[b:]
# approach groups: three spacings
old = """        sf = [a['storage']['veh_per_lane_fzp'] for a in rows]"""
new = """        sf = [a['storage']['veh_per_lane_fzp'] for a in rows]
        sm = [a['storage']['veh_per_lane_fzp_mean'] for a in rows]"""
assert old in s; s = s.replace(old, new, 1)
old = """                 link_sum_storage_6m=sum(s6), link_sum_storage_fzp=sum(sf), codex_included"""
new = """                 lane_storage_fzp_mean=[min(sm), max(sm)], link_sum_storage_fzp_mean=sum(sm),
                 link_sum_storage_6m=sum(s6), link_sum_storage_fzp=sum(sf), codex_included"""
assert old in s; s = s.replace(old, new, 1)
old = """    t = ['| SC | 링크(차로, 길이 m) | 차로:SG/현시 | 머리 m | 구간 시작 m | 차로 저장 대 (6 m) | 차로 저장 대 (FZP %s m) | 링크 합 (6 m / FZP) | codex USG | Ω701 분할 | plant 저장 키(설정 대) |' % f1(SF, 2),
         '|---|---|---|---|---|---|---|---|---|---|---|']"""
new = """    def rg(v):
        return f1(v[0]) if abs(v[1] - v[0]) < 0.05 else '%s–%s' % (f1(v[0]), f1(v[1]))
    t = ['| SC | 링크(차로, 길이 m) | 차로:SG/현시 | 머리 m | 구간 시작 m | 차로 저장 대 (6 m / 중앙 %s / 평균 %s) | 링크 합 (6 m / 중앙 / 평균) | codex USG | Ω701 분할 | plant 저장 키(설정 대) |' % (f1(SF, 2), f1(inv['spacing_fzp_mean'], 2)),
         '|---|---|---|---|---|---|---|---|---|---|']"""
assert old in s; s = s.replace(old, new, 1)
old = """        t.append('| %s | %s (%d, %s) | %s | %s–%s | %s | %s–%s | %s–%s | %s / %s | %s | %s | %s |' % (
            g['sc'], g['link'], g['link_lanes'], f1(g['link_len_m']), g['lanes_text'], f1(g['head_pos_m'][0]), f1(g['head_pos_m'][1]),
            '/'.join(f1(x) for x in g['segment_start_m']), f1(g['lane_storage_6m'][0]), f1(g['lane_storage_6m'][1]),
            f1(g['lane_storage_fzp'][0]), f1(g['lane_storage_fzp'][1]), f1(g['link_sum_storage_6m']), f1(g['link_sum_storage_fzp']),"""
new = """        t.append('| %s | %s (%d, %s) | %s | %s | %s | %s / %s / %s | %s / %s / %s | %s | %s | %s |' % (
            g['sc'], g['link'], g['link_lanes'], f1(g['link_len_m']), g['lanes_text'], rg(g['head_pos_m']),
            '/'.join(f1(x) for x in g['segment_start_m']), rg(g['lane_storage_6m']), rg(g['lane_storage_fzp']), rg(g['lane_storage_fzp_mean']),
            f1(g['link_sum_storage_6m']), f1(g['link_sum_storage_fzp']), f1(g['link_sum_storage_fzp_mean']),"""
assert old in s; s = s.replace(old, new, 1)
# assemble: decisions -> dec_out
s = s.replace("occupancy_existing_states=dict(runs=runs, spacings=occ['spacings'], decisions=occ['decisions'],",
              "occupancy_existing_states=dict(runs=runs, spacings=occ['spacings'], length_rule=occ['length_rule'], decisions_any_ge_1_cap_ge_2=dec_out,")
s = s.replace("spacing=dict(codex_and_ours_m=S6, fzp_m=SF, fzp_summary=", "spacing=dict(codex_and_ours_m=S6, fzp_m=SF, fzp_mean_m=inv['spacing_fzp_mean'], fzp_summary=")
open(p, 'w', encoding='utf-8').write(s)
print('ok')
