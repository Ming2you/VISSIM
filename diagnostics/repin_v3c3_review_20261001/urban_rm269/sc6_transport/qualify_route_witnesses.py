"""Separate head-to-head path witnesses from an observed chosen direct turn.

No two-head ID match alone is promoted to a unique intermediate connector.
"""
import hashlib,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
PINS={}

def data(path):
    b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest();return b

def read(path):return json.loads(data(path))

def main():
    assert not (HERE/'route_qualification.json').exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    audit=read(HERE/'assessment.json')
    tree=ET.fromstring(data(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    decisions={d.get('no'):d for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    assert not any(d.get('link')=='1220012103' for d in decisions.values())
    head=tree.find("./signalHeads/signalHead[@no='50201']")
    assert head.get('lane')=='1220012103 2' and head.get('sg')=='12 5'
    connector=tree.find("./links/link[@no='10242']")
    assert connector.find('fromLinkEndPt').get('lane')=='1220012103 2'
    assert connector.find('toLinkEndPt').get('lane').split()[0]=='1220015100'
    report={}
    for arm in ('hold','selected'):
        folder=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        frames={}
        for t in (2400,2550,2700):
            raw=read(folder/f'state_{t:06}.json')
            info=raw['obs150']['frames']['current'];path=folder/info['path'];b=data(path)
            assert PINS[str(path)]==info['sha256']
            frame=json.loads(b)
            assert frame['complete'] is True and frame['time_s']==t
            assert frame['run_id']==raw['run_provenance']['run_id']
            assert all(len(v)==15 for v in frame['vehicles'])
            assert len({v[0] for v in frame['vehicles']})==len(frame['vehicles'])==info['vehicles']
            frames[t]={v[0]:v for v in frame['vehicles']}
        qualified=[]
        witnesses=[w for w in audit['arms'][arm]['path_witnesses'] if w['source']=='SC12_W']
        for w in witnesses:
            t=max(t for t in frames if t<=w['source_sec'])
            v=frames[t].get(w['vehicle_id'])
            if not v or v[1]!=1220012103 or v[3]>=float(head.get('pos')) or v[6] is None or v[8]!='STATIC':continue
            assert float(v[6]).is_integer() and float(v[7]).is_integer()
            d=decisions[str(int(v[6]))]
            r=d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(v[7])}']")
            path=[d.get('link')]+[n.get('key') for n in r.findall('./linkSeq/intObjectRef')]+[r.get('destLink')]
            if path.count('1220012103')!=1:continue
            idx=path.index('1220012103')
            if path[idx+1:idx+3]!=['10242','1220015100']:continue
            qualified.append(dict(**w,frame_sec=t,frame_link=v[1],frame_lane=v[2],frame_position_m=v[3],
                current_route=f'{int(v[6])}:{int(v[7])}',next_path_links=path[idx:idx+3]))
        assert len({w['vehicle_id'] for w in qualified})==len(qualified)
        predicted=audit['arms'][arm]['model_same450s_source_departures']['SC12_W']
        assert len(qualified)>predicted
        report[arm]=dict(head_to_head_witnesses=len(witnesses),observed_chosen_direct_turn_lower_bound=len(qualified),
            unresolved_direct_turn=len(witnesses)-len(qualified),model_direct_turn_departures=predicted,witnesses=qualified)
    data(Path(__file__))
    document=dict(status='complete_direct_turn_support_qualified',arms=report,source_pins=PINS,
        interpretation='31/15 two-head witnesses establish source-to-SC6 travel, not a unique intermediate connector. Only8/7 have a preceding complete snapshot on the same pre-head source link with an active static route immediately selecting10242; no intervening routing decision is present on that link.',
        limitation='The connector itself has no detector in this data. This is current chosen-route support plus later downstream passage, not a directly observed10242 crossing census or saturation capacity. Do not fit to future validation witnesses.',
        supersedes='Any northbound-connector lower-bound interpretation of31/15 in service_binding.json; raw two-head observations remain valid.',
        production_changes=0,new_forecasts=0,native_runs=0,fzp_scans=0)
    (HERE/'route_qualification.json').write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print({k:{x:v[x] for x in ('head_to_head_witnesses','observed_chosen_direct_turn_lower_bound','model_direct_turn_departures')} for k,v in report.items()})

if __name__=='__main__':main()
