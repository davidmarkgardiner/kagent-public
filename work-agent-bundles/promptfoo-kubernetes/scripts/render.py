#!/usr/bin/env python3
import argparse,json,re
from pathlib import Path
import yaml
B=Path(__file__).resolve().parents[1]
def render(values):
    image=values['INTERNAL_PROMPTFOO_EVAL_IMAGE_WITH_SHA256_DIGEST']
    if not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}',image):raise ValueError('Pin the imported image digest')
    if values['EVALUATION_SUITE'] not in ['quality','routing','baseline']:raise ValueError('Invalid suite')
    if not values['INTERNAL_OPENAI_COMPATIBLE_BASE_URL'].startswith('https://'):raise ValueError('Use an internal HTTPS model endpoint')
    def replace(obj):
        if isinstance(obj,dict):return {k:replace(v) for k,v in obj.items()}
        if isinstance(obj,list):return [replace(v) for v in obj]
        if isinstance(obj,str):return re.sub(r'\{\{([A-Z_]+)\}\}',lambda m:values[m[1]],obj)
        return obj
    return {p.name:[replace(d) for d in yaml.safe_load_all(p.read_text())] for p in (B/'manifests').glob('*.yaml')}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('values',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    result=render(json.loads(args.values.read_text()));args.output.mkdir(parents=True,exist_ok=True)
    for name,docs in result.items():(args.output/name).write_text(yaml.safe_dump_all(docs,sort_keys=False))
