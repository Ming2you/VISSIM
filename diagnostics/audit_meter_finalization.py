"""Read-only audit of final meter commands; no controller solve or VISSIM access."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor/NumSim-mine'))
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.models.state import ControlAction


def summarize(path: Path, mapping: dict) -> dict:
    doc = json.loads(path.read_text(encoding='utf-8'))
    diag = doc.get('diagnostics', {})
    groups = {}
    for meter in mapping['ramp_meters']:
        groups.setdefault(meter['model_ramp_key'], []).append(meter['id'])
    rows = []
    for group, meters in groups.items():
        requested = diag.get('rw_meter_requested_' + group)
        realized = diag.get('rw_meter_realized_' + group)
        rows.append({
            'group': group, 'requested_vph': requested, 'realized_vph': realized,
            'delta_vph': None if requested is None or realized is None else realized-requested,
            'action_vph': doc.get('ramp_metering', {}).get(group),
            'open': diag.get('rw_meter_open_' + group),
            'spill_guard_forced': doc.get('metadata', {}).get('rw_spill_guard_' + group, 0.),
            'spill_guard_from_vph': doc.get('metadata', {}).get('rw_spill_guard_' + group + '_from_vph'),
            'physical_green_sec': {m: diag.get('rw_meter_green_' + m) for m in meters},
            'demand_hint_vph': {m: diag.get('rw_meter_demand_' + m) for m in meters},
        })
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'sim_sec': doc.get('metadata', {}).get('sim_sec'), 'groups': rows}


def stale_cache_probe() -> dict:
    cfg = SimpleNamespace(network=SimpleNamespace(ramp_capacity_veh_h={'R': 1800.}))
    meters = [{'id': 'A', 'model_ramp_key': 'R'}, {'id': 'B', 'model_ramp_key': 'R'}]
    settings = {'allocation': 'measured_table', 'min_green_sec': 2, 'max_green_sec': 10}
    original = ControlAction(ramp_metering={'R': 1000.})
    first = adapter._measured_meter_allocation(original, cfg, settings, meters)
    copied = original.copy()
    copied.ramp_metering['R'] = 1800.
    reused = adapter._measured_meter_allocation(copied, cfg, settings, meters)
    clean = ControlAction(ramp_metering={'R': 1800.})
    recalculated = adapter._measured_meter_allocation(clean, cfg, settings, meters)
    return {'original_request_vph': 1000., 'new_request_vph': 1800., 'original': first,
            'copy_reused': reused, 'fresh_recalculation': recalculated,
            'stale_cache_confirmed': reused != recalculated,
            'original_unchanged': original.ramp_metering['R'] == 1000.}


def main() -> None:
    mapping_path = ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    base = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910'
    paths = sorted(p for p in base.glob('action_*.json') if int(p.stem.split('_')[-1]) >= 900)
    pure = [summarize(p, mapping) for p in paths]
    actual = []
    for name in ('wu-link_t900_beta0_20260909T183226944811Z', 't1200_beta0_20260909T181838217126Z',
                 'wu-link_t3300_beta300_20260909T183707416734Z'):
        path = ROOT/'diagnostics/area_production_preflight'/name/'action.json'
        if path.exists():
            actual.append(summarize(path, mapping))
    def aggregate(items):
        flat = [(x['sim_sec'], r) for x in items for r in x['groups']]
        known = [(t, r) for t, r in flat if r['delta_vph'] is not None]
        changed = [{'sim_sec': t, **r} for t, r in known if abs(r['delta_vph']) > 1e-9]
        return {'decisions': len(items), 'group_rows': len(flat), 'missing': len(flat)-len(known),
                'changed_rows': changed, 'max_absolute_delta_vph': max((abs(r['delta_vph']) for _, r in known), default=0),
                'all_open_rows': sum(r['open'] == 1 for _, r in known),
                'spill_guard_forced_rows': [{'sim_sec':t,**r} for t,r in flat if r['spill_guard_forced']]}
    out = {'schema': 'meter-finalization-audit/v1', 'pure_summary': aggregate(pure),
           'actual_main_summary': aggregate(actual), 'pure': pure, 'actual_main': actual,
           'stale_cache_probe': stale_cache_probe(),
           'source_sha256': hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest()}
    target = ROOT/'diagnostics/meter_finalization_audit.json'
    target.write_text(json.dumps(out, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({key: {**out[key], 'changed_rows': len(out[key]['changed_rows'])}
                      for key in ('pure_summary', 'actual_main_summary')}, indent=2))


if __name__ == '__main__':
    main()
