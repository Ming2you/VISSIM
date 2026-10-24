"""Read-only source/head cohorts from the completed seed13 one-second FZP.

Crossing times are interval observations; interpolation is an explicitly labelled
summary, never a sub-second measurement or a fitted saturation flow.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import csv,hashlib,json,math,statistics,time,xml.etree.ElementTree as ET
from plant.src.vissim_strict.signal_program import parse_sig
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
ROOT=Path(__file__).resolve().parents[1]
RUN='codex_area_observed_nc_s13_20260910'
SOURCES={'343':('1086','1099'),'341':('1087','1100')}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def topology():
    out={}
    for source,(no,decision) in SOURCES.items():
        evidence=ROOT/f'diagnostics/route_choice_corridor_{decision}_ver2.json';doc=json.loads(evidence.read_text(encoding='utf-8'))
        network=ROOT/doc['network']['path'];tree=ET.parse(network).getroot();nodes={x.get('no'):x for x in tree.findall('./links/link')}
        heads={x.get('no'):x for x in tree.findall('./signalHeads/signalHead')};service=doc['native_fixed_service'];head=heads[service['head']]
        # The evidence and physical network are independently pinned here.
        if sha(network)!=doc['network']['sha256'] or sha(ROOT/service['sig_file']['path'])!=service['sig_file']['sha256']:raise ValueError('Source evidence changed')
        head_position=float(head.get('pos'));branches={}
        for route,path in doc['native_paths'].items():
            node=nodes[path[1]];a=node.find('fromLinkEndPt');b=node.find('toLinkEndPt')
            if a.get('lane').split()[0]!=source or float(a.get('pos'))<=head_position:raise ValueError('Branch does not follow native head')
            pts=[tuple(float(p.get(k,0)) for k in ('x','y','zOffset')) for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
            branches[path[1]]={'route':route,'from_pos_m':float(a.get('pos')),'target':b.get('lane').split()[0],
                'target_pos_m':float(b.get('pos')),'length_m':sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))}
        incoming=[x.get('no') for x in nodes.values() if x.find('toLinkEndPt') is not None and x.find('toLinkEndPt').get('lane').split()[0]==source]
        if incoming:raise ValueError('Source is not an isolated native generation road')
        native=next(x for x in tree.findall('./vehicleInputs/vehicleInput') if x.get('no')==no)
        rates=[{'start_sec':int(x.get('timeInt').split()[1])/1000,'rate_veh_h':float(x.get('volume')),'volume_type':x.get('volType')} for x in native.findall('./timeIntVehVols/timeIntervalVehVolume')]
        out[source]={'source':source,'input_no':no,'decision':decision,'head_position_m':head_position,'head_id':service['head'],
            'signal_group':service['signal_group'],'controller_offset_sec':service['controller_offset_sec'],'branches':branches,
            'native_rates':rates,'evidence_path':str(evidence.relative_to(ROOT)),
            'program':parse_sig(ROOT/service['sig_file']['path'],service['program_no'])}
    return out

def collect(stream,specs):
    sourcebytes={s.encode():s for s in specs};cohorts={};seen=set();total=0;header=False;last_t=None;frames=[];cadence=Counter()
    for line in stream:
        if line.startswith(b'$VEHICLE:'):
            if line.strip()!=b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM':raise ValueError('FZP schema changed')
            header=True;continue
        if not header or not line.strip() or line.startswith((b'*',b'$')):continue
        f=line.split(b';',4);t=float(f[0]);no=f[1].strip();link=f[2].strip();total+=1
        if t!=last_t:
            if last_t is not None:
                if t<=last_t:raise ValueError('Unordered frames')
                cadence[t-last_t]+=1
            frames.append(t);last_t=t
        source=sourcebytes.get(link)
        if source is not None or no in cohorts and cohorts[no]['first_non_source'] is None:
            tail=f[4].split(b';');row={'sec':t,'link':link.decode(),'lane':int(f[3]),'pos_m':float(tail[0]),'speed_kph':float(tail[2])}
            if source is not None:
                if no not in cohorts:cohorts[no]={'vehicle_id':int(no),'source':source,'first_seen_on_source':no not in seen,'samples':[],'first_non_source':None}
                c=cohorts[no]
                if c['source']!=source or c['first_non_source'] is not None:raise ValueError('Source ID returned or source changed')
                if c['samples'] and t-c['samples'][-1]['sec']!=1:raise ValueError('Source observation gap or duplicate ID')
                c['samples'].append(row)
            else:cohorts[no]['first_non_source']=row
        seen.add(no)
    if dict(cadence)!={1.0:5399} or len(frames)!=5400:raise ValueError('Expected completed 1s,5400-frame FZP')
    return list(cohorts.values()),{'rows':total,'frames':len(frames),'first_sec':frames[0],'last_sec':frames[-1],'cadence_sec':dict(cadence),'unique_network_ids':len(seen)}

def head_crossing(c,spec):
    samples=c['samples'];head=spec['head_position_m']
    for prev,cur in zip(samples,samples[1:]):
        if prev['pos_m']<head<=cur['pos_m']:
            fraction=(head-prev['pos_m'])/(cur['pos_m']-prev['pos_m'])
            return {'lower_sec':prev['sec'],'upper_sec':cur['sec'],'linear_estimate_sec':prev['sec']+fraction*(cur['sec']-prev['sec']),'method':'same_source_position_bracket'}
    if samples[0]['pos_m']>=head:return {'method':'left_censored_before_first_source_sample'}
    prev=samples[-1];cur=c['first_non_source']
    if cur is None:return {'method':'right_censored_on_source'}
    if cur['sec']-prev['sec']!=1:return {'method':'unresolved_departure_observation_gap'}
    candidates=[(key,b) for key,b in spec['branches'].items() if key==cur['link'] or b['target']==cur['link']]
    if len(candidates)!=1:return {'method':'unresolved_first_non_source'}
    key,b=candidates[0];distance=b['from_pos_m']-prev['pos_m']
    if cur['link']==key:distance+=cur['pos_m'];method='source_to_observed_connector_bracket'
    else:distance+=b['length_m']+cur['pos_m']-b['target_pos_m'];method='source_to_unique_target_bracket'
    if distance<=0 or not 0<=head-prev['pos_m']<=distance:return {'method':'unresolved_path_distance'}
    return {'lower_sec':prev['sec'],'upper_sec':cur['sec'],'linear_estimate_sec':prev['sec']+(head-prev['pos_m'])/distance,
        'method':method,'branch_connector':key}

def quantiles(values):
    values=sorted(values)
    if not values:return {'n':0}
    def q(p):
        i=(len(values)-1)*p;a=int(i);return values[a]+(values[min(a+1,len(values)-1)]-values[a])*(i-a)
    return {'n':len(values),'min':values[0],'median':statistics.median(values),'mean':statistics.mean(values),'p10':q(.1),'p90':q(.9),'max':values[-1]}

def green_windows(spec):
    program=spec['program'];group=spec['signal_group'];offset=spec['controller_offset_sec'];rows=[];start=None
    for t in range(5401):
        green=t<5400 and program.state_at(t,group,controller_offset_sec=offset)=='GREEN'
        if green and start is None:start=t
        if not green and start is not None:rows.append((start,t));start=None
    return rows

def desired(spec,start,end):
    rows=spec['native_rates'];total=0
    for i,row in enumerate(rows):
        a=max(start,row['start_sec']);b=min(end,rows[i+1]['start_sec'] if i+1<len(rows) else 5400)
        total+=max(0,b-a)*row['rate_veh_h']/3600
    return total

def analyze(cohorts,spec):
    own=[c for c in cohorts if c['source']==spec['source']];frames={t:{'n':0,'stopped_before_head':0,'stopped_near_head_20m':0} for t in range(1,5401)}
    events=[];departures=[]
    for c in own:
        for row in c['samples']:
            frame=frames[int(row['sec'])];frame['n']+=1
            stopped=row['speed_kph']<=5 and row['pos_m']<spec['head_position_m']
            frame['stopped_before_head']+=int(stopped)
            frame['stopped_near_head_20m']+=int(stopped and row['pos_m']>=spec['head_position_m']-20)
        cross=head_crossing(c,spec);first=c['samples'][0];last=c['samples'][-1]
        event={'vehicle_id':c['vehicle_id'],'source':c['source'],'input_no':spec['input_no'],'first_source_sec':first['sec'],
            'first_seen_on_source':c['first_seen_on_source'],'last_source_sec':last['sec'],'source_stopped_samples_sec':sum(r['speed_kph']<=5 for r in c['samples']),
            'source_observed_samples':len(c['samples']),**cross}
        if 'lower_sec' in cross:
            a,b=cross['lower_sec'],cross['upper_sec'];green=_union_green_overlap(spec['program'],(spec['signal_group'],),a,b,spec['controller_offset_sec'])
            event['green_fraction_of_observation_interval']=green/(b-a)
            event['guaranteed_green']=abs(green-(b-a))<1e-9
            event['linear_estimate_signal_state']=spec['program'].state_at(cross['linear_estimate_sec'],spec['signal_group'],controller_offset_sec=spec['controller_offset_sec'])
            event['residence_to_head_lower_sec']=a-first['sec'];event['residence_to_head_upper_sec']=b-first['sec']+1
        events.append(event)
        if c['first_non_source'] is not None:departures.append({'vehicle_id':c['vehicle_id'],'sec':c['first_non_source']['sec'],'link':c['first_non_source']['link']})
    crossed=sorted([e for e in events if 'lower_sec' in e],key=lambda e:e['linear_estimate_sec']);cycles=[];headways=[]
    for cycle,(a,b) in enumerate(green_windows(spec)):
        ev=[e for e in crossed if a<=e['linear_estimate_sec']<b];q0=frames.get(a,frames[1])['stopped_before_head'];qend=frames.get(b,frames[5400])['stopped_before_head']
        for order,(prev,cur) in enumerate(zip(ev,ev[1:]),start=2):
            if not prev['guaranteed_green'] or not cur['guaranteed_green']:continue
            sample_times=range(math.ceil(prev['upper_sec']),math.floor(cur['lower_sec'])+1)
            q=[frames[t]['stopped_before_head'] for t in sample_times if t in frames]
            row={'input_no':spec['input_no'],'green_start_sec':a,'green_end_sec':b,'departure_ordinal':order,
                'previous_vehicle_id':prev['vehicle_id'],'vehicle_id':cur['vehicle_id'],
                'linear_estimate_headway_sec':cur['linear_estimate_sec']-prev['linear_estimate_sec'],
                'lower_headway_sec':max(0.,cur['lower_sec']-prev['upper_sec']),'upper_headway_sec':cur['upper_sec']-prev['lower_sec'],
                'minimum_observed_prehead_stopped_queue':min(q) if q else None,
                'queued_after_third_departure':order>=4 and bool(q) and min(q)>=1}
            headways.append(row)
        cycles.append({'start_sec':a,'end_sec':b,'head_crossings_linear_assignment':len(ev),'guaranteed_green_crossings':sum(e['guaranteed_green'] for e in ev),
            'initial_stopped_queue':q0,'ending_stopped_queue':qend,'green_seconds_with_stopped_queue':sum(frames[t]['stopped_before_head']>0 for t in range(max(1,a),min(5400,b-1)+1)),
            'max_stopped_queue':max(frames[t]['stopped_before_head'] for t in range(max(1,a),min(5400,b-1)+1))})
    windows=[]
    for a,b in [(s,s+900) for s in range(0,5400,900)]+[(900,1350),(2700,3150)]:
        admissions=sum(a<e['first_source_sec']<=b for e in events);exits=sum(a<e['sec']<=b for e in departures)
        n0=frames[a]['n'] if a else 0;n1=frames[b]['n'];g=_union_green_overlap(spec['program'],(spec['signal_group'],),a,b,spec['controller_offset_sec'])
        windows.append({'start_sec':a,'end_sec':b,'nominal_stochastic_expected_veh':desired(spec,a,b),'observed_source_admissions_veh':admissions,
            'admissions_over_nominal_expectation':admissions/desired(spec,a,b),'source_departures_veh':exits,
            'initial_source_n_veh':n0,'final_source_n_veh':n1,'observed_stock_closure_veh':n0+admissions-exits-n1,
            'head_crossings_whole_interval_veh':sum(a<=e['lower_sec'] and e['upper_sec']<=b for e in crossed),
            'head_crossings_interval_overlap_upper_veh':sum(e['upper_sec']>a and e['lower_sec']<b for e in crossed),
            'native_green_sec':g,'green_effective_departure_vph':sum(a<=e['lower_sec'] and e['upper_sec']<=b and e['guaranteed_green'] for e in crossed)*3600/g,
            'source_ttt_veh_h':sum(frames[t]['n'] for t in range(a+1,b+1))/3600,
            'stopped_before_head_veh_sec':sum(frames[t]['stopped_before_head'] for t in range(a+1,b+1))})
    qualified=[h for h in headways if h['queued_after_third_departure']]
    summary={'input_no':spec['input_no'],'source':spec['source'],'head':spec['head_id'],'group':spec['signal_group'],
        'observed_source_unique_veh':len(own),'not_first_seen_on_source_ids':[e['vehicle_id'] for e in events if not e['first_seen_on_source']],
        'crossing_resolution_counts':dict(Counter(e['method'] for e in events)),'head_crossings_veh':len(crossed),
        'guaranteed_green_crossings_veh':sum(e['guaranteed_green'] for e in crossed),'linear_crossing_states':dict(Counter(e['linear_estimate_signal_state'] for e in crossed)),
        'source_stopped_time_samples_sec':quantiles([e['source_stopped_samples_sec'] for e in events]),
        'residence_to_head_lower_sec':quantiles([e['residence_to_head_lower_sec'] for e in crossed]),
        'source_occupancy_veh':quantiles([f['n'] for f in frames.values()]),'source_prehead_stopped_queue_veh':quantiles([f['stopped_before_head'] for f in frames.values()]),
        'all_same_green_headway_estimate_sec':quantiles([h['linear_estimate_headway_sec'] for h in headways]),
        'queued_after_third_headway_estimate_sec':quantiles([h['linear_estimate_headway_sec'] for h in qualified]),
        'queued_after_third_headway_lower_sec':quantiles([h['lower_headway_sec'] for h in qualified]),
        'queued_after_third_headway_upper_sec':quantiles([h['upper_headway_sec'] for h in qualified]),
        'green_windows':cycles,'windows':windows}
    return summary,events,headways,[{'source':spec['source'],'input_no':spec['input_no'],'sec':t,**f} for t,f in frames.items()]

def write_csv(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',encoding='utf-8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    start=time.monotonic();specs=topology();run=ROOT/'evaluation/runs'/RUN;fzp=next(run.glob('vissim_eval/*.fzp'));lsa=next(run.glob('vissim_eval/*.lsa'))
    paths=[Path(__file__),ROOT/'diagnostics/native_sc15_clock_audit.json',ROOT/'diagnostics/native_route_choice_integration.json',
        ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',ROOT/'network/real_world_gaepo_modi/개포동 test-bed11.sig',
        ROOT/'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv',next(run.glob('run_provenance*.json')),lsa]+[ROOT/s['evidence_path'] for s in specs.values()]
    before={str(p.relative_to(ROOT)):sha(p) for p in paths};stat=fzp.stat()
    with fzp.open('rb') as stream:cohorts,sampling=collect(stream,specs)
    if (stat.st_size,stat.st_mtime_ns)!=(fzp.stat().st_size,fzp.stat().st_mtime_ns):raise ValueError('FZP changed')
    summaries={};events=[];headways=[];frames=[]
    for source,spec in specs.items():
        summary,es,hs,fs=analyze(cohorts,spec);summaries[spec['input_no']]=summary;events+=es;headways+=hs;frames+=fs
    result={'schema':'native-sc15-source-discharge-audit/v1','run':RUN,'seed':13,'sampling':sampling,'inputs':summaries,
        'source_sha256':before,'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h],
        'fzp':{'path':str(fzp.relative_to(ROOT)),'sha256':sha(fzp),'bytes':stat.st_size},'elapsed_sec':time.monotonic()-start,
        'definitions':{'stopped':'speed<=5 km/h, source position before native head','crossing':'Vehicle front source coordinate brackets head, or unique outgoing path brackets it across two consecutive 1s frames.',
            'guaranteed_green':'Entire 1s crossing interval lies inside canonical GREEN; canonical native clock separately matches observed LSA.',
            'qualified_headway':'Both crossings guaranteed GREEN in same green window, second crossing ordinal>=4, and all intervening integer-frame pre-head stopped counts>=1.',
            'admission_ratio':'Observed first-source IDs divided by nominal stochastic expected vehicles; not a measured realized request acceptance probability.'},
        'limitations':['One-second FZP cannot yield exact sub-second headways; lower/upper brackets accompany linear interpolation.',
            'Queue-present post-startup observations are discharge evidence, not proof of unconstrained saturation; downstream receiver blocking and microscopic yielding can remain.',
            'IDs never observed on the source would be missing from this cohort; sources have no incoming connector and all first-seen qualifications are explicit.',
            'Source stopped samples and right-endpoint stock rectangles are descriptive one-second measures, not exact arrival residence times.',
            'STOCHASTIC requested generation realizations are not in FZP; nominal expected volume does not establish rejected demand or a loss count.',
            'This completed seed13 audit is offline evidence, not a fitted capacity or seed14 holdout validation.']}
    out=ROOT/'diagnostics/native_sc15_source_discharge.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_csv(out.with_name('native_sc15_head_crossings.csv'),events);write_csv(out.with_name('native_sc15_headways.csv'),headways);write_csv(out.with_name('native_sc15_source_timeseries.csv'),frames)
    print(json.dumps({'inputs':{no:{k:v for k,v in summary.items() if k not in ('green_windows','windows')} for no,summary in summaries.items()},'windows':{no:s['windows'][-2:] for no,s in summaries.items()},'source_changes':result['source_changes'],'elapsed_sec':result['elapsed_sec']},ensure_ascii=False))

if __name__=='__main__':main()
