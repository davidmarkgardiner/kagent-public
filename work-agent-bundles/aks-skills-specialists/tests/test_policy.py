import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
B=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('renderer',B/'scripts/render.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PolicyTests(unittest.TestCase):
    def test_startup_order_and_rejection(self):
        values=json.loads((B/'tests/values.json').read_text())
        policy=next(d for d in m.render(values) if d['kind']=='ClusterPolicy')
        pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':'synthetic-agent','namespace':'aks-skills-test','labels':{'aks-skills-bundle':'true','aks-skills-agent':'aks-incident-specialist'}},'spec':{'serviceAccountName':'aks-skills-no-api','containers':[{'name':'kagent','image':'registry.example.com/agent:test'}],'initContainers':[{'name':'skills-init','image':'registry.example.com/init:test'}],'volumes':[{'name':'kagent-skills','emptyDir':{}}]}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pp=root/'policy.yaml';rp=root/'pod.yaml';pp.write_text(yaml.safe_dump(policy))
            for unsafe in [False,True]:
                pod['spec']['serviceAccountName']='default' if unsafe else 'aks-skills-no-api';rp.write_text(yaml.safe_dump(pod))
                out=root/('bad' if unsafe else 'good')
                r=subprocess.run(['kyverno','apply',str(pp),'--resource',str(rp),'--set','request.operation=CREATE','--output',str(out)],capture_output=True,text=True)
                self.assertEqual(r.returncode,1 if unsafe else 0,r.stdout+r.stderr)
                self.assertIn('fail: 1' if unsafe else 'pass: 2, fail: 0',r.stdout)
                changed=yaml.safe_load_all((out/'synthetic-agent-mutated.yaml').read_text());obj=next(changed)
                self.assertEqual([c['name'] for c in obj['spec']['initContainers']],['skills-init','verify-mounted-skills'])
                self.assertFalse(obj['spec']['automountServiceAccountToken'])
if __name__=='__main__':unittest.main()
