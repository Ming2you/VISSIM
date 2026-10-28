# B0 offline test of the ported K8-9 phantom route alias in the b0 codex control_area_objective.py (no VISSIM).
# (1) the b0 Omega701 route contract: the three phantom keys have null probabilities and their siblings have numbers;
# (2) ModelAreaLedger.transfer: without alias_route a phantom transfer raises "unresolved destination"; with the sibling
#     route it books the sibling's probabilities and counts phantom_route_alias:<key>; a non-phantom path is unchanged.
# usage: python -B test_alias_b0.py
import json, os, sys
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code'
sys.path.insert(0, B0)
sys.dont_write_bytecode = True
from evaluation.controllers import control_area_objective as cao  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
rc = json.load(open(B0 + '/diagnostics/b0_v3c3/omega701/route_contract.json', encoding='utf-8'))
res = {'contract': {}, 'ledger': {}}
for phantom, sib in cao.PHANTOM_ROUTE_ALIAS.items():
    p, s = rc.get(phantom, {}), rc.get(sib, {})
    res['contract'][phantom] = {'phantom_probs': [p.get('inside_to_inside'), p.get('outside_to_inside')], 'phantom_status': p.get('status'),
                                'sibling': sib, 'sibling_probs': [s.get('inside_to_inside'), s.get('outside_to_inside')],
                                'sibling_ok': cao._phantom_alias_probabilities_ok(s)}
phantom = 'movement:SC5_S_to_N_SC102'
sib = rc[cao.PHANTOM_ROUTE_ALIAS[phantom]]
led = cao.ModelAreaLedger({'q': {'inside': 3.0, 'outside': 1.0}})
try:
    led.transfer('q', 'r', 2.0, inside_to_inside=None, outside_to_inside=None, route_key=phantom)
    res['ledger']['no_alias'] = 'no error'
except cao.MembershipError as exc:
    res['ledger']['no_alias'] = 'MembershipError: ' + str(exc)[:120]
led2 = cao.ModelAreaLedger({'q': {'inside': 3.0, 'outside': 1.0}})
led2.transfer('q', 'r', 2.0, inside_to_inside=None, outside_to_inside=None, route_key=phantom, alias_route=sib)
res['ledger']['with_alias'] = {'stocks': led2.stocks, 'flow_counts': dict(led2.flow_counts)}
led3 = cao.ModelAreaLedger({'q': {'inside': 3.0, 'outside': 1.0}})
led3.transfer('q', 'r', 2.0, inside_to_inside=1.0, outside_to_inside=0.0, route_key='movement:other', alias_route=sib)
res['ledger']['non_phantom_with_probs'] = {'stocks': led3.stocks, 'flow_counts': dict(led3.flow_counts)}
json.dump(res, open(os.path.join(HERE, 'test_alias_b0.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, default=str)[:1500])
