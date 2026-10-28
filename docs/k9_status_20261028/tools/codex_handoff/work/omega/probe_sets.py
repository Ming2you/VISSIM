# probe: membership sets and chains (read only)
import sys, json, hashlib
sys.dont_write_bytecode = True
sys.path.insert(0, 'D:/VISSIM-merge/tools/stage1')
import stage1_common as C
C.find_rule_policy = lambda run_dir: None
inside635, keys, doc = C.membership_inside()
ex = json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8-sig'))
in701 = set(map(int, ex['inside_links'])); out701 = set(map(int, ex['outside_links']))
cie = ex['controlled_intersection_expansion']
print('cie keys', list(cie.keys()))
prev = set(map(int, cie['previous_inside_links'])) if 'previous_inside_links' in cie else None
added = cie.get('added_links')
print('635', len(inside635), '701', len(in701), 'out701', len(out701), 'keys', len(keys), 'all701', len(in701 | out701), 'keys==all701', keys == (in701 | out701))
print('635 subset 701', inside635 <= in701, 'diff', len(in701 - inside635))
print('prev==635', prev == inside635 if prev is not None else None, 'added', len(added) if added else None, (set(map(int, added)) if added and not isinstance(added[0], dict) else None) == (in701 - inside635) if added else None)
rd = json.load(open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/net/omega/omega701_rederived.json', encoding='utf-8-sig'))
print('rederived keys', list(rd.keys())[:20])
net = C.load_network('D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/prepared/network/baseline_s31_v3c3nc.inpx')
ch = C.chains(net)
print('FW_E', ch['FW_E']['links'], 'FW_W', ch['FW_W']['links'])
print('net links', len(net['links']), 'inputs', len(net['inputs']), [ (i['no'], i['link']) for i in net['inputs']][:40])
print('701 not in net', sorted(in701 - set(net['links']))[:10], '635 not in net', sorted(inside635 - set(net['links']))[:10])
print('MEMBERSHIP', C.MEMBERSHIP, hashlib.sha256(open(C.MEMBERSHIP,'rb').read()).hexdigest())
