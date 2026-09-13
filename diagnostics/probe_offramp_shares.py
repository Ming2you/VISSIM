"""Audit prior provenance and sampled branch departures without changing tuning."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.offramp_routing import derive_prior


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def fingerprint(path):return {'path':str(path),'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}


def main():
    prior=read('diagnostics/offramp_route_prior_ver2.json')
    routes=derive_prior(prior)
    tree=ET.parse(ROOT/prior['network']['path']).getroot()
    mapping=read('evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    split=read('outputs/freeway_ramp_split_v2_20260907.json')
    evidence={}
    for group,spec in prior['groups'].items():
        direction='FW_'+group[-1]
        chain=mapping['freeway_model_links'][direction]
        offsets=dict(zip(map(str,chain['chain_links']),chain['chain_offsets_m']))
        decision=routes[group]['decision']
        position=offsets[decision['link']]+float(decision['pos'])
        branch_rows=[r for r in split['off_ramps'] if r['legacy_group']==group]
        first,last=sorted(r['chain_pos_m'] for r in branch_rows)
        after=[r for r in split['on_ramps'] if r['direction']==direction and position<r['chain_pos_m']<last]
        middle=[r for r in after if first<r['chain_pos_m']<last]
        lengths={}
        for conn in (spec['direct_connector'],spec['signal_connector']):
            link=tree.find(f".//links/link[@no='{conn}']")
            pts=[(float(p.get('x')),float(p.get('y'))) for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')]
            length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
            lengths[conn]={'length_m':length,'illustrative_travel_sec_at_60kmh':length/60*3.6}
        evidence[group]={'decision_chain_pos_m':position,'branches':branch_rows,
            'merges_after_decision_before_final_branch':after,'merges_between_branches':middle,'connector_lengths':lengths}
    rows=[]
    sources=[]
    for run in ['codex_nc_s13_6056c94_20260909_retry','codex_n7_s13_6056c94_20260909']:
        base=Path('evaluation/runs')/run
        state_csv=base/f'state_{run}.csv'
        with (ROOT/state_csv).open(encoding='utf-8-sig') as f:
            csv_rows=list(csv.DictReader(f))
        time_key='sim_sec'
        logtimes=sorted(float(r[time_key]) for r in csv_rows)
        step=statistics.median(b-a for a,b in zip(logtimes,logtimes[1:]))
        decisions=sorted((ROOT/base/('decisions_'+run)).glob('state_*.json'))
        previous=0
        for path in decisions:
            raw=json.loads(path.read_text(encoding='utf-8-sig'))
            t=float(raw['sim_sec']); obs=raw['local_observation']; n=obs.get('queue_window_samples',0)
            nc='codex_nc_' in run
            logs=[x for x in logtimes if x>=previous and (x<=t if nc and t>1 else x<t)]
            deficit=len(logs)-n
            lower=max([x for x in logtimes if logs and x<logs[0]],default=logs[0] if logs else 0)
            upper=logs[-1] if logs else 0
            for group,spec in prior['groups'].items():
                direct=obs['link_departures_window'].get(spec['direct_connector'])
                signal=obs['link_departures_window'].get(spec['signal_connector'])
                if direct is None or signal is None:raise ValueError('Missing branch observation')
                total=direct+signal
                rows.append({'run':run,'decision_sec':t,'group':group,'samples':n,'sample_step_sec':step,
                    'nominal_transitions_from_sec':lower,'nominal_transitions_to_sec':upper,
                    'samples_missing_from_nominal_schedule':deficit,
                    'direct_departures_observed':direct,'signal_departures_observed':signal,
                    'observed_direct_fraction':direct/total if total else '',
                    'configured_share':.468 if '_D_' in group else .484,
                    'static_route_prior':spec['direct_share']})
            previous=t
            sources.append(fingerprint(path.relative_to(ROOT)))
    target=ROOT/'diagnostics/offramp_share_windows.csv'
    with target.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=[]
    for run in sorted({r['run'] for r in rows}):
        for group in prior['groups']:
            subset=[r for r in rows if r['run']==run and r['group']==group and r['samples']]
            direct=sum(r['direct_departures_observed'] for r in subset); signal=sum(r['signal_departures_observed'] for r in subset)
            rates=[r['observed_direct_fraction'] for r in subset if r['observed_direct_fraction']!='']
            summary.append({'run':run,'group':group,'windows':len(subset),'direct_observed':direct,'signal_observed':signal,
                'pooled_observed_share':direct/(direct+signal) if direct+signal else None,
                'minimum_window_share':min(rates),'maximum_window_share':max(rates),
                'last_nominal_sampled_time_sec':max(r['nominal_transitions_to_sec'] for r in subset),
                'windows_with_sample_deficit':sum(r['samples_missing_from_nominal_schedule']!=0 for r in subset)})
    output={'source_files':sources,'network':prior['network'],'static_route_priors':routes,'topology_scope':evidence,
        'summary':summary,'observation_method':{'source':'VBS AccumulateDepartures at LogStateCsv sampling times',
            'counts':'Previous sampled link receives one departure when vehicle changes link or disappears.',
            'limitations':['Vehicles traversing a connector wholly between samples are invisible.','Differing length, speed and queue residence create branch-dependent detection bias.','Disappearances are counted from last sampled link, not necessarily a physical crossing.','Controlled decisions reset the window before the log at that second, normally yielding a 30-second lag.','NC 900 has 31 accumulated samples; it is not a single 150-second window.','Pooled/min/max shares are observed sample statistics, not routing truth or calibrated priors.']}}
    (ROOT/'diagnostics/offramp_share_audit.json').write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
