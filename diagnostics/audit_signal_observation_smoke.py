"""Read-only observer smoke audit; ordered FZP prefix comparison only on request.

Uses the existing observed-NC auditor's raw ordered-payload definition, bounded
at an explicit complete second instead of hashing the entire reference run.
No controller, simulator or optimizer is invoked.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.signal_head_observation import validate_provenance, serialized_head_position
from plant.src.vissim_strict.signal_program import parse_sig


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def action_evidence(action, previous, context, run_id, start, end):
    """Check recorded provenance and carry; do not infer capacity increases."""
    metadata = action['metadata']
    keys = [k for k in metadata if k.startswith('head_provenance_')]
    if (keys != ['head_provenance_'+context] or metadata[keys[0]] != 1
            or action['run_provenance']['run_id'] != run_id
            or metadata['head_observation_snapshot_sec'] != end
            or metadata['sim_sec'] != end):
        raise ValueError('Recorded action head provenance/time mismatch')
    prior = previous.get('metadata', {}) if previous else {}
    current_floors = {k:v for k,v in metadata.items() if k.startswith('head_discharge_floor_')}
    prior_floors = {k:v for k,v in prior.items() if k.startswith('head_discharge_floor_')}
    for key,value in current_floors.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid recorded discharge floor')
        if key in prior_floors and value < prior_floors[key]:
            raise ValueError('Recorded same-source floor was not preserved')
        suffix = key.removeprefix('head_discharge_floor_')
        candidate = 'head_candidate_rate_'+suffix
        candidate_end = 'head_candidate_end_'+suffix
        if key not in prior_floors and not (
                candidate in prior and candidate in metadata
                and prior[candidate_end] == start and metadata[candidate_end] == end
                and value >= min(prior[candidate], metadata[candidate])):
            raise ValueError('New floor lacks two adjacent recorded candidate windows')
    if set(prior_floors) - set(current_floors):
        raise ValueError('Same-source carried floor disappeared')
    for key,value in metadata.items():
        if key.startswith('head_candidate_rate_') and (not math.isfinite(value) or value <= 0):
            raise ValueError('Invalid recorded candidate rate')
        if key.startswith('head_candidate_end_') and value != end:
            raise ValueError('Recorded candidate has stale end time')
    return {'provenance_matches':True,'prior_floor_count':len(prior_floors),
            'current_floor_count':len(current_floors),
            'new_floor_count':len(set(current_floors)-set(prior_floors)),
            'prior_floor_increases':{k:current_floors[k]-v for k,v in prior_floors.items()
                                      if current_floors[k] > v},
            'limits':'A floor may equal the pre-existing installed base capacity; groups_updated is not the count of actual capacity increases.'}


def prefix_payload(path, through_sec, *, completed_eof=False):
    """Hash exact native rows once through T; metadata excluded, no sorting."""
    if through_sec < 1 or int(through_sec) != through_sec:
        raise ValueError('Positive integer prefix endpoint required')
    before = path.stat(); digest = hashlib.sha256(); rows = size = 0
    times = []; previous = None; lookahead = None
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                header = line.rstrip(b'\r\n').decode('ascii'); break
        else: raise ValueError('Missing native vehicle header')
        offset = stream.tell()
        for line in stream:
            if not line.endswith(b'\n'): raise ValueError('Partial FZP row')
            t = float(line.split(b';', 1)[0])
            if not math.isfinite(t) or t != int(t): raise ValueError('Noninteger FZP time')
            if previous is not None and t < previous: raise ValueError('FZP record order changed')
            if t > through_sec:
                lookahead = t; break
            if previous != t: times.append(int(t))
            digest.update(line); rows += 1; size += len(line); previous = t
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Completed prefix source changed during read')
    if times != list(range(1, int(through_sec)+1)):
        raise ValueError('Missing one-second frames in requested prefix')
    if lookahead is None and not completed_eof:
        raise ValueError('Final frame requires later timestamp or completed-run EOF')
    return {'path': str(path), 'file_size_observed': after.st_size, 'mtime_ns': after.st_mtime_ns,
            'header': header, 'payload_offset': offset, 'payload_bytes': size, 'rows': rows,
            'payload_sha256': digest.hexdigest(), 'first_sec': 1, 'last_sec': int(through_sec),
            'frames': len(times), 'lookahead_sec': lookahead,
            'completion_basis': 'later complete row' if lookahead is not None else 'SIM_DONE and stable EOF',
            'full_file_hashed': False}


def compare_trajectory_prefixes(run_name, reference_name, through_sec):
    """Shared ON/OFF comparison; does not require a head window in OFF data."""
    runs=[ROOT/'evaluation/runs'/name for name in (run_name,reference_name)]
    payloads, manifests = [], []
    for run in runs:
        log=(run/f'runlog_{run.name}.txt').read_bytes()
        if b'STAGE=SIM_DONE' not in log:
            raise ValueError('Wait for SIM_DONE before the prefix trajectory comparison')
        manifest_path=run/f'run_provenance_{run.name}.json'
        raw_manifest=manifest_path.read_bytes();manifest=json.loads(raw_manifest.decode('utf-8-sig'))
        if manifest['sim_period_sec'] < through_sec:
            raise ValueError('Requested prefix exceeds recorded simulation period')
        paths=list(run.glob('vissim_eval/*.fzp'))
        if len(paths)!=1:raise ValueError('Expected one native FZP per run')
        payloads.append(prefix_payload(paths[0],through_sec,completed_eof=True))
        manifests.append({'path':str(manifest_path),'sha256':sha(raw_manifest),
                          'run_id':manifest['run_id'],'controller':manifest['controller'],
                          'seed':manifest['seed'],'sim_period_sec':manifest['sim_period_sec']})
    fields=('header','payload_sha256','rows','payload_bytes','first_sec','last_sec')
    return {'run':run_name,'reference_run':reference_name,'through_sec':through_sec,
            'payloads':payloads,'manifests':manifests,
            'ordered_payload_exact':all(payloads[0][k]==payloads[1][k] for k in fields),
            'scope':'Ordered native payload comparison only; separate configuration, actuation and provenance review is required for causal attribution.'}


def audit(run_name, reference_name, through_sec, with_trajectories):
    run = ROOT/'evaluation/runs'/run_name
    manifest_path = run/f'run_provenance_{run_name}.json'
    manifest = load(manifest_path)
    log_path = run/f'runlog_{run_name}.txt'; log_bytes = log_path.read_bytes()
    log = log_bytes.decode('utf-8', errors='replace'); done = 'STAGE=SIM_DONE' in log
    failed = bool(re.search(r'(?:DECISION_FAILED|STAGE=FAIL|Traceback|result=exit=[1-9])',log))
    network = Path(manifest['files']['network']['path'])
    if sha(network.read_bytes()) != manifest['files']['network']['sha256']:
        raise ValueError('Network source changed')
    tree = ET.parse(network).getroot()
    native_controllers = {x.get('no'): x for x in tree.findall('./signalControllers/signalController')}
    geometry = {x.get('no'): x for x in tree.findall('./signalHeads/signalHead')}
    config_source = manifest['files']['generated_vbs_config']
    config_bytes = Path(config_source['path']).read_bytes()
    if sha(config_bytes) != config_source['sha256']:
        raise ValueError('Generated physical VBS configuration changed')
    selected_rows = re.findall(r'^RW_SIGNAL_SCS\s*=\s*"([0-9,]+)"',
                               config_bytes.decode('utf-8-sig'),re.MULTILINE)
    if len(selected_rows) != 1:
        raise ValueError('Expected one pinned physical selected-controller list')
    selected = set(selected_rows[0].split(','))
    expected_heads = {no for no,node in geometry.items() if node.get('sg').split()[0] in selected}
    programs, native_cache, native_sources = {}, {}, {}
    decisions = run/f'decisions_{run_name}'
    snapshots, identities = [], set()
    previous_action = None
    last_window_end = None
    for path in sorted(decisions.glob('state_*.json')):
        raw = load(path); window = raw.get('local_observation', {}).get('signal_observation_window')
        if window is None: raise ValueError('Enabled smoke snapshot has no physical head window')
        options = manifest['signal_observation']['options']
        context = validate_provenance(raw, window, options)
        identities.add(context)
        a, b = window['start_sec'], window['end_sec']; duration = b-a
        if (b != raw['sim_sec'] or window['cadence_sec'] != 1
                or window['transition_count'] != duration or not window['clock_complete']):
            raise ValueError('Window timestamp/cadence/clock invalid')
        if last_window_end is not None and a != last_window_end:
            raise ValueError('Successive decision windows overlap or have a gap')
        last_window_end = b
        differences, rows = [], []
        seen = set()
        for head in window['heads']:
            no = head['head_id']; node = geometry[no]
            if no in seen: raise ValueError('Duplicate physical head')
            seen.add(no)
            if (node.get('lane') != str(head['link'])+' '+str(head['lane'])
                    or node.get('sg') != str(head['sc'])+' '+str(head['sg'])
                    or serialized_head_position(float(node.get('pos'))) != head['position_m']):
                raise ValueError('Physical head geometry differs')
            numeric = ('green_sec','native_sec','controlled_sec','unverified_sec','crossings','qualified_crossings')
            if any(not math.isfinite(head[k]) or head[k] < 0 for k in numeric):
                raise ValueError('Nonfinite/negative head evidence')
            if (head['native_sec']+head['controlled_sec']+head['unverified_sec'] != duration
                    or head['green_sec'] > duration or head['qualified_crossings'] > head['crossings']):
                raise ValueError('Head exposure/flow conservation failed')
            sc, sg = str(head['sc']), str(head['sg'])
            controller = native_controllers[sc]
            if sc not in programs:
                sig = network.parent/controller.get('supplyFile2').removeprefix('#data#')
                native_sources[str(sig)] = sha(sig.read_bytes())
                pins = [p for p in manifest['signal_programs'] if Path(p['path']).resolve()==sig.resolve()]
                if len(pins) != 1 or pins[0]['sha256'] != native_sources[str(sig)]:
                    raise ValueError('Native signal program differs from recorded run source')
                programs[sc] = (parse_sig(sig, int(controller.get('progNo'))), float(controller.get('offset')))
            key = (sc,sg,a,b)
            if key not in native_cache:
                program, offset = programs[sc]
                native_cache[key] = sum(program.state_at(t,sg,controller_offset_sec=offset)=='GREEN'
                                        for t in range(int(a),int(b)))
            expected = native_cache[key]
            row = {'head':no,'sc':sc,'sg':sg,'link':head['link'],'lane':head['lane'],
                   'actual_green_sec':head['green_sec'],'native_program_left_step_green_sec':expected,
                   'difference_sec':head['green_sec']-expected}
            rows.append(row)
            if row['difference_sec'] != 0: differences.append(row)
        if seen != expected_heads:
            raise ValueError('Physical head window omits/adds configured selected-controller heads')
        action_path = path.with_name(path.name.replace('state_','action_'))
        action = load(action_path) if action_path.is_file() else {}
        metadata = action.get('metadata',{})
        recorded_action = action_evidence(action,previous_action,context,manifest['run_id'],a,b) if action else None
        if action: previous_action = action
        snapshots.append({'path':str(path),'sha256':sha(path.read_bytes()),'sim_sec':raw['sim_sec'],
                          'window_sec':[a,b],'transitions':window['transition_count'],'heads':len(seen),
                          'native_sec_total':sum(h['native_sec'] for h in window['heads']),
                          'controlled_sec_total':sum(h['controlled_sec'] for h in window['heads']),
                          'unverified_sec_total':sum(h['unverified_sec'] for h in window['heads']),
                          'green_differences':differences,'per_head_green':rows,
                          'crossings_total':sum(h['crossings'] for h in window['heads']),
                          'qualified_crossings_total':sum(h['qualified_crossings'] for h in window['heads']),
                          'unknown_links':window['unknown_links'],'bypass_link_exits':window.get('bypass_link_exits',{}),
                          'action_present':bool(action),'head_metadata':{k:v for k,v in metadata.items() if k.startswith('head_')},
                          'recorded_action_evidence':recorded_action,
                          'action_sha256':sha(action_path.read_bytes()) if action else None})
    if len(identities) > 1: raise ValueError('One run has conflicting head provenance identities')
    result = {'schema':'signal-observer-smoke/v1','run':run_name,'run_id':manifest['run_id'],
              'status':'complete' if done else 'failed_partial' if failed else 'partial',
              'sim_done':done,'failure_logged':failed,'snapshots':snapshots,
              'head_provenance_identities':list(identities),
              'bulk_reads':[int(x) for x in re.findall(r'HEAD_OBSERVATION_BULK_READS=(\d+)',log)],
              'cache_hits':[int(x) for x in re.findall(r'HEAD_OBSERVATION_CACHE_HITS=(\d+)',log)],
              'bulk_counter_unit':'One verified whole-vehicle capture, containing four GetMultiAttValues arrays; not one counter increment per attribute.',
              'run_log_sha256':sha(log_bytes),'manifest_sha256':sha(manifest_path.read_bytes()),
              'source_sha256':{str(Path(__file__)):sha(Path(__file__).read_bytes())},
              'native_program_sha256':native_sources,
              'limits':['Program comparison uses integer left-step states; first-cycle native initialization may require LSA evidence before declaring a discrepancy a collector bug.',
                        'Native NC cannot test controlled GREEN ownership; fake-COM tests cover that branch.',
                        'No member mapping or capacity installation success is inferred from accurate collection alone.']}
    if any(sha(Path(p).read_bytes()) != value for p,value in native_sources.items()):
        raise ValueError('Native signal source changed during audit')
    if with_trajectories:
        if not done: raise ValueError('Wait for SIM_DONE before the one prefix trajectory comparison')
        result['trajectory']=compare_trajectory_prefixes(run_name,reference_name,through_sec)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True)
    p.add_argument('--reference',default='codex_area_observed_nc_s13_20260910')
    p.add_argument('--through-sec',type=int,default=1050)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--with-trajectories',action='store_true')
    mode.add_argument('--trajectory-only',action='store_true',help='Compare completed ON/OFF native prefixes without requiring head windows.')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    output=a.output.resolve()
    if not output.is_relative_to(ROOT/'diagnostics') or output.exists():
        raise ValueError('New diagnostic output required; historical results cannot be overwritten')
    result=({'schema':'signal-observer-prefix-comparison/v1','status':'complete',
             'trajectory':compare_trajectory_prefixes(a.run,a.reference,a.through_sec),
             'source_sha256':{str(Path(__file__)):sha(Path(__file__).read_bytes())}}
            if a.trajectory_only else audit(a.run,a.reference,a.through_sec,a.with_trajectories))
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'status':result['status'],'snapshots':len(result.get('snapshots',[])),
                      'trajectory_exact':result.get('trajectory',{}).get('ordered_payload_exact')}))


if __name__=='__main__':main()
