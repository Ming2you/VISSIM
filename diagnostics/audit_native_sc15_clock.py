"""Check the unactuated native SC15 program against completed native LSA."""
from pathlib import Path
import hashlib,json
from plant.src.vissim_strict.signal_program import parse_sig
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'diagnostics/route_choice_corridor_1099_ver2.json';doc=json.loads(evidence.read_text());spec=doc['native_fixed_service']
    sig=ROOT/spec['sig_file']['path'];program=parse_sig(sig,spec['program_no']);lsa=next((ROOT/'evaluation/runs/codex_area_observed_nc_s13_20260910/vissim_eval').glob('*.lsa'))
    changes={'1':[],'5':[]}
    for line in lsa.read_text(errors='replace').splitlines():
        cols=[s.strip() for s in line.split(';')]
        if len(cols)<5 or cols[2]!='15' or cols[3] not in changes:continue
        changes[cols[3]].append({'sec':float(cols[0]),'native_cycle_sec':float(cols[1]),'state':cols[4].upper()})
    output={}
    for group,rows in changes.items():
        event_mismatch=[r for r in rows if program.state_at(r['sec'],group,controller_offset_sec=spec['controller_offset_sec'])!=r['state']]
        phase_mismatch=[r for r in rows if (r['sec']-program.program_offset_sec-spec['controller_offset_sec'])%program.cycle_length_sec!=r['native_cycle_sec']]
        i=0;dense_mismatch=[];green_mismatch=[]
        for t in range(int(rows[0]['sec']),5400):
            while i+1<len(rows) and rows[i+1]['sec']<=t:i+=1
            observed=rows[i]['state'];predicted=program.state_at(t,group,controller_offset_sec=spec['controller_offset_sec'])
            if observed!=predicted:dense_mismatch.append(t)
            seconds=_union_green_overlap(program,(group,),t,t+1,spec['controller_offset_sec'])
            if seconds!=float(observed=='GREEN'):green_mismatch.append(t)
        output[group]={'changes':len(rows),'first_change_sec':rows[0]['sec'],'last_change_sec':rows[-1]['sec'],
            'event_state_mismatches':event_mismatch,'event_cycle_phase_mismatches':phase_mismatch,
            'every_second_comparison_window':[rows[0]['sec'],5399],'dense_state_mismatch_seconds':dense_mismatch,
            'canonical_green_overlap_mismatch_seconds':green_mismatch,
            'canonical_green_seconds_0_5400':_union_green_overlap(program,(group,),0,5400,spec['controller_offset_sec']),
            'first_three_events':rows[:3],'last_three_events':rows[-3:]}
    report={'schema':'native-sc15-clock-audit/v1','controller':'15','program_no':spec['program_no'],'controller_offset_sec':spec['controller_offset_sec'],
        'program_offset_sec':program.program_offset_sec,'cycle_sec':program.cycle_length_sec,'groups':output,
        'clock':'Canonical parse_sig source-phase and fixed_signal_schedule green_overlap; no retiming or fitted offset.',
        'limits':['LSA native fixed-time state is used only for unactuatedSC15; it does not validate COM-overridden controllers.',
                  'Before the first recorded change23s the LSA supplies no explicit state for these two groups; no dense observational assertion is made there.',
                  'GREEN overlap proves timing only. Existing per-lane model capacity is not calibrated by this audit.'],
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (evidence,sig,lsa,ROOT/doc['network']['path'],Path(__file__))}}
    (ROOT/'diagnostics/native_sc15_clock_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if any(r[k] for r in output.values() for k in ('event_state_mismatches','event_cycle_phase_mismatches','dense_state_mismatch_seconds','canonical_green_overlap_mismatch_seconds')):raise SystemExit('Native clock disagrees')
if __name__=='__main__':main()
