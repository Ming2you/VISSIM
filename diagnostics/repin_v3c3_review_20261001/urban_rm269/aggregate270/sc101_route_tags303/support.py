"""Build source-specific aggregate category shares without imputing observed routes."""
import hashlib,json,pickle
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE.parent;ROOT=HERE.parents[4]
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
MOVEMENTS={"straight":"SC101_S_SC1_to_N_SC2005","right":"SC101_S_SC1_to_E_SC5","left":"SC101_S_SC1_to_W_SC1002"}

def main():
    assert not (HERE/"support.json").exists()
    cal=read(A/"sc15_source301/calibration.json")
    for p,h in cal["source_pins"].items():assert sha(p)==h,p
    cfg,_,_=pickle.loads((A/"citysplit287/forecast2400/initial.pickle").read_bytes())
    specs={m:s for m,s in cfg.network.urban_movements.items() if s.get("origin")=="SC1_to_SC101"}
    assert set(specs)==set(MOVEMENTS.values())
    beta={kind:specs[m]["beta"] for kind,m in MOVEMENTS.items()}
    assert abs(sum(beta.values())-1)<1e-10
    sources={}
    for inp,decision,lane in (("1086","1099",4),("1087","1100",1)):
        r=cal["inputs"][inp];counts={k:r["route_counts"].get(k,0) for k in (*MOVEMENTS,"unresolved")}
        n=sum(counts.values());assert n>0
        shares={k:v/n for k,v in counts.items()}
        implied={k:shares[k]+shares["unresolved"]*beta[k] for k in MOVEMENTS}
        for k,v in implied.items():
            lohi=r["route_share_identification_bounds"][k]
            assert lohi["lower"]-1e-12<=v<=lohi["upper"]+1e-12
        sources[decision]=dict(input=inp,entry_lane=lane,counts=counts,n=n,category_shares=shares,
            effective_route_shares_if_prior_used=implied,identified_bounds=r["route_share_identification_bounds"])
    paths=[HERE/"plan.json",Path(__file__),A/"sc15_source301/calibration.json",
           A/"sc15_source301/completion.json",A/"sc101_peeloff302/completion.json",
           A/"citysplit287/forecast2400/initial.pickle",
           A.parent.parent/"upstream_worklog/02_urban_b2/diag_c3_r2/U7.md"]
    out=dict(schema="aggregate-source-route-support303/v1",receiver="SC1_to_SC101",
        movements=MOVEMENTS,base_beta=beta,sources=sources,fit_window=cal["training_head_window"],
        route_followup_end=cal["route_followup_end"],validation_start=2400,
        unresolved_policy="Keep explicit unresolved mass and distribute it using existing receiving-node beta at arrival; not an observed route or an identified probability.",
        assumptions=["Source-specific observed proportions transfer from the past period to the new accepted flow.",
                     "Unobserved route outcomes may be non-random; baseline-beta allocation is a modelling prior.",
                     "Source entry lane supports route distinction but no individual lane-change outcome is predicted."],
        source_pins={str(p):sha(p) for p in paths})
    (HERE/"support.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    for k,r in sources.items():print(k,"known+unknown",r["category_shares"],"effective_with_prior",r["effective_route_shares_if_prior_used"])

if __name__=="__main__":main()

