"""Post-completion four-arm observations; each native FZP is opened exactly once.

Default is a metadata-only plan. --execute requires all four completed receipts.
No simulator, COM, process control, adapter execution or source modification.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from diagnostics.analyze_no_control_corridors import native_frames
from diagnostics.capture_native_runtime_errors import parse_bytes
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1 import extract_observations as ex
from scripts.measure_control_area import Frame, Vehicle, measure_frames, physical_membership_from_ledger

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE.parents[1]/'metanet_terms_implementation_v2/physical_geometry21_v1.json'
MEMBERSHIP = ROOT/'diagnostics/control_area_membership.json'
ARMS = ('none', 'vsl', 'rm', 'both')
WINDOWS = ((1350, 1800), (1800, 2250), (1350, 2250))
END, CONTROL = 2250, 1350
HEAD, CONNECTOR = 272.6035592816065, 10490
DROP, VSL_START, VSL_END = 6841.743, 5386.554349, 6733.192994


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def table(path, rows, fields=None):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def completed(experiment, arm):
    run, prepared = experiment/f'run_{arm}', experiment/f'prepared_{arm}'
    receipt, meta = load(run/'run.json'), load(prepared/'prepared.json')
    validation = load(run/'fixed_validation.json')
    require(receipt.get('completed') is True and receipt.get('exit_code') == 0
            and receipt.get('owned_native_alive') is False and receipt.get('error') is None,
            'Completed exit0/closed-owned-native receipt required: '+arm)
    require(receipt.get('fixed_profile') is True and meta.get('mode') == 'fixed_profile'
            and receipt.get('native_preserve') is False, 'Explicit fixed-profile receipt required')
    require(receipt.get('terminal_sec') == END and meta['terminal_sec'] == END
            and meta['seed'] == receipt['seed'] == 13, 'Wrong fixed experiment extent/seed')
    require(receipt.get('fixed_profile_validation_exit_code') == 0 and validation.get('passed') is True,
            'Native command/LDP validation did not pass: '+arm)
    require(Path(receipt['prepared']).resolve() == prepared.resolve()
            and Path(receipt['output']).resolve() == run.resolve(), 'Receipt path mismatch')
    network = Path(meta['network']).resolve()
    require(network == (prepared/'network/baseline.inpx').resolve()
            and Path(receipt['network']).resolve() == network, 'Prepared network identity mismatch')
    expected = meta['snapshot_sha256'][str(network)]
    require(sha(network) == expected == meta['fixed_profile_proof']['network_sha256'], 'Prepared network SHA changed')
    log = (run/'stdout.txt').read_text(encoding='utf-8-sig', errors='replace')
    require(re.search(r'^STAGE=SIM_DONE\s*$', log, re.M) and not re.search(r'^ERROR=', log, re.M), 'Incomplete native log')
    seconds = re.findall(r'^SIM_SEC=([^\r\n]+)', log, re.M)
    require(seconds and float(seconds[-1]) == END, 'Wrong native terminal log')
    fzp = run/'vissim_eval/baseline_001.fzp'
    require(fzp.is_file() and fzp.stat().st_size > 0, 'Missing complete FZP')
    names = [item['name'] for item in receipt['error_files']]
    require(names and len(names) == len(set(names))
            and all(Path(n).name == n and n.lower().endswith('.err') for n in names), 'Invalid native ERR evidence')
    return {'arm':arm, 'run':run, 'prepared':prepared, 'receipt':receipt, 'meta':meta,
            'validation':validation, 'network':network, 'fzp':fzp, 'errors':[run/n for n in names]}


def physical_network(path):
    tree = ET.parse(path)
    links, connectors = {}, {}
    for row in tree.findall('./links/link'):
        no = row.get('no')
        points = [tuple(float(p.get(k, 0)) for k in ('x','y','zOffset'))
                  for p in row.findall('./geometry/linkPolyPts/linkPolyPoint')]
        links[no] = {'length_m':math.fsum(math.dist(a,b) for a,b in zip(points,points[1:])),
                     'lanes':len(row.findall('./lanes/lane'))}
        a,b = row.find('fromLinkEndPt'),row.find('toLinkEndPt')
        if a is not None or b is not None:
            require(a is not None and b is not None, 'Half connector endpoint')
            connectors[no] = {'from_link':a.get('lane').split()[0], 'to_link':b.get('lane').split()[0],
                              'from_pos_m':float(a.get('pos')), 'to_pos_m':float(b.get('pos'))}
    return links,connectors


def area_proof(network, geometry):
    """Revalidate whole-link Omega on actual topology; never replace the old SHA guard."""
    ledger = load(MEMBERSHIP)
    proof = {'ledger':str(MEMBERSHIP), 'ledger_sha256':sha(MEMBERSHIP), 'status':'FAIL',
             'basis':'Same canonical whole-link definition, revalidated against actual links/endpoints; lengths refreshed from actual INPX.'}
    try:
        original = ROOT/ledger['network']['path']
        require(sha(original) == ledger['network']['sha256'], 'Original membership network pin is unavailable/changed')
        proof['original_network'] = ledger['network']
        for source in ledger['sources']:
            require(sha(ROOT/source['path']) == source['sha256'], 'Area membership source changed: '+source['path'])
        old_links,old_edges = physical_network(original)
        links,edges = physical_network(network)
        membership = physical_membership_from_ledger(ledger)
        require(set(links) == set(old_links) == set(membership), 'Changed/missing physical links require fresh Omega review')
        require(set(edges) == set(old_edges), 'Changed connector set requires fresh Omega review')
        changed_geometry = []
        for no,edge in edges.items():
            require(all(edge[k] == old_edges[no][k] for k in ('from_link','to_link')),
                    'Changed connector road topology requires fresh Omega review: '+no)
            if edge != old_edges[no]:
                changed_geometry.append({'connector':no, 'before':old_edges[no], 'after':edge})
        for path in ledger['verified_all_inside_paths']:
            require(all(membership[n] for n in path), 'Canonical corridor no longer internal')
            for i in range(1,len(path),2):
                require((edges[path[i]]['from_link'],edges[path[i]]['to_link']) == (path[i-1],path[i+1]),
                        'Canonical corridor endpoint mismatch')
        for row in ledger['connector_transitions']:
            edge = edges[row['connector']]
            require(all(edge[k] == row[k] for k in ('from_link','to_link')), 'Area crossing edge changed')
        tails = {str(chain[-1]['link']) for chain in geometry['chains'].values()}
        outgoing = {e['from_link'] for e in edges.values()}
        natural = {n for n,inside in membership.items() if inside and n not in edges and n not in outgoing}
        require(set(ledger['terminal_inside_links']) == tails|natural, 'Terminal definition no longer matches actual network')
        terminals = {n:links[n]['length_m'] for n in ledger['terminal_inside_links']}
        require(all(math.isfinite(v) and v>0 for v in terminals.values()), 'Invalid physical terminal length')
        proof.update(status='PASS', network={'path':str(network),'sha256':sha(network)},
                     inside_links=sum(membership.values()), outside_links=sum(not v for v in membership.values()),
                     connector_endpoint_position_changes=changed_geometry,
                     link_geometry_changes=[{'link':n,'before':old_links[n],'after':links[n]} for n in links if links[n]!=old_links[n]],
                     terminal_lengths_m=terminals)
        return proof,membership,terminals
    except (ValueError,OSError,KeyError) as exc:
        proof['error'] = str(exc)
        return proof,None,None


class PrefixStream:
    def __init__(self, path, owner):
        self.stream, self.owner = path.open('rb'), owner

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()

    def __iter__(self):
        for raw in self.stream:
            if raw[:1].isdigit():
                sec = float(raw.split(b';',1)[0])
                self.owner.full_digest.update(raw.rstrip(b'\r\n')+b'\n')
                self.owner.full_rows += 1
                self.owner.full_last = sec
                if sec <= CONTROL:
                    self.owner.digest.update(raw.rstrip(b'\r\n')+b'\n')
                    self.owner.rows += 1
                    self.owner.last = sec
            yield raw


class SingleScanPath:
    """Native reader receives the original bytes; prefix digest shares the same IO."""
    def __init__(self, path):
        self.path, self.opens = path, 0
        self.digest, self.rows, self.last = hashlib.sha256(),0,None
        self.full_digest, self.full_rows, self.full_last = hashlib.sha256(),0,None

    def open(self, mode):
        require(mode=='rb' and self.opens==0, 'FZP must be opened exactly once')
        self.opens += 1
        return PrefixStream(self.path,self)

    def proof(self):
        require(self.opens==1 and self.last==CONTROL, 'Incomplete paired FZP warmup')
        return {'sha256':self.digest.hexdigest(),'rows':self.rows,'last_time_s':self.last}

    def full_proof(self):
        require(self.opens==1 and self.full_last==END,'Incomplete full native prefix')
        return {'sha256':self.full_digest.hexdigest(),'rows':self.full_rows,'last_time_s':self.full_last}


def inside_window(sec, window):
    return window[0] < sec <= window[1]


class Measurements:
    def __init__(self, geometry, signal_frames, membership, terminals, removals):
        self.geometry,self.signals = geometry,signal_frames
        self.membership,self.terminals,self.removals = membership,terminals or {},removals
        self.addresses = {int(k):(v[0],float(v[1])) for k,v in geometry['addresses'].items()}
        self.ports = {int(b['connector']):b for b in geometry['boundaries'] if b['kind'] in ('ramp','offramp')}
        self.component = set(self.addresses)|set(self.ports)
        self.scopes = {r:{int(p['link']) for p in chain} for r,chain in geometry['chains'].items()}
        self.scopes.update({str(n):{n} for n in self.ports})
        freeway = set(self.addresses)
        offramps = {n for n,b in self.ports.items() if b['kind']=='offramp'}
        self.scopes['freeway_all'] = freeway
        self.scopes['offramps_all'] = offramps
        self.scopes['model_component'] = freeway|offramps|{CONNECTOR}
        self.scopes['component'] = self.component
        self.previous, self.last_sec = {},0
        self.previous_counts = Counter()
        self.ttt = {(a,b,name):0. for a,b in WINDOWS for name in self.scopes}
        self.left_ttt,self.right_ttt = dict.fromkeys(self.ttt,0.),dict.fromkeys(self.ttt,0.)
        self.stock_rows = []
        self.cutoff_counts, self.meter_states,self.spatial,self.head_events,self.merge_events,self.collisions = {},[],[],[],[],[]
        self.zones = {'vsl_affected':(VSL_START,VSL_END),'drop_upstream_1000_500':(DROP-1000,DROP-500),
            'drop_upstream_500_0':(DROP-500,DROP),'drop_downstream_0_500':(DROP,DROP+500),
            'drop_downstream_500_1000':(DROP+500,DROP+1000)}
        self.removal_index = defaultdict(list)
        self.removal_matches = []
        for i,row in enumerate(removals):
            self.removal_index[int(row['vehicle_id']),int(row['link'])].append((i,row))

    def advance(self, sec, current):
        require(sec == self.last_sec+1 and sec<=END, 'Expected complete 1 Hz frames from fresh t0')
        link_counts=Counter(row[0] for row in current.values())
        counts={name:sum(link_counts[n] for n in ids) for name,ids in self.scopes.items()}
        for a,b in WINDOWS:
            if a < sec <= b:
                for name,n in counts.items():
                    self.ttt[a,b,name] += (self.previous_counts[name]+n)/7200.
                    self.left_ttt[a,b,name] += self.previous_counts[name]/3600.
                    self.right_ttt[a,b,name] += n/3600.
        for name,n in counts.items():
            self.stock_rows.append({'window_start_s':sec-1,'window_end_s':sec,'scope':name,
                'start_n_veh':self.previous_counts[name],'end_n_veh':n,
                'vehicle_seconds_trapezoid':(self.previous_counts[name]+n)/2.,
                'vehicle_seconds_left':self.previous_counts[name],'vehicle_seconds_right':n})
        if sec in {1350,1800,2250}:
            self.cutoff_counts[sec]=dict(counts)
        meter=Counter()
        zones={name:[] for name in self.zones}
        for row in current.values():
            if row[0]==CONNECTOR:
                side='upstream' if row[2]<=HEAD else 'downstream'
                meter[side+'_n']+=1
                meter[side+'_stopped']+=row[3]<=1.
            address=self.addresses.get(row[0])
            if address and address[0]=='FW_E':
                pos=address[1]+row[2]
                for name,(a,b) in self.zones.items():
                    if a<=pos<b:
                        zones[name].append(row)
        state=self.signals[sec]['9107:1']
        self.meter_states.append({'time_s':sec,'ldp_state':state,
            **{k:meter[k] for k in ('upstream_n','downstream_n','upstream_stopped','downstream_stopped')}})
        for vehicle,old in self.previous.items():
            new=current.get(vehicle)
            if old[0]==CONNECTOR and new is not None:
                crossed=old[2]<=HEAD and ((new[0]==CONNECTOR and new[2]>HEAD) or new[0]==119)
                if crossed:
                    self.head_events.append({'lower_s':sec-1,'upper_s':sec,'vehicle':vehicle,
                        'old_link':old[0],'new_link':new[0],'old_pos_m':old[2],'new_pos_m':new[2],
                        'ldp_interval_end_state':state,'previous_ldp_state':self.signals.get(sec-1,{}).get('9107:1'),
                        'evidence':'same_connector_straddle' if new[0]==CONNECTOR else 'connector_to_verified_mainline_bracket'})
                if new[0]==119:
                    self.merge_events.append({'lower_s':sec-1,'upper_s':sec,'vehicle':vehicle,'ldp_interval_end_state':state,
                        'already_downstream_of_head_at_lower':old[2]>HEAD})
            if new is None:
                matches=[(i,r) for i,r in self.removal_index[vehicle,old[0]] if abs(r['time_sec']-sec)<=1]
                if matches:
                    reach=old[3]/3.6+1.5+10.
                    collision=(str(old[0]) in self.terminals and -reach<=self.terminals[str(old[0])]-old[2]<=reach)
                    item={'lower_s':sec-1,'upper_s':sec,'vehicle':vehicle,'link':old[0],
                          'native_event_indices':[i for i,_ in matches],'unique_match':len(matches)==1,
                          'terminal_inference_collision':collision}
                    self.removal_matches.append(item)
                    if collision:self.collisions.append(item)
        if sec%30==0:
            for name,rows in zones.items():
                self.spatial.append({'time_s':sec,'zone':name,'global_start_m':self.zones[name][0],
                    'global_end_m':self.zones[name][1],'n_veh':len(rows),'stopped_veh':sum(r[3]<=1. for r in rows),
                    'v_kmh':sum(r[3] for r in rows)/len(rows) if rows else None})
        self.previous,self.previous_counts,self.last_sec=current,counts,sec

    def windows(self, observer, ports):
        rows=[]
        for a,b in WINDOWS:
            for name in self.scopes:
                item={'window_start_s':a,'window_end_s':b,'scope':name,'ttt_veh_h':self.ttt[a,b,name],
                      'ttt_left_veh_h':self.left_ttt[a,b,name],'ttt_right_veh_h':self.right_ttt[a,b,name],
                      'sampled_vehicle_seconds_trapezoid':self.ttt[a,b,name]*3600.,
                      'start_n_veh':self.cutoff_counts[a][name],'end_n_veh':self.cutoff_counts[b][name]}
                if name in ('FW_E','FW_W'):
                    selected=[r for r in observer.flows if r['road']==name and a<r['window_end_s']<=b]
                    item.update({k:sum(r[k] for r in selected) for k in ('source_admissions','ramp_merges','off_departures','terminal_exits_inferred')})
                elif name.isdigit():
                    selected=[r for r in ports.rows if str(r['connector'])==name and a<r['window_end_s']<=b]
                    item.update({k:sum(r[k] for r in selected) for k in ('arrivals_veh','departures_veh','unresolved_absences_veh')})
                    boundary=self.ports[int(name)]
                    crossings=sum(r['crossings'] for r in observer.boundary_rows
                        if r['id']==boundary['id'] and a<r['window_end_s']<=b)
                    item['ramp_merges' if boundary['kind']=='ramp' else 'off_admissions']=crossings
                rows.append(item)
        fields=list(dict.fromkeys(k for r in rows for k in r))
        return [{k:r.get(k) for k in fields} for r in rows]

    def meter_cycles(self):
        rows=[]
        states={r['time_s']:r for r in self.meter_states}
        for start in range(CONTROL,END,10):
            seconds=range(start+1,start+11)
            heads=[r for r in self.head_events if start<r['upper_s']<=start+10]
            merges=[r for r in self.merge_events if start<r['upper_s']<=start+10]
            counts=Counter(states[t]['ldp_state'] for t in seconds)
            rows.append({'window_start_s':start,'window_end_s':start+10,
                'actual_green_s':counts['GREEN'],'actual_red_s':counts['RED'],'actual_off_s':counts['OFF'],
                'head_crossings':len(heads),'head_crossings_on_green':sum(r['ldp_interval_end_state']=='GREEN' for r in heads),
                'head_crossings_on_off':sum(r['ldp_interval_end_state']=='OFF' for r in heads),'actual_merges':len(merges),
                'upstream_n_at_start':states[start]['upstream_n'],'upstream_stopped_at_start':states[start]['upstream_stopped'],
                'downstream_n_at_start':states[start]['downstream_n'],'downstream_stopped_at_start':states[start]['downstream_stopped']})
        episodes=[]
        start=None
        for t in range(CONTROL+1,END+2):
            green=t<=END and states[t]['ldp_state']=='GREEN'
            if green and start is None:start=t
            if not green and start is not None:
                heads=[r for r in self.head_events if start<=r['upper_s']<t]
                merges=[r for r in self.merge_events if start<=r['upper_s']<t]
                episodes.append({'first_green_frame_s':start,'last_green_frame_s':t-1,'green_seconds':t-start,
                    'write_clock_start_s':start-1,'initial_upstream_n':states[start-1]['upstream_n'],
                    'initial_upstream_stopped':states[start-1]['upstream_stopped'],
                    'head_crossings':len(heads),'actual_merges':len(merges),'right_censored':t==END+1})
                start=None
        return rows,episodes


def congestion(rows, key):
    grouped=defaultdict(list)
    for row in rows:grouped[key(row)].append(row)
    result=[]
    for name,series in grouped.items():
        active=[]
        for row in sorted(series,key=lambda r:r['time_s'])+[None]:
            qualifies=row is not None and row['n_veh']>=5 and row['v_kmh'] is not None and row['v_kmh']<30
            if qualifies:active.append(row['time_s'])
            else:
                if len(active)>=5:
                    result.append({'location':name,'first_s':active[0],'last_s':active[-1],
                        'samples':len(active),'span_s':active[-1]-active[0],'right_censored':row is None})
                active=[]
    return result


def analyze(item, out, profile):
    arm,run,network=item['arm'],item['run'],item['network']
    out.mkdir()
    geometry=ex.physical_geometry(network,geometry_profile=profile)
    geometry['source_network']={'path':item['meta']['source_network'],'sha256':item['meta']['source_network_sha256']}
    proof,membership,terminals=area_proof(network,geometry)
    save(out/'area_provenance.json',proof)
    warnings,error_proofs=[],[]
    for path in item['errors']:
        raw=path.read_bytes();parsed=parse_bytes(raw)
        require(parsed['partial_tail_bytes']==0 and not parsed['unparsed_removal_lines'], 'Incomplete/unparsed native removal evidence')
        warnings.extend(parsed['events'])
        error_proofs.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'counts':parsed['counts']})
    removals=[r for r in warnings if r['kind']=='lane_change_removal']
    groups={int(k):v for k,v in item['meta']['fixed_profile_proof']['ldp_signal_groups'].items()}
    ldp=read_ldp_frames({sc:run/'vissim_eval'/f'baseline_{sc}_001.ldp' for sc in groups},groups,1,END)
    require(all(n==END for n in ldp['file_row_count_by_sc'].values()), 'LDP wrong final extent')
    require(ldp['pins']==item['validation']['ldp_pins'], 'Native LDP changed after validation')
    observer,ports=ex.Observer(geometry,removals),ex.PortObserver(geometry)
    measured=Measurements(geometry,ldp['frames'],membership,terminals,removals)
    fzp=item['fzp'];before=fzp.stat();wrapped=SingleScanPath(fzp)
    evidence={'path':str(fzp),'bytes':before.st_size}
    code_paths = [Path(sys.modules[f.__module__].__file__) for f in (native_frames,measure_frames,read_ldp_frames,parse_bytes)]
    input_pins={str(p):sha(p) for p in (Path(__file__),Path(ex.__file__),profile,network,run/'run.json',
        run/'fixed_validation.json',ROOT/'evaluation/controllers/freeway_geometry.py',*code_paths)}
    started=time.monotonic()
    def frames():
        for sec,current in native_frames(wrapped,evidence,deadline=started+1800):
            observer.advance(sec,current);ports.advance(sec,current);measured.advance(sec,current)
            if sec%450==0:print(json.dumps({'arm':arm,'scanned_sec':sec}),flush=True)
            if membership is not None:
                yield Frame(float(sec),{str(n):Vehicle(str(r[0]),r[2],r[3]) for n,r in current.items()})
    if membership is not None:
        area,area_rows=measure_frames(frames(),membership,terminals,end_sec=END,max_tail_extrap_sec=0)
        table(out/'area_timeseries.csv',area_rows)
        at={int(r['sim_sec']):r for r in area_rows}
        area_windows=[]
        for a,b in WINDOWS:
            selected=[r for r in area_rows if a<r['sim_sec']<=b]
            collisions=[r for r in measured.collisions if a<r['upper_s']<=b]
            area_windows.append({'window_start_s':a,'window_end_s':b,
                'ttt_veh_h':at[b]['ttt_veh_h_cumulative']-at[a]['ttt_veh_h_cumulative'],
                'ttd_observed_plus_terminal':at[b]['ttd_observed_plus_terminal_cumulative']-at[a]['ttd_observed_plus_terminal_cumulative'],
                'observed_exit_events':sum(r['observed_exit_events'] for r in selected),
                'terminal_exit_inferred_events':sum(r['terminal_exit_inferred_events'] for r in selected),
                'unresolved_inside_disappearances':sum(r['unresolved_inside_disappearances'] for r in selected),
                'start_n_veh':at[a]['inside_vehicles'],'end_n_veh':at[b]['inside_vehicles'],
                'native_removals_by_warning_clock':sum(a<r['time_sec']<=b and membership[r['link']] for r in removals),
                'terminal_removal_collisions':collisions,'TD_usable_for_ranking':not collisions})
        save(out/'area_windows.json',area_windows)
        save(out/'area_full_fresh_run.json',area)
    else:
        for _ in frames():pass
        area_windows=None
    after=fzp.stat()
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns), 'FZP changed during scan')
    require(measured.last_sec==observer.sec==END,'Missing terminal frame')
    require(input_pins=={p:sha(p) for p in input_pins}, 'Analysis inputs/source changed during scan')
    observations=out/'observations';observations.mkdir()
    save(observations/'geometry.json',geometry)
    for name,rows in (('cells_30s',observer.cells),('flows_30s',observer.flows),('boundaries_30s',observer.boundary_rows),('ports_30s',ports.rows),('port_events',ports.events)):
        table(observations/(name+'.csv'),rows)
    save(observations/'port_cohorts_30s.json',ports.snapshots)
    table(observations/'desired_source_demand.csv',geometry['desired_source_demand'])
    save(observations/'exclusion_evidence.json',{'events':observer.evidence,'native_removals':removals,
         'unmatched_native_removal_indices':sorted(set(range(len(removals)))-observer.removal_matched)})
    save(observations/'manifest.json',{'schema':'metanet-spatial-observations/v1','seed':13,'terminal_sec':END,
        'cell_index_base':0,'fzp':evidence,'network':geometry['network'],'run_receipt':{'path':str(run/'run.json'),'sha256':sha(run/'run.json')},
        'mode':'native-fixed-profile/v1','extractor_sha256':sha(ex.__file__),'driver_sha256':sha(__file__),
        'cell_window_conservation_checks':observer.checks,'max_conservation_residual_veh':0,
        'clock':{'states':'exact FZP endpoint; empty t0 only','flows':'(start,end]; one-second transition brackets',
                 'forecast_use':'Future observations diagnostic only; initial state and cohorts must use cutoff only'},
        'files':{p.name:sha(p) for p in observations.iterdir()}})
    component=measured.windows(observer,ports)
    table(out/'component_windows.csv',component)
    table(out/'component_stocks_1s.csv',measured.stock_rows)
    table(out/'meter_states_1s.csv',measured.meter_states)
    table(out/'meter_head_events.csv',measured.head_events,fields=['lower_s','upper_s','vehicle','old_link','new_link','old_pos_m','new_pos_m','ldp_interval_end_state','previous_ldp_state','evidence'])
    table(out/'meter_merge_events.csv',measured.merge_events,fields=['lower_s','upper_s','vehicle','ldp_interval_end_state','already_downstream_of_head_at_lower'])
    cycles,episodes=measured.meter_cycles()
    table(out/'meter_cycles_10s.csv',cycles)
    save(out/'meter_green_episodes.json',episodes)
    states={r['time_s']:r for r in measured.meter_states}
    meter_windows=[]
    for a,b in WINDOWS:
        selected=[r for r in measured.head_events if a<r['upper_s']<=b]
        meter_windows.append({'window_start_s':a,'window_end_s':b,
            'actual_green_seconds':sum(states[t]['ldp_state']=='GREEN' for t in range(a+1,b+1)),
            'actual_off_seconds':sum(states[t]['ldp_state']=='OFF' for t in range(a+1,b+1)),
            'head_crossings':len(selected),'head_crossings_on_green':sum(r['ldp_interval_end_state']=='GREEN' for r in selected),
            'head_crossings_on_off':sum(r['ldp_interval_end_state']=='OFF' for r in selected),
            'actual_merges':sum(a<r['upper_s']<=b for r in measured.merge_events),
            **{key+'_veh_h':sum((states[t-1][key]+states[t][key])/7200. for t in range(a+1,b+1))
               for key in ('upstream_n','downstream_n','upstream_stopped','downstream_stopped')}})
    save(out/'meter_windows.json',meter_windows)
    table(out/'spatial_30s.csv',measured.spatial)
    save(out/'congestion_episodes.json',congestion(measured.spatial,lambda r:r['zone'])+
         congestion(observer.cells,lambda r:f"{r['road']}_display{r['cell']+1}"))
    summary={'arm':arm,'complete':True,'network_sha256':sha(network),'input_pins':input_pins,'fzp':evidence,
        'paired_warmup_prefix':wrapped.proof(),'full_native_prefix':wrapped.full_proof(),
        'area_status':proof['status'],'area_windows':area_windows,
        'native_error_proofs':error_proofs,'native_warnings':warnings,'removal_matches':measured.removal_matches,
        'unfinished_inputs_at_2250':[r for r in warnings if r['kind']=='unfinished_vehicle_input'],
        'component_windows':component,'meter_head_crossings_1350_2250':sum(CONTROL<r['upper_s']<=END for r in measured.head_events),
        'limits':['Omega TTT uses the existing 1Hz trapezoid stock definition; TTD means boundary exit events, not distance.',
            'Component is physical freeway chains plus the disjoint 16 connectors; it is a subset of Omega, never added to Omega.',
            'model_component is the freeway plus eight off connectors plus target10490; seven other on-ramps are external to this model scope. Composite rows are alternatives, never additive.',
            'Physical-link component stock includes finite negative source positions; canonical cell extraction excludes negative chain positions.',
            'Native uninserted demand is outside spatial TTT; native ERR remainder is only an end-of-run figure, not a measured intermediate queue.',
            'Known terminal-removal collisions hold TTD ranking rather than silently treating deletion as completion.',
            'Head queues are sampled stopped stocks (speed<=1), split at the actual head; head crossings and actual mainline merges are distinct events.',
            'LDP frame t follows motion from t-1 and precedes COM write at t; event state is actual LDP at crossing upper t. Crossing times are brackets.',
            'OFF remains OFF. No g10/GREEN versus native OFF equivalence is asserted.',
            'Congestion requires n>=5 and speed<30 at five consecutive30s samples (120s span).',
            'Native effect windows are450/450/900s; model450s forecasts are separate comparisons.'],
        'elapsed_sec_not_benchmark':time.monotonic()-started}
    save(out/'summary.json',summary)
    return summary,ldp['frames']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',type=Path,default=HERE.parent)
    parser.add_argument('--geometry-profile',type=Path,default=DEFAULT_PROFILE)
    parser.add_argument('--baseline-parity-proof',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    experiment=args.experiment.resolve();profile=args.geometry_profile.resolve()
    plan={'experiment':str(experiment),'geometry_profile':str(profile),'windows':WINDOWS,
          'arms':[{k:str(experiment/(prefix+arm)) for k,prefix in [('run','run_'),('prepared','prepared_')]} for arm in ARMS],
          'execute':args.execute,'warning':'Do not execute until root confirms all native runs have ended.'}
    if not args.execute:
        print(json.dumps(plan,ensure_ascii=False,indent=2));return
    items=[completed(experiment,arm) for arm in ARMS]
    require(len({sha(i['network']) for i in items})==1,'Arms use different native network bytes')
    require(args.baseline_parity_proof is not None,'Explicit root-reviewed original-native parity proof required')
    parity=load(args.baseline_parity_proof)
    # Require the full v3 original-native comparison, not merely a command check.
    require(parity.get('passed') is True and parity.get('paired_comparison_end_sec')==END
            and parity.get('paired_native_signals_passed') is True
            and parity.get('paired_warmup_prefix',{}).get('last_time_s')==END,
            'Root original-native full2250 parity proof is not passed')
    require(Path(parity['reference']).resolve()==(experiment.parent/'east080_v1/native9000').resolve(),
            'Parity reference is not the original seed13 native9000 run')
    require(parity.get('saved_simulation_period_sec')==parity.get('effective_simulation_period_sec')==9001,
            'Original native SimPeriod must be preserved')
    out=(args.out or experiment/'analysis/results_v1').resolve()
    require(out.is_relative_to(experiment) and not out.exists(),'New output inside selected experiment required')
    out.mkdir(parents=True)
    save(out/'analysis_plan.json',plan)
    save(out/'baseline_parity_provenance.json',{'path':str(args.baseline_parity_proof.resolve()),'sha256':sha(args.baseline_parity_proof),'proof':parity})
    summaries=[];reference_signals=None
    for item in items:
        summary,signals=analyze(item,out/item['arm'],profile)
        if reference_signals is None:
            require(summary['full_native_prefix']==parity['paired_warmup_prefix'],
                    'Baseline parity proof does not belong to this none FZP')
            reference_signals=signals;prefix=summary['paired_warmup_prefix']
        else:
            require(summary['paired_warmup_prefix']==prefix,'Paired full-column FZP prefix differs: '+item['arm'])
            targeted={'9107:1'} if item['arm'] in ('rm','both') else set()
            for sec,frame in signals.items():
                require(all(value==reference_signals[sec][key] for key,value in frame.items() if sec<=CONTROL or key not in targeted),
                        'Untargeted/warmup native LDP differs: '+item['arm'])
        summaries.append(summary)
    save(out/'comparison.json',{'schema':'native-four-arm-observed-response/v1','paired_prefix_passed':True,
        'paired_native_signals_passed':True,'analysis_scope':'Measured effects on identical native prefix; no optimizer/controller-benefit claim',
        'all_Omega_provenance_passed':all(s['area_status']=='PASS' for s in summaries),'arms':summaries})
    print(json.dumps({'completed':str(out),'paired_prefix_passed':True},ensure_ascii=False))


if __name__=='__main__':
    main()
