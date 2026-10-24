"""Trace missing SC101 supply in existing closed records; no new forecast."""
import gzip,importlib.util,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
loader=importlib.util.spec_from_file_location('reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC1_S':1220006903}
def main():
    dest=HERE/'source_check.json';assert not dest.exists()
    tree=ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='1220006903' and h.get('sg')=='1 8']
    assert {int(h.get('lane').split()[1]) for h in heads}=={2,3,4}
    links={l.get('no'):l for l in tree.findall('./links/link')}
    for h in heads:
        lane=int(h.get('lane').split()[1]);post=[]
        for key,l in links.items():
            s=l.find('fromLinkEndPt')
            if s is None or s.get('lane').split()[0]!='1220006903':continue
            lo=int(s.get('lane').split()[1])
            if lane in range(lo,lo+len(l.findall('./lanes/lane'))) and float(s.get('pos'))>float(h.get('pos')):post.append(key)
        assert post==['10025']
    assert links['10025'].find('toLinkEndPt').get('lane').split()[0]=='1220008501'
    moves=('SC1_S_SC107_to_N_SC101','SC1_S_to_N_SC101')
    results={}
    for arm in ('hold','selected'):
        response=json.loads(gzip.decompress(a.pin(H/'native_beta/forecast2400_checked'/(arm+'.response.json.gz'))))
        rows=[]
        for start in (2400,2550,2700):
            physical,_=a.heads_and_entries(a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29',start+150)
            counts=[r for r in physical['SC1_S']['rows'] if r['head_id'] in {h.get('no') for h in heads}]
            transfers=[t for t in response['transfers'] if start<=t['start_sec']<start+150]
            model={m:sum(t['vehicles'] for t in transfers if t['source']=='movement:'+m and t['target']=='storage:SC1_to_SC101') for m in moves}
            receiver=sum(t['vehicles'] for t in transfers if t['target']=='storage:SC1_to_SC101' and t['source']!=t['target'])
            rows.append(dict(start_sec=start,native_known_through_lower_bound=sum(h['crossings'] for h in counts),native_heads=counts,
                model_physical_through_alias_sum=sum(model.values()),model_by_alias=model,model_all_SC101_origin_incoming=receiver))
        results[arm]=rows
    a.pin(Path(__file__))
    out=dict(status='complete_readonly_source_lower_bound',source_pins=a.PINS,results=results,
        limitations=['SC1 south lanes2-4 uniquely continue via10025 into1220008501; lane5 can take10025 or10571, so its crossings are excluded and reported total is a lower bound.',
        'Native head passage is entrance into the SC1-to-SC101 corridor, not immediate arrival at the SC101 stop line.',
        'Future observations here diagnose errors and are never installed in an autonomous prediction.',
        'Model aliases are summed only across the same physical through connector. This does not qualify their independent lane sharing.',
        'The service candidate changes SC101 downstream; source comparison intentionally reuses native_beta baseline.'])
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

