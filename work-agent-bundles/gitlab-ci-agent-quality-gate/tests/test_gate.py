import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('gate', Path(__file__).parents[1] / 'scripts/gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
HEAD = 'a' * 40
BASE = 'b' * 40


def good():
    tests = [{'kind': kind, 'outcome': 'pass', 'candidate_sha': HEAD,
              'artifact': 'authority-artifact', 'harness_version': 'v1'}
             for kind in ('positive', 'negative', 'regression')]
    tests[-1].update(baseline_sha=BASE, baseline_outcome='expected_failure', baseline_artifact='baseline-artifact')
    return {'schema_version': 1, 'project_id': 7, 'mr_iid': 3, 'head_sha': HEAD,
            'verdict': 'PASS', 'review': {'verdict': 'PASS', 'artifact': 'review-artifact'}, 'tests': tests}


class GateTests(unittest.TestCase):
    def test_pass_requires_all_evidence(self):
        gate.validate(good(), 7, 3, HEAD)

    def test_stale_or_wrong_identity_blocks(self):
        for key, value in [('project_id', 8), ('mr_iid', 4), ('head_sha', BASE), ('schema_version', True)]:
            with self.subTest(key=key):
                result = good()
                result[key] = value
                with self.assertRaises(ValueError):
                    gate.validate(result, 7, 3, HEAD)

    def test_each_failed_or_stale_test_blocks(self):
        for index in range(3):
            for field, value in [('outcome', 'fail'), ('candidate_sha', BASE), ('artifact', '')]:
                with self.subTest(index=index, field=field):
                    result = good()
                    result['tests'][index][field] = value
                    with self.assertRaises(ValueError):
                        gate.validate(result, 7, 3, HEAD)

    def test_missing_kinds_block(self):
        for index in range(3):
            result = good()
            result['tests'].pop(index)
            with self.assertRaises(ValueError):
                gate.validate(result, 7, 3, HEAD)

    def test_unrelated_baseline_failure_blocks(self):
        for field, value in [('baseline_outcome', 'infrastructure_error'), ('baseline_sha', HEAD), ('baseline_artifact', '')]:
            result = good()
            result['tests'][-1][field] = value
            with self.assertRaises(ValueError):
                gate.validate(result, 7, 3, HEAD)

    def test_review_block_or_missing_artifact_blocks(self):
        for field, value in [('verdict', 'BLOCK'), ('artifact', '')]:
            result = good()
            result['review'][field] = value
            with self.assertRaises(ValueError):
                gate.validate(result, 7, 3, HEAD)

    def test_unsafe_endpoint_rejected(self):
        for origin in ['http://example.invalid', 'https://user@example.invalid', 'https://example.invalid/x', 'https://example.invalid/?x=y']:
            with self.assertRaises(ValueError):
                gate.endpoint(origin)

    def test_redirect_rejected(self):
        with self.assertRaises(ValueError):
            gate.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid')

    def test_poll_same_origin_no_resubmit(self):
        calls = []
        replies = iter([{'evaluation_id': 'one', 'status': 'pending'},
                        {'evaluation_id': 'one', 'status': 'running'},
                        {'evaluation_id': 'one', 'status': 'completed', 'result': good()}])
        def request(method, url, identity, body):
            calls.append((method, url))
            return next(replies)
        payload = {'project_id': 7, 'mr_iid': 3, 'expected_head_sha': HEAD}
        result = gate.evaluate('https://example.invalid', 'fixture', payload, request, sleep=lambda _: None)
        self.assertEqual(result, good())
        self.assertEqual([x[0] for x in calls], ['POST', 'GET', 'GET'])
        self.assertTrue(all(url.startswith('https://example.invalid/v1/evaluations') for _, url in calls))

    def test_bad_eval_id_rejected_before_get(self):
        with self.assertRaises(ValueError):
            gate.evaluate('https://example.invalid', 'fixture', {}, lambda *args: {'evaluation_id': '../elsewhere'})

    def test_unknown_state_blocks(self):
        replies = iter([{'evaluation_id': 'one'}, {'evaluation_id': 'one', 'status': 'failed'}])
        with self.assertRaises(ValueError):
            gate.evaluate('https://example.invalid', 'fixture', {}, lambda *args: next(replies))

    def test_deadline_blocks_without_replay(self):
        ticks = iter([0, 601])
        calls = []
        def request(*args):
            calls.append(args[0])
            return {'evaluation_id': 'one'}
        with self.assertRaises(ValueError):
            gate.evaluate('https://example.invalid', 'fixture', {}, request, clock=lambda: next(ticks))
        self.assertEqual(calls, ['POST'])


if __name__ == '__main__':
    unittest.main()
