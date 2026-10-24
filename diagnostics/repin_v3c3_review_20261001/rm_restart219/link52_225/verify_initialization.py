"""Verify physical52 initialization from saved native observations; no forecasts."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'

def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    from evaluation.controllers import obs150_contract as oc
    protocol = read(HERE / 'protocol.json')
    for p, h in protocol['source_sha256'].items():
        assert sha(ROOT / p) == h, p
    assert sha(Path(protocol['STOP']['path'])) == protocol['STOP']['sha256']
    old = read(I / 'closedloop_recorded2700_init_rm225_link52/audit.json')
    new = read(I / 'closedloop_recorded2700_init_rm225_candidate52/audit.json')
    rt0 = read(I / 'closedloop_recorded2700_init_rm225_link52/runtime.json')
    rt1 = read(I / 'closedloop_recorded2700_init_rm225_candidate52/runtime.json')
    a, b = old['projection'], new['projection']
    pa = a['projection_diagnostics']['physical_stock_assignment_by_link']
    pb = b['projection_diagnostics']['physical_stock_assignment_by_link']
    changed_links = [k for k in pa if pa[k] != pb[k]]
    assert changed_links == ['52'], changed_links
    for k in pa:
        assert abs(math.fsum(pa[k].values()) - math.fsum(pb[k].values())) < 1e-9, k
    assert pb['52'] == {'storage:SC1005_to_SC1004': 10.,
        'movement:SC1004_E_SC1005_to_W': 17.,
        'movement:SC1004_E_SC1005_to_N_SC1003': 0.,
        'movement:SC1004_E_SC1005_to_S': 0.}
    source = 'SC1005_to_SC1004'
    for k in ('urban_link_storage_occupancy', 'ramp_queue', 'boundary_queue',
              'link_counts', 'queue_count_by_link', 'storage_count_by_link'):
        assert a[k] == b[k], k
    assert a['urban_link_storage_occupancy'][source] == 19.5
    assert a['urban_link_storage_occupancy']['SC107_to_SC1004'] == 6.
    changes = []
    for name, before in old['runtime_movement_capacity'].items():
        after = new['runtime_movement_capacity'][name]
        fields = [k for k in before if before[k] != after[k]]
        if fields:
            assert name.startswith('SC1004_E_SC1005_to_') and set(fields) <= {'beta','queue_veh'}, (name,fields)
            changes.append(dict(movement=name, fields=fields, old=before, new=after))
    for k in ('posthead_receiving', 'movement_capacity_veh_h', 'head_resources',
              'gate_future_travel', 'gate_entry_capacity_veh_h'):
        assert rt0[k] == rt1[k], k
    for origin in old['storage_release_buffer']:
        assert abs(sum(old['storage_release_buffer'][origin].values()) -
                   sum(new['storage_release_buffer'][origin].values())) < 1e-9, origin
        if origin != source:
            assert old['storage_release_buffer'][origin] == new['storage_release_buffer'][origin], origin
    releases = new['storage_release_buffer'][source]
    tags = rt1['gate_initial_route_tags'][source]
    tagged = Counter()
    for sec, row in tags.items():
        assert sum(row.values()) <= releases[sec]
        tagged.update(row)
    assert tagged == {'SC1004_E_SC1005_to_W': 9., 'SC1004_E_SC1005_to_N_SC1003': 1.}
    assert releases['2715'] == 9.5
    coverage = []
    prior = read(ROOT / 'diagnostics/repin_v3c3_review_20261001/corrected_s47_neighbors/arrival10681_native_paths.json')
    for path, digest in prior['input_sha256'].items():
        if not path.endswith('.json'): continue
        p = Path(path)
        assert sha(p) == digest, path
        raw = read(p)
        bundle = oc.load_bundle(raw)
        rows = [v for v in bundle.frame_end['vehicles'] if v[1] == 52]
        unknown = [v[0] for v in rows if v[3] >= 11.07016755143615 and
                   (v[6] != 1123 or v[7] not in (1,2,3) or v[8] != 'STATIC')]
        assert not unknown, (path, unknown)
        coverage.append(dict(path=path, sha256=digest, sim_sec=raw['sim_sec'],
            vehicles=len(rows), routes=dict(Counter(str(v[6:9]) for v in rows)),
            unresolved_after_choice_ids=unknown))
    result = dict(status='PASS', changed_physical_links=changed_links,
        initial_queue_before=pa['52'], initial_queue_after=pb['52'],
        physical52_vehicles=27., initial_source_total_vehicles=36.5,
        upstream_generic_reservation=9.5, independent_SC107_storage=6.,
        known_moving_destinations=dict(tagged), release_buffer=releases,
        changes=changes, route_coverage=coverage, capacity_and_ramps_unchanged=True,
        forecasts=0, new_native=0, FZP=0,
        limits=['Primary52 origin corrected only; SC107 future branch prior is unchanged.',
                'Existing physical ETA rule retained; future observation frames only check route coverage.',
                'Does not establish correct 150/450-second arrivals or RM/VSL gain.'])
    (HERE / 'initialization_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','changed_physical_links','known_moving_destinations','capacity_and_ramps_unchanged')}))

if __name__ == '__main__': main()
