import unittest
from copy import deepcopy
from evaluation.controllers.obs150_contract import ScheduleRow
from evaluation.controllers.source_boundary import forecast
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.source_history328.candidate import historical_cap,predict

def records():return [dict(end_sec=150*(i+1),interval_s=150,admitted_window=v,run_id='same') for i,v in enumerate((100,120,80,100))]

class SourceHistory(unittest.TestCase):
    def test_no_future_leak_and_original_unchanged(self):
        r=records();old=deepcopy(r);result=historical_cap(r,600)
        r.append(dict(end_sec=750,interval_s=150,admitted_window=99999,run_id='future'))
        self.assertEqual(result,historical_cap(r,600));self.assertEqual(r[:4],old)
        self.assertEqual(result['cap_vph'],2400.)

    def test_constant_history_exact_existing_recursion(self):
        r=records()
        for x in r:x['admitted_window']=100
        s=(ScheduleRow(0,None,3000.),)
        new,_=predict(r,600,50,s)
        self.assertEqual(new,forecast(2400.,50,s,600.,150,3,10))

    def test_schedule_and_available_vehicles_remain_binding(self):
        s=(ScheduleRow(0,600,3000.),ScheduleRow(600,None,1200.))
        rates,_=predict(records(),600,25,s)
        self.assertLessEqual(sum(r/24 for r in rates),25+1200*450/3600+1e-8)
        self.assertEqual(rates[-1],1200.)

    def test_no_gap_duplicate_or_cross_run_pooling(self):
        for mode in ('gap','duplicate','run'):
            r=records()
            if mode=='gap':r[1]['end_sec']=301
            elif mode=='duplicate':r[1]['end_sec']=150
            else:r[1]['run_id']='different'
            with self.subTest(mode=mode),self.assertRaises(ValueError):historical_cap(r,600)

    def test_short_history_falls_back_to_current_observation(self):
        r=records()[:2];out=historical_cap(r,300)
        self.assertEqual(out['cap_vph'],2880);self.assertEqual(out['windows'],1)

if __name__=='__main__':unittest.main()
