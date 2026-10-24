"""Build one explicit composite diagnostic from the reviewed306 runner."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]


def main():
    parent=A/'sc12_initial306/run.py'
    source=parent.read_text(encoding='utf8')
    replacements={
        'from candidate import project, SOURCE as ROUTE_SOURCE':
            'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.candidate import project, SOURCE as ROUTE_SOURCE\nfrom candidate import install as install_sc109',
        'from test_candidate import inputs':
            'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.test_candidate import inputs',
        'from state_check import equal':
            'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal',
        'HERE=Path(__file__).resolve().parent':
            "CASE=Path(__file__).resolve().parent\nHERE=CASE.parent/'sc12_initial306'",
        "OUT=Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')":
            "OUT=Path('E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400')",
        "    pins=dict(old['source_pins'])":
            "    pins=dict(old['source_pins'])\n    for p in (*CASE.glob('*.py'),CASE/'plan.json',CASE/'tests_v2.log'):\n        pins[str(p)]=sha(p)",
        '            baseline_state=pickle.dumps(state,protocol=5)':
            "            prior_rates=dict(cfg.network.movement_capacity_by_movement_veh_h)\n            sc109_application=install_sc109(cfg,state.time_sec)\n            assert {k for k,v in prior_rates.items() if v!=cfg.network.movement_capacity_by_movement_veh_h[k]}=={sc109_application['movement']}\n            pins.update(sc109_application['source_pins'])\n            save('sc109_application.json',sc109_application)\n            baseline_state=pickle.dumps(state,protocol=5)",
        "print('SC12_INITIAL306',arm,point.ttt,wall,flush=True)":
            "print('SC109_COMPOSITE308',arm,point.ttt,wall,flush=True)",
        'initial_projection=projection,changed_initial_fields=sorted(changed_fields)':
            'initial_projection=projection,sc109_application=sc109_application,changed_initial_fields=sorted(changed_fields)',
    }
    for before,after in replacements.items():
        assert source.count(before)==1,before
        source=source.replace(before,after)
    assert not (HERE/'run.py').exists()
    (HERE/'run.py').write_text(source,encoding='utf8')
    plan=dict(status='prepared_single_composite_pair',goal_complete=False,
        hypothesis='The existing too-low SC109 left-turn observed service starves SC16/SC12/SC6; test the previously measured floor together with the later route/gate model, not in isolation.',
        candidate='Reuse four past windows, unique heads1090501/1090502 on173 lanes4/5, connector10286; only one capacity changes696.774 to2000 at saved2400. No new fit.',
        limitations=['Previous old3300 candidate overestimated17.91 versus12. This combination is not qualified for deployment or other states.',
                    'Future admission differences remain distinct from this internal service repair.',
                    'Only a material response improvement warrants a bounded fresh-state validation or full AD. No rate grid.'],
        output='E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400',
        budget=dict(full450=2,optimizer=0,ad=0,native=0,fzp_scans=0,new_fits=0),
        preserved=['Same306 initial projection/demand/commands','FW5/U10','450s','terminalOFF','Omega701TTT','finite receiving and physical conservation','same NP/NUF caps','immutable native queue'],
        parent_runner=str(parent),parent_runner_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                     [HERE/'candidate.py',HERE/'test_candidate.py',HERE/'tests_v2.log',HERE/'run.py',
                      A/'timing307/source_limits.json',A/'timing307/assessment.json']})
    (HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Prepared exactly two fixed450s responses; no optimizer/native/fit.')


if __name__=='__main__': main()
