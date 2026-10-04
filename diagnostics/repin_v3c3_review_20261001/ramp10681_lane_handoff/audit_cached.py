"""Reuse matched five-second departure events and first mainline observations."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/cohort_early'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def main():
    output=HERE/'audit.json';assert not output.exists()
    ledger=read(F/'summary.json');cases={}
    runtime=read(HERE.parent/'entry10643/native_cohorts.json')['route_runtime']
    net=ROOT/runtime['network']['path'];data=net.read_bytes()
    assert hashlib.sha256(data).hexdigest()==runtime['network']['sha256'];PINS[str(net)]=runtime['network']['sha256']
    connector=ET.fromstring(data).find("./links/link[@no='10681']")
    assert len(connector.findall('./lanes/lane'))==2 and connector.find('toLinkEndPt').attrib['lane']=='2 1'
    paths=[Path(p) for p in ledger['pins'] if p.endswith('port_events.csv')]
    for seed,marker in [(29,'reference_observations'),(43,'seed43')]:
        path=next(p for p in paths if marker in p.parts and p.parent.name=='none')
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();assert digest==ledger['pins'][str(path)];PINS[str(path)]=digest
        frames=read(F/f's{seed}_none_frames.json.gz');assert frames['fields']==['cell','speed_kmh','x_m','lane']
        events=[];missing=[]
        for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))):
            t=float(row['time_s'])
            if row['connector']!='10681' or row['kind']!='departure' or not 2250.1<t<=2700.1:continue
            assert row['other_link']=='2' and float(row['upper_time_s'])==t
            z=frames['frames'][str(t)].get(row['vehicle'])
            if z is None:missing.append(row);continue
            events.append(dict(time_sec=t,vehicle=row['vehicle'],last_ramp_lane=int(row['lane']),
                first_mainline_lane=z[3],first_cell=z[0],first_speed=z[1],
                distance_after_merge_m=z[2]-(runtime['physical']['2'][1]+float(connector.find('toLinkEndPt').attrib['pos'])),
                bracket_sec=t-float(row['lower_time_s'])))
        from_lane=[sum(e['last_ramp_lane']==g for e in events) for g in (1,2)]
        to_lane=[sum(e['first_mainline_lane']==g for e in events) for g in (1,2,3,4)]
        cases[str(seed)]=dict(events=events,missing=missing,last_ramp_lane=from_lane,first_mainline_lane=to_lane,
            endpoint_lane_changed=sum(e['last_ramp_lane']!=e['first_mainline_lane'] for e in events))
        print(seed,from_lane,to_lane,'changed',cases[str(seed)]['endpoint_lane_changed'],'missing',len(missing))
    predicted={}
    for seed,prefix in [('43','closedloop_recorded2250_lever450_trace10681_'),('47','closedloop_recorded2700_select_check_trace10681_')]:
        trace=read(I/(prefix+'lane10682_inlet_flux'+seed)/'held_actual_RM_C10681_trace.json.gz')
        receipts=[x['receipt'] for x in trace['lane_interval_receipts']];assert len(receipts)==450
        values=[sum(x['lane_receipts'][j]['accepted_merge_veh'] for x in receipts) for j in (0,1)]
        assert abs(sum(values)-sum(x['accepted_merge_veh'] for x in receipts))<1e-8
        predicted[seed]=values;print('predicted_ramp_receipts',seed,values)
    output.write_text(json.dumps(dict(status='completed_cached_lane_handoff_audit',native=cases,
        predicted_ramp_receipts=predicted,source_pins=PINS,new_forecasts=0,new_native=0,new_fzp=0,
        limitations=['Native2250.1-2700.1 differs by0.1s from current43 forecast2250-2700; do not force count parity.',
        'Five-second endpoint lane differences are unresolved within-bracket changes, not exact connector crossing lanes.',
        'No seed47 receiving-lane native trajectory is claimed from150s frames.',
        'Earlier1s observation assumption failed before full scan; failed audit.py and both logs preserved.']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
