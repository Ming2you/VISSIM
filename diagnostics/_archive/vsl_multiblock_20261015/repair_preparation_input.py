"""Preserve failed bootstrap and point a new attempt at qualified OFF inputs."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=HERE/'prepare_multizone.py';dst=HERE/'prepare_multizone_v2.py'
assert not dst.exists()
failed=json.loads((HERE/'native_preparation_failure.json').read_bytes())
assert 'derived_002250.json' in failed['traceback']
assert not (HERE/'matched_off2250/progress.json').exists()
assert not (HERE/'matched_off2250/summary.json').exists()
text=src.read_text(encoding='utf8')
replacements={
    "OUT=HERE/'matched_off2250'":"OUT=HERE/'matched_off2250_v2'\nOBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')",
    "assert not PACK.exists() and not OUT.exists(),'Preserve any prior attempt'":"assert PACK.exists() and not OUT.exists() and not (PACK/'protocol.json').exists(),'Preserve existing completed attempts'",
    "dest=PACK/'selected/commands';dest.mkdir(parents=True)":"dest=PACK/'selected/commands'\n    assert summary['original_initial_history_exact'] and summary['source_observed_model_inputs_exact']\n    assert len(summary['observed_input_checks'])==15 and all(r['source_observations_exact'] for r in summary['observed_input_checks'])\n    assert (OBS/'obs150/derived_002250.json').exists()\n    assert {p.name for p in dest.iterdir()}=={f'action_{s:06d}.{ext}' for s in [1,*range(150,2250,150)] for ext in ('json','csv')}",
    "shutil.copyfile(src,dst);assert sha(dst)==digest":"assert sha(dst)==digest,('Preserve prefix mismatch',dst)",
    "'--decisions',str(F),'--full-selection'":"'--decisions',str(OBS),'--full-selection'",
    "'scope='":"'scope='",
    "save(HERE/'native_preparation_failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),native_runs=0))":"save(HERE/'native_preparation_failure_v2.json',dict(error=repr(exc),traceback=traceback.format_exc(),native_runs=0))"
}
replacements.pop("'scope='")
for before,after in replacements.items():
    assert text.count(before)==1,before
    text=text.replace(before,after)
text=text.replace("future_observations_used=False,\n            scope=", "future_observations_used=False,qualified_observation_source=str(OBS),observed_input_equality_receipt=str(ANALYSIS/'summary.json'),\n            scope=")
dst.write_text(text,encoding='utf8')
receipt=dict(cause='Replay native never ran the online adapter and has no derived obs150 sidecar. Original OFF observations were already verified identical for15 timestamps through2250 and same physical prefix.',
    original_script=str(src),original_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    revised_script=str(dst),revised_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
    forecasts_consumed_by_failed_attempt=0,native_runs=0,source_observations_modified=False,
    completed_prefix_reused_by_byte_hash=True,read_only_original_off_observations=True)
(HERE/'preparation_input_repair.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(receipt))
