#!/usr/bin/env python3
"""Render private environment values from a local JSON file; never commit output."""
import argparse, json, re
from pathlib import Path
import yaml
BUNDLE = Path(__file__).resolve().parents[1]


def render(values):
    if not re.fullmatch(r'[a-f0-9]{40}', values['GITLAB_SKILLS_COMMIT']):
        raise ValueError('GitLab skills must be pinned to a full commit SHA')
    if not re.fullmatch(r'aks-skills-[a-f0-9]{12}', values['GITLAB_SKILLS_REF']) or values['GITLAB_SKILLS_REF'] != 'aks-skills-'+values['GITLAB_SKILLS_COMMIT'][:12]:
        raise ValueError('Use the protected release tag matching the recorded commit')
    url = values['GITLAB_SKILLS_REPO_URL']
    if not re.fullmatch(r'https://[^/@:]+/[^\s?#]+', url):
        raise ValueError('Use a credential-free HTTPS clone URL')
    if not re.fullmatch(r'[a-zA-Z0-9._/-]+', values['GITLAB_BUNDLE_PATH']) or '..' in values['GITLAB_BUNDLE_PATH'].split('/') or values['GITLAB_BUNDLE_PATH'].startswith('/'):
        raise ValueError('Invalid relative GitLab bundle path')
    if not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}', values['SKILL_CHECK_IMAGE']):
        raise ValueError('Startup verifier image must be digest-pinned and contain python3')
    docs = []
    for f in sorted((BUNDLE / 'manifests').glob('*.yaml')):
        content = f.read_text()
        # Replace at YAML scalar level: JSON quoting cannot become YAML structure.
        doc = yaml.safe_load(content)
        def replace(obj):
            if isinstance(obj, dict): return {k: replace(v) for k, v in obj.items()}
            if isinstance(obj, list): return [replace(v) for v in obj]
            if isinstance(obj, str):
                return re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], obj)
            return obj
        docs.append(replace(doc))
    docs.append({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'aks-skills-startup-check','namespace':values['AGENT_NAMESPACE']},'data':{'check_mounted.py':(BUNDLE/'scripts/check_mounted.py').read_text(),'skills.lock.json':(BUNDLE/'skills.lock.json').read_text()}})
    # Admission appends verifier after native skills-init. Enforce rule rejects bypass.
    match = {'any':[{'resources':{'kinds':['Pod'],'operations':['CREATE'],'namespaces':[values['AGENT_NAMESPACE']],'selector':{'matchLabels':{'aks-skills-bundle':'true'}}}}]}
    patch = {'spec':{'automountServiceAccountToken':False,'volumes':[{'name':'aks-skills-startup-check','configMap':{'name':'aks-skills-startup-check'}}], 'initContainers':[{'name':'verify-mounted-skills','image':values['SKILL_CHECK_IMAGE'],'command':['python3','/skill-check/check_mounted.py'],'env':[{'name':'SKILL_AGENT_NAME','valueFrom':{'fieldRef':{'fieldPath':"metadata.labels['aks-skills-agent']"}}}],'securityContext':{'runAsNonRoot':True,'runAsUser':65532,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},'volumeMounts':[{'name':'kagent-skills','mountPath':'/skills','readOnly':True},{'name':'aks-skills-startup-check','mountPath':'/skill-check','readOnly':True}]}]}}
    docs.append({'apiVersion':'kyverno.io/v1','kind':'ClusterPolicy','metadata':{'name':'aks-skills-startup-'+values['AGENT_NAMESPACE']},'spec':{'background':False,'failurePolicy':'Fail','validationFailureAction':'Enforce','rules':[{'name':'add-skill-startup-check','match':match,'mutate':{'patchesJson6902':json.dumps([{'op':'add','path':'/spec/automountServiceAccountToken','value':False}, {'op':'add','path':'/spec/volumes/-','value':patch['spec']['volumes'][0]}, {'op':'add','path':'/spec/initContainers/-','value':patch['spec']['initContainers'][0]}])}}, {'name':'require-ordered-check','match':match,'validate':{'message':'Reviewed skills must be verified after fetching, before the agent starts.','deny':{'conditions':{'any':[{'key':'{{ request.object.spec.initContainers[0].name || `"missing"` }}','operator':'NotEquals','value':'skills-init'}, {'key':'{{ request.object.spec.initContainers[1].name || `"missing"` }}','operator':'NotEquals','value':'verify-mounted-skills'}, {'key':'{{ length(request.object.spec.initContainers) }}','operator':'NotEquals','value':2}, {'key':'{{ request.object.spec.serviceAccountName }}','operator':'NotEquals','value':'aks-skills-no-api'}, {'key':'{{ request.object.spec.automountServiceAccountToken }}','operator':'NotEquals','value':False}]}}}}]}})
    return docs

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('values',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.write_text(yaml.safe_dump_all(render(json.loads(a.values.read_text())),sort_keys=False))
