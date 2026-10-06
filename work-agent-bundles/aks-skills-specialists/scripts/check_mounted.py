#!/usr/bin/env python3
"""Fail startup unless all selected skill payloads match reviewed content."""
import argparse, hashlib, json, os
from pathlib import Path


def verify(root, lock, agent):
    expected = lock['agents'][agent]
    actual = sorted(p.name for p in root.iterdir() if p.is_dir())
    if sorted(expected) != actual:
        raise ValueError('Mounted skill inventory differs from reviewed inventory')
    for name in expected:
        skill = root / name
        files = {}
        for p in skill.rglob('*'):
            if p.is_symlink():
                raise ValueError('Symlinks are not permitted in mounted skills')
            if p.is_file():
                files[str(p.relative_to(skill))] = hashlib.sha256(p.read_bytes()).hexdigest()
        if files != lock['skills'][name]['files']:
            raise ValueError('Skill hash mismatch: ' + name)
        text = (skill / 'SKILL.md').read_text()
        if not text.startswith('---\n') or '\n---\n' not in text[4:]:
            raise ValueError('Invalid skill metadata: ' + name)
    return {'agent': agent, 'skills': expected, 'verified': True,
            'upstream_commit': lock['upstream_commit']}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path('/skills'))
    p.add_argument('--lock', type=Path, default=Path('/skill-check/skills.lock.json'))
    p.add_argument('--agent', default=os.environ.get('SKILL_AGENT_NAME'))
    args = p.parse_args()
    print(json.dumps(verify(args.root, json.loads(args.lock.read_text()), args.agent)))
