"""Read-only native/model evidence for positive unresolved 450 s movements."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from probe_area_endpoint import fixture
from test_observation_projection import ActualInstalledProjection as Harness
from evaluation.controllers.physical_movement_routes import load_evidence


def main():
    cfg, state, _, _ = fixture()
    document, routes, _ = load_evidence('diagnostics/physical_movement_routes_ver2.json')
    tree = ET.parse(ROOT / document['network']['path']).getroot()
    links = {row.get('no'): row for row in tree.findall('./links/link')}
    selected = {name: dict(spec) for name, spec in cfg.network.urban_movements.items()
                if (spec.get('signal') == 'SC1004' and (str(spec.get('approach')).startswith('E')
                    or spec.get('receiving_link') == 'SC1004_to_SC107'))
                or (spec.get('signal') == 'SC107' and str(spec.get('approach')).startswith('W'))
                or (spec.get('signal') == 'SC108' and spec.get('origin') == 'in_SC108_W')}
    origin_names = {row.get('origin') for row in selected.values()}
    source_support = {}
    nc = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry'
    _, _, detectors, _, _, _, _ = Harness.build_projected(Harness.config_path, nc / 'state_000900.json', nc / 'action_000001.json')
    phantom = {name for name, spec in selected.items() if spec['turn'] == 'u_turn'}
    projection_rows = {link: rows for link, rows in detectors['link_to_movements'].items()
                       if any(row['movement'] in phantom for row in rows)}
    raw_assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    for link, rows in raw_assignment.items():
        matches = {stock: value for stock, value in rows.items()
                   if any(stock.endswith(':' + str(origin)) for origin in origin_names)}
        if matches:
            source_support[link] = matches
    interesting = {'13', '56', '52', '387', '1220000201', '71', '46', '10643', '10638', '70', '126'}
    native = {key: value for key, value in routes.items()
              if value['path'][0] in interesting or key in {'1140:2', '1138:2', '1133:2', '1129:1'}}
    positioned = {}
    for key, row in native.items():
        path = row['path']
        transitions = []
        for index, physical in enumerate(path):
            link = links[physical]
            start, end = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
            if start is not None:
                transitions.append({'connector': physical, 'from': dict(start.attrib), 'to': dict(end.attrib)})
        positioned[key] = dict(row, connector_positions=transitions)
    output = {'model_specs': selected, 'projected_source_support': source_support,
              'phantom_projection_rows': projection_rows,
              'link13_projection': {'origins': detectors['link_to_origins'].get('13'),
                                    'movements': detectors['link_to_movements'].get('13')},
              'link379_projection': {'origins': detectors['link_to_origins'].get('379'),
                                     'movements': detectors['link_to_movements'].get('379')},
              'sc106_models': {name: dict(spec) for name, spec in cfg.network.urban_movements.items() if spec['signal'] == 'SC106'},
              'sc106_support': {link: origins for link, origins in detectors['link_to_origins'].items()
                               if link in {'13', '6', '5', '3', '10017', '10002', '10005', '10000', '1220017202'}},
              'native_routes': positioned,
              'unresolved': {k: v for k, v in cfg.network.control_area_routes.items()
                             if any(k.endswith(name) for name in selected) and type(v.get('target_inside')) is not bool}}
    target = ROOT / 'diagnostics/dynamic_area_route_evidence.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'specs': selected, 'native': {k: {'path': v['path'], 'weight': v['weight']} for k, v in native.items()}}, indent=2))


if __name__ == '__main__':
    main()
