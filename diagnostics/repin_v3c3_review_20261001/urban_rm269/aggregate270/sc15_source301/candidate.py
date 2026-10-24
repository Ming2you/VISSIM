"""Offline-only past-supported SC15 source service, composed with299."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib,json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_clock299 import candidate as prior

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
validate_turns,west,east=prior.validate_turns,prior.west,prior.east


def document():
    value=json.loads((HERE/'calibration.json').read_bytes())
    assert value['status']=='complete_past_queue_platoon_and_source_turn_support'
    for p,h in value['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Source301 calibration evidence changed')
    return value


def install(cfg,cutoff,calibration):
    if calibration['route_followup_end']>=cutoff or calibration['training_head_window'][1]>=cutoff:
        raise ValueError('Calibration must precede this prediction initial state')
    updated=[];metadata={}
    for spec in cfg.network.route_choice_corridor['corridors']:
        inp=next((k for k in calibration['inputs'] if k in spec.get('generated_inputs',{})),None)
        if inp is None:continue
        value=calibration['inputs'][inp];native=spec['native_fixed_service']
        if (spec['decision']!=value['decision'] or spec['decision_link']!=str(value['source_link'])
            or str(native['controller'])!='15' or native['signal_group']!=value['sg']
            or native['calibrated_service_veh_h']!=value['old_rate_veh_h']):
            raise ValueError('SC15 physical/prior source identity changed')
        rate=value['selected_service_veh_h']
        if not value['measurement_lower_veh_h']<=rate<=value['measurement_upper_veh_h']:
            raise ValueError('Selected source rate outside measured timing bounds')
        updated.append((native,rate))
        metadata[inp]=dict(old=native['calibrated_service_veh_h'],new=rate,
            gap_count=value['gaps'],head_fit_end=calibration['training_head_window'][1])
    if set(metadata)!=set(calibration['inputs']):raise ValueError('Missing/duplicate SC15 source')
    for native,rate in updated:native['calibrated_service_veh_h']=rate
    cfg.network.sc15_source301=metadata
    return deepcopy(metadata)


@contextmanager
def hook(option):
    with prior.hook(option) as side:
        from evaluation.controllers import regular_alias_service
        original=regular_alias_service.configure
        calibration=document()
        def configure(cfg,tuning,raw):
            base=original(cfg,tuning,raw)
            return {**base,'diagnostic_sc15_source301':install(cfg,int(raw['sim_sec']),calibration)}
        regular_alias_service.configure=configure
        try:yield side
        finally:regular_alias_service.configure=original
