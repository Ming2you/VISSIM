"""Use the existing passive flow audit on the baseline and rejected210 model."""
import copy
import ctypes
import json
from pathlib import Path
import time
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
OUT=h.R/'phase_joint183/supply211'


def prepare():
    assert not OUT.exists()
    previous=h.R/'phase_joint183/restart210/train'
    protocol=copy.deepcopy(h.read(previous/'protocol.json'))
    protocol.update(previous_goal_turn='PROGRESS210: bounded restart ablation rejected; slow subset falls but total cell20 inventory remains high.',
        hypothesis='Trace whether residual high cell20 inventory comes from actual accepted arrivals, downstream receiving/merge allocation, shared exit loss or insufficient request.',
        fit='None. Unchanged baseline and completed210 ablation replayed with passive existing182 audit.',
        train='Four29late saved cases; every cells/flows/ports/ramps table must match its completed reference exactly.',
        validation='No new validation case or gain candidate; this is an execution-path audit.',
        budget=dict(audited450=8,fits=0,native=0,FZP=0),
        scope211='All-lane native cell19--21 conservation versus lane-resolved model supply. Native endpoint lanes do not determine every microscopic crossing lane.')
    h.save(HERE/'protocol.json',protocol)
    pins=h.read(previous/'pins.json')
    for name in ('state_lateral168/run.py','flowbudget182/analyze.py'):
        pins[str(h.R/name)]=h.sha(h.R/name)
    for label,structure,reference in [('baseline','baseline',h.R/'phase_equilibrium181/forecast/baseline'),
                                       ('ablation','queue',previous/'forecast/queue')]:
        folder=OUT/label;folder.mkdir(parents=True)
        for name in ('spec.json','coefficients.json','executed_function_sources.json'):
            h.save(folder/name,h.read(previous/name))
        h.save(folder/'protocol.json',protocol);h.save(folder/'pins.json',pins)
        h.save(folder/'setting.json',dict(manifest=str(h.R/'lane_state132/eval_01/manifest.json'),
            structure=structure,records='train',flow_audit182=True,audit_reference_dir=str(reference)))
    h.save(HERE/'source_pins.json',pins)


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (HERE/'completion.json').exists()
    from diagnostics.repin_v3c3_review_20261001.state_lateral168.run import queue178
    from diagnostics.repin_v3c3_review_20261001.flowbudget182.analyze import main as analyze
    records=[r for r in h.read(h.C/'data_catalog.json')['checked_records'] if r['case']=='s29_late']
    assert len(records)==4 and all(abs(r['cutoff']-2670.1)<1e-8 for r in records)
    dirs={r['arm']:r['truth'] for r in records}
    started=time.perf_counter()
    for label,mode in [('baseline','baseline'),('ablation','queue')]:
        folder=OUT/label
        queue178(calibration183=folder)
        analyze(work=folder,case='s29_late',arms=tuple(dirs),modes=(mode,),observation_dirs=dirs)
    core=h.read(h.R/'restart_supply210/protocol.json')['source_sha256']
    stop=h.read(HERE/'protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items())
    assert h.sha(stop['path'])==stop['sha256']
    completion=dict(status='COMPLETE_PASSIVE_FLOW_AUDIT',audited450=8,fits=0,
        new_physical_candidates=0,native=0,FZP_reads=0,core_preserved=len(core),
        old_STOP_preserved=True,seconds=time.perf_counter()-started,
        adopted=False,goal='ACTIVE_NOT_QUALIFIED')
    h.save(HERE/'completion.json',completion)
    print(json.dumps(completion))


if __name__=='__main__':
    import sys
    if '--prepare' in sys.argv:prepare()
    else:main()
