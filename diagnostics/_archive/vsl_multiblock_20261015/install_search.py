"""Integrate only the reviewed opt-in audit into the existing development tree."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path('E:/VISSIM_workspaces/vsl349_causal_20261011')
receipt = json.loads((HERE/'integration_receipt.json').read_bytes())
target = ROOT/'evaluation/controllers/sdmpc.py'
assert hashlib.sha256(target.read_bytes()).hexdigest() == receipt['source_sha256'], 'Source changed since review'
helper = ROOT/'evaluation/controllers/vsl_schedule_neighbors.py'
test = ROOT/'tests/test_sdmpc_vsl_schedules.py'
cfg = ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
assert not any(p.exists() for p in (helper,test,cfg))
assert not (HERE/'search_installation.json').exists()
staged = Path(receipt['staged'])
assert hashlib.sha256(staged.read_bytes()).hexdigest() == receipt['staged_sha256']
assert hashlib.sha256((HERE/'vsl_schedule_neighbors.py').read_bytes()).hexdigest() == receipt['helper_sha256']
helper.write_bytes((HERE/'vsl_schedule_neighbors.py').read_bytes())
test.write_text((HERE/'test_vsl_schedules.py').read_text(encoding='utf8').replace(
    'from vsl_schedule_neighbors import schedules, audit',
    'from evaluation.controllers.vsl_schedule_neighbors import schedules, audit'),encoding='utf8')
cfg.parent.mkdir(parents=True)
cfg.write_bytes((HERE/'staged_config.json').read_bytes())
target.write_bytes(staged.read_bytes())
result = dict(status='implemented_opt_in_not_native_deployed', developer_tree=str(ROOT),
    source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target,helper,test,cfg)},
    previous_sdmpc_sha256=receipt['source_sha256'], default_off=True,
    native_deployments=0, frozen_files_modified=False, existing_configs_modified=False,
    dynamics_modified=False, objective_modified=False)
(HERE/'search_installation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status=result['status'],files=4)))
