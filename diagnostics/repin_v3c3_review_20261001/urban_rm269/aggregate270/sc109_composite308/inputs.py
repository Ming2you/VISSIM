import hashlib, json, pickle
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.candidate import LINK
from evaluation.controllers import vissim_stackelberg_adapter as adapter
HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
RAW=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_002400.json')
def inputs():
    proof=json.loads((A/'sc12_phase305/current_projection.json').read_bytes())
    for p,h in proof['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h: raise ValueError('Evidence source changed: '+p)
    cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    raw=json.loads(RAW.read_bytes()); frame_path=RAW.parent/raw['obs150']['frames']['current']['path']
    assert hashlib.sha256(frame_path.read_bytes()).hexdigest()==raw['obs150']['frames']['current']['sha256']
    frame=json.loads(frame_path.read_bytes())
    tuning=json.loads((A/'flow279/config_10686_free.json').read_bytes())
    membership_path=ROOT/tuning['control_area_objective']['membership_path']
    membership=json.loads(membership_path.read_bytes())
    assert LINK in membership['inside_links'] or int(LINK) in membership['inside_links']
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    return cfg,state,raw,frame,network.read_bytes(),True,adapter._contiguous_stopline_queue(raw,per_lane=True)
