"""Read existing native receipts only; no COM or FZP scan."""
import collections
import csv
import hashlib
import json
from pathlib import Path
from evaluation.controllers import obs150_contract as oc
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw)

def main():
    target=HERE/'native_evidence.json'
    if target.exists():raise FileExistsError(target)
    cache=ROOT.parent/'control-full-review/diagnostics/dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none'
    path=cache/'port_events.csv';raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    events=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
    native43={}
    for ramp,off in [('10646','10638'),('10480','10491')]:
        merges=[x for x in events if x['connector']==ramp and x['kind']=='departure' and 2250<float(x['time_s'])<=2700.1]
        pairs=[];unmatched=[]
        for m in merges:
            follow=[e for e in events if e['vehicle']==m['vehicle'] and e['connector']==off
                    and e['kind']=='arrival' and float(m['time_s'])<=float(e['time_s'])<=float(m['time_s'])+60]
            if not follow:unmatched.append(m);continue
            x=min(follow,key=lambda e:float(e['time_s']))
            pairs.append(dict(vehicle=int(m['vehicle']),merge_s=float(m['time_s']),exit_s=float(x['time_s']),
                              in_window=float(x['time_s'])<=2700.1))
        native43[ramp]=dict(next_exit=off,merges=len(merges),matched=len(pairs),
                           matched_within_window=sum(p['in_window'] for p in pairs),pairs=pairs,unmatched=unmatched)
    # Native 47 MER identifies ramp ENTRY and exit ENTRY. Merge count remains
    # separately balance-inferred in the canonical receipt, not a detector claim.
    audit=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    table=I/'selected/obs150/obs150_detectors_v2.csv'
    detectors,digest=oc.read_detector_csv(table);pins[str(table)]=digest
    groups=oc.group_boundaries(detectors);native47={}
    for arm in ('hold','selected'):
        raws={}
        for text,digest in audit['input_sha256'].items():
            path=Path(text)
            if arm not in path.parts:continue
            d=read(path);assert pins[str(path)]==digest;raws[int(d['sim_sec'])]=d
        entries=collections.defaultdict(list)
        for t in (2850,3000,3150):
            bundle=oc.load_bundle(raws[t]);window=oc.assign_window(bundle.obs,bundle.mer_rows)
            for ref in ('ramp_arrival:RM_C10646','off_entry:10638'):
                for det in groups[ref]:
                    assert window.tails[det.dcp_no]==0
                    entries[ref].extend(window.entries[det.dcp_no])
        off=entries['off_entry:10638'];arrivals=entries['ramp_arrival:RM_C10646']
        initial={v['veh_no'] for v in raws[2700]['vehicle_records']['records'] if v['link_no']==10646}
        initial_routes=read(Path(raws[2700]['lane_plant_observation']['directory'])/'frame_002700.json')
        route_by_id={v[0]:(v[6],v[7]) for v in initial_routes['vehicles']}
        assert all(route_by_id[v]==(1135.,2.) for v in initial)
        pairs=[]
        for e in off:
            prior=[x for x in arrivals if x.veh==e.veh and x.t_entry<e.t_entry]
            if e.veh in initial or prior:
                pairs.append(dict(vehicle=e.veh,exit_entry_s=e.t_entry,initial_ramp=e.veh in initial,
                                  ramp_entry_s=max(x.t_entry for x in prior) if prior else None))
        expected=read(HERE.parent/'offramp_drain_profile/eight_offramps.json')['arms'][arm]['10638']['native_entry']
        assert len(off)==expected
        native47[arm]=dict(off_entry_count=len(off),identified_from10646=len(pairs),
                           initial_ramp_count=len(initial),ramp_entry_count=len(arrivals),
                           balance_inferred_merge=audit['arms'][arm]['RM_C10646']['actual']['merge'],pairs=pairs,
                           note='Pairs identify observed origin; no exact merge time inferred from entry detector.')
    result=dict(status='PHYSICAL_ROUTE_FREE_CONTINUATION_MISSING_IN_PLANT',native43=native43,native47=native47,
                source_pins=pins,new_native=0,new_fzp_scan=0,fit=0,
                documentation='https://cgi.ptvgroup.com/vision-help/VISSIM_2026_COM-Help/VISSIMLIB~ILink_attributes.html',
                limitation='Direction ALL rule documented in2026; mechanism independently observed in installed2020. 10480 unmatched vehicles retained, not invented exits.')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('43',[(r,d['merges'],d['matched'],d['matched_within_window']) for r,d in native43.items()])
    print('47',[(a,d['off_entry_count'],d['identified_from10646'],d['balance_inferred_merge']) for a,d in native47.items()])

if __name__=='__main__':main()

