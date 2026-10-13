"""Where were actual SC6 head-crossing vehicles at the initial observation?

Read completed obs150 detector IDs only. This is a diagnostic of initial
support, not a future-input correction or a proof of a complete approach area.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc


def main():
    out = HERE / 'observed_cohorts.json'
    assert not out.exists()
    pins, cases = {}, {}
    support = {138, 10209, 1210018302, 1220015100, 1220018301, 1220018302}
    for arm in ('hold', 'selected'):
        folder = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29') / arm / f'decisions_sdmpc31_g_2400_{arm}_s29'
        raw_path = folder / 'state_002400.json'
        data = raw_path.read_bytes(); pins[str(raw_path)] = hashlib.sha256(data).hexdigest()
        initial = json.loads(data)['vehicle_records']
        assert initial['complete']
        initial = {r['veh_no']: r for r in initial['records']}
        cases[arm] = []
        for end in (2550, 2700, 2850):
            p = folder / f'state_{end:06}.json'
            data = p.read_bytes(); pins[str(p)] = hashlib.sha256(data).hexdigest()
            bundle = oc.load_bundle(json.loads(data))
            ds, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
            window = oc.assign_window(bundle.obs, bundle.mer_rows)
            rows, unresolved = [], {}
            for d in ds:
                if d.role == 'head' and d.link == 1210018302:
                    # Canonical obs150 permits a bounded final MER tail. The
                    # detector count is known but those vehicle IDs are not.
                    unresolved[str(d.lane)] = window.tails[d.dcp_no]
                    rows.extend((d.lane, r.veh) for r in window.entries[d.dcp_no])
            assert len(rows) == len({veh for lane, veh in rows})
            groups = {}
            for name, group in [('left', [v for lane, v in rows if lane == 4]), ('through_right', [v for lane, v in rows if lane != 4])]:
                locations = Counter(str(initial[v]['link_no']) if v in initial else 'not_in_initial_network' for v in group)
                missing = sum(n for lane,n in unresolved.items() if (int(lane)==4) == (name=='left'))
                groups[name] = dict(known_vehicle_ids=len(group), unresolved_vehicle_ids=missing,
                    actual_head_count=len(group)+missing, initial_links=dict(locations),
                    in_initial_support=sum(v in initial and initial[v]['link_no'] in support for v in group),
                    initially_on_head_link=sum(v in initial and initial[v]['link_no'] == 1210018302 for v in group))
            cases[arm].append(dict(start_sec=end-150, groups=groups))
    report = dict(cases=cases, source_pins=pins, fzp_scans=0, new_predictions=0,
        initial_support_links=sorted(support), future_inputs=False,
        limitations=['Tracks observed crossing vehicle identities, not a reconstructed future arrival process.',
                     'Permitted MER tail IDs remain unresolved; initial-location attribution uses known IDs only.',
                     'Initial support is not a complete future geographic boundary; side roads and connectors can contribute later.',
                     'No saturation rate, queue length or causal isolated-RM effect is inferred from these counts.'])
    out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps({a:[dict(start=r['start_sec'],groups={g:{k:v for k,v in d.items() if k!='initial_links'} for g,d in r['groups'].items()}) for r in rows] for a,rows in cases.items()}))


if __name__ == '__main__':
    main()
