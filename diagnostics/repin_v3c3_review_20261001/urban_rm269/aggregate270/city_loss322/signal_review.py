"""Check native green exposure separately from retained model operands."""
import json,hashlib
from pathlib import Path
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322 import audit

HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'signal_review.json';assert not out.exists()
    report=json.loads((HERE/'assessment.json').read_bytes())
    pins={str(HERE/'assessment.json'):hashlib.sha256((HERE/'assessment.json').read_bytes()).hexdigest()}
    result={}
    # Actual SG identity: SC6 south through/right=8; SC101 through=8; SC16 north left=7.
    for arm,folder in audit.RUNS.items():
        stem=folder.name.removeprefix('decisions_')
        paths={sc:folder.parent/'vissim_eval'/f'{stem}_{sc}_001.ldp' for sc in (6,101,16)}
        native=read_ldp_frames(paths,{sc:list(range(1,9)) for sc in paths},2100,2850)
        assert len(native['frames'])==751
        pins.update({p:v['sha256'] for p,v in native['pins'].items()})
        result[arm]={}
        for group,sc,sg in [('SC6_S',6,8),('SC101_S',101,8),('SC16_N_left',16,7)]:
            rows=[]
            for n in report['native'][arm][group]:
                t=n['start_sec'];greens=sum(native['frames'][x][f'{sc}:{sg}']=='GREEN' for x in range(t,t+150))
                m=next((b for b in report['model'][arm][group]['blocks'] if b['start_sec']==t),None)
                model_green=sum(next(iter(x['movements'].values()))['green_sec'] for x in m['ticks']) if m else None
                rows.append(dict(start_sec=t,native_green_sec=greens,model_green_sec=model_green,
                    native_count=n['count'],achieved_count_per_green_hour=3600*n['count']/greens if greens else None))
            result[arm][group]=rows
    pins[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    review=dict(status='complete_native_green_exposure_separated',arms=result,source_pins=pins,
        limits=['Achieved count per green hour is not a fitted or universal saturation rate.',
            'Native LDP states are sampled at1s; green endpoints need not equal model interval accounting exactly.',
            'This checks selected signal groups, not all actuator execution.'])
    out.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,r in result.items():
        print(arm,{k:[(x['native_count'],x['native_green_sec'],x['model_green_sec']) for x in v] for k,v in r.items()})

if __name__=='__main__':main()
