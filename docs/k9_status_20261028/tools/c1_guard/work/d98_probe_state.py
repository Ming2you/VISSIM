# Read-only, data-after look (D-K9-98 definition drafting): compare OFF vs Omega captured
# bootstrap (detector mapping + state_json) for the 29 support connectors at the already-seen
# C1 probe state v3c3-s31 T=1500. No writes outside guard/work.
import pickle, sys, json, hashlib, collections
TREE = 'D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_5cdc6eb1'
sys.path.insert(0, TREE); sys.path.insert(0, TREE + '/vendor/NumSim-mine')
base = 'D:/VISSIM-merge/k8_gate_trees/c1/out/probe/plant/sa/cap/%s/TL3/001500/SAF/template.pickle'
out = {'inputs': {}}
T = {}
for a in ('c1poff', 'c1pomega'):
    b = open(base % a, 'rb').read()
    out['inputs'][a] = hashlib.sha256(b).hexdigest()
    T[a] = pickle.loads(b)
om = T['c1pomega']['bootstrap']['detector_mapping']
of = T['c1poff']['bootstrap']['detector_mapping']
sj_o = T['c1pomega']['bootstrap']['state_json']; sj_f = T['c1poff']['bootstrap']['state_json']
out['state_json_top_keys'] = sorted(sj_f)[:60]
vr = sj_f.get('vehicle_records')
out['vehicle_records_type'] = type(vr).__name__
if isinstance(vr, dict):
    out['vehicle_records_keys'] = sorted(vr)[:20]
prov_o = om['physical_support_repair_provenance'].get('links', {})
prov_f = of['physical_support_repair_provenance'].get('links', {})
added = sorted(set(prov_o) - set(prov_f), key=int)
out['n_links_prov_omega'] = len(prov_o); out['n_links_prov_off'] = len(prov_f); out['n_added'] = len(added)
recs = (vr or {}).get('records', []) if isinstance(vr, dict) else []
cnt = collections.Counter(str(r.get('link_no')) for r in recs)
out['n_records'] = len(recs)
lc_f = sj_f.get('local_observation', {}).get('link_counts', {})
lc_o = sj_o.get('local_observation', {}).get('link_counts', {})
rows = []
for c in added:
    p = prov_o[c]
    rows.append([c, p['target'], p['snapshot_vehicles'], p['restored_count_channel'], p['previous_origins'],
                 of.get('link_to_origins', {}).get(c), of.get('link_to_movements', {}).get(c),
                 of.get('transit_storage_projection', {}).get(c), c in set(map(str, of.get('observable_links', []))),
                 lc_f.get(c), lc_o.get(c), cnt.get(c, 0)])
out['cols'] = ['conn', 'omega_target', 'snapshot_veh', 'restored_channel', 'prev_origins', 'off_l2o', 'off_l2m',
               'off_transit', 'off_observable', 'off_state_link_count', 'omega_state_link_count', 'records']
out['rows'] = rows
out['nonzero_rows'] = [r for r in rows if r[2] or r[9] or r[10] or r[11]]
print(json.dumps(out, ensure_ascii=False, default=str))
