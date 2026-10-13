"""Reuse the verified299 fixed-command runner with only source301 scope changes."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'sc101_clock299'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'run.py').exists() and not (HERE/'forecast2400').exists()
    log=(HERE/'tests.log').read_text(encoding='utf8')
    assert 'Ran 3 tests' in log and '\nOK' in log and 'FAILED' not in log
    config=json.loads((OLD/'config.json').read_bytes())
    config['diagnostic_sc15_source_service']='past_queued_platoon_midpoint'
    config['source_service_calibration']='sc15_source301/calibration.json'
    (HERE/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    code=(OLD/'run.py').read_text(encoding='utf8')
    substitutions={
        "HERE/'source_geometry.py',HERE/'source_geometry.json'":"A/'sc101_clock299/source_geometry.py',A/'sc101_clock299/source_geometry.json',HERE/'calibration.json',A/'sc101_clock299/candidate.py'",
        "save('service_metadata.json',cfg.network.combined298_service)":"save('service_metadata.json',dict(combined298=cfg.network.combined298_service,sc15_source301=cfg.network.sc15_source301))",
        "'SC101_SIDE_ENTRY_GEOMETRY'":"'SC15_SOURCE_SERVICE'",
        "fits=0,":"fits=2,",
        "sc101_side_entry_geometry=True,gate_dynamics_added=True":"sc101_side_entry_geometry=True,gate_dynamics_added=True,sc15_source_service=True"
    }
    for before,after in substitutions.items():
        assert code.count(before)==1,(before,code.count(before))
        code=code.replace(before,after)
    compile(code,str(HERE/'run.py'),'exec')
    (HERE/'run.py').write_text(code,encoding='utf8')
    pins={str(p):sha(p) for p in (HERE/'candidate.py',HERE/'test_candidate.py',HERE/'tests.log',HERE/'calibration.json',HERE/'config.json',HERE/'plan.json',HERE/'run.py',Path(__file__),OLD/'run.py')}
    (HERE/'preflight.json').write_text(json.dumps(dict(status='pass',unit_tests=3,runner_parent_sha256=sha(OLD/'run.py'),
        bounded_candidate='SC15 source service only; source routing correction not installed',
        budget=dict(fixed450=2,full_optimizer=0,ad=0,native=0),source_pins=pins),indent=2)+'\n',encoding='utf8')
    print('PREPARED301 two fixed450 predictions; three source/future/isolation tests passed')


if __name__=='__main__':main()
