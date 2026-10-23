"""Compare the observed18->19 exit with accepted model flows, using caches."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math

OUT = Path(__file__).resolve().parent
HERE = OUT.parent
PINS = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def main():
    assert not (OUT/'approach_flux.json').exists()
    current = read(OUT/'summary.json')
    folders = {
        'hold': Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29'),
        'single90': Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/vsl90/decisions_sdmpc31_g_2250_vsl90_s29'),
        'selected': Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29/selected/decisions_sdmpc31_g_2250_selected_s29'),
    }
    cases = {}
    for case, folder in folders.items():
        states = [read(folder/f'state_{t:06d}.json') for t in (2250,2400,2550,2700)]
        pin = states[0]['obs150']['detector_config']
        detector = Path(pin['path'])
        blob = detector.read_bytes()
        PINS[str(detector)] = hashlib.sha256(blob).hexdigest()
        assert PINS[str(detector)] == pin['sha256'] == '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc'
        detectors = list(csv.DictReader(blob.decode('utf-8-sig').splitlines()))
        counts, slabs = {}, {}
        for ref, link, lanes in [('through:10481',10613,3), ('off_entry:10481',10481,2)]:
            rows = [r for r in detectors if r['boundary_ref'] == ref]
            assert len(rows) == lanes and {int(r['lane']) for r in rows} == set(range(1,lanes+1))
            assert all(int(r['link']) == link and float(r['pos']) == 1 for r in rows)
            keys = [r['dcm_no'] for r in rows]
            cum = [sum(s['obs150']['detectors_cum'][key] for key in keys) for s in states]
            counts[ref] = [b-a for a,b in zip(cum,cum[1:])]
            assert counts[ref] == [sum(s['obs150']['detectors'][key] for key in keys) for s in states[1:]]
            slabs[ref] = [sum(int(v['link_no']) == link and 0 <= float(v['position_m']) < 1 for v in s['vehicle_records']['records']) for s in states]
        response = read(HERE/'matched_off2250_v3'/f'{case}_response.json.gz')
        initial_n = next(x for x in read(HERE/'matched_off2250_v3/summary.json')['results'] if x['name']==case)['snapshots'][0]['n']['FW_E']
        model = {}
        for end in (150,300,450):
            values = {'incoming13':0.,'outgoing18':0.,'off10481':0.}
            for a in response['resource_allocations']:
                if a['end_sec'] > 2250+end+1e-8:
                    continue
                key = ({('freeway_mainline_sending','FW_E:cell:13'):'incoming13',
                        ('freeway_mainline_sending','FW_E:cell:18'):'outgoing18',
                        ('freeway_offramp_sending','10481'):'off10481'}).get((a['kind'],a['resource']))
                if key:
                    values[key] += a['accepted_total_veh']
            model[end] = values
        points = [x for x in current['absolute_operating_points'] if x['case']==case and x['region']=='approach14_18']
        assert len(points)==4
        native_n = [x['native_n'] for x in points]
        for i,end in enumerate((150,300,450),1):
            m=model[end]
            assert abs(points[i]['model_n']-sum(initial_n[14:19])-m['incoming13']+m['outgoing18']+m['off10481']) < 1e-7
        cases[case] = {'detector_counts150':counts, 'first_meter_storage':slabs, 'native_region_n':native_n, 'model_cumulative':model}
    rows=[]
    for case in ('single90','selected'):
        for i,end in enumerate((150,300,450),1):
            a,b=cases['hold'],cases[case]
            row={'case':case,'horizon_sec':end}
            for key,ref in [('outgoing18','through:10481'),('off10481','off_entry:10481')]:
                observed=sum(b['detector_counts150'][ref][:i])-sum(a['detector_counts150'][ref][:i])
                storage=(b['first_meter_storage'][ref][i]-b['first_meter_storage'][ref][0])-(a['first_meter_storage'][ref][i]-a['first_meter_storage'][ref][0])
                row[key+'_detector_delta']=observed
                row[key+'_first_meter_storage_delta']=storage
                row[key+'_boundary_delta_if_no_loss_in_first_meter']=observed+storage
                row[key+'_model_delta']=b['model_cumulative'][end][key]-a['model_cumulative'][end][key]
            row['model_incoming13_delta']=b['model_cumulative'][end]['incoming13']-a['model_cumulative'][end]['incoming13']
            row['native_region_stock_delta']=b['native_region_n'][i]-a['native_region_n'][i]
            row['native_incoming13_plus_unknown_sources_minus_sinks_remainder']=row['native_region_stock_delta']+row['outgoing18_boundary_delta_if_no_loss_in_first_meter']+row['off10481_boundary_delta_if_no_loss_in_first_meter']
            rows.append(row)
    for path,digest in PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    report=dict(status='complete_new_approach_cut_comparison', cases=cases, rows=rows, source_pins=PINS,
                new_native=0,new_forecasts=0,new_fzp_scans=0,production_edits=0,
                limitation='Detector is1m inside downstream connector. First-meter stock correction is explicit, assumes no unobserved deletion/birth in that1m; raw detector counts remain separate. Upstream13 inflow remainder is not independently observed.')
    (OUT/'approach_flux.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'rows':rows,'pins':len(PINS)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
