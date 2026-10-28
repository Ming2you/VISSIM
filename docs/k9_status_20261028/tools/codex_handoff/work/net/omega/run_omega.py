import json, sys, hashlib, xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
sys.path.insert(0,'.')
import bcam_codex as B
R='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/'
rd=lambda p: json.load(open(p,encoding='utf-8'))
mapping=rd(R+'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
terr=rd(R+'outputs/urban_player_territory_v2_20260907.json')
codex701=rd(R+'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json')
res={}
for nm,old,net in [('64cf',R+'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/control_area_membership_213a5d.json',R+'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'),
                   ('v3c3','D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json','D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx')]:
    area=B.expand_controlled_intersection_area(rd(old),ET.parse(net).getroot(),mapping,terr)
    ins=set(area['inside_links']); res[nm]=sorted(ins,key=int)
    print(nm,'inside',len(ins),'outside',len(area['outside_links']),'== codex701:',ins==set(codex701['inside_links']),
          'added',len(area['controlled_intersection_expansion']['added_links']))
print('v3c3 701 == 64cf 701:', res['v3c3']==res['64cf'])
json.dump(res,open('omega701_rederived.json','w'),indent=0)
