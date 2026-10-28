import json,hashlib,os
FO=r'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954'
B1=r'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410'
S=json.load(open(r'D:\VISSIM_handoff\20261024\evidence\original_solo_FREEZE.json',encoding='utf-8'))
J=json.load(open(r'D:\VISSIM_handoff\20261024\evidence\original_FREEZE.json',encoding='utf-8'))
F=json.load(open(FO+r'\FREEZE.json',encoding='utf-8'))['files']
Bm=json.load(open(B1+r'\FREEZE.json',encoding='utf-8'))['files']
sf=S['files'] if 'files' in S else S
jf=J['files'] if 'files' in J else J
def h(v): return v.get('sha256') if isinstance(v,dict) else v
def fh(p):
    m=hashlib.sha256(); m.update(open(p,'rb').read()); return m.hexdigest()
names=[k for k in F if (k not in Bm) or h(F[k])!=h(Bm[k])]
for k in sorted(names):
    disk=fh(os.path.join(FO,k))
    print(k[len('evaluation/controllers/'):] if k.startswith('evaluation/controllers/') else k, 'disk==man', disk==h(F[k]), 'solo==', h(sf.get(k)) == disk if k in sf else 'NA', 'b1==joint', (h(Bm.get(k))==h(jf.get(k))) if k in Bm else 'new')
# the runner + config
for k in ['diagnostics/b0_v3c3/config_b0_v3c3.json','diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1']:
    print(k, fh(os.path.join(FO,k)), fh(os.path.join(B1,k)), h(F[k])==h(Bm[k]))
