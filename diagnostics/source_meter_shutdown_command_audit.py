"""Serialize the two saved meter arms with the canonical CSV writer, no rollout."""
import copy,csv,json,pickle
from diagnostics.source_meter_shutdown_diagnosis import ROOT,RUN,CONFIG,OUTPUT,load,sha,adapter,build_projected,area_meter_finalization,ControlAction
from diagnostics.audit_live_prediction_interval import command_roundtrip
from diagnostics.probe_model_area_integration import replay_provenance

def main():
    report=load(OUTPUT);dec=ROOT/'evaluation/runs'/RUN/('decisions_'+RUN)
    cfg,state,det,tuning,raw,mapping,meta=build_projected(CONFIG,dec/'state_001200.json',dec/'action_001050.json',fixture_inputs=False)
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    paths=[ROOT/p for p in report['source_sha256']]+[OUTPUT,ROOT/'diagnostics/audit_live_prediction_interval.py',__file__,dec/'action_001200.csv']
    before=replay_provenance(tuning,*paths);out={}
    action_json=load(dec/'action_001200.json');original=adapter.control_from_json(dec/'action_001200.json',cfg,ControlAction)
    with (dec/'action_001200.csv').open(encoding='utf-8-sig',newline='') as f:columns=next(csv.reader(f))
    physical_columns=[c for c in columns if c!='metadata']
    for name,arm in report['paired'].items():
        control=original.copy()
        if name!='recorded_closed':control.ramp_metering.update(R_D_W=1800.,R_F_E=1800.)
        area_meter_finalization.finalize(control,cfg);control.N_UF_star=sum(control.ramp_metering.values())
        assert control.ramp_metering==arm['meters_vph'] and control.N_UF_star==arm['N_UF_star_vph']
        untouched=pickle.dumps(control,protocol=5)
        result=command_roundtrip(control,cfg,mapping,calibration,tuning,copy.deepcopy(action_json),dec/'action_001200.csv')
        assert pickle.dumps(control,protocol=5)==untouched
        changed=[dict(zip(physical_columns,row)) for row in result['missing_rows']]
        old=[dict(zip(physical_columns,row)) for row in result['extra_rows']]
        if name=='recorded_closed':assert result['physical_columns_exact']
        else:
            expected={'RM_C10480','RM_C10482','RM_C10639','RM_C10681'}
            assert len(changed)==len(old)==4 and {r['id'] for r in changed}==expected
            assert all(r['kind']=='ramp_meter' and float(r['green_sec'])==10. for r in changed)
            assert all(r['kind']=='ramp_meter' and float(r['green_sec'])==0. for r in old)
        out[name]={'canonical_writer_comparison_to_actual1200':result,'changed_physical_rows':changed,'original_changed_rows':old,
                   'only_expected_meter_rows_change':True,'input_action_unchanged':True}
    result={'schema':'source-meter-shutdown-command/v1','arms':out,'source_sha256':before,
            'source_changes':[p for p,h in before.items() if sha(ROOT/p)!=h]}
    assert not result['source_changes']
    path=ROOT/'diagnostics/source_meter_shutdown_command_audit.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','arms':list(out),'source_changes':[]}))

if __name__=='__main__':main()
