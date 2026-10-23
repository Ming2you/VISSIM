"""Preserve the rejected input-reuse attempt and retain exact replay caps."""
from pathlib import Path
import json
A=Path(__file__).resolve().parent
old=A/'run_refine15_regime_fit.py';new=A/'run_refine15_regime_fit_v2.py'
assert not new.exists()
failure=json.loads((A/'refine15_regime_fit/failure.json').read_bytes())
assert "N_P_star" in failure['error']
assert not (A/'refine15_regime_fit/progress.json').exists()
s=old.read_text(encoding='utf8')
def replace(old,new):
    global s
    assert s.count(old)==1,(old[:70],s.count(old))
    s=s.replace(old,new)
replace("O=A/'refine15_regime_fit'", "O=A/'refine15_regime_fit_v2'")
replace("train_controls='Existing completed OFF110 replay city/RM.1650 free flow,2250 breakdown,2850 recovery. Previous2250 holdout is now explicitly development/training. All90 outcomes and seeds67/71 excluded from fitting.',", "train_controls='1650/2250 use exact hold replay actions including their recorded NP/NUF caps;2850 uses completed original OFF actions. Applied physical commands match across the common replay prefix, later coordination-cap metadata does not.2250 is now development/training. All90 outcomes and seeds67/71 excluded from fitting.',")
replace("path=OBS/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)\n            assert Path(str(path)+'.applied').is_file(),str(path)", "path=(HOLD if at in (1650,2250) else OBS)/f'action_{sec:06d}.json';PINS[str(path)]=sha(path)\n            assert Path(str(path)+'.applied').is_file(),str(path)")
replace("prior=seq.first_action(adapter.control_from_json(HOLD/f'action_{sec:06d}.json',temp['cfg'],ControlAction))\n                for field in ('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'):", "prior=seq.first_action(adapter.control_from_json(OBS/f'action_{sec:06d}.json',temp['cfg'],ControlAction))\n                for field in ('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'):")
replace("raw=read(OBS/f'state_{sec:06d}.json');assert raw['sim_sec']==sec", "raw=read((HOLD if at in (1650,2250) else OBS)/f'state_{sec:06d}.json');assert raw['sim_sec']==sec")
needle="    initial_audit=read(A/'refine15_update_audit.json');spec=read(SPEC)"
preflight="""    # Qualify exact physical replay without substituting coordination budgets.
    for at in (1650,2250,2850):
        folder=HOLD if at in (1650,2250) else OBS
        for sec in range(at,at+450,150):
            path=folder/f'action_{sec:06d}.json';doc=read(path)
            assert Path(str(path)+'.applied').is_file()
            assert all(v==110 for v in doc['vsl'].values())
            if at in (1650,2250):
                other=read(OBS/f'action_{sec:06d}.json')
                assert all(doc.get(k)==other.get(k) for k in ('ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation'))
    initial_audit=read(A/'refine15_update_audit.json');spec=read(SPEC)"""
replace(needle,preflight)
compile(s,str(new),'exec');new.write_text(s,encoding='utf8');print(new)
