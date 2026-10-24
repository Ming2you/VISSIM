"""Recalculate184 observed-state budgets from immutable cached vehicle frames."""
from pathlib import Path
import ast
import gzip
import hashlib
import json
import math
import statistics

HERE=Path(__file__).resolve().parent
R=HERE.parent


def load(path):
    with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as f:
        return json.load(f)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out=HERE/'attempt3'
    result=load(out/'analysis.json');protocol=load(out/'protocol.json');rows=load(out/'rows.json')
    assert result['status']=='complete' and len(rows)==360
    assert protocol['budget']==dict(forecasts=0,fits=0,native=0,FZP_reads=0)
    checks=0;maximum=0.
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        source=load(R/f'blocking176/{arm}_frames.json.gz');ix={k:i for i,k in enumerate(source['fields'])}
        for z in [z for z in rows if z['arm']==arm]:
            frame=source['frames'][str(z['time_s'])]
            counts=[sum(v[ix['cell']]==21 and v[ix['lane']]==g for v in frame.values()) for g in (1,2,3)]
            assert counts==z['n21']
            for name,p in result['parameters'].items():
                for g,n in enumerate(counts):
                    # Independent triangular receiving equation, no imported
                    # plant function or saved per-step budget as predictor.
                    density=n/p['length_km']
                    expected=5*max(0.,min(p['jam']*p['length_km']-n,
                        p['capacity_vph']/3600.,p['wave_kmh']*(p['jam']-density)/3600.))
                    error=abs(expected-z['receiving'][name][g]);maximum=max(maximum,error)
                    assert error<1e-10
                    checks+=1
    for window in result['native']:
        zs=[z for z in rows if z['arm']==window['arm'] and window['start']<=z['time_s']<window['end']]
        assert len(zs)==30
        for g in range(3):
            assert abs(statistics.mean(z['n21'][g] for z in zs)-window['mean_n21_by_lane'][g])<1e-12
        for key in ('cross_all','merge','off','exit_request','through_request'):
            assert abs(sum(z[key] for z in zs)-window[key])<1e-9
        for name in result['parameters']:
            for g in range(3):
                assert abs(sum(z['receiving'][name][g] for z in zs)-window['receiving'][name][g])<1e-9
    for path,digest in result['input_sha256'].items():assert sha(Path(path))==digest,path
    for path,digest in protocol['protected_sha256'].items():assert sha(Path(path))==digest,path
    assert sha(Path(protocol['STOP']['path']))==protocol['STOP']['sha256']
    # The old182 analyzer's original main remains the same AST.
    def main_ast(path):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return ast.dump(next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main'))
    assert main_ast(HERE/'completed182_analyze.py.txt')==main_ast(R/'flowbudget182/analyze.py')
    summary=dict(status='verified',observed_receiving_checks=checks,max_receiving_error=maximum,
        native_windows=12,old182_main_unchanged=True,pins_and_STOP=True,
        final_rows_format='Plain JSON at attempt3/rows.json; attempt2 misnamed plain JSON preserved.',
        adopted=False,operational_forecast=False,full_goal='ACTIVE_NOT_QUALIFIED',
        source_sha256=sha(Path(__file__)))
    (HERE/'verification.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':main()
