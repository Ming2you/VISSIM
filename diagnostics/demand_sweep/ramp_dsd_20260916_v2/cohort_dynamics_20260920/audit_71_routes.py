"""Read-only approach/route audit; never writes an INPX or changes demand."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H
import xml.etree.ElementTree as ET
import hashlib

HERE=Path(__file__).resolve().parent


def main():
    path=H/'source_dsd/baseline.inpx';root=ET.parse(path).getroot()
    links={int(n.get('no')):n for n in root.findall('./links/link')}
    decisions={int(n.get('no')):n for n in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    out=HERE/'route71_readonly_v1.json';assert not out.exists()
    def point(n,tag):
        x=n.find(tag);link,lane=map(int,x.get('lane').split())
        return {'link':link,'lane':lane,'pos_m':float(x.get('pos'))}
    connections={}
    for cid in [10640,10641,10700,10634,10635,10642,10643]:
        n=links[cid];connections[str(cid)]={'from':point(n,'fromLinkEndPt'),'to':point(n,'toLinkEndPt'),
            'lanes':len(n.findall('./lanes/lane')),'lane_change_distance_m':float(n.get('lnChgDist'))}
    access=[]
    for incoming in [10640,10641,10700]:
        a=connections[str(incoming)];entry=a['to'];lanes_in=range(entry['lane'],entry['lane']+a['lanes'])
        for outgoing in [10634,10635,10642]:
            b=connections[str(outgoing)];exit=b['from'];lanes_out=range(exit['lane'],exit['lane']+b['lanes'])
            distance=exit['pos_m']-entry['pos_m'];assert distance>0
            access.append({'incoming':incoming,'outgoing':outgoing,'entry_lanes':list(lanes_in),
                'exit_lanes':list(lanes_out),'minimum_lane_changes':min(abs(i-j) for i in lanes_in for j in lanes_out),
                'available_distance_m':distance})
    route_rows=[];feeders=[]
    for did,n in decisions.items():
        for r in n.findall('./vehRoutSta/vehicleRouteStatic'):
            dlink=int(r.get('destLink'));dpos=float(r.get('destPos'))
            seq=[int(x.get('key')) for x in r.findall('./linkSeq/intObjectRef')]
            row={'decision':did,'source_link':int(n.get('link')),'source_pos_m':float(n.get('pos')),
                'combine':n.get('combineStaRoutDec'),'route':int(r.get('no')),'dest_link':dlink,'dest_pos_m':dpos,
                'relative_flow_raw':r.get('relFlow'),'intermediate_links':seq}
            if did in [1126,1134,1138,1140]:route_rows.append(row)
            for target in [1126,1138,1140]:
                t=decisions[target]
                if dlink==int(t.get('link')) and dpos<float(t.get('pos')):
                    feeders.append({'source_decision':did,'source_route':int(r.get('no')),'next_decision':target,
                        'gap_to_decision_m':float(t.get('pos'))-dpos})
    d=decisions[1134];rs=d.findall('./vehRoutSta/vehicleRouteStatic')
    assert [r.get('relFlow') for r in rs]==['2 0:3','2 0:3','2 0:3','']
    assert all(r.get('relFlow')=='' for r in decisions[1138].findall('./vehRoutSta/vehicleRouteStatic'))
    inputs=[v for v in root.findall('./vehicleInputs/vehicleInput') if v.get('link')=='69'];assert len(inputs)==1
    demand=[]
    for row in inputs[0].findall('./timeIntVehVols/timeIntervalVehVolume'):
        q=float(row.get('volume'))
        parts={'1134_to_FW_W':q*.3,'1134_to_75':q*.3,'1134_to_FW_E':q*.3,
            '1134_1138_to_47':q/30,'1134_1138_to_56':q/30,'1134_1138_to_67':q/30}
        assert abs(sum(parts.values())-q)<1e-9
        demand.append({'time_interval_raw':row.get('timeInt'),'input_vph':q,'type':row.get('volType'),'configured_destinations_vph':parts})
    behavior=next(n for n in root.findall('./drivingBehaviors/drivingBehavior') if n.get('no')=='1')
    e.save(out,{'status':'READ_ONLY_NO_NETWORK_CHANGE','source':str(path.relative_to(e.ROOT)),
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'connections':connections,'access':access,
        'route_rows':route_rows,'routes_ending_before_decisions':feeders,'input69_conditional_demand':demand,
        'behavior1':{k:behavior.get(k) for k in ['vehRoutDecLookAhead','diffusTm','lookAheadDistMax']},
        'caveat':'Configured conditional demand, not realized counts; existing active long static routes ignore intervening static decisions. Combining applies to compatible routes ending before next decision, not arbitrary overwrite.',
        'official_2020_sources':[
            'https://www.cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_RoutenEntsch_mod.htm',
            'https://www.cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_RoutenEntsch_Attr.htm']})
    print('READ_ONLY access pairs',len(access),'input intervals',len(demand),'feeders',feeders,flush=True)


if __name__=='__main__':main()
