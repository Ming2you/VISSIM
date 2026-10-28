"""Synthetic self-test of vp_analyze.py definitions (no probe or VISSIM data).  python -B vp_selftest.py <out.json>"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402
import vp_analyze as A  # noqa: E402

RES = []


def check(name, cond, detail=''):
    RES.append({'name': name, 'ok': bool(cond), 'detail': str(detail)[:300]})


def close(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


def hook_const(T, stock, speed, flow, oq=0.0):
    blocks = {}
    for b in range(3):
        blocks[str(b)] = {'dt': 150.0, 'steps': 150, 'n_dt': [s * 150.0 for s in stock],
                          'nv_dt': [s * v * 150.0 for s, v in zip(stock, speed)], 'q_dt': [q * 150.0 for q in flow],
                          'oq_dt': oq * 150.0}
    return {'steps': 450, 't_first': float(T), 't_last': float(T + 449), 'errors': [], 'blocks': blocks,
            'first': {'params': {'lengths_km': list(A.LEN_KM), 'segment_rows': [{'v_free': 100.0, 'rho_crit': 30.0}] * 31,
                                 'metanet_delta_merge': 0.0, 'freeway_lane_drop_phi': 0.0, 'by_direction': None,
                                 'capacity_drop_discharge_phi': 1.0, 'capacity_drop_anticipation': False,
                                 'vsl_fd_response_present': False, 'vsl_transport': None},
                      'initial': {'stock_veh': stock, 'speed_kmh': speed}}}


def frames_const(T0, T1, N31, SV31):
    frames, N, SV = [], [], []
    t = T0 + 0.1
    while t < T1:
        frames.append(round(t, 1))
        N.append(list(N31))
        SV.append(list(SV31))
        t += 5.0
    return {'frames': frames, 'N': N, 'SV': SV}


def main():
    # 1. geometry and zones
    check('cells_31', C.N_CELL == 31 and len(C.CELL_B) == 32 and abs(C.CELL_B[-1] - 10784.028) < 1e-6)
    check('lane_drop_after_18', C.CELL_LANES[18] == 4 and C.CELL_LANES[19] == 3)
    check('zones', C.ZONES['VSa'] == [16, 17, 18] and C.ZONES['VSb'] == list(range(19, 26))
          and C.ZONES['M1'] == [14, 15] and C.ZONES['B1'] == list(range(8, 14)) and C.ZONES["VS0'"] == [18])
    check('focus_8_25', C.FOCUS_CELLS == list(range(8, 26)))
    # 2. plant cells and zones
    stock = [10.0 + i for i in range(31)]
    speed = [100.0 - i for i in range(31)]
    flow = [1000.0 + 10 * i for i in range(31)]
    h = hook_const(3000, stock, speed, flow, oq=4.0)
    pc = A.plant_cells(h, [0, 1, 2])
    check('plant_stock', close(pc['stock'][5], 15.0))
    check('plant_speed', close(pc['speed'][5], 95.0))
    check('plant_flow', close(pc['flow'][5], 1050.0))
    z = A.zone_plant(pc, 'VSb')
    idx = list(range(19, 26))
    want_speed = sum(stock[i] * speed[i] for i in idx) / sum(stock[i] for i in idx)
    want_flow = sum(flow[i] * A.LEN_KM[i] for i in idx) / sum(A.LEN_KM[i] for i in idx)
    check('plant_zone_speed', close(z['speed'], want_speed))
    check('plant_zone_flow', close(z['flow'], want_flow))
    check('plant_zone_stock', close(z['stock'], sum(stock[i] for i in idx)))
    check('origin_queue_veh_h', close(A.oq_veh_h(h), 4.0 * 450 / 3600.0))
    # 3. VISSIM frames
    N31 = [2.0] * 31
    SV31 = [2.0 * 90.0] * 31
    SV31[18] = 2.0 * 60.0
    scan = frames_const(2950.0, 3500.0, N31, SV31)
    vc = A.vissim_cells(scan, 3000.0, 3150.0)
    check('vissim_frames_30', vc is not None and vc['frames'] == 30, vc and vc['frames'])
    check('vissim_cell8_stock', close(vc['stock'][8], 2.0))
    check('vissim_vsa_speed', close(A.zone_vissim(vc, 'VSa')['speed'], (90 + 90 + 60) / 3.0))
    check('vissim_flow_edie', close(vc['flow'][10], 2.0 * 90.0 / A.LEN_KM[10]))
    check('vissim_vs0', close(A.zone_vissim(vc, "VS0'")['speed'], 60.0))
    check('vissim_lt25_frames_none', A.vissim_cells(frames_const(3000.0, 3100.0, N31, SV31), 3000.0, 3150.0) is None)
    vc450 = A.vissim_cells(scan, 3000.0, 3450.0)
    check('vissim_w450_frames_90', vc450 is not None and vc450['frames'] == 90)
    # 4. sign rule
    check('sign_rule', A.sign(0.009) == '0' and A.sign(-0.011) == '-' and A.sign(0.02) == '+')
    # 5. windows table + e
    tabs = A.rollout_windows(h, scan, 3000)
    e = tabs['w450']['zones']['M1']['e']['speed']
    check('window_e_M1', close(e, (stock[14] * speed[14] + stock[15] * speed[15]) / (stock[14] + stock[15]) - 90.0), e)
    check('window_cell_e', close(tabs['b1']['cells']['18']['speed']['e'], speed[18] - 60.0))
    ib = A.initial_bias(h, scan, 3000)
    check('initial_bias_frames_2', ib['frames'] == 2 and close(ib['cells']['18']['e_speed'], speed[18] - 60.0), ib and ib['frames'])
    # 6. hook / map checks
    check('hook_ok', A.hook_ok(h, 3000)[0])
    h_bad = json.loads(json.dumps(h))
    h_bad['steps'] = 449
    check('hook_bad_steps', not A.hook_ok(h_bad, 3000)[0])
    check('map_ok', A.map_ok(h)[0], A.map_ok(h))
    h_off = json.loads(json.dumps(h))
    h_off['first']['params']['lengths_km'][3] += 0.002
    check('map_off_2m', not A.map_ok(h_off)[0])
    # 7. reach
    check('reach_C3', A.reach({}, h, 'C3_merge')[0])
    check('reach_C5', A.reach({}, h, 'C5_capdrop')[0])
    check('reach_C6', A.reach({}, h, 'C6_compliance')[0])
    check('reach_C1', A.reach({'cells': {'8': {'old': 1.0, 'new': 100.0}}}, h, 'C1_vfree')[0])
    check('reach_C1_miss', not A.reach({'cells': {'8': {'old': 1.0, 'new': 101.0}}}, h, 'C1_vfree')[0])
    check('reach_C7', A.reach({'cells': {'8': {'old': 1.0, 'new': speed[8]}}}, h, 'C7_initial')[0])
    check('reach_C7_miss', not A.reach({'cells': {'8': {'old': 1.0, 'new': speed[8] + 1.0}}}, h, 'C7_initial')[0])
    # 8. pointing rule
    def st(R):
        return {'ablations': {'C4_lanedrop': {'bit_identical_to_base': False,
                                              'metrics': {m: {'R': R} for m in A.METRICS}}}}
    s = A.summarise_p1([st(0.6)] * 6 + [st(0.1)] * 3)['C4_lanedrop']['m1_VSa_speed']
    check('pointing_6of9', s['points_to_term'] and s['n_defined'] == 9 and s['n_R_ge_0.5'] == 6, s)
    s2 = A.summarise_p1([st(0.6)] * 5 + [st(0.1)] * 4)['C4_lanedrop']['m1_VSa_speed']
    check('pointing_5of9_not', not s2['points_to_term'], s2)
    s3 = A.summarise_p1([st(0.9)] * 5 + [st(None)] * 4)['C4_lanedrop']['m1_VSa_speed']
    check('pointing_needs_6_defined', not s3['points_to_term'] and s3['n_defined'] == 5, s3)
    # 9. FZP 60 s profile
    nw = 151
    cells = [[[[0, 0.0, 0.0, 0, 0.0] for _ in range(4)] for _ in range(31)] for _ in range(nw)]
    for w in range(nw):
        for c in range(31):
            for li in range(4):
                n = 3 if w % 2 == 0 else 120
                v = 100.0 if w % 2 == 0 else 40.0
                cells[w][c][li] = [n, n * v, n * 110.0, 0, 0.0]
    scan60 = {'win_s': 60.0, 'nw': nw, 'frames': [12] * nw, 'cells': cells}
    prof = A.p1_fzp_profile(scan60)
    p8 = prof['8']
    check('fzp_low_speed', close(p8['low_speed_med'], 100.0), p8)
    check('fzp_low_k', close(p8['low_k_med'], (4 * 3 / 12.0) / (A.LEN_KM[8] * 4)), p8['low_k_med'])
    check('fzp_congested_share', 0.4 < p8['congested_share'] < 0.6, p8['congested_share'])
    check('fzp_sub_diff_zero', close(prof['18']["low_VS0'_minus_Mu'_speed_med"], 0.0, 1e-9))
    rows = A.cell_scan_rows(scan60)
    check('fzp_window_range', rows[0]['t0'] == 900.0 and rows[-1]['t0'] == 8940.0, (rows[0]['t0'], rows[-1]['t0']))
    # 9b. probe B block pooling by executed VSL
    check('block_vsl_on', A.block_vsl_on({'RW_FW_E_S10': [101.0, 110.0]}) is True
          and A.block_vsl_on({'RW_FW_E_S10': [110.0]}) is False and A.block_vsl_on(None) is None)
    tabsB = A.rollout_windows(h, scan, 3000)
    stB = [{'label': 'v3c3-s31', 'T': 3000, 'tag': 'A2', 'B_exec': tabsB, 'arms': {}}]
    decl = [{'label': 'v3c3-s31', 'T': 3000, 'written_fwe_T': {'x': [101.0]}, 'written_fwe_T150': {'x': [110.0]},
             'written_fwe_T300': {'x': [101.0]}}]
    sb = A.summarise_ab(stB, decl)
    on_n = sb['B_block_pool']['on']['VSa']['speed']['n']
    off_n = sb['B_block_pool']['off']['VSa']['speed']['n']
    check('block_pool_counts', on_n == 2 and off_n == 1, (on_n, off_n))
    # 9c. hook mapping by batch (temporary folder under VP/selftest)
    import shutil
    tmp = C.VP / 'selftest' / ('hookmap_%d' % __import__('os').getpid())
    (tmp / 'hooks').mkdir(parents=True, exist_ok=True)
    try:
        sha_a, sha_b = 'a' * 64, 'b' * 64
        ha = dict(h, request_sha256=sha_a)
        hb = json.loads(json.dumps(h))
        hb['request_sha256'] = sha_b
        hb['blocks']['0']['n_dt'][0] += 1.0
        for name, obj in (('vphook_%s_1.json' % sha_a[:16], ha), ('vphook_%s_2.json' % sha_a[:16], ha),
                          ('vphook_%s_3.json' % sha_b[:16], hb)):
            C.write_json(tmp / 'hooks' / name, obj)
        probe = {'evaluations': {'X': {'evaluated_action_token': 't1', 'mode': 'scalar', 'batch': 'B1'},
                                 'Y': {'evaluated_action_token': 't1', 'mode': 'scalar', 'batch': 'B2'}},
                 'runs': [{'batch': 'B1', 'action_token': 't1', 'mode': 'scalar', 'request_sha256': sha_a},
                          {'batch': 'B2', 'action_token': 't1', 'mode': 'scalar', 'request_sha256': sha_b}]}
        hx, wx = A.hook_for(tmp, probe, 'X')
        hy, wy = A.hook_for(tmp, probe, 'Y')
        check('hook_for_batch_x', hx is not None and hx['request_sha256'] == sha_a, wx)
        check('hook_for_batch_y', hy is not None and hy['request_sha256'] == sha_b, wy)
        C.write_json(tmp / 'hooks' / ('vphook_%s_4.json' % sha_a[:16]), dict(hb, request_sha256=sha_a))
        hz, wz = A.hook_for(tmp, probe, 'X')
        check('hook_for_ambiguous', hz is None and 'ambiguous' in (wz or ''), wz)
        check('reach_no_hook', A.reach({}, None, 'null') == (False, 'no hook'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # 9d. lock pause after our own release (temporary lock files, pause shortened to 1 s)
    import os
    import time as _time
    tmpd = C.VP / 'selftest' / ('lock_%d' % os.getpid())
    tmpd.mkdir(parents=True, exist_ok=True)
    saved = (C.LOCK, C.LAST_RELEASE, C.RELEASE_PAUSE_SEC)
    try:
        C.LOCK, C.LAST_RELEASE, C.RELEASE_PAUSE_SEC = tmpd / 'heavy.lock', tmpd / 'last.json', 1.0
        C.write_json(C.LAST_RELEASE, {'epoch': _time.time()})
        t_0 = _time.time()
        C.lock_acquire('selftest', log=lambda m: None, poll_sec=0.05)
        waited = _time.time() - t_0
        held = C.LOCK.is_file()
        released = C.lock_release(log=lambda m: None)
        check('lock_pause_after_release', waited >= 0.9 and held and released and not C.LOCK.exists(), waited)
    finally:
        C.LOCK, C.LAST_RELEASE, C.RELEASE_PAUSE_SEC = saved
        import shutil
        shutil.rmtree(tmpd, ignore_errors=True)
    # 9e. review r2 (PRE_VP_FIXED): C8 / C9 reach, exit record X1/X2, direction columns, X1 summary
    h8 = json.loads(json.dumps(h))
    h8['first']['params']['segment_rows'] = [dict(r) for r in h8['first']['params']['segment_rows']]
    h8['first']['params']['segment_rows'][18]['metanet_nu_km2_h'] = 0.0
    app8 = {'cells': {'18': {'old': 38.7, 'new': 0.0}}}
    check('reach_C8', A.reach(app8, h8, 'C8_antic18')[0])
    check('reach_C8_miss', not A.reach(app8, h, 'C8_antic18')[0])
    check('reach_C8_empty_cells', not A.reach({'cells': {}}, h8, 'C8_antic18')[0])
    h8c = json.loads(json.dumps(h8))
    h8c['first']['params']['capacity_drop_anticipation'] = True
    check('reach_C8_nucong_on', not A.reach(app8, h8c, 'C8_antic18')[0])
    check('reach_C9', A.reach(app8, h8, 'C9_lanedrop_both')[0])
    h9 = json.loads(json.dumps(h8))
    h9['first']['params']['freeway_lane_drop_phi'] = 3.0
    check('reach_C9_phi_miss', not A.reach(app8, h9, 'C9_lanedrop_both')[0])
    hx = json.loads(json.dumps(h))
    hx['exits'] = sorted(A.EXITS)
    hx['exit_missing'] = []
    for b in range(3):
        hx['blocks'][str(b)]['exit_dt'] = {o: 360.0 * 150.0 for o in A.EXITS}
        hx['blocks'][str(b)]['exit_blocked_dt'] = {o: (36.0 * 150.0 if o == '10481' else 0.0) for o in A.EXITS}
        hx['blocks'][str(b)]['speed_proj'] = 2.0
    xe = A.exits(hx)
    check('exits_sum', xe is not None and close(xe['exit_veh']['10483'], 45.0) and close(xe['blocked_veh']['10481'], 4.5)
          and close(xe['blocked_veh']['10483'], 0.0) and close(xe['speed_proj'], 6.0), xe)
    check('exits_b0_only', close(A.exits(hx, (0,))['exit_veh']['10643'], 15.0))
    hxm = json.loads(json.dumps(hx))
    hxm['exit_missing'] = ['offramp_flow_10481']
    check('exits_missing_none', A.exits(hxm) is None and A.exits(h) is None)
    p1x = {'states': [{'base': True, 'exits_base': xe}, {'base': True, 'exits_base': None},
                      {'base': True, 'exits_base': {'blocked_veh': {'10481': 0.5}}}]}
    xs = A.x1_summary(p1x)['10481']
    check('x1_summary', xs['n_states'] == 3 and xs['n_available'] == 2 and xs['n_ge_1veh'] == 1, xs)
    pp = {'cells': {str(i): {'rho_crit': 35.0, 'plant_fd_speed_at_k_med': 90.0, 'vissim_s_med': 100.0}
                    for i in A.FOCUS}}
    nc3p = {}
    for lab, k in (('NC3_v3c3-s31', 40.0), ('NC3_v3c3-s41', 30.0), ('NC3_v3c3-s43', 38.0)):
        nc3p[lab] = {'all': {str(i): {'k_at_qmax': (k if i != 19 else 20.0)} for i in A.FOCUS}}
    nc3p['VA_v3c3-s31'] = {'all': {str(i): {'k_at_qmax': 1.0} for i in A.FOCUS}}
    dbx = A.direction_basis(nc3p, pp)
    check('direction_C1_gap', close(dbx['m1_VSa_speed']['C1_fd_minus_vissim_low_speed_mean'], -10.0)
          and dbx['m1_VSa_speed']['C1_cells'] == 3, dbx['m1_VSa_speed'])
    check('direction_C2_count', dbx['m3_VSb_stock']['C2_cells'] == 7 and dbx['m3_VSb_stock']['C2_cells_kqmax_above_rhoc'] == 6
          and dbx['m3_VSb_stock']['C2_basis'] is True, dbx['m3_VSb_stock'])
    check('direction_none', A.direction_basis(nc3p, None) is None)
    check('ablation_list_r2', A.ABLATIONS[-2:] == ['C8_antic18', 'C9_lanedrop_both'] and len(A.ABLATIONS) == 9)

    def stz(name):
        return {'ablations': {name: {'bit_identical_to_base': True, 'metrics': {m: {'R': 0.0} for m in A.METRICS}}}}
    sz = A.summarise_p1([stz('C5_capdrop')] * 9)['C5_capdrop']['m1_VSa_speed']
    check('n_states_and_identical', sz['n_states'] == 9 and sz['n_bit_identical'] == 9, sz)
    # 10. markdown renders on a synthetic result
    res = {'AB': {'states': [dict(stB[0], label='v3c3-s31', exits={'EXEC_scalar': xe})], 'stops': [], 'summary': sb},
           'P1': {'states': [], 'stops': [], 'summary': A.summarise_p1([st(0.6)] * 6 + [stz('C5_capdrop')] * 6)},
           'P1_FZP': {'X': {'all': prof}}, 'P1_direction': dbx, 'P1_X1': A.x1_summary(p1x)}
    md = A.md_tables(res)
    check('md_renders', '표 P1-R' in md and '가리킴' in md)
    check('md_r2_columns', '표 B5' in md and '방향 근거' in md and 'X1 요약' in md and '구조상 0' in md
          and 'FD−VISSIM 저밀도 -10.0' in md, md[-600:])
    ok = all(r['ok'] for r in RES)
    C.write_json(sys.argv[1], {'schema': 'vp-selftest/1', 'kst': C.kst(), 'ok': ok, 'n': len(RES),
                               'n_ok': sum(r['ok'] for r in RES), 'results': RES})
    print('SELFTEST %d/%d ok=%s' % (sum(r['ok'] for r in RES), len(RES), ok))
    for r in RES:
        if not r['ok']:
            print('FAIL', r)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
