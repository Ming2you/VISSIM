"""Build reviewable pinned paths/repairs; never change runtime modules."""
from pathlib import Path
import json
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]


def main():
    audit = json.loads((ROOT / 'diagnostics/dynamic_area_route_evidence.json').read_text(encoding='utf-8'))
    old = json.loads((ROOT / 'diagnostics/physical_movement_routes_ver2.json').read_text(encoding='utf-8'))
    definitions = {
        'SC1004_N_SC1003_to_E_SC107': (['46', '10627', '56', '10621'], ['1125:3', '1129:1']),
        'SC1004_W_to_E_SC107': (['71', '10634', '56', '10621'], ['1138:2', '1129:1']),
        'SC1004_offE_to_E_SC107': (['10643', '126', '10641', '71', '10634', '56', '10621'], ['1126:2', '1129:1']),
        'SC1004_offW_to_E_SC107': (['10638', '70', '10776', '126', '10641', '71', '10634', '56', '10621'], ['1133:2', '1140:2', '1129:1']),
    }
    by_movement = {}
    for name, (path, refs) in definitions.items():
        spec = audit['model_specs'][name]
        by_movement[name] = {'path': path, 'native_routes': refs,
            'expected_spec': {key: spec[key] for key in ('signal', 'origin', 'approach', 'turn', 'receiving_link', 'kind')},
            'rationale': 'The actual SC1004 east exit continues along native bypass 10621 to the distinct SC107 receiver.',
            'timing_assumption': 'Accepted model service aggregates this physical path travel; native identities prove membership, not individual vehicle routing or travel time.'}
    repairs = []
    for name, spec in audit['model_specs'].items():
        if spec['turn'] != 'u_turn':
            continue
        sc1004 = spec['signal'] == 'SC1004'
        by_turn = {'right': '1123:1', 'through': '1123:2', 'left': '1123:3'} if sc1004 else {
            'left': '1061:1', 'through': '1061:2', 'right': '1061:3'}
        keep = {other: by_turn[row['turn']] for other, row in audit['model_specs'].items()
                if row['origin'] == spec['origin'] and row['signal'] == spec['signal'] and other != name}
        repairs.append({'remove_movement': name,
            'expected_removed_spec': {key: spec[key] for key in ('signal', 'origin', 'approach', 'turn', 'receiving_link', 'kind')},
            'physical_stopline': '52' if sc1004 else '1220000201',
            'expected_outgoing_connectors': ['10628', '10629', '10630'] if sc1004 else ['10622', '10023', '10616'],
            'keep_movements': keep,
            'physical_projection_links': [link for link, rows in audit['phantom_projection_rows'].items()
                                          if any(row['movement'] == name for row in rows)],
            'prior_limitations': 'Frozen offline NC seed13 source-specific completed-cohort prior. Five-second sampling and censoring limits are recorded in calibration. Seed14 holdout validation is required. Reproject original physical records; do not move an existing model queue.'})
    calibration_path = ROOT / 'diagnostics/dynamic_area_nc13_calibration.json'
    output = {'schema': 'physical-movement-routes/v1', 'network': old['network'],
              'by_movement': by_movement, 'topology_repairs': repairs,
              'calibration': {'path': str(calibration_path.relative_to(ROOT)),
                              'sha256': hashlib.sha256(calibration_path.read_bytes()).hexdigest()},
              'origin_repairs': [{'physical_link': '379', 'expected_origins': ['SC107_to_SC108', 'in_SC107_S', 'in_SC108_W'],
                                  'target_origin': 'in_SC107_S', 'native_routes': ['1064:1', '1064:3'],
                                  'rationale': 'Input379 reaches SC107 south approach378; no SC108 stopline is reached first.'}]}
    target = ROOT / 'diagnostics/dynamic_area_routes_ver2.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
