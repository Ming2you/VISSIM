"""Bounded canonical bootstrap checks; no current/future native run mutation."""
from pathlib import Path
import argparse,importlib.util,json,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]

def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=('window','optimized','off'),required=True)
    p.add_argument('--at',type=int,required=True);p.add_argument('--mode',choices=('initial','response','full'),required=True)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    sys.argv=['verify.py','--at',str(args.at),'--out',str(args.out),'--tuning',str(HERE/(args.arm+'_config.json')),
        '--decisions','E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29']
    sys.argv+=['--full-selection'] if args.mode=='full' else ['--cold-prices','--no-prediction' if args.mode=='initial' else '--single-prediction']
    spec=importlib.util.spec_from_file_location('native348_verify',ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py')
    verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
    if args.mode=='response':
        from evaluation.controllers.sdmpc_tangent_surrogate import Query
        original=Query.evaluate;seen=[]
        def compare(self,actions,*,derivatives=False):
            scalar=original(self,actions,derivatives=derivatives)
            if derivatives:return scalar
            if seen:raise ValueError('Only one bounded scalar/AD pair')
            ad=original(self,actions,derivatives=True)
            assert len(scalar)==len(ad)==1
            x,y=scalar[0],ad[0]
            costs=x['sdmpc_omega_partition']['costs'];other=y['sdmpc_omega_partition']['costs']
            assert set(costs)==set(other)
            errors={k:abs(costs[k]-other[k]) for k in costs}
            error=abs(x['objective_veh_h']-y['objective_veh_h'])
            assert max([error,*errors.values()])<1e-8
            proof=dict(status='passed',objective_veh_h=x['objective_veh_h'],objective_difference=error,
                owner_cost_max_difference=max(errors.values()),arm=args.arm,at_sec=args.at,
                source='Canonical runtime bootstrap; current observations only; fixed historical calibration',
                native_runs=0)
            (args.out/'scalar_ad.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
            seen.append(proof)
            return scalar
        Query.evaluate=compare
    verify.main()

if __name__=='__main__':main()
