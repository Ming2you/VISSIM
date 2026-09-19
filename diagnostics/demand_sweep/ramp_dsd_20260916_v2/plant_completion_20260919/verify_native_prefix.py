"""Read-only data-row comparison after the integration smoke test has ended."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent

def payload(path):
    with path.open('rb') as f:
        for line in f:
            if line.startswith(b'$VEHICLE:'):break
        else:raise ValueError('Missing native vehicle header')
        for line in f:
            if line.strip():yield line

def main():
    tested=HERE/'native_smoke_v1/run_both_retry/vissim_eval/baseline_001.fzp'
    reference=H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp'
    baseline=payload(reference);digest=hashlib.sha256();count=0;last=None
    for count,row in enumerate(payload(tested),1):
        old=next(baseline,None)
        if row!=old:raise AssertionError(('Native FZP first difference',count,row,old))
        digest.update(row);last=float(row.split(b';',1)[0])
    if last!=1050:raise AssertionError(('Unexpected final native frame',last))
    result={'passed':True,'reference':str(reference),'tested':str(tested),
        'data_rows_exact':count,'last_sec':last,'data_payload_sha256':digest.hexdigest(),
        'scope':'Entire 0-1050s smoke FZP payload exactly equals the existing no-control prefix; headers excluded'}
    with (HERE/'native_prefix.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
