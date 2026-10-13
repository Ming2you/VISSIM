"""Add the missing VSL-enabled whole-choice check; no dynamics changes."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target = HERE / 'config.json'
    assert not target.exists()
    base_path = HERE.parent / 'flow279/config_10686_free.json'
    optimized_path = ROOT / 'diagnostics/repin_v3c3_review_20261001/goal8_265/spillback2000/coupling268/vsl_three_20261008/optimized_config.json'
    base, optimized = read(base_path), read(optimized_path)
    assert 'sdmpc_fixed_vsl' not in optimized['adapter']
    for key in ('vsl_zone_heads', 'vsl_zone_free'):
        assert base['freeway'][key] == optimized['freeway'][key]
    cfg = copy.deepcopy(base)
    previous_fixed = cfg['adapter'].pop('sdmpc_fixed_vsl')
    cfg['name'] = 'aggregate288_fw5_urban10_optimized_vsl_offline'
    cfg['description'] = 'Current flow279 plant, FW/ramp5s urban10s. VSL optimization enabled by removing only the fixed schedule. Saved3300 full SDMPC check, no native launch.'
    assert cfg['freeway']['multirate_exchange_sec'] == 5
    assert cfg['urban']['multirate_exchange_sec'] == 10
    target.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    plan = dict(status='prepared', reason='Earlier whole-choice benchmarks fixed VSL; include its24 additional horizon decision axes before broader runtime claims.',
        at_sec=3300, horizon_sec=450, control_sec=150, terminal_cost=False,
        objective='Omega701 TTT', freeway_sec=5, urban_sec=10,
        full_decisions_limit=1, execution_forecasts_limit=2, coefficient_fits=0,
        pfo_max_iterations=2, sdmpc_max_iterations=2, automatic_retries=0,
        native_runs=0, production_changes=0,
        output='E:/VISSIM_analysis/20261010_aggregate288_optimized3300',
        reference_decision=str(HERE.parent/'decision285/full_decision_execution.json'),
        removed_fixed_schedule=previous_fixed,
        source_pins={str(base_path):sha(base_path),str(optimized_path):sha(optimized_path),str(target):sha(target)},
        limits=['Not a timing-only comparison to fixed VSL; control dimensions and possible queries differ.',
                'No native VSL benefit qualification from model selection.',
                'Do not touch current coupling268 frozen native queue or citysplit287 prepared protocol.'])
    (HERE/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('PREPARED_VSL_ENABLED_ONE_CHOICE')


if __name__ == '__main__':
    main()
