"""Prepare one fixed-command pair, with current-route composition only."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'sc12_phase305'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
    assert not (HERE/'run.py').exists()
    log=(HERE/'tests.log').read_text(encoding='utf-8-sig')
    assert 'Ran 5 tests' in log and 'OK' in log and 'FAILED' not in log
    config=json.loads((OLD/'config.json').read_bytes())
    config['diagnostic_initial_route306']='SC12W current terminal-link subset; unchanged ETA'
    save(HERE/'config.json',config)
    save(HERE/'plan.json',dict(status='prepared',goal_complete=False,
        previous_goal_turn='status_only_time_step_reply; revalidated305 finding and resumed concrete correction',
        purpose='Retain independently observed current SC12W routes in initial queues and parent reservations',
        scope='Four terminal-link vehicles only; two ready and two residual. Other five origin residual vehicles keep prior treatment.',
        budget=dict(fixed450=2,rate_candidates=0,optimizer=0,ad=0,native=0,fzp=0),
        preserve=['current total stock','paired arrival/release times','Omega701 membership','FW5/U10',
                  '450s','terminalOFF','same commands/caps/demand','shared physical service and finite receiving','native queue unchanged'],
        output='E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400'))
    code=(OLD/'run.py').read_text(encoding='utf8')
    changes={
        'from candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR':
          'from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook, validate_turns, west, east, MOV, verify_pending, ATTR\nfrom candidate import project, SOURCE as ROUTE_SOURCE\nfrom test_candidate import inputs',
        "E:/VISSIM_analysis/20261010_sc12_phase305/forecast2400":"E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400",
        "HERE/support_file":"A/'sc12_phase305'/support_file",
        "HERE/'past_shared_prefix_support.json'":"A/'sc12_phase305/past_shared_prefix_support.json'",
        "            baseline_state=pickle.dumps(state,protocol=5)":
          "            canonical=state\n"
          "            _,_,raw,frame,network,inside,lanes=inputs()\n"
          "            state,projection=project(canonical,cfg,raw,frame,network,inside,lanes)\n"
          "            changed_fields={k for k,v in vars(state).items() if pickle.dumps(v,protocol=5)!=pickle.dumps(vars(canonical)[k],protocol=5)}\n"
          "            assert changed_fields=={'urban_movement_queue','local_observation_summary','gate_initial_route_tags','_control_area_ledger'},changed_fields\n"
          "            assert state.urban_arrival_buffer==canonical.urban_arrival_buffer and state.urban_storage_release_buffer==canonical.urban_storage_release_buffer\n"
          "            for side_key in ('inside','outside'):\n"
          "                assert abs(sum(x[side_key] for x in get_ledger(state).stocks.values())-sum(x[side_key] for x in get_ledger(canonical).stocks.values()))<1e-8\n"
          "            pins.update(read(A/'sc12_phase305/current_projection.json')['source_pins'])\n"
          "            membership=ROOT/read(tuning)['control_area_objective']['membership_path'];pins[str(membership)]=sha(membership)\n"
          "            save('initial_projection.json',projection)\n"
          "            baseline_state=pickle.dumps(state,protocol=5)",
        "                route_tag_states=[getattr(s,ATTR,{}) for s in point.states]":
          "                assert all(s.gate_initial_route_tags.get(ROUTE_SOURCE,{})=={} for s in point.states),'Initial route cohort failed to mature'\n"
          "                route_tag_states=[getattr(s,ATTR,{}) for s in point.states]",
        "'SC12_SHARED_PREFIX305'":"'SC12_INITIAL306'",
        "initial_state_error=error,source_pins=pins":"canonical_state_error_before_projection=error,initial_projection=projection,changed_initial_fields=sorted(changed_fields),source_pins=pins",
        "fits=1,inherited_source_rates=2":"fits=0,inherited_source_rates=3",
        "sc12_shared_prefix305=True,":"sc12_shared_prefix305=True,sc12_initial306=True,"
    }
    for before,after in changes.items():
        expected=2 if before in ("HERE/'past_shared_prefix_support.json'", "HERE/support_file") else 1
        assert code.count(before)==expected,(before,code.count(before))
        code=code.replace(before,after)
    # Include the new initializer/test and inherited hook in the immutable evidence set.
    code=code.replace("    option=read(HERE/'config.json');", "    for p in (HERE/'tests.log',A/'sc12_phase305/candidate.py',A/'sc12_phase305/current_projection.json'):\n        pins[str(p)]=sha(p)\n    option=read(HERE/'config.json');")
    compile(code,str(HERE/'run.py'),'exec')
    (HERE/'run.py').write_text(code,encoding='utf8')
    files=[*HERE.glob('*.py'),HERE/'config.json',HERE/'plan.json',HERE/'tests.log',OLD/'run.py',OLD/'completion.json']
    save(HERE/'preflight.json',dict(status='pass',tests=5,forecasts=2,production_changes=0,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    print('PREPARED306: two fixed450 forecasts; no new rate fitting')
if __name__=='__main__':main()
