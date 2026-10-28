import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
d=o['diagnostics']
for k,v in d.items():
    s=json.dumps(v); print(k, len(s), s[:250])
print('vsl', {k:v for k,v in o['vsl'].items() if v!=110})
