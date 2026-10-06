#!/usr/bin/env python3
"""Require nonempty, entirely passing promptfoo results for promotion."""
import json, sys
for filename in sys.argv[1:]:
    data=json.load(open(filename)); rows=data.get('results',{}).get('results',[])
    if not rows or any(r.get('success') is not True or r.get('error') for r in rows):
        raise SystemExit('FAIL: missing/empty/failed evaluation: '+filename)
    print('PASS:',filename,len(rows),'cases')
if len(sys.argv)<2: raise SystemExit('Provide quality and routing results')
