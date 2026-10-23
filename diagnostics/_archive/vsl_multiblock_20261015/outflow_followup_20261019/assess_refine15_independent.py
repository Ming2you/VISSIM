"""Compare the frozen correction against original coefficients on reserved seeds."""
import hashlib,json,math,os,sys
from pathlib import Path
os.environ['PYTHONDONTWRITEBYTECODE']='1'
A=Path(__file__).resolve().parent;ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015');PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def rmse(xs):return math.sqrt(sum(x*x for x in xs)/len(xs))
def main():
    out=A/'refine15_independent_assessment.json';assert not out.exists()
    actual=read(A/'independent_approach.json')['rows'];rows=[];absolute=[]
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    c=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json');rt=route.compile_inventory(c,read(ROOT/c['mapping']['path']));bs=rt['bounds']['FW_E']
    def spatial(path):
        raw=read(path);groups=[[] for _ in range(7)]
        assert raw['vehicle_records']['complete']
        for v in raw['vehicle_records']['records']:
            p=rt['physical'].get(str(v['link_no']))
            if p is None or p[0]!='FW_E' or not bs[14]<=p[1]+v['position_m']<bs[19]:continue
            road,pos,i=route._position(rt,v['link_no'],v['position_m']);j=0 if i==14 else (1+min(2,int(3*(pos-bs[15])/(bs[16]-bs[15]))) if i==15 else i-12)
            groups[j].append(v['speed_kph'])
        assert all(groups)
        return dict(n=[len(g) for g in groups],speed=[sum(g)/len(g) for g in groups])
    for seed,arms in ((67,('release','release_vsl90')),(71,('rm','both'))):
        folder=A/f'refine15_independent_s{seed}';summary=read(folder/'summary.json')
        for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        replay=read(folder/'fixed_replay_receipt.json');observed_delta=read(Path(f'E:/VISSIM_analysis/20261011_vsl_response349/matched_seed{seed}_v3/matched_assessment.json'))['native_delta']['omega']
        for variant in ('original','fitted'):
            left,right=[summary['results'][f'{variant}_{arm}'] for arm in arms]
            snaps={arm:read(folder/f'{variant}_{arm}_snapshots.json') for arm in arms}
            for j,t in enumerate((150,300,450),1):
                a=next(r for r in actual if r['seed']==seed and r['horizon']==t)
                n=sum(snaps[arms[1]][j]['n']['FW_E'][14:19])-sum(snaps[arms[0]][j]['n']['FW_E'][14:19])
                rows.append(dict(seed=seed,variant=variant,horizon=t,native_flow=a['native_through18'],predicted_flow=right['throughflow'][j-1]-left['throughflow'][j-1],native_stock=a['native_approach_n'],predicted_stock=n,
                    native_omega=observed_delta if t==450 else None,predicted_omega=right['ttt']-left['ttt'] if t==450 else None))
            for arm in arms:
                errors={k:[] for k in ('n','speed')};native_folder=Path(replay['candidate_actions'][arm][0]).parent
                for j,t in enumerate((150,300,450),1):
                    truth=spatial(native_folder/f"state_{summary['start']+t:06d}.json");snap=snaps[arm][j];r=snap['refinement']
                    pred=dict(n=[snap['n']['FW_E'][14],*[sum(x.values()) for x in r['routes']],*snap['n']['FW_E'][16:19]],speed=[snap['speed']['FW_E'][14],*r['speed'],*snap['speed']['FW_E'][16:19]])
                    for key in errors:errors[key].extend(x-y for x,y in zip(pred[key],truth[key]))
                absolute.append(dict(seed=seed,arm=arm,variant=variant,stock_rmse=rmse(errors['n']),speed_rmse=rmse(errors['speed'])))
    result=dict(status='completed_frozen_independent_assessment',rows=rows,absolute=absolute,new_forecasts=0,new_native=0,new_fits=0,source_pins=PINS,candidate_adopted=False,goal_complete=False,
        limitations=['Seeds are excluded from this parameter fit; historical outcomes were already seen during model development, so this is not blind validation.','Observed detector lies inside connector; model is upstream face. Existing face-location limitation preserved.','Different VSL footprints; only within-pair contrasts are compared.','Scalar prediction checks do not validate AD, NP/NUF optimization or policy performance.'])
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(rows=[r for r in rows if r['horizon']==450],absolute=absolute),indent=2))
if __name__=='__main__':main()
