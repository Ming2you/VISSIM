"""Bounded transfer check of upstream L1 against already completed native cases.

No fitting, optimizer, future-state input, native launch or production adoption.
Uses the canonical component and previously pinned primitive prediction inputs.
"""
import copy
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
I = D.parent
ROOT = I.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.freeway_fd import literature_vsl_parameters
from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, d): Path(p).write_text(json.dumps(d, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')

def main():
    assert not (D/'l1_summary.json').exists(), 'Preserve completed results'
    old = I/'closedloop9000_d4e2_analysis/local_merge_cell23'
    reference = load(old/'candidate_reference_config.json')
    original_spec = copy.deepcopy(reference['freeway']['vsl_fd_response']['FW_E'])
    reference['freeway']['vsl_fd_response']['FW_E'] = dict(law='carlson', A=.94, E=1.44, alpha=0.)
    restored = copy.deepcopy(reference)
    restored['freeway']['vsl_fd_response']['FW_E'] = original_spec
    assert restored == load(old/'candidate_reference_config.json')
    refpath = D/'l1_reference_config.json'
    save(refpath, reference)
    manifest = load(old/'candidate_manifest.json')
    manifest['sources']['reference_config'] = dict(path=refpath.relative_to(ROOT).as_posix(), sha256=sha(refpath))
    manifest['qualification'] = 'Upstream L1 transfer candidate on selected 64cf network; NOT adopted. No native gain claim.'
    mpath = D/'l1_manifest.json'
    save(mpath, manifest)
    full = load(old/'candidate_full_config.json')
    full['freeway']['lane_plant'] = mpath.relative_to(ROOT).as_posix()
    save(D/'l1_full_config.json', full)
    assert full['config_overrides']['freeway_follower']['vsl_set'] == [50.,60.,70.,80.,90.,100.,110.]
    records = load(I/'decision_response/capture.json')['records']
    records += [dict(r, case='s53_late', cutoff=2670.1, reference='hold',
                     truth=str(I/'heldout53_response_v2/observations'/r['arm']))
                for r in load(I/'heldout53_response_v2/capture.json')['records']]
    assert len(records) == 20
    baseline = {(r['case'],r['arm']):r for r in load(old/'summary.json')['rows'] if r['variant']=='nu0.25_delta2'}
    quality = {(r['case'],r['arm']):r['clean_component_boundary'] for r in load(old/'native_boundary_quality.json')}
    protocol = dict(upstream_commit=load(D/'source_manifest.json')['ref'], old_spec=original_spec,
        new_spec=reference['freeway']['vsl_fd_response']['FW_E'], max_rollouts=40,
        scope='East31 plus east8 physical ramp/off connectors, NOT full Omega.',
        cases=[dict(case=r['case'],arm=r['arm']) for r in records],
        fitting=False, future_observations=False, optimizer_iterations=0, native_runs=0,
        decision='No automatic adoption. Compare cost-direction/ranking and physical discharge; no repeat parameter grid.',
        limitations=['Upstream different network/compliance; L1 formally rejected by upstream goodness-of-fit.',
                    '50/60/70 retained by user contract but outside upstream calibration range.',
                    'Previously inspected seeds, not pristine holdout; s47 VSL excluded from clean ranking.'],
        pins={str(p):sha(p) for p in [old/'candidate_manifest.json',old/'candidate_reference_config.json',
             old/'summary.json',old/'native_boundary_quality.json',I/'decision_response/capture.json',
             I/'heldout53_response_v2/capture.json',D/'source_manifest.json',Path(__file__)]})
    save(D/'l1_protocol_v2.json', protocol)
    models={'local':lpr.load_sources(old/'candidate_manifest.json')['component'],
            'l1':lpr.load_sources(mpath)['component']}
    predictions={}; rows=[]; count=0; started=time.perf_counter()
    for name,model in models.items():
        for r in records:
            assert count < 40
            args,kwargs=read_primitive_capture(r['input'],r['sha256'])
            then=time.perf_counter(); pred=model.rollout(*args,**kwargs); wall=time.perf_counter()-then; count+=1
            pred=json.loads(json.dumps(pred,allow_nan=False))
            key=(r['case'],r['arm']); previous=old/'nu0.25_delta2'/f'{key[0]}_{key[1]}.json.gz'
            with gzip.open(previous,'rt',encoding='utf-8') as f: saved=json.load(f)
            if name=='local':
                assert all(pred[k]==saved[k] for k in ('cells','flows','ports','ramps')), key
            target=D/(name+'_v2'); target.mkdir(exist_ok=True)
            with gzip.open(target/f'{key[0]}_{key[1]}.json.gz','wt',encoding='utf-8') as f: json.dump(pred,f,allow_nan=False)
            times=[round(r['cutoff']+dt,6) for dt in range(0,451,30)]
            cells={(round(x['time_s'],6),int(x['cell'])):x for x in pred['cells']}
            flows={(round(x['window_end_s'],6),int(x['cell'])):x for x in pred['flows']}
            # Native initial stock only; later observations never enter prediction.
            with (Path(r['truth'])/'cells_30s.csv').open(encoding='utf-8-sig',newline='') as f:
                initial_cells={int(x['cell']):float(x['n_veh']) for x in csv.DictReader(f)
                    if x['road']=='FW_E' and round(float(x['time_s']),6)==times[0]}
            assert len(initial_cells)==31
            for c,n0 in initial_cells.items(): cells[times[0],c]={'n_veh':n0}
            n={t:sum(cells[t,c]['n_veh'] for c in range(31)) for t in times}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)
                    +sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            def integral(d): return sum((d[a]+d[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(o) for o,v in model.offramps.items() if v['road']=='FW_E'}
            port_file=Path(r['truth'])/'ports_30s.csv'
            with port_file.open(encoding='utf-8-sig',newline='') as f:
                initial={x['connector']:float(x['end_n_veh']) for x in csv.DictReader(f)
                         if round(float(x['window_end_s']),6)==times[0] and x['connector'] in ids}
            assert initial.keys()==ids
            port[times[0]]=sum(initial.values())
            costs=dict(main=integral(n),ports=integral(port)); costs['total']=sum(costs.values())
            if name=='local': assert abs(costs['total']-baseline[key]['costs']['predicted']['total'])<1e-9
            residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
            for t in times[1:]:
                for c in range(31):
                    q=flows[t,c]; incoming=flows[t,c-1]['downstream_crossings'] if c else 0.
                    expected=cells[round(t-30,6),c]['n_veh']+incoming+q['source_admissions']+q['ramp_merges']-q['downstream_crossings']-q['off_departures']-q['terminal_exits']
                    residual=max(residual,abs(expected-cells[t,c]['n_veh']))
            assert residual < 1e-7
            row=dict(variant=name,case=key[0],arm=key[1],reference=r['reference'],costs=costs,
                actual=baseline[key]['costs']['actual'],clean_boundary=quality[key],wall_sec=wall,
                conservation_max=residual,merge=sum(x['accepted_merge_veh'] for x in pred['ramps']),
                off=sum(x['off_departures'] for x in pred['flows']),terminal=sum(x['terminal_exits'] for x in pred['flows']),
                cell12_speed=sum(cells[t,12]['v_kmh'] for t in times[1:])/15,
                cell18_speed=sum(cells[t,18]['v_kmh'] for t in times[1:])/15,
                arrays_equal_local=all(pred[k]==saved[k] for k in ('cells','flows','ports','ramps')))
            rows.append(row); print(json.dumps({k:row[k] for k in ('variant','case','arm','costs','wall_sec')}),flush=True)
    choices=[]
    for name in models:
        for case in sorted({r['case'] for r in records}):
            group=[r for r in rows if r['variant']==name and r['case']==case]
            ref=next(r for r in group if r['arm']==r['reference'])
            for r in group:
                r['predicted_delta']=r['costs']['total']-ref['costs']['total']
                r['actual_delta']=r['actual']['total']-ref['actual']['total']
            clean=[r for r in group if r['clean_boundary']]
            selected=min(clean,key=lambda r:r['costs']['total']); actual=min(clean,key=lambda r:r['actual']['total'])
            choices.append(dict(variant=name,case=case,selected=selected['arm'],actual_best=actual['arm'],
                regret=selected['actual']['total']-actual['actual']['total']))
    save(D/'l1_summary.json',dict(rows=rows,choices=choices,rollouts=count,wall_sec=time.perf_counter()-started,
        baseline_exact_cases=20,native_runs=0,optimizer_iterations=0,fitted_parameters=0,adopted=False))

if __name__=='__main__': main()
