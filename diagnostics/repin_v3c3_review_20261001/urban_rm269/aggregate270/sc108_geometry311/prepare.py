from pathlib import Path
import hashlib
import json
HERE=Path(__file__).resolve().parent
src=HERE.parent/'sc108_side310/run.py'
text=src.read_text(encoding='utf8')
assert not (HERE/'run.py').exists()
text=text.replace('from candidate import install as install_side', 'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_side310.candidate import install as install_side\nfrom candidate import install as install_geometry, clock as geometry_clock')
text=text.replace('20261010_sc108_side310/forecast2400','20261010_sc108_geometry311/forecast2400')
needle='            baseline_state=pickle.dumps(state,protocol=5)'
assert text.count(needle)==1
text=text.replace(needle,"            geometry_application=install_geometry(cfg,state)\n            save('prehead_geometry.json',geometry_application)\n"+needle)
needle="                with installed(cfg,option['diagnostic_source_path_delay'],geom) as receipts:"
assert text.count(needle)==1
text=text.replace(needle,needle[:-1]+", geometry_clock(cfg) as clock_receipts:")
text=text.replace("                wall=time.perf_counter()-start", "                wall=time.perf_counter()-start\n                save(arm+'.prehead_clock.json',clock_receipts)\n                assert len(clock_receipts)==45 and all(r['delay_sec']<=20 for r in clock_receipts)")
text=text.replace('sc108_side_application=side_application,changed_initial_fields', 'sc108_side_application=side_application,prehead_geometry=geometry_application,changed_initial_fields')
text=text.replace('SC108_SIDE310','SC108_GEOMETRY311')
(HERE/'run.py').write_text(text,encoding='utf8')
plan=dict(status='prepared',baseline='sc108_side310',structural_change='source21 head-bounded storage and geometric travel clock',
    budget=dict(full450=2,parameter_sets=0,ad=0,optimizer=0,native=0,fzp_scans=0),
    inherited_harness=dict(path=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest()),
    output='E:/VISSIM_analysis/20261010_sc108_geometry311/forecast2400',production_adopted=False,
    preserve=['No clipping current stock','current pending due times','physical receiving','same demand and commands','FW5/urban10','450s','terminalOFF'])
(HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('PREPARED')
