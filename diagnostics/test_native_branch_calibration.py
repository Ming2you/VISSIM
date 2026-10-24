"""Cohort identity, observed/skipped branches and censoring on tiny FZP fixtures."""
from io import BytesIO
import unittest
from diagnostics.calibrate_native_1092_1093 import collect,summarize

HEADER=b'$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM\n'
SPEC={'217':{'input_no':'1092','outgoing':[{'connector':'11','target':'21'},{'connector':'12','target':'22'}]}}
def row(t,no,link):return f'{t};{no};{link};1;1.00;0.50;30.00;0.00;0.00\n'.encode()
def run(*records):return collect(BytesIO(HEADER+b''.join(records)),SPEC)[0]

class Cohorts(unittest.TestCase):
    def test_observed_connector_vs_skipped_target(self):
        a,b=run(row(1,1,217),row(1,2,217),row(2,1,11),row(2,2,22))
        self.assertEqual((a['branch_connector'],a['resolution']),('11','observed_first_connector'))
        self.assertEqual((b['branch_connector'],b['resolution']),('12','unique_target_after_skipped_connector'))
        summary=summarize([a,b],SPEC['217']);self.assertEqual(summary['branches'][0]['fraction_of_all_source_observed'],.5)

    def test_unknown_and_censored_stay_in_denominator(self):
        c=run(row(1,1,217),row(1,2,217),row(1,3,217),row(2,1,11),row(2,2,99),row(2,3,217))
        summary=summarize(c,SPEC['217']);self.assertEqual(summary['resolved_ids'],1);self.assertEqual(summary['unresolved_or_censored_ids'],2)
        self.assertEqual(summary['branches'][0]['fraction_among_resolved'],1.);self.assertEqual(summary['branches'][0]['fraction_of_all_source_observed'],1/3)
        self.assertEqual(c[2]['resolution'],'right_censored_on_source_at_final_frame')

    def test_disappearance_is_not_destination(self):
        c=run(row(1,1,217),row(2,2,99))[0]
        self.assertEqual(c['resolution'],'disappeared_before_observed_branch');self.assertIsNone(c['branch_connector'])

    def test_repeated_source_id_not_new_admission(self):
        c=run(row(1,1,217),row(2,1,11),row(3,1,217))
        self.assertEqual(len(c),1);self.assertEqual(c[0]['source_return_after_departure_count'],1)
        self.assertEqual(summarize(c,SPEC['217'])['repeated_source_after_departure_ids'],[1])

    def test_not_first_seen_source_flag(self):
        c=run(row(1,1,99),row(2,1,217),row(3,1,12))[0]
        self.assertFalse(c['first_seen_on_source'])

    def test_duplicate_snapshot_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate ID'):run(row(1,1,217),row(1,1,217))

if __name__=='__main__':unittest.main()
