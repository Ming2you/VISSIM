"""Writer-only repair in a new diagnostic folder; zero rollouts/native runs.

Reuse the pinned preparation initialization and canonical writer, adding the
same experiment metadata used by the production adapter. Preserve failed files.
"""
import hashlib
import json
import shutil
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ORIGINAL = HERE / 'prepare_multizone_v3.py'
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() == '38acce36226c98387073ba9e6ccba26a3448bae5bb398049b6af26b0f22bcb91'
PACK = HERE / 'command_metadata_repair'
OUT = HERE / 'writer_metadata_check2250'
assert not PACK.exists() and not OUT.exists(), 'Preserve existing repair attempt'
commands = PACK / 'selected/commands'
commands.mkdir(parents=True)
source = Path('D:/VISSIM_packages/vsl_multizone355_20261015/diagnostics/sdmpc_n31_20260924/integration_20260926/native_vsl_multizone2250/selected/commands')
for sec in [1, *range(150, 2250, 150)]:
    for ext in ('csv', 'json'):
        shutil.copyfile(source / f'action_{sec:06d}.{ext}', commands / f'action_{sec:06d}.{ext}')
text = ORIGINAL.read_text(encoding='utf8')

def replace(old, new):
    global text
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new)

replace("PACK=ROOT/REL/'native_vsl_multizone2250'", "PACK=HERE/'command_metadata_repair'")
replace("OUT=HERE/'matched_off2250_v3'", "OUT=HERE/'writer_metadata_check2250'")
replace("                source=F/f'action_{sec:06d}.json';target=dest/source.name", """                source=F/f'action_{sec:06d}.json';target=dest/source.name
                from evaluation.controllers import offset_promotion
                assert signals.enabled(cfg.network)
                writer_metadata=dict(read(source)['metadata'])
                writer_metadata.update(offset_promotion.action_metadata(action, 'experiment'))
                writer_metadata['physical_signal_contract_enabled']=1.0""")
replace("                    read(source)['metadata'],adapter.adapter_actuation_settings", "                    writer_metadata,adapter.adapter_actuation_settings")
replace("                save(target,adapter.control_to_json_dict(action,metadata))", """                metadata.update({k:writer_metadata[k] for k in ('offset_writer','offset_experiment','physical_signal_contract_enabled')})
                save(target,adapter.control_to_json_dict(action,metadata))
                with source.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as f: baseline_rows=list(csv.DictReader(f))
                with target.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as f: fixed_rows=list(csv.DictReader(f))
                assert len(baseline_rows)==len(fixed_rows)==213
                assert all(a['metadata']==b['metadata'] for a,b in zip(baseline_rows,fixed_rows)), 'Every metadata token must match the validated native hold'""")
start = text.index('        for name,action in actions.items():')
end = text.index('        raise verifier.Done()', start)
text = text[:start] + "        save(OUT/'writer_metadata_verification.json',dict(status='writer_contract_verified',checks=checks,new_forecasts=0,new_native=0,full_optimizations=0))\n" + text[end:]
start = text.index('    assert len(results)==3 and len(checks)==3')
end = text.index("\nif __name__=='__main__':", start)
text = text[:start] + "    assert len(results)==0 and len(checks)==3\n    print('WRITER_REPAIR_READY; native_runs=0; forecasts=0',flush=True)\n" + text[end:]
generated = HERE / 'prepare_multizone_writer_only.py'
assert not generated.exists()
generated.write_text(text, encoding='utf8')
module = types.ModuleType('scoped_replay_writer_metadata_repair')
module.__file__ = str(generated)
sys.modules[module.__name__] = module
exec(compile(text, str(generated), 'exec'), module.__dict__)
module.main()
(HERE / 'writer_repair_preparation.json').write_text(json.dumps(dict(
    script=str(generated), sha256=hashlib.sha256(generated.read_bytes()).hexdigest(),
    output=str(PACK), forecasts=0, native_runs=0, failed_native_preserved=True,
    source_preparation=str(ORIGINAL), status='ready_for_offline_native_metadata_contract_check'
), indent=2) + '\n', encoding='utf8')
