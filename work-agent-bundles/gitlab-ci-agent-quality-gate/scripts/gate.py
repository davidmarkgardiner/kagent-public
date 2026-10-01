#!/usr/bin/env python3
"""Fail-closed CI client for contracts/PROTOCOL.md; stdlib only."""
import argparse
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

SHA = re.compile(r'[0-9a-f]{40}')
EVAL_ID = re.compile(r'[A-Za-z0-9_-]{1,128}')
MAX_BYTES = 262144


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(result, project, mr, sha):
    require(isinstance(result, dict), 'Invalid result')
    require(type(result.get('schema_version')) is int and result['schema_version'] == 1, 'Unknown schema')
    require(type(result.get('project_id')) is int and result['project_id'] == project, 'Wrong project')
    require(type(result.get('mr_iid')) is int and result['mr_iid'] == mr, 'Wrong MR')
    require(result.get('head_sha') == sha, 'Stale head')
    require(result.get('verdict') == 'PASS', 'Evaluation blocked')
    review = result.get('review')
    require(isinstance(review, dict) and review.get('verdict') == 'PASS'
            and isinstance(review.get('artifact'), str) and bool(review['artifact'].strip()), 'Missing review evidence')
    tests = result.get('tests')
    require(isinstance(tests, list) and 1 <= len(tests) <= 100, 'Missing or excessive tests')
    kinds = set()
    for test in tests:
        require(isinstance(test, dict), 'Invalid test')
        kind = test.get('kind')
        require(kind in ('positive', 'negative', 'regression'), 'Unknown test kind')
        require(test.get('outcome') == 'pass' and test.get('candidate_sha') == sha, 'Failed or stale test')
        for key in ('artifact', 'harness_version'):
            require(isinstance(test.get(key), str) and bool(test[key].strip()), 'Missing executor evidence')
        if kind == 'regression':
            base = test.get('baseline_sha')
            require(isinstance(base, str) and SHA.fullmatch(base) is not None and base != sha, 'Invalid baseline')
            require(test.get('baseline_outcome') == 'expected_failure', 'Regression did not catch baseline bug')
            require(isinstance(test.get('baseline_artifact'), str) and bool(test['baseline_artifact'].strip()), 'Missing baseline evidence')
        kinds.add(kind)
    require(kinds == {'positive', 'negative', 'regression'}, 'Incomplete test coverage')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect rejected')


def endpoint(value):
    url = urllib.parse.urlsplit(value)
    require(url.scheme == 'https' and bool(url.hostname) and not url.username
            and not url.password and not url.query and not url.fragment
            and url.path in ('', '/'), 'Expected HTTPS origin')
    return value.rstrip('/')


def evaluate(origin, identity, payload, request, clock=time.monotonic, sleep=time.sleep, budget=600):
    origin = endpoint(origin)
    started = clock()
    response = request('POST', origin + '/v1/evaluations', identity, payload)
    evaluation_id = response.get('evaluation_id')
    require(isinstance(evaluation_id, str) and EVAL_ID.fullmatch(evaluation_id) is not None, 'Invalid evaluation ID')
    while clock() - started < budget:
        response = request('GET', origin + '/v1/evaluations/' + evaluation_id, identity, None)
        require(response.get('evaluation_id') == evaluation_id, 'Wrong evaluation response')
        state = response.get('status')
        if state == 'completed':
            result = response.get('result')
            validate(result, payload['project_id'], payload['mr_iid'], payload['expected_head_sha'])
            return result
        require(state in ('pending', 'running'), 'Evaluation failed or unknown status')
        sleep(min(3, max(0, budget - (clock() - started))))
    raise ValueError('Evaluation deadline exceeded; task may still be running')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=int, required=True)
    parser.add_argument('--mr', type=int, required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--pipeline', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    try:
        require(args.project > 0 and args.mr > 0 and SHA.fullmatch(args.sha) is not None, 'Invalid MR selectors')
        origin = endpoint(os.environ['AGENT_GATE_URL'])
        identity = os.environ['AGENT_GATE_ID_TOKEN']
        require(bool(identity) and '\n' not in identity and '\r' not in identity, 'Missing identity')
        context = ssl.create_default_context(cafile=os.environ.get('AGENT_GATE_CA_FILE') or None)
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))

        def request(method, url, credential, data):
            headers = {'Authorization': 'Bearer' + ' ' + credential, 'Accept': 'application/json'}
            body = None if data is None else json.dumps(data).encode()
            if body is not None:
                headers['Content-Type'] = 'application/json'
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with opener.open(req, timeout=30) as reply:
                require(reply.status == (202 if method == 'POST' else 200), 'Unexpected HTTP status')
                raw = reply.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, 'Oversized response')
            result = json.loads(raw)
            require(isinstance(result, dict), 'Malformed response')
            return result

        payload = {'schema_version': 1, 'project_id': args.project, 'mr_iid': args.mr,
                   'expected_head_sha': args.sha, 'pipeline_id': args.pipeline}
        result = evaluate(origin, identity, payload, request)
        output.write_text(json.dumps(result, indent=2) + '\n')
        print('PASS: exact-head review and required test evidence validated')
        return 0
    except Exception as exc:
        # Do not log exception bodies, request URLs, tokens, or model responses.
        output.write_text(json.dumps({'verdict': 'BLOCK', 'error_type': type(exc).__name__}) + '\n')
        print('BLOCK: evaluation incomplete, invalid, stale, or failed', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
