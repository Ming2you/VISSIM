"""Extract new-geometry observations using the established physical observers."""
from collections import defaultdict
import csv
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1 import extract_observations as ex
from diagnostics.demand_sweep.user_native_20260914.metanet_terms_implementation_v2.build_physical_geometry import build
from diagnostics.analyze_no_control_corridors import native_frames
from diagnostics.capture_native_runtime_errors import parse_bytes

HERE=Path(__file__).resolve().parent
OUT=HERE/'controller_response_v1'


def save(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def table(p,rows):
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pairs',action='store_true')
    parser.add_argument('--terminal-sec',type=int,choices=(3000,4500),default=3000)
    parser.add_argument('--runs',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--nested-runs',action='store_true',help='Read arm/run instead of run_arm')
    parser.add_argument('--component-stocks',action='store_true',help='Retain 1s mainline/on/off inventory by direction in the existing pass')
    args=parser.parse_args()
    pair_runs=args.runs or HERE/'response_pairs_v1'
    pair_protocol=ex.load(pair_runs/'protocol.json') if args.pairs else None
    output=args.output or (pair_runs/'observations' if args.pairs else
        (OUT if args.terminal_sec==3000 else HERE/'controller_response_4500_v1'))
    output.mkdir(exist_ok=False)
    source=HERE/'source_dsd/baseline.inpx'
    geometry=ex.physical_geometry(source)
    mapping=ex.load(Path(geometry['mapping']['path']))
    profile=build(geometry,mapping)
    save(output/'geometry_profile.json',profile)
    tree=ET.parse(source)
    heads={}
    for ramp in mapping['ramp_meters']:
        entries=tree.findall(f"./signalHeads/signalHead[@sg='{ramp['sc_no']} 1']")
        assert entries and all(int(h.get('lane').split()[0])==ramp['connector'] for h in entries)
        heads[ramp['connector']]={int(h.get('lane').split()[1]):float(h.get('pos')) for h in entries}
    save(output/'heads.json',heads)
    for arm in (tuple(pair_protocol['candidate_bank']) if args.pairs else ('none','rm','vsl','both')):
        runs=args.runs or HERE/('response_pairs_v1' if args.pairs else
            ('rules_v1' if args.terminal_sec==3000 else 'rules_4500_v1'))
        run=runs/arm/'run' if args.nested_runs else runs/f'run_{arm}'
        receipt=ex.load(run/'run.json')
        end=pair_protocol['run_end_s'] if args.pairs else args.terminal_sec
        assert receipt['completed'] and receipt['terminal_sec']==end
        assert ex.load(run/'fixed_validation.json')['passed']
        network=Path(receipt['network'])
        g=ex.physical_geometry(network,geometry_profile=output/'geometry_profile.json')
        out=output/arm;out.mkdir()
        save(out/'geometry.json',g)
        table(out/'desired_source_demand.csv',g['desired_source_demand'])
        removals=[]
        for f in receipt['error_files']:
            parsed=parse_bytes((run/f['name']).read_bytes())
            assert not parsed['unparsed_removal_lines']
            removals.extend(e for e in parsed['events'] if e['kind']=='lane_change_removal')
        observer,ports=ex.Observer(g,removals),ex.PortObserver(g)
        evidence={};previous={};crossings=[];head_stock=[];spatial=defaultdict(lambda:[0,0,0]);component_stocks=[]
        port_scope={b['connector']:(b['road'],'on' if b['kind']=='ramp' else 'off')
                    for b in g['boundaries'] if b['kind'] in ('ramp','offramp')}
        for sec,current in native_frames(run/'vissim_eval/baseline_001.fzp',evidence,deadline=time.monotonic()+1800):
            observer.advance(sec,current);ports.advance(sec,current)
            if args.component_stocks:
                stock={'time_s':sec,**{road+'_'+kind:0 for road in ('FW_E','FW_W') for kind in ('mainline','on','off')}}
                stock.update({road+'_source_negative':0 for road in ('FW_E','FW_W')})
                for road,cell,_ in observer.previous_cells.values():stock[road+'_mainline']+=1
                for row in current.values():
                    address=observer.addresses.get(row[0])
                    if address and address[1]+row[2]<0:stock[address[0]+'_source_negative']+=1
                    if row[0] in port_scope:
                        road,kind=port_scope[row[0]];stock[road+'_'+kind]+=1
                component_stocks.append(stock)
            counters=defaultdict(lambda:[0,0,0,0,None,None])
            for no,row in current.items():
                link,lane,pos,speed=row
                if link in heads:
                    head=heads[link][lane]
                    c=counters[link];c[0]+=pos<=head;c[1]+=pos>head;c[2]+=(pos<=head and speed<5);c[3]+=(pos>head and speed<5)
                    if args.pairs and pos<=head and (c[4] is None or head-pos<c[4]):
                        c[4],c[5]=head-pos,speed
                if link in (74,26) and 0<=pos<2400:
                    key=((sec-1)//150*150,link,int(pos//100)*100)
                    c=spatial[key];c[0]+=1;c[1]+=speed;c[2]+=speed<30
            for no,before in previous.items():
                if before[0] not in heads or no not in current:continue
                row=current[no];head=heads[before[0]][before[1]]
                if before[2]<=head and (row[0]!=before[0] or row[2]>heads[row[0]][row[1]]):
                    crossings.append({'time_s':sec,'ramp':before[0],'lane':before[1],'vehicle':no,'speed_before':before[3],'speed_after':row[3]})
            for ramp in heads:
                a,b,c,d,front_distance,front_speed=counters[ramp]
                row={'time_s':sec,'ramp':ramp,'prehead_n':a,'posthead_n':b,'prehead_stopped':c,'posthead_stopped':d}
                if args.pairs:row.update(front_distance_m=front_distance,front_speed_kmh=front_speed)
                head_stock.append(row)
            previous=current
        assert observer.sec==end
        for name,rows in [('cells_30s',observer.cells),('flows_30s',observer.flows),('boundaries_30s',observer.boundary_rows),('ports_30s',ports.rows),('port_events',ports.events),('head_crossings',crossings),('head_stock_1s',head_stock)]:table(out/(name+'.csv'),rows)
        table(out/'entry_spatial_150s.csv',[{'start_s':t,'link':l,'start_m':b,'n_mean':s[0]/150,'speed_kmh':s[1]/s[0],'slow_fraction':s[2]/s[0]} for (t,l,b),s in sorted(spatial.items())])
        save(out/'port_cohorts_30s.json',ports.snapshots)
        if args.component_stocks:table(out/'component_stocks_1s.csv',component_stocks)
        save(out/'manifest.json',{'source_run':str(run),'source_receipt_sha256':sha(run/'run.json'),'network_sha256':sha(network),'fzp':evidence,'cell_conservation_checks':observer.checks,'exclusions':observer.evidence,'removals':removals,'extractor_sha256':sha(Path(__file__)),'complete':True})
        print(arm+' physical extraction complete',flush=True)


if __name__=='__main__':main()
