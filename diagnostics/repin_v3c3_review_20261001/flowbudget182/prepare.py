"""Freeze four non-mutating replays; preserve the prior executed runner."""
from pathlib import Path
import copy
import hashlib
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists()
    prior=h.R/'phase_equilibrium181'
    runner=h.R/'state_lateral168/run.py'
    # Recover the immediately prior runner from its archived predecessor and
    # the exact181 patch. Accept it ONLY if its bytes match the executed pin.
    code=(prior/'completed179_runner.py.txt').read_text(encoding='utf-8')
    changes=[
        ('def queue178(*, transport_once179=False):','def queue178(*, transport_once179=False, phase_equilibrium181=False):'),
        ("    work=h.R/('transport_once179' if transport_once179 else 'queue_dynamics178');out=work/'forecast'",
         "    reuse_baseline=transport_once179 or phase_equilibrium181\n    prior_phase='transport_once179' if phase_equilibrium181 else 'queue_dynamics178'\n    prior_label='old179' if phase_equilibrium181 else 'old178'\n    work=h.R/('phase_equilibrium181' if phase_equilibrium181 else ('transport_once179' if transport_once179 else 'queue_dynamics178'));out=work/'forecast'"),
        ("        if transport_once179:\n            old178=h.read(h.R/'queue_dynamics178/executed_function_sources.json')", "        if reuse_baseline:\n            old178=h.read(h.R/prior_phase/'executed_function_sources.json')"),
        ("cls.__init__=observed_old;classes['old178']=cls","cls.__init__=observed_old;classes[prior_label]=cls"),
        ("if transport_once179 and mode=='baseline':","if reuse_baseline and mode=='baseline':"),
        ("lanes.RouteLaneRegion=classes['old178']","lanes.RouteLaneRegion=classes[prior_label]"),
        ("path=h.R/'queue_dynamics178/forecast/queue'/f", "path=h.R/prior_phase/'forecast/queue'/f"),
        ("h.save(out/'old178_parity.json',parity)","h.save(out/(prior_label+'_parity.json'),parity)"),
        ('if forecasts==1 and not transport_once179:','if forecasts==1 and not reuse_baseline:'),
        ('assert forecasts==(13 if transport_once179 else 24)','assert forecasts==(13 if reuse_baseline else 24)'),
        ("    parser.add_argument('--transport-once179',action='store_true')", "    parser.add_argument('--transport-once179',action='store_true')\n    parser.add_argument('--phase-equilibrium181',action='store_true')"),
        ('if args.queue178 or args.transport_once179:','if args.queue178 or args.transport_once179 or args.phase_equilibrium181:'),
        ('        assert not (args.queue178 and args.transport_once179)\n        queue178(transport_once179=args.transport_once179)',
         '        assert sum((args.queue178,args.transport_once179,args.phase_equilibrium181))==1\n        queue178(transport_once179=args.transport_once179,phase_equilibrium181=args.phase_equilibrium181)'),
    ]
    for old,new in changes:
        assert code.count(old)==1,(old,code.count(old));code=code.replace(old,new)
    expected=h.read(prior/'forecast/preservation.json')['input_sha256'][str(runner)]
    variants=[code.encode('utf-8'),code.replace('\n','\r\n').encode('utf-8')]
    matches=[b for b in variants if hashlib.sha256(b).hexdigest()==expected]
    assert matches,'Do not claim an unverified reconstructed archive'
    archive=HERE/'completed181_runner.py.txt';archive.write_bytes(matches[0])
    h.save(HERE/'source_archive.json',dict(path=str(runner),archive=str(archive),historical_sha256=expected,
        recovered_from='181 archived179 runner plus exact181 patch; byte hash matches executed181 pin'))
    for name in ('executed_function_sources.json','spec.json','coefficients.json'):
        (HERE/name).write_bytes((prior/name).read_bytes())
    protocol=copy.deepcopy(h.read(prior/'protocol.json'))
    protocol.update(previous_goal_turn='PROGRESS181: equilibrium interpretation tested and rejected; speed ledger points to accumulated state and transport.',
        hypothesis='Locate current-model inventory errors in source/merge/through/off flow budgets and active receiving constraints without changing physics.',
        scope='Same67 initial state, release110/90, baseline and181; four exact replays with post-plan read-only instrumentation.',
        budget=dict(autonomous450_max=4,new_fits=0,native=0,FZP=0),
        gates='Exact cells/flows/ports/ramps equality with completed181 for all4; per-lane and aggregate conservation, native budget reconciliation. No candidate adoption.')
    h.save(HERE/'protocol.json',protocol)
    pins={str(Path(__file__)):h.sha(__file__),str(prior/'protocol.json'):h.sha(prior/'protocol.json')}
    for name in ('executed_function_sources.json','spec.json','coefficients.json'):
        pins[str(prior/name)]=h.sha(prior/name)
    h.save(HERE/'pins.json',pins)
    print('182 frozen4 exact diagnostic replays; archived181 bytes verified.')


if __name__=='__main__':main()
