import copy,unittest
import numpy as np
import vsl_response as v


class ResponseObjective(unittest.TestCase):
    def setUp(self):self.observed={a:v.observed(a) for a in ('none','vsl')}

    def test_exact_responses_have_zero_error(self):
        residual,metrics=v.response_metrics(self.observed)
        self.assertEqual(metrics['response_loss'],0.)
        self.assertTrue(np.all(residual==0))

    def test_late_and_unobserved_terminal_flow_cannot_change_training(self):
        changed=copy.deepcopy(self.observed)
        for values in changed.values():
            for value in values.values():value[10:]+=12345
            values['q'][:,30]+=54321
        a,_=v.response_metrics(self.observed);b,_=v.response_metrics(changed)
        np.testing.assert_array_equal(a,b)

    def test_common_flow_bias_is_separate_from_control_response(self):
        changed=copy.deepcopy(self.observed)
        for values in changed.values():values['q']+=10
        a,_=v.response_metrics(self.observed);b,_=v.response_metrics(changed)
        np.testing.assert_array_equal(a,b)


if __name__=='__main__':unittest.main()
