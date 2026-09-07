import json,os
BS=chr(92)
for R in ['h11_canon0905_lcd1000_x18_20260907','b0_rl_b0_lcd1000_x18_20260907','g1_base_x18_20260905','h0_nocontrol_lcd1000_x18_20260906']:
    s=json.load(open(f'evaluation/runs/{R}/decisions_{R}/state_003000.json',encoding='utf-8'))
    lo=s['local_observation']; print(R[:4], lo['detector_mapping_json'].split(BS)[-1], 'n link_counts',len(lo['link_counts']), '31 in?', '31' in lo['link_counts'])
for mp in ['detector_local_mapping_distributed_core17legs4b_20260819.json','detector_local_mapping_distributed_core17legs4f_20260903_blindfix20260905b.json']:
    m=json.load(open('evaluation/real_world_modi_control_distributed_20260728/'+mp,encoding='utf-8')); print(mp,'observable',len(m['observable_links']))
c=json.load(open('evaluation/configs/h_base_20260906.json',encoding='utf-8'))
print('config mapping_json',c.get('mapping_json'),'| detector_mapping_json',c.get('detector_mapping_json'))
def find(o,p=''):
    if isinstance(o,dict):
        for k,v in o.items():
            if isinstance(v,dict) and v.get('signal')=='SC1001' and 'phase' in v:
                print(f"  {k:32s} appr={str(v.get('approach')):10s} phase={v.get('phase')} beta={v.get('beta'):.3f} kind={v.get('kind')} recv={v.get('receiving_link')}")
            else: find(v,p+'/'+str(k))
find(c)
def path_of(o,p=''):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=='SC1001_S_SC1003_to_W': print('movement table path:',p); return True
            if path_of(v,p+'/'+str(k)): return True
    return False
path_of(c)
