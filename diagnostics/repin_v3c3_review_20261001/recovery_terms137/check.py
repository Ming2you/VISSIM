"""Reuse the validated134 lane ledger on downstream cells, cached data only."""
import ast
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.onset_reaction134 import check as prior
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'status.json').exists(), 'No automatic retry'
    source=Path(prior.__file__).read_text(encoding='utf-8')
    # Keep the frozen134 helper and its fitting pins intact. Execute that same
    # diagnostic with only the cell scope and the second merge changed.
    replacements={
        'cells=[19,20,21]':'cells=[22,23,24,25]',
        "a['cell'] in (19,20,21)":"a['cell'] in (22,23,24,25)",
        'for cell in (19,20,21):':'for cell in (22,23,24,25):',
        "if cell==21 and lane==1 and case=='s67_late':":"if cell in (21,23) and lane==1 and case=='s67_late':",
        "sum(e['cell']==21 and e['road']=='FW_E'":"sum(e['cell']==cell and e['road']=='FW_E'",
        "merge_known=(cell!=21 or lane!=1 or case=='s67_late')":"merge_known=(cell not in (21,23) or lane!=1 or case=='s67_late')",
        "previous_goal_turn='NO_PROGRESS: explained existing131/132 evidence only; revalidated133 completed and no live owned processes.'":"previous_goal_turn='PROGRESS:136 exact VSL target/exposure replays confirmed active approach exposure;135 structural speed cap candidate failed. Current137 is a new downstream native-state diagnostic.'",
        "question='Do first30/150s lane19-21 recovery errors arise from population turnover, lateral composition, or same-vehicle acceleration? Compare132 coefficients at current native states in110 arms.'":"question='Do cells22-25 themselves under-recover at current observed states, or is autonomous slowing primarily propagated through wrong states? Reuse134 population ledger; include actual23 merge only as conditional diagnosis.'"
    }
    counts={}
    for old,new in replacements.items():
        counts[old]=source.count(old);assert counts[old]>=1,old
        source=source.replace(old,new)
    ast.parse(source)
    h.save(HERE/'transformation.json',dict(original_file=prior.__file__,original_sha256=h.sha(prior.__file__),changes=replacements,occurrences=counts,
        limits='No production changes, no autonomous forecast, no fitting. Original134 limitations still apply.23 merge flux uses following5s observed arrivals only for conditional causal separation, not operational prediction.'))
    (HERE/'executed_diagnostic.py.txt').write_text(source,encoding='utf-8')
    namespace=dict(prior.__dict__);namespace['__name__']='recovery_terms137_diagnostic';namespace['__file__']=str(HERE/'executed_diagnostic.py.txt')
    exec(compile(source,namespace['__file__'],'exec'),namespace)
    namespace['main']()


if __name__=='__main__':main()
