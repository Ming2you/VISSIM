"""Reuse the closed native pair to assess large tradeoffs, without refitting."""
import hashlib
import json
from pathlib import Path

A=Path(__file__).resolve().parent
H=A.parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=A/'isolated2400_lane_offer_verified'
    assert read(out/'completion.json')['status']=='complete'
    summary=read(out/'summary.json')
    for path,digest in summary['source_pins'].items():
        assert sha(Path(path))==digest,path
    hold=read(out/'hold.json');released=read(out/'selected.json')
    native=read(H/'isolated10681/practical_calibration_assessment.json')
    footprints=read(H/'native2400_component_footprint.json')['groups']
    delta={k:released['costs_by_stock'].get(k,0)-hold['costs_by_stock'].get(k,0)
           for k in set(hold['costs_by_stock'])|set(released['costs_by_stock'])}
    groups={g:sum(delta.get(k,0) for k in row['initial_model_stock_keys'])
            +(delta.get('transit:gate:in_SC1004_S',0) if g=='approach66' else 0)
            for g,row in footprints.items()}
    groups.update(ramp10681=delta['ramp:RM_C10681'],ramp10646=delta['ramp:RM_C10646'],
                  mainline=sum(v for k,v in delta.items() if k.startswith('freeway:')))
    groups['other_Omega']=sum(delta.values())-sum(groups.values())
    groups['Omega']=sum(delta.values())
    assert abs(groups['Omega']-summary['delta_omega_veh_h'])<1e-7
    # These were the material components in the retained native pair. Small
    # near-cancellation of their total is not a target for coefficient search.
    material=('approach52_with58','shared_W_out','ramp10681','mainline')
    native_costs=native['native_cost_delta_veh_h']
    signs={k:groups[k]*native_costs[k]>0 for k in material}
    result=dict(status='completed_direction_assessment',
                large_tradeoff_directions_pass=all(signs.values()),material_sign_checks=signs,
                native_cost_delta_veh_h=native_costs,predicted_cost_delta_veh_h=groups,
                native_added_merge_veh=native['native_added_merge'],
                predicted_added_merge_veh=summary['extra_merge10681_veh'],
                both_same_caps_feasible=summary['both_same_caps_feasible'],
                scalar_seconds=[hold['wall_sec'],released['wall_sec']],
                objective_changed=False,new_coefficients=0,native_runs=0,
                complete_optimizer_seconds=None,full_sdmpc_qualified=False,
                source_pins={str(p):sha(p) for p in (out/'summary.json',out/'hold.json',
                    out/'selected.json',H/'isolated10681/practical_calibration_assessment.json',
                    H/'native2400_component_footprint.json',Path(__file__))},
                limits=['Same development seed29/state2400; not independent-seed evidence.',
                        'Aggregate approximation;52 absolute stock direction still wrong at3300.',
                        'Agreement of large components does not qualify a near-zero net sign or candidate ranking.',
                        'Discrete actual-command response; AD/continuous objective and full wall remain separate.'])
    assert result['both_same_caps_feasible']
    (A/'isolated_pair_assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('large_tradeoff_directions_pass','predicted_added_merge_veh',
          'native_added_merge_veh','predicted_cost_delta_veh_h','scalar_seconds')},indent=2))


if __name__=='__main__':main()
