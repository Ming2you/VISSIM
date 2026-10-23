"""Prepare a bounded numerical-resolution diagnostic from the qualified replay harness."""
import hashlib,json
from pathlib import Path

A=Path(__file__).resolve().parent
source=(A/'run_refine15.py').read_text(encoding='utf8')
def replace(old,new):
    global source
    assert source.count(old)==1,(old,source.count(old))
    source=source.replace(old,new)

replace("OUT=AUDIT/'refine15_candidate'","CLOCK=AUDIT/'refine15_clock'\nOUT=CLOCK/'forecasts'")
replace("assert not OUT.exists() and not (AUDIT/'refine15_launch.json').exists() and not (AUDIT/'STOP').exists()",
        "assert not OUT.exists() and not (CLOCK/'launch.json').exists() and not (AUDIT/'STOP').exists()")
start=source.index('    tests=unittest.TextTestRunner')
end=source.index("    sys.path[:0]=",start)
source=source[:start]+'''    protocol=read(CLOCK/'protocol.json')
    assert protocol['budget']['forecasts']==4
    save(CLOCK/'launch.json',dict(pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=sys.argv,forecast_budget=4,native=0))
'''+source[end:]
replace("refinement=Refinement(AUDIT)","refinement=Refinement(CLOCK)\n    from evaluation.controllers import multirate_freeway\n    original_limit=multirate_freeway.time_limit\n    cap=1.25\n    multirate_freeway.time_limit=lambda runtime,state:min(cap,original_limit(runtime,state))")
replace("for name,zones in [('hold',{}),('selected',{'FW_E__seg10':90,'FW_E__seg13':90})]:",
        "for name,cap,zones in [('hold125',1.25,{}),('selected125',1.25,{'FW_E__seg10':90,'FW_E__seg13':90}),('hold0625',.625,{}),('selected0625',.625,{'FW_E__seg10':90,'FW_E__seg13':90})]:")
replace("        state,cfg=captured['state'],captured['cfg']","        nonlocal cap\n        state,cfg=captured['state'],captured['cfg']")
replace('assert len(results)<2','assert len(results)<4')
replace("result=dict(name=name,ttt_veh_h=point.ttt,seconds=elapsed,costs=costs", "result=dict(name=name,internal_cap_sec=cap,ttt_veh_h=point.ttt,seconds=elapsed,costs=costs")
replace('finally:refinement.restore()', 'finally:\n        refinement.restore()\n        multirate_freeway.time_limit=original_limit')
replace('assert len(results)==2','assert len(results)==4')
replace("new_forecasts=2,new_native=0", "new_forecasts=4,new_native=0")
replace('tests=tests.testsRun','tests=0,prior_transport_tests_reused=5')
replace("AUDIT/'refine15_failure.json'","CLOCK/'failure.json'")
target=A/'run_refine15_clock.py'
clock=A/'refine15_clock'
assert not target.exists() and not clock.exists()
compile(source,str(target),'exec')
target.write_text(source,encoding='utf8')
clock.mkdir()
protocol=dict(hypothesis='Determine whether the fixed-parameter cell15 refinement response and rapid speed-floor contact are mostly time-integration effects.',
    budget=dict(forecasts=4,native=0,optimizer=0,fits=0),internal_cap_sec=[1.25,.625],macro_clock_sec=dict(freeway=5,urban=10),horizon_sec=450,
    controls='Two matched hold110/two-zone90 pairs with original city/RM and all other commands. No changes to coefficients, objective, demand, geometry or initial state versus the completed refined candidate.',
    comparisons=['Initial first10s middle-compartment minimum speed and floor duration',
        'Fixed hold baseline subcell stocks/speeds at150/300/450 against existing native snapshots',
        'Approach14-18 throughflow/inventory and wholeOmega contrast, plus conservation and source pins'],
    reporting_rule='Treat agreement between two capped grids as sensitivity evidence, not a proof of an exact solution or of behavioral calibration. No candidate is adopted by this test. Do not choose coefficients or grids to obtain a VSL benefit sign.',
    preregistered_screen=dict(hold_subcell_max_speed_change_kmh=2.,hold_subcell_max_stock_change_veh=1.,response_throughflow_change_veh=1.,omega_contrast_change_veh_h=.05),
    prior_diagnostic='Existing440 tested unrefined31-cell internal1s on seed67/71. Those results remain; this tests the newly refined cell15 representation on seed29 and does not repeat them.',
    new_native=0,production_changes=0,source_pins={str((A/f).resolve()):hashlib.sha256((A/f).read_bytes()).hexdigest() for f in ('run_refine15.py','refine_approach15.py','refine15_candidate/completion.json','refinement_decision.json')})
(clock/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(target)
