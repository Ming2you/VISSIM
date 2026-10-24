"""Audit saved source observations; no FZP scan, fit, or model mutation."""
from pathlib import Path
from types import SimpleNamespace
from dataclasses import asdict
import hashlib
import json
import pickle
import xml.etree.ElementTree as ET

from evaluation.controllers import obs150_contract as oc, obs150_lane as ol
from evaluation.controllers.source_boundary import road_schedules

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = A.parents[3]
ARMS = {
    'hold': Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29'),
    'city': Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29'),
}
PINS = {}


def pin(path):
    path = Path(path)
    PINS[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def stats(rows):
    return {'vehicles': len(rows), 'stopped_le5': sum(r[4] <= 5 for r in rows),
            'mean_kph': sum(r[4] for r in rows) / len(rows) if rows else None}


def main():
    fixture = pin(A / 'citysplit287/forecast2400/initial.pickle')
    cfg, initial_state, initial_forecast = pickle.loads(fixture.read_bytes())
    schedules = road_schedules(cfg.network.native_input_schedule)
    context = SimpleNamespace(source_refs={r: 'source:' + r for r in oc.ROADS}, source_schedule=schedules)
    results = {}
    xml_sources = {}
    for arm, directory in ARMS.items():
        records = []
        for end in (2400, 2550, 2700, 2850):
            snapshot = json.loads(pin(directory / f'state_{end:06}.json').read_bytes())
            obs = snapshot['obs150']
            all_rows, _ = oc.read_detector_csv(pin(obs['detector_config']['path']), obs['detector_config']['sha256'])
            rows = [r for r in all_rows if r.role == 'source']
            frames = {}
            for name, at in (('current', end), ('previous', end - 150)):
                meta = obs['frames'][name]
                frames[name] = oc.load_frame(pin(oc.resolve(obs, meta['path'])), meta['sha256'], at)
            err = oc.load_err_chunk(pin(oc.resolve(obs, obs['err']['chunk'])), obs['err']['chunk_sha256'])
            terms = oc.evaluate_boundaries(obs, rows, frames['current'], frames['previous'], err)
            source = ol.source_boundary(obs, context, terms)
            if end == 2400:
                net = ET.parse(pin(snapshot['network_path'])).getroot()
                xml_sources[arm] = {
                    n: dict(net.find(f".//vehicleInput[@no='{n}']").attrib,
                            intervals=[dict(v.attrib) for v in net.findall(f".//vehicleInput[@no='{n}']//timeIntervalVehVolume")])
                    for n in ('1098', '1099')
                }
                assert net.find('simulation').get('randSeed') == '29'
                for no, road in cfg.network.native_input_schedule['freeway_link_by_input'].items():
                    intervals = xml_sources[arm][no]['intervals']
                    assert len(intervals) == len(schedules[road]) > 0
                    for interval, declared in zip(intervals, schedules[road]):
                        assert float(interval['timeInt'].split()[1]) / 1000 == declared.start_sec
                        assert abs(float(interval['volume']) - declared.vph) < 1e-8
                        assert interval['volType'] == 'STOCHASTIC'
            record = {'time_sec': end, 'source': source, 'roads': {}}
            for road in oc.ROADS:
                rs = [r for r in rows if r.ref == road]
                link = rs[0].link
                t = terms['source:' + road]
                assert t.orientation == 'down' and all(r.pos == 40 for r in rs)
                assert obs['source_cumulative_vehs'][road] == sum(obs['detectors_cum'][str(r.dcm_no)] for r in rs)
                if records:
                    prev = records[-1]
                    assert source[road]['admitted_cum'] - prev['source'][road]['admitted_cum'] == t.cross
                record['roads'][road] = {
                    'physical_source_link': link,
                    'raw_station_cumulative': obs['source_cumulative_vehs'][road],
                    'identity': t.as_dict(),
                    'entry_40m_by_lane': {
                        str(r.lane): stats([v for v in frames['current']['vehicles']
                                          if v[1] == link and v[2] == r.lane and 0 <= v[3] < 40])
                        for r in rs
                    },
                    'entry_200m': stats([v for v in frames['current']['vehicles'] if v[1] == link and 0 <= v[3] < 200]),
                }
            records.append(record)
        results[arm] = records
    assert xml_sources['hold'] == xml_sources['city']
    assert results['hold'][0]['source'] == results['city'][0]['source']
    assert results['hold'][0]['source'] == cfg.network.freeway_source_boundary_observed['by_road']
    deltas = {}
    for road in oc.ROADS:
        deltas[road] = {}
        for arm, records in results.items():
            counts = [r['source'][road]['admitted_window'] for r in records[1:]]
            stations = [r['roads'][road]['identity']['vehs'] for r in records[1:]]
            expected = [d.freeway_mainline[road] * 150 / 3600 for d in initial_forecast[:3]]
            deltas[road][arm] = {'corrected_admissions_150s': counts, 'raw_station_passages_150s': stations,
                                 'corrected_admissions_450s': sum(counts), 'forecast_admissions_450s': sum(expected)}
        deltas[road]['city_minus_hold_corrected_450s'] = sum(r['source'][road]['admitted_window'] for r in results['city'][1:]) - sum(r['source'][road]['admitted_window'] for r in results['hold'][1:])
    for module in (oc, ol):
        pin(module.__file__)
    pin(__file__)
    report = {'status': 'complete_saved_source_identity_audit', 'production_changes': 0, 'fzp_scans': 0,
              'native_runs': 0, 'new_forecasts': 0, 'goal_complete': False,
              'definition': 'station passages at 40m plus source-prefix stock change plus removals',
              'backlog_caveat': 'Observer backlog is desired schedule integral minus corrected admissions, not measured uninserted vehicles for stochastic offered demand.',
              'scope': 'RM-hold baseline versus city-only changed commands; neither is a no-control full-run arm',
              'source_schedule': {r: [asdict(x) for x in s] for r, s in schedules.items()},
              'native_source_inputs': xml_sources, 'records': results, 'comparison': deltas,
              'future_source_diagnostic_only': True, 'source_pins': PINS}
    (HERE / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(deltas, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
