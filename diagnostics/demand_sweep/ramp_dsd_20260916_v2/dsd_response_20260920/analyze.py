"""Post-run exact trajectory projection and actual desired-speed response audit."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from evaluation.controllers.desired_speed_transport import SpeedDistribution, selected_distribution
from collections import defaultdict
import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import argparse

HERE=Path(__file__).resolve().parent;H=HERE.parent


def data_lines(path, expected):
    with path.open('rb') as stream:
        header=None
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                header=line.strip().split(b':',1)[1].split(b';')
                if header!=expected:raise ValueError(('Unexpected native fields',header))
            elif line[:1].isdigit():
                if header is None:raise ValueError('Data before native header')
                parts=line.rstrip(b'\r\n').split(b';')
                if parts[-1:]==[b'']:parts.pop()
                if len(parts)!=len(header):raise ValueError('Incomplete native record')
                yield parts


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run=HERE/'native_v2/run_retry1';out=HERE/args.output;out.mkdir(exist_ok=False)
    assert e.load(run/'run.json')['completed']
    assert e.load(run/'fixed_validation.json')['passed']
    reference=H/'response_late_s23_v1/run_vsl/vissim_eval/baseline_001.fzp'
    source=run/'vissim_eval/baseline_001.fzp'
    fields=b'SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM'.split(b';')
    root=ET.parse(HERE/'native_v2/prepared/network/baseline.inpx').getroot()
    distributions={int(d.get('no')):SpeedDistribution(tuple((float(p.get('fx')),float(p.get('x')))
        for p in d.findall('./speedDistrDatPts/speedDistributionDataPoint')))
        for d in root.findall('./desSpeedDistributions/desSpeedDistribution') if d.get('no') in ['80','100','120']}
    decisions=defaultdict(list)
    for d in root.findall('./desSpeedDecisions/desSpeedDecision'):
        ids={int(p.get('desSpeedDistr')) for p in d.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}
        if len(ids)==1 and next(iter(ids)) in distributions:
            link,lane=map(int,d.get('lane').split());decisions[link,lane].append((float(d.get('pos')),int(d.get('no')),next(iter(ids))))
    for rows in decisions.values():rows.sort()
    events=defaultdict(list)
    for r in e.load(HERE/'native_v2/profile.json')['vsl_commands']:events[r['dsd_no']].append((r['time_s'],r['speed_id']))
    observer=Observer(e.ObservationData(H/'controller_response_s23_v1/none').geometry)
    stations={2:[48.185556564965211,400.,1305.3887036831929,1500.,1651.806,1964.218,2307.379,2652.027,3998.666],
              119:[395.105],24:[165.698]}
    ref=iter(data_lines(reference,fields));digest=hashlib.sha256();count=0;previous={};current={};last_sec=None
    identities={};crossings=[];census=defaultdict(lambda:[0.,0.,0.,0.,0.]);snapshots={}
    station_file=(out/'station_crossings.csv').open('x',newline='',encoding='utf-8')
    writer=csv.writer(station_file);writer.writerow(['time_s','link','pos_m','lane','vehicle','speed_kmh','desired_kmh','distribution_id','lane_changed_in_frame'])
    def frame(sec,rows):
        nonlocal previous
        if sec in [2250,2400,2550,2700,2850,3000]:snapshots[str(sec)]=[]
        for vid,row in rows.items():
            link,lane,pos,speed,desired=row;old=previous.get(vid)
            loc=observer.locate(row[:4])
            old_loc=observer.locate(old[:4]) if old else None
            # A 1s sample can step from a connector past the first DSD on
            # the next link. Preserve that crossing instead of retaining an
            # obsolete distribution until the next sign.
            interlink=bool(old and old[0]!=link and loc and old_loc and
                          loc[0]==old_loc[0] and loc[2]>old_loc[2])
            old_pos=old[2] if old and old[0]==link else (
                pos-(loc[2]-old_loc[2]) if interlink else None)
            if old_pos is not None and pos>old_pos:
                for point,no,native in decisions.get((link,lane),[]):
                    if old_pos<point<=pos:
                        t=sec-1+(point-old_pos)/(pos-old_pos);prior=identities.get(vid)
                        target=selected_distribution(native,events[no],t)
                        if old[1]!=lane:
                            equivalent=any(abs(p-point)<1e-7 and selected_distribution(n,events[d],t)==target
                                for p,d,n in decisions.get((link,old[1]),[]))
                            if not equivalent:
                                identities.pop(vid,None)
                                continue
                        if prior in distributions:
                            try:
                                u=distributions[prior].fractile(old[4])
                                predicted=distributions[target].quantile(u)
                                error=desired-predicted
                            except ValueError:u=predicted=error=None
                        else:u=predicted=error=None
                        identities[vid]=target
                        if 2250<sec<=3000 and link in (2,119,24) and old[1]==lane:
                            crossings.append({'time_s':t,'vehicle':vid,'dsd':no,'prior_id':prior,'new_id':target,
                                'crossing_kind':'link_entry' if interlink else 'same_link',
                                'before_desired':old[4],'actual_desired':desired,'predicted_desired':predicted,'error_kmh':error,
                                'speed_before':old[3],'speed_after':speed,'fractile':u})
            if old and old[0]==link and pos>old[2] and 2250<sec<=3000:
                for point in stations.get(link,[]):
                    if old[2]<point<=pos:
                        t=sec-1+(point-old[2])/(pos-old[2])
                        writer.writerow([t,link,point,lane,vid,speed,desired,identities.get(vid),int(old[1]!=lane)])
            if loc and loc[0]=='FW_E' and 2250<=sec<=3000:
                cell=loc[1];dist=identities.get(vid)
                if sec>=2400:
                    x=census[sec,cell];x[0]+=1;x[1]+=int(dist==100);x[2]+=desired;x[3]+=desired*desired;x[4]+=int(dist is None)
                if str(sec) in snapshots:snapshots[str(sec)].append({'vehicle':vid,'cell':cell,'lane':lane,
                    'position_m':loc[2],'speed_kmh':speed,'desired_kmh':desired,'distribution_id':dist})
        previous=rows
    for row in data_lines(source,fields+[b'DESSPEED']):
        comparison=next(ref)
        if row[:9]!=comparison:raise AssertionError(('First physical replay mismatch',count,row[:9],comparison))
        digest.update(b';'.join(row[:9])+b'\n');count+=1
        sec=int(float(row[0]))
        if last_sec is not None and sec!=last_sec:
            frame(last_sec,current);current={}
        last_sec=sec
        current[int(row[1])]=(int(row[2]),int(row[3]),float(row[4]),float(row[6]),float(row[9]))
    frame(last_sec,current);station_file.close()
    assert last_sec==3000 and float(next(ref)[0])>3000
    assert count>1000000
    e.save(out/'crossings.json',crossings);e.save(out/'snapshots.json',snapshots)
    e.save(out/'census.json',[{'time_s':s,'cell':c,'n':x[0],'exposed_n':x[1],'unidentified_n':x[4],
                              'desired_mean':x[2]/x[0],'desired_sd':math.sqrt(max(0.,x[3]/x[0]-(x[2]/x[0])**2))} for (s,c),x in census.items()])
    valid=[r for r in crossings if r['error_kmh'] is not None]
    errors=[abs(r['error_kmh']) for r in valid]
    changed=[r for r in valid if r['prior_id']!=r['new_id']]
    e.save(out/'validation.json',{'physical_original_nine_columns_exact':True,'rows':count,'terminal_s':last_sec,
        'projected_payload_sha256':digest.hexdigest(),'desired_speed_extra_native_attribute':True,
        'same_lane_dsd_crossings_tested':len(valid),'changed_distribution_crossings':len(changed),
        'persistent_fractile_max_abs_error_kmh':max(errors),'persistent_fractile_mae_kmh':sum(errors)/len(errors),
        'over_001_kmh':sum(x>.01 for x in errors),'ambiguous_lane_changes':'Excluded from exact DSD-crossing test',
        'distribution_moments':{k:v.moments() for k,v in distributions.items()},
        'observed_field_is_desired_not_actual_speed':True})
    print('REPLAY EXACT',count,'DSD crossings',len(valid),'max error',max(errors),flush=True)


if __name__=='__main__':main()
