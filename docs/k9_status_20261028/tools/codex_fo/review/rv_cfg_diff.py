import json
FO=r'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954'
a=json.load(open(FO+r'\diagnostics\b0_v3c3\config_b0_v3c3.json',encoding='utf-8'))
b=json.load(open(FO+r'\diagnostics\b0_v3c3\config_fo_v3c3.json',encoding='utf-8'))
c=json.load(open(r'D:\VISSIM_handoff\20261024\original_code_dependencies\solo\diagnostics\solo355_local_20261013\freeway_only_config.json',encoding='utf-8')) if __import__('os').path.exists(r'D:\VISSIM_handoff\20261024\original_code_dependencies\solo\diagnostics\solo355_local_20261013\freeway_only_config.json') else None
def leaves(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): yield from leaves(v,p+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x): yield from leaves(v,p+'/'+str(i))
    else: yield p,x
A=dict(leaves(a)); B=dict(leaves(b))
d=[k for k in set(A)|set(B) if A.get(k,'<none>')!=B.get(k,'<none>')]
print('diff leaves',len(d), 'outside scope', [k for k in d if not k.startswith('/adapter/sdmpc_actuator_scope')])
print('scope mode', b['adapter']['sdmpc_actuator_scope']['mode'], 'keys', list(b['adapter']['sdmpc_actuator_scope'].keys()), list(b['adapter']['sdmpc_actuator_scope']['baseline'].keys()))
print('fixed_vsl', a['adapter'].get('sdmpc_fixed_vsl'), b['adapter'].get('sdmpc_fixed_vsl'))
print('info scope in fo', 'sdmpc_information_scope' in b['adapter'])
if c is not None:
    print('baseline equals codex', c['adapter']['sdmpc_actuator_scope']==b['adapter']['sdmpc_actuator_scope'])
# list fast path keys
fk=[k for k in b['adapter'] if any(s in k for s in ['fast','hotpath','cache','overlap','compact','shared','concurrent','pipeline','transport','spatial','fifo'])]
for k in sorted(fk): print(' ',k, b['adapter'][k])
print('adapter keys count', len(a['adapter']), len(b['adapter']))
