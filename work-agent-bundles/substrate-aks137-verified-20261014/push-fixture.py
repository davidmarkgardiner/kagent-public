#!/usr/bin/env python3
import argparse
import hashlib
import json
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--registry', required=True)
p.add_argument('--archive', required=True)
a = p.parse_args()
base = a.registry.rstrip('/')
def request(path, method='GET', data=None, content_type=None):
    url = urllib.parse.urljoin(base + '/', path)
    headers = {'Content-Type': content_type} if content_type else {}
    return urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=60)

with tarfile.open(a.archive) as archive:
    top = json.load(archive.extractfile('index.json'))['manifests'][0]
    blobs = {}
    for member in archive.getmembers():
        if member.isfile() and member.name.startswith('blobs/sha256/'):
            data = archive.extractfile(member).read()
            digest = 'sha256:' + hashlib.sha256(data).hexdigest()
            assert digest.split(':')[1] == member.name.split('/')[-1]
            blobs[digest] = data
    for digest, data in blobs.items():
        with request('/v2/fixture/blobs/uploads/', 'POST', b'') as result:
            location = result.headers['Location']
        separator = '&' if '?' in location else '?'
        with request(location + separator + 'digest=' + digest, 'PUT', data, 'application/octet-stream') as result:
            assert result.status == 201
    published = set()
    def manifest(digest):
        if digest in published:
            return
        data = blobs[digest]
        doc = json.loads(data)
        for child in doc.get('manifests', []):
            manifest(child['digest'])
        with request('/v2/fixture/manifests/' + digest, 'PUT', data, doc['mediaType']) as result:
            assert result.status == 201
        published.add(digest)
    manifest(top['digest'])
    doc = json.loads(blobs[top['digest']])
    with request('/v2/fixture/manifests/proof', 'PUT', blobs[top['digest']], doc['mediaType']) as result:
        assert result.headers['Docker-Content-Digest'] == top['digest']
    print(json.dumps({'digest': top['digest'], 'platforms': doc['manifests']}, indent=2))
