"""Check an inherited shared head ceiling against retained pre-horizon evidence."""
from pathlib import Path
import gzip,hashlib,json,math
from diagnostics.validate_native_signal_record import read_ldp_frames

HERE=Path(__file__).resolve().parent;A=HERE.parent
def main():
    out=HERE/'past_head_bound.json';assert not out.exists()
    p=Path('E:/VISSIM_analysis/20261010_sc107_composition312/retained_past.json.gz')
    data=p.read_bytes();past=json.loads(gzip.decompress(data))
    assert past['fit_head_window']==[1800,2250] and past['tracking_end_exclusive']==2400
    ldp=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/vissim_eval/sdmpc31_g_2400_hold_s29_107_001.ldp')
    frames=read_ldp_frames({107:ldp},{107:list(range(1,9))},1800,2250)['frames']
    eligible={t for t in range(1800,2250) if frames[t]['107:2']=='GREEN' and frames[t+1]['107:2']=='GREEN'}
    known=[x for x in past['witnesses'] if x['sg']=='2' and x['turn']=='through' and math.floor(x['time']) in eligible
           and 1800<=x['time']<2250 and x['downstream_first'][0]<2400]
    assert len({x['vehicle'] for x in known})==len(known)
    prior=Path('E:/VISSIM_analysis/20261010_sc107_shared316/forecast2400/shared_head_application.json')
    shared=json.loads(prior.read_bytes());old=shared['service_veh_h']
    floor=len(known)*3600/len(eligible)
    result=dict(status='complete_past_physical_head_bound_audit',old_shared_service_veh_h=old,
        observed_green_throughput_lower_bound_veh_h=floor,known_through_count=len(known),green_interior_sec=len(eligible),
        old_envelope_vehicles=old*len(eligible)/3600,bound_contradicted=floor>old,
        witnesses=known,training_window=[1800,2250],future_inputs=False,
        budget=dict(forecasts=0,ad=0,optimizer=0,native=0,fzp_scans=0,new_capacity_fit=0),
        source_pins={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (p,ldp,prior,Path(__file__))},
        limits=['Only uniquely witnessed through vehicles during interior green seconds are included.',
          'Selected cohorts omit other vehicles and idle green is retained; achieved flow is a lower bound, not saturation.',
          'No original FZP reread. Downstream classification is entirely before the2400 prediction boundary.',
          'This checks a service ceiling; it does not quantify a control gain.'])
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k in ('old_shared_service_veh_h','observed_green_throughput_lower_bound_veh_h','known_through_count','green_interior_sec','old_envelope_vehicles','bound_contradicted')}))

if __name__=='__main__':main()
