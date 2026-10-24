"""Read only the short mismatching FZP tail, after the exact block comparison."""
from collections import Counter
from pathlib import Path
import json
import pandas as pd
from analyze_cooldown import ROOT, OUT, load, save, data_start

def tail(path, offset):
    records={}
    with path.open('rb') as f:
        start,_=data_start(f)
        f.seek(start+max(0,offset-1000000))
        f.readline()  # Skip a partial row; this is earlier than the proven first difference.
        for raw in f:
            values=raw.decode('ascii').rstrip().split(';')
            sec=int(float(values[0]))
            if sec>5400: break
            records[sec,int(values[1])]=values
    return records

def main():
    validation=load(OUT/'validation.json')
    evidence={}
    all_changes=[]
    for pct in (80,90):
        case=f'fw{pct:03d}_urban050'
        proof=validation['conditions'][str(pct)]['original_fzp_prefix']
        old=ROOT/f'evaluation/runs/fast_nc_{case}_s13_v1/vissim_eval/baseline_001.fzp'
        new=ROOT/f'evaluation/runs/fast_nc_{case}_s13_9000_v1/vissim_eval/baseline_001.fzp'
        a=tail(old,proof['first_difference_payload_byte'])
        b=tail(new,proof['first_difference_payload_byte'])
        keys=a.keys()&b.keys()
        changed=[k for k in sorted(keys) if a[k]!=b[k]]
        missing=sorted(a.keys()-b.keys());extra=sorted(b.keys()-a.keys())
        fw={74,10699,2,10613,119,10702,24,26,10771,120}
        differences=[]
        for k in changed:
            x,y=a[k],b[k]
            differences.append(dict(freeway_percent=pct,sec=k[0],vehicle=k[1],old_link=int(x[2]),new_link=int(y[2]),
                old_lane=int(x[3]),new_lane=int(y[3]),old_pos=float(x[4]),new_pos=float(y[4]),old_speed=float(x[6]),new_speed=float(y[6])))
        all_changes.extend(differences)
        original_area=pd.read_csv(ROOT/f'diagnostics/demand_sweep/{case}/results/area_timeseries.csv')
        extended_area=pd.read_csv(ROOT/f'diagnostics/demand_sweep/{case}_cooldown9000/results/area_timeseries.csv')
        extended_area=extended_area[extended_area.sim_sec<=5400]
        assert list(original_area.columns)==list(extended_area.columns)
        numeric_columns=original_area.select_dtypes(include='number').columns
        numeric_delta=(original_area[numeric_columns].reset_index(drop=True)-extended_area[numeric_columns].reset_index(drop=True)).abs().max().to_dict()
        evidence[str(pct)]=dict(first_difference_sec=changed[0][0],first_difference_vehicle=changed[0][1],
            first_original_row=a[changed[0]],first_extended_row=b[changed[0]],
            exact_complete_frames_through_sec=changed[0][0]-1,changed_rows=len(changed),changed_vehicle_count=len({k[1] for k in changed}),
            changed_original_links=dict(Counter(a[k][2] for k in changed)),missing_keys=missing,extra_keys=extra,
            changed_mainline_rows=sum(int(a[k][2]) in fw or int(b[k][2]) in fw for k in changed),
            max_speed_delta_kph=max(abs(float(a[k][6])-float(b[k][6])) for k in changed),
            max_same_link_pos_delta_m=max(abs(float(a[k][4])-float(b[k][4])) for k in changed if a[k][2]==b[k][2]),
            omega_0_5400_max_absolute_column_differences=numeric_delta,
            same_mainline_5400_snapshots=(
                pd.read_csv(ROOT/f'diagnostics/demand_sweep/{case}/results/fw_cells_30s.csv').query('sec==5400').reset_index(drop=True).equals(
                pd.read_csv(ROOT/f'diagnostics/demand_sweep/{case}_cooldown9000/results/fw_cells_30s.csv').query('sec==5400').reset_index(drop=True))),
            cause='Not established. SimPeriod and evaluation horizons changed; one core, identical demand/route/control settings and LSA prefix.')
    pd.DataFrame(all_changes).to_csv(OUT/'prefix_changed_rows.csv',index=False)
    save(OUT/'prefix_difference_diagnosis.json',evidence)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
