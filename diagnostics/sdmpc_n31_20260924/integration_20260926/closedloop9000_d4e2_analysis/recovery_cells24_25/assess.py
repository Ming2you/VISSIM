"""Post-run checks for the bounded four-model recovery comparison (no fitting)."""
import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent; A=D.parent; I=A.parent; ROOT=I.parents[2]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

s=load(D/'summary.json'); assert s['new_rollouts']==48 and len(s['reused_predictions'])==40
assert s['selection']['selected']=='acc6'
rows=[r for r in s['rows'] if r['variant'] in s['comparison']]
index={(r['variant'],r['case'],r['arm']):r for r in rows}
records=load(I/'decision_response/capture.json')['records']
records += [dict(r,case='s53_late',cutoff=2670.1,reference='hold',truth=str(I/'heldout53_response_v2/observations'/r['arm']))
            for r in load(I/'heldout53_response_v2/capture.json')['records']]
record={(r['case'],r['arm']):r for r in records}
truth_cache={}; balances=[]; validations=[]; metrics=[]
for r in rows:
    path=Path(r['prediction']);assert sha(path)==r['prediction_sha256']
    with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
    rec=record[r['case'],r['arm']]; t0=rec['cutoff']; folder=Path(rec['truth'])
    if str(folder) not in truth_cache:
        with (folder/'cells_30s.csv').open(encoding='utf-8-sig',newline='') as f:
            truth_cache[str(folder)]={(round(float(z['time_s']),6),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
    actual=truth_cache[str(folder)]
    cells={(round(z['time_s'],6),z['cell']):z for z in pred['cells']}
    flows={(round(z['window_end_s'],6),z['cell']):z for z in pred['flows']}
    residual=0.
    for t in sorted({t for t,c in flows}):
        before=round(t-30,6)
        for c in range(31):
            q=flows[t,c]; prev=float(actual[t0,c]['n_veh']) if abs(before-t0)<1e-6 else cells[before,c]['n_veh']
            incoming=flows[t,c-1]['downstream_crossings'] if c else 0.
            expected=prev+incoming+q['source_admissions']+q['ramp_merges']-q['downstream_crossings']-q['off_departures']-q['terminal_exits']
            residual=max(residual,abs(cells[t,c]['n_veh']-expected))
    assert residual<1e-7,(r['variant'],r['case'],r['arm'],residual)
    # This does not reinterpret native unexplained disappearance as normal exit.
    balances.append(dict(variant=r['variant'],case=r['case'],arm=r['arm'],main_residual=residual,
        port_ramp_residual=r['conservation_max']))
    context='cell23' if r['variant'].startswith('combined_') else 'baseline'
    old=index[context,r['case'],r['arm']]
    for z in r['cell_metrics']:
        prior=next(x for x in old['cell_metrics'] if x['cell']==z['cell'])
        for kind in ('actual','predicted'):
            metrics.append(dict(variant=r['variant'],case=r['case'],arm=r['arm'],cell=z['cell'],kind=kind,
                mean_speed_kmh=z[kind]['mean_speed_kmh'],end_n_veh=z[kind]['end_n_veh'],
                downstream_veh=z[kind]['downstream_veh'],**z[kind]['events']))
        ae=z['actual']['events']; pe=z['predicted']['events']; be=prior['predicted']['events']
        if r['case'] in ('s47_late','s53_late') and r['arm'].startswith('release'):
            too_fast=(ae['low_speed_sample_sec']>=90 and pe['low_speed_sample_sec']<ae['low_speed_sample_sec']-90
                      and pe['low_speed_sample_sec']<be['low_speed_sample_sec']-60)
            validations.append(dict(variant=r['variant'],case=r['case'],arm=r['arm'],cell=z['cell'],
                falsely_cleared_sustained_congestion=too_fast))
with (D/'cell_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(metrics[0]));writer.writeheader();writer.writerows(metrics)

# Keep both standalone configurations reviewable; the production config stays pinned.
manifests={}
for name in ('recovery_acc6','combined_acc6'):
    reference=load(I/'heldout53_response_v2/candidate_config.json')
    reference['freeway']['state_response']=load(D/name/'state_response.json')
    restored=copy.deepcopy(reference)
    nominal=load(I/'heldout53_response_v2/candidate_config.json')
    for c in (23,24,25):
        restored['freeway']['state_response']['FW_E']['cell_overrides'][str(c)]=nominal['freeway']['state_response']['FW_E']['cell_overrides'][str(c)]
    assert restored==nominal
    for c in (24,25):
        spec=reference['freeway']['state_response']['FW_E']['cell_overrides'][str(c)]
        assert spec['recovery_relaxation']=={'acceleration_sec':6.}
    refpath=D/name/'reference_config.json';save(refpath,reference)
    manifest=load(A/'local_merge_cell23/candidate_manifest.json')
    manifest['sources']['reference_config']=dict(path=refpath.relative_to(ROOT).as_posix(),sha256=sha(refpath))
    manifest['qualification']='Experimental grouped24/25 recovery calibration; no production adoption or general gain qualification.'
    mpath=D/name/'manifest.json';save(mpath,manifest)
    full=load(A/'local_merge_cell23/candidate_full_config.json')
    full['freeway']['lane_plant']=mpath.relative_to(ROOT).as_posix()
    fpath=D/name/'full_config.json';save(fpath,full)
    manifests[name]=dict(reference=str(refpath),manifest=str(mpath),full=str(fpath),sha256=sha(fpath))

assert sha(I/'selected/config_n31_v2.json')=='b86534bab6e9360abf5d79c5b7a0edcc9867242af4eb50b009280978150a9347'
assert sha(I/'selected/network/native_seed29.inpx')=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
assert Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP').exists()
save(D/'assessment.json',dict(new_calibration_validation_rollouts=48,reused_predictions=40,
    main_conservation_max=max(r['main_residual'] for r in balances),
    port_ramp_conservation_max=max(r['port_ramp_residual'] for r in balances),
    balances=balances,release_persistence_checks=validations,
    premature_clearing_failures=[r for r in validations if r['falsely_cleared_sustained_congestion']],
    manifests=manifests,selected_config_unchanged=True,STOP_preserved=True,
    future_measured_boundaries_used_for_forecast=False,native_runs=0,push=False,
    optimizer_iterations=0,adopted=False,gain_qualified=False,
    status='RECOVERY_BIAS_PARTLY_REDUCED_CONTROL_RANK_NOT_IMPROVED',
    limitations=['Threshold crossings are30s sample diagnostics; next30 cell-mean trend is not individual acceleration.',
        'Cell21/22 and25 own conditional dynamics remain biased; propagated cell23 error is not the sole explanation.',
        'Seed47 hold_vsl90 four unexplained losses excluded from clean rankings.',
        'Component costs exclude urban residence and outside queues; report coupled Omega separately.']))
print(json.dumps(dict(main_residual=max(r['main_residual'] for r in balances),
    premature_clearing_failures=sum(r['falsely_cleared_sustained_congestion'] for r in validations),
    configuration_files=list(manifests)),ensure_ascii=False))
