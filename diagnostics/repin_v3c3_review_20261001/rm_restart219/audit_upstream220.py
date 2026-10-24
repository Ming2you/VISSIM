"""Post-hoc saved SC1004 head/10681 identities for the first applied interval."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from evaluation.controllers import obs150_contract as oc

HERE = Path(__file__).resolve().parent
DEC = Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')

def main():
    out = HERE/'upstream220v2/native_paths.json'
    assert not out.exists()
    assert json.loads((out.parent/'completion.json').read_bytes())['status'] == 'COMPLETE'
    pins, states, assigned, heads = {}, {}, {}, defaultdict(list)
    detector_rows = None
    for t in (750,900,1050):
        p = DEC/f'state_{t:06d}.json'
        blob = p.read_bytes(); pins[str(p)] = hashlib.sha256(blob).hexdigest()
        states[t] = json.loads(blob)
        bundle = oc.load_bundle(states[t])
        assignment = oc.assign_window(bundle.obs, bundle.mer_rows)
        assert assignment.lag_ok and assignment.end_s == t
        det, digest = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
        pins[bundle.obs['detector_config']['path']] = digest
        assert detector_rows is None or detector_rows == det
        detector_rows = det
        assigned[t] = (bundle, assignment)
        for d in det:
            if d.role == 'head' and d.link in (52,66,46):
                for row in assignment.entries[d.dcp_no]:
                    heads[row.veh].append((row,d))
    before = {v['veh_no']:v for v in states[900]['vehicle_records']['records']}
    bundle, assignment = assigned[1050]
    arrivals = [d for d in detector_rows if d.role == 'ramp_arrival' and d.link == 10681]
    assert len(arrivals) == 2
    rows = []
    for d in arrivals:
        assert assignment.tails[d.dcp_no] == 0
        for a in assignment.entries[d.dcp_no]:
            known = [(h,p) for h,p in heads[a.veh] if h.t_entry <= a.t_entry]
            h,p = max(known,key=lambda x:x[0].t_entry) if known else (None,None)
            rows.append(dict(veh=a.veh,arrival_sec=a.t_entry,lane=d.lane,
                state900=before.get(a.veh),last_head_link=p.link if p else None,
                last_head_lane=p.lane if p else None,last_head_sec=h.t_entry if h else None,
                observed_trip_sec=a.t_entry-h.t_entry if h else None))
    expected = json.loads((HERE/'first_interval_ramps.json').read_bytes())['arms']['current']['RM_C10681']
    assert len(rows) == len({x['veh'] for x in rows}) == expected['arrivals_at_boundary'] == 31
    head_counts = [dict(link=d.link,lane=d.lane,position=d.pos,dcp=d.dcp_no,
        count=bundle.obs['detectors'][str(d.dcm_no)],entries=len(assignment.entries[d.dcp_no]),tail=assignment.tails[d.dcp_no])
        for d in detector_rows if d.role=='head' and d.link in (52,66,46)]
    stock_counts = {str(t):dict(Counter(str(v['link_no']) for v in states[t]['vehicle_records']['records']
                                    if v['link_no'] in (52,66,46,68,10625,10629,10633,10681,10682))) for t in (900,1050)}
    summary = dict(status='PASS',window=[900,1050],history_start=600,head_counts=head_counts,
        arrived31_by_initial_link=dict(Counter(str(x['state900']['link_no']) if x['state900'] else 'not_in_900_frame' for x in rows)),
        arrived31_by_last_head=dict(Counter(str(x['last_head_link']) for x in rows)),
        arrived31_after_head900=sum(x['last_head_sec'] is not None and x['last_head_sec']>=900 for x in rows),
        physical_stock_counts=stock_counts,arrivals=rows,input_sha256=pins,
        limits=['Completed trips only; other destinations and future arrivals are not desired ramp demand.',
                'Head detector is before the connector entry; these are not identical measurement planes.',
                'Unmatched head origins retained; no invented origin or lane change path.',
                'Observed future data used only after autonomous prediction, for validation.'])
    out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('arrivals','input_sha256','limits')}))

if __name__ == '__main__':
    main()
