"""Check the same upstream cut in two existing independent native pairs."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
B=Path('E:/VISSIM_analysis/20261011_vsl_response349')
R=Path('E:/VISSIM_analysis/20261012_ramp_plant355')
PINS={}


def read(path):
    path=Path(path);blob=path.read_bytes();PINS[str(path)]=hashlib.sha256(blob).hexdigest()
    return json.loads(gzip.decompress(blob) if path.suffix=='.gz' else blob)


def main():
    assert not (OUT/'independent_approach.json').exists()
    rows=[];absolute=[]
    for seed,arms,model_folder in [(67,('release','release_vsl90'),R/'seed67_spatial360'),(71,('rm','both'),R/'seed71_spatial')]:
        original=read(B/f'matched_seed{seed}_v3/matched_assessment.json')
        protocol=read(model_folder/'protocol.json')
        assert protocol['same_city_commands']
        if seed==67:
            assert protocol['same_rm'] and protocol['only_vsl_intervention']
        else:
            assert protocol['both_vs_rm_same_rm'] and tuple(arms)==('rm','both')
        assert protocol['start']==original['start'] and protocol['end']==original['end']
        results={}
        for arm in arms:
            snaps=read(model_folder/f'{arm}_snapshots.json')
            response=read(model_folder/f'{arm}_response.json.gz')
            native=original['physical31_snapshots'][arm]
            assert [s['time_sec'] for s in snaps]==[s['time_sec'] for s in native]
            assert max(abs(a-b) for a,b in zip(snaps[0]['n']['FW_E'],native[0]['actual']['n']['FW_E']))<1e-7
            paths=[Path(p) for p in original['source_pins'] if f'/{arm}/' in p.replace('\\','/') and Path(p).name.startswith('state_')]
            assert len(paths)==4
            states=[]
            for path in sorted(paths):
                states.append(read(path))
                assert PINS[str(path)]==original['source_pins'][str(path)]
            detpath=Path(states[0]['obs150']['detector_config']['path']);blob=detpath.read_bytes()
            PINS[str(detpath)]=hashlib.sha256(blob).hexdigest()
            assert all(s['obs150']['detector_config']['sha256']==PINS[str(detpath)] for s in states)
            dets=list(csv.DictReader(blob.decode('utf-8-sig').splitlines()))
            ids=[r['dcm_no'] for r in dets if r['boundary_ref']=='through:10481']
            assert len(ids)==3 and all(r['link']=='10613' and float(r['pos'])==1 for r in dets if r['dcm_no'] in ids)
            counts=[sum(s['obs150']['detectors_cum'][k] for k in ids) for s in states]
            for i,end in enumerate((150,300,450),1):
                flow=sum(r['accepted_total_veh'] for r in response['resource_allocations'] if r['kind']=='freeway_mainline_sending' and r['resource']=='FW_E:cell:18' and r['end_sec']<=protocol['start']+end+1e-8)
                m=snaps[i];a=native[i]['actual']
                row=dict(seed=seed,arm=arm,horizon=end,native_through18=counts[i]-counts[0],model_through18=flow,
                         native_approach_n=sum(a['n']['FW_E'][14:19]),model_approach_n=sum(m['n']['FW_E'][14:19]),
                         native_cell18_n=a['n']['FW_E'][18],model_cell18_n=m['n']['FW_E'][18],
                         native_cell18_v=a['speed']['FW_E'][18],model_cell18_v=m['speed']['FW_E'][18],
                         native_bottleneck_n=sum(a['n']['FW_E'][19:24]),model_bottleneck_n=sum(m['n']['FW_E'][19:24]))
                absolute.append(row)
                results[(arm,end)]=row
        for end in (150,300,450):
            base,control=results[(arms[0],end)],results[(arms[1],end)]
            rows.append(dict(seed=seed,horizon=end,**{k:control[k]-base[k] for k in base if k not in ('seed','arm','horizon')}))
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for p,h in PINS.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    report=dict(status='completed_existing_independent_approach_comparison',rows=rows,absolute=absolute,source_pins=PINS,
                new_forecasts=0,new_native=0,new_fzp_scans=0,production_edits=0,
                limitations=['Existing non-blind independent operating conditions; not new independent validation of a correction.',
                             'Native through detector is inside connector, while model flow is its upstream cell face; no claim of exact face equivalence.',
                             'VSL control footprints and starts differ across experiments; compare within each qualified pair, not raw levels across seeds.'])
    (OUT/'independent_approach.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
