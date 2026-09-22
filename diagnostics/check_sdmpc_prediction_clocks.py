"""Exact saved command VBS clocks; no VISSIM instance or COM traffic writes."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import pickle
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    folder=ROOT/'diagnostics/sdmpc_prediction_20260922'
    out=folder/'clocks_v1';out.mkdir(exist_ok=False)
    reports=[pickle.loads(p.read_bytes()) for p in
        (ROOT/'diagnostics/sdmpc_speed_20260922/full_decision_v1/result.pickle',folder/'full_decision_v1/result.pickle')]
    request=pickle.loads((folder/'cached_h3_v2/request.pickle').read_bytes())
    cfg=request['owned'][0].cfg
    runner=ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
    source=runner.read_text(encoding='utf-8-sig')
    names=['FMod','SignalClockPosition','SignalGroupPlanKey','SignalGroupPlanWindows',
           'SignalGroupStateFromPlan','AnySignalGroupGreenAt']
    functions=[]
    for name in names:
        functions.append(re.search(r'^Function '+name+r'\([^\n]*\).*?^End Function',source,re.M|re.S).group())
    amber=re.search(r'^Const AMBER_SEC\s*=\s*([^\r\n]+)',source,re.M).group(1)
    outputs=[]
    group_count=None
    for name,report in zip(('before','after'),reports):
        groups=defaultdict(list)
        for row in report['response']['command_evidence']['ordered_rows']:
            if row['kind']=='signal_sg':groups[str(row['sc_no']),str(row['dsd_no'])].append(row)
        group_count=len(groups)
        lines=['Option Explicit','Const AMBER_SEC = '+amber,'Dim nativeClockPlans, sgPlanWindows',
            'Set nativeClockPlans = CreateObject("Scripting.Dictionary")',
            'Set sgPlanWindows = CreateObject("Scripting.Dictionary")','Dim t, pos']
        for signal,row in cfg.network.signal_actuation_contract['nodes'].items():
            if row.get('native_clock_basis'):
                lines.append('nativeClockPlans.Add "'+signal.removeprefix('SC')+'", True')
        for (sc,sg),rows in sorted(groups.items()):
            windows=';'.join(str(r['p1_green'])+'|'+str(r['p2_green']) for r in rows)
            lines.append(f'sgPlanWindows.Add "{sc}-{sg}", "{windows}"')
        for (sc,sg),rows in sorted(groups.items()):
            cycle,offset=rows[0]['green_sec'],rows[0]['offset']
            assert all(r['green_sec']==cycle and r['offset']==offset for r in rows)
            lines.extend(['For t = 900 To 1049',f'pos = SignalClockPosition("{sc}", t, {offset}, {cycle})',
                f'WScript.Echo "{sc}:{sg}:" & CStr(t) & ":" & SignalGroupStateFromPlan({sc}, {sg}, pos, {cycle})','Next'])
        script=out/(name+'.vbs');script.write_text('\n'.join(lines+functions)+'\n',encoding='utf-16')
        result=subprocess.run(['cscript.exe','//nologo',str(script)],capture_output=True,check=True)
        (out/(name+'.txt')).write_bytes(result.stdout);outputs.append(result.stdout)
    from evaluation.controllers import sdmpc_sequence as sequence,signal_actuation_contract as signals
    blocks=[sequence.actions(r['response']['control'],3) for r in reports]
    phase_checks=0;differences=[]
    for k,(old,new) in enumerate(zip(*blocks)):
        for sec in range(900+150*k,1050+150*k):
            for signal in cfg.network.signals:
                for phase in signals.PHASES:
                    spec={'phase':signal+'_'+phase}
                    a,b=[signals.phase_fraction(control,cfg,spec,sec) for control in (old,new)]
                    phase_checks+=1
                    if a!=b:differences.append(dict(block=k,sec=sec,signal=signal,phase=phase,before=a,after=b))
    report=dict(scope=__doc__,native_applied=False,vbs_runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest(),
        copied_functions=names,first_block_signal_groups=group_count,first_block_sg_seconds=group_count*150,
        first_block_vbs_green_amber_red_exact=outputs[0]==outputs[1],future_blocks_native_phase_checks=phase_checks,
        all_three_blocks_native_phase_fractions_exact=not differences,phase_differences=differences,
        first_block_vbs_sha256=[hashlib.sha256(x).hexdigest() for x in outputs])
    report['pass_all']=report['first_block_vbs_green_amber_red_exact'] and not differences
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
