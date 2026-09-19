"""Compare executed signal states and every FZP row before intervention."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.fast_fixed_profile_verify import verify

def main():
    bank=HERE/'native_s33_v1';result={}
    for arm in ['none','rm_ramp','vsl','both']:
        run=bank/f'run_{arm}'
        receipt=json.loads((run/'run.json').read_text(encoding='utf-8-sig'))
        assert receipt['completed'] and receipt['terminal_sec']==4500 and not receipt['owned_native_alive']
        result[arm]=verify(bank/f'prepared_{arm}',run,bank/'run_none' if arm!='none' else None)
        print(arm,'native signal/readback/prefix PASS',flush=True)
    with (bank/'paired_verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)

if __name__=='__main__':main()
