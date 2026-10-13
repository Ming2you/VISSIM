"""Pin two fixed-action decompositions; retain prior evidence and live queue."""
import difflib, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=HERE/'plan.json'
    assert not out.exists(), 'No duplicate preparation'
    old=read(H/'native_beta/plan.json')['source_pins']
    old={**old,**read(H/'native_beta/forecast2400_checked/summary.json')['source_pins']}
    core=ROOT/'evaluation/controllers/head_service_resources.py'
    before=H/'sc109_service/head_service_resources.before.py.txt'
    assert sha(before)==old[str(core)]
    for p,d in old.items():
        if Path(p)!=core:assert sha(Path(p))==d,p
    patch=''.join(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),core.read_text(encoding='utf8').splitlines(True)))
    (HERE/'additive_v12_review.patch').write_text(patch,encoding='utf8')
    # The reviewed addition only permits the opt-in10286/v12 contract. Baseline
    # remains v11; canonical initialization will compare its network and state.
    pins={p:sha(Path(p)) for p in old}
    for p in (Path(__file__),HERE/'forecast.py',before,H/'native_beta/forecast2400_checked/summary.json',
              H/'native_beta/forecast2400_checked/state.json',H/'native_beta/forecast2400_checked/network.json'):
        pins[str(p)]=sha(p)
    for arm in ('hold','selected'):
        for at in (2400,2550,2700):
            for suffix in ('json','csv'):
                p=H/'selection2400_discrete'/arm/f'action_{at:06}.{suffix}'
                pins[str(p)]=sha(p)
    doc=dict(status='prepared',max_forecasts=2,full_selection_calls=0,native_launches=0,
        preparation_failure='First preparation looked for a runtime core pin in the config plan; corrected to merge the separate forecast pins. No initialization or forecast had started.',
        base_config=str(H/'native_beta/config.json'),reuse=['native_beta/forecast2400_checked/hold.json','native_beta/forecast2400_checked/selected.json'],
        source_pins=pins,preserve=['same2400observedstate','same450horizon/3blocks','sameNP/NUFcap','sameVSL','sameOmega701TTT','terminalOFF'],
        scope='Model-only city/RM action decomposition; no separate native causal identification.',
        inactive_core_change='Additive v12 support only; v11 contract retained;28regressions passed. Verify initialized serialized state/network against prior before forecasts.')
    out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Prepared exactly two450s forecasts; no native/optimizer')

if __name__=='__main__':main()
