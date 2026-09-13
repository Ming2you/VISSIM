"""Four binary-seek physical snapshots, kept separate from train-only fit."""
from pathlib import Path
from collections import Counter
import hashlib,json,time
from diagnostics.probe_e8_lane_receiving import IndexedFzp
ROOT=Path(__file__).resolve().parents[1]


def main():
    start=time.monotonic();calibration=json.loads((ROOT/'diagnostics/sc1004_resource_service_calibration.json').read_text())
    spec=json.loads((ROOT/'diagnostics/route_choice_corridor_ver2.json').read_text());source=ROOT/calibration['original_fzp']['path']
    stat=source.stat();proof=calibration['original_fzp']
    if (stat.st_size,stat.st_mtime_ns)!=(proof['bytes'],proof['mtime_ns']):raise ValueError('Original source changed')
    reader=IndexedFzp(source,max_bytes=4*1024*1024);rows=[]
    try:
        for second in (900,1350,2700,3150):
            values=reader.snapshot(second);counts=Counter(str(v[0]) for v in values.values())
            selected=[{'vehicle_id':no,'link':str(v[0]),'lane':v[1],'position_m':v[2],'speed_kph':v[3]} for no,v in values.items() if str(v[0]) in spec['prefix_links']]
            alignment=None
            if second in (900,2700):
                comfile=ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/decisions_codex_area_observed_nc_s13_20260910'/('state_000900.json' if second==900 else 'anchor_002700.json')
                raw=json.loads(comfile.read_text(encoding='utf-8-sig'));com={v['veh_no']:v for v in raw['vehicle_records']['records']}
                paired=[v for v in selected if v['vehicle_id'] in com]
                alignment={'com_path':str(comfile.relative_to(ROOT)),'com_sha256':hashlib.sha256(comfile.read_bytes()).hexdigest(),
                    'COM_whole_network_n_veh':len(com),'FZP_only_ids':sorted(values.keys()-com.keys()),'COM_only_ids':sorted(com.keys()-values.keys()),
                    'prefix_ids_match':{v['vehicle_id'] for v in selected}=={no for no,v in com.items() if str(v['link_no']) in spec['prefix_links']},
                    'prefix_common_max_position_difference_m':max((abs(v['position_m']-com[v['vehicle_id']]['position_m']) for v in paired),default=0.),
                    'prefix_common_max_speed_difference_kph':max((abs(v['speed_kph']-com[v['vehicle_id']]['speed_kph']) for v in paired),default=0.)}
            rows.append({'second':second,'whole_network_n_veh':len(values),'prefix_storage':spec['prefix_storage'],'paused_COM_alignment':alignment,
                'prefix_count_veh':len(selected),'prefix_stopped_le5_veh':sum(v['speed_kph']<=5 for v in selected),
                'prefix_count_by_physical_link':{k:counts[k] for k in spec['prefix_links']},'prefix_physical_records':selected})
        reads=reader.bytes_read
    finally:reader.handle.close()
    # Verify precisely the sampled source bytes again; no whole-file rescan.
    with source.open('rb') as stream:
        for second,pin in reader.selected.items():
            stream.seek(pin['first_byte_offset']);digest=hashlib.sha256()
            while row:=stream.readline():
                if float(row.split(b';',1)[0])!=float(second):break
                digest.update(row)
            if digest.hexdigest()!=pin['selected_raw_rows_sha256']:raise ValueError('Sampled snapshot changed')
    result={'schema':'sc1004-resource-physical-holdout/v1','original_fzp':proof,
        'source_bytes_read_including_binary_seeks':reads,'snapshot_byte_provenance':reader.selected,'snapshots':rows,
        'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'elapsed_sec':time.monotonic()-start,
        'scope':'Same seed13 native NC physical snapshots, no route allocation or new fit. At1350/3150 these are heldout outcomes.',
        'limits':'FZP and paused COM populations can differ at an identical timestamp; the initial prefix IDs and rounded positions/speeds are explicitly crosschecked. The paired model uses matching SG2 but not all other native signal clocks; stock discrepancy is descriptive, not an isolated calibration error.'}
    (ROOT/'diagnostics/sc1004_resource_service_physical_holdout.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'bytes_read':reads,'elapsed_sec':result['elapsed_sec'],'snapshots':[{k:v for k,v in x.items() if k!='prefix_physical_records'} for x in rows]},indent=2))


if __name__=='__main__':main()
