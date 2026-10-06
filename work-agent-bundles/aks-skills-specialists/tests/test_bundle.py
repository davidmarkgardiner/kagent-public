import copy, importlib.util, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
import yaml
B=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
check=module('check',B/'scripts/check_mounted.py');render=module('render',B/'scripts/render.py')
class BundleTests(unittest.TestCase):
    def setUp(self):
        self.lock=json.loads((B/'skills.lock.json').read_text());self.values=json.loads((B/'tests/values.json').read_text())
    def test_committed_gitlab_import(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)
            def git(*args):
                return subprocess.run(['git','-C',d,*args],check=True,capture_output=True,text=True)
            git('init');git('config','user.name','Synthetic import test');git('config','user.email','test@example.com')
            (target/'README.md').write_text('Synthetic fixture\n');git('add','README.md');git('commit','-m','fixture')
            command=[str(B/'scripts/import-to-gitlab.sh'),d,'work-agent-bundles/aks-skills-specialists']
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            imported=target/'work-agent-bundles/aks-skills-specialists'
            self.assertTrue((imported/'skills.lock.json').is_file())
            self.assertFalse((imported/'payload/upstream/evals/node_modules').exists())
            self.assertEqual(git('status','--porcelain').stdout,'')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
    def test_evaluation_configs_have_all_cases_and_valid_assertion_paths(self):
        for filename in ['quality.yaml','baseline.yaml','routing.yaml']:
            config=yaml.safe_load((B/'evaluation'/filename).read_text())
            self.assertGreater(len(config['tests']),10)
            for case in config['tests']:
                for assertion in case.get('assert',[]):
                    value=assertion.get('value')
                    if isinstance(value,str) and value.startswith('file://'):
                        self.assertTrue((B/'evaluation'/value[7:]).is_file(),value)
    def test_upstream_snapshot_integrity(self):
        snapshot=json.loads((B/'upstream.lock.json').read_text())
        import hashlib
        for path,digest in snapshot['files'].items():
            self.assertEqual(hashlib.sha256((B/'payload/upstream'/path).read_bytes()).hexdigest(),digest,path)
    def test_all_ten_skills_and_every_agent_mount(self):
        self.assertEqual(len(self.lock['skills']),10)
        self.assertEqual(sum(s['origin']=='Microsoft' for s in self.lock['skills'].values()),7)
        for agent,names in self.lock['agents'].items():
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)
                for name in names:shutil.copytree(B/self.lock['skills'][name]['path'],root/name)
                self.assertTrue(check.verify(root,self.lock,agent)['verified'])
                (root/names[0]/'SKILL.md').write_text('tampered')
                with self.assertRaises(ValueError):check.verify(root,self.lock,agent)
    def test_missing_skill_blocks_startup(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):check.verify(Path(d),self.lock,'aks-incident-specialist')
    def test_unexpected_reference_file_blocks_startup(self):
        agent='aks-efficiency-specialist'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in self.lock['agents'][agent]:shutil.copytree(B/self.lock['skills'][name]['path'],root/name)
            (root/self.lock['agents'][agent][0]/'extra.sh').write_text('unreviewed')
            with self.assertRaises(ValueError):check.verify(root,self.lock,agent)
    def test_renderer_rejects_moving_refs_credentials_and_unpinned_images(self):
        for key,value in [('GITLAB_SKILLS_COMMIT','main'),('GITLAB_SKILLS_REF','main'),('GITLAB_SKILLS_REPO_URL','https://user:credential@gitlab.com/group/repo'),('GITLAB_BUNDLE_PATH','../escape'),('SKILL_CHECK_IMAGE','python:latest')]:
            values=copy.deepcopy(self.values);values[key]=value
            with self.assertRaises(ValueError):render.render(values)
    def test_rendered_agents_and_policy(self):
        docs=render.render(self.values)
        for d in docs:
            if d['kind']=='Agent':
                self.assertEqual(d['spec']['declarative']['deployment']['serviceAccountName'],'aks-skills-no-api')
                self.assertEqual(d['spec']['declarative']['tools'][0]['mcpServer']['toolNames'],['read_inventory'])
                self.assertEqual([r['name'] for r in d['spec']['skills']['gitRefs']],self.lock['agents'][d['metadata']['name']])
            if d['kind']=='ClusterPolicy':self.assertEqual(d['spec']['validationFailureAction'],'Enforce')
    def test_promotion_gate_empty_failed_and_passing(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'results.json'
            for rows,code in [([],1),([{'success':False}],1),([{'success':True,'error':'bad'}],1),([{'success':True}],0)]:
                f.write_text(json.dumps({'results':{'results':rows}}))
                result=subprocess.run(['python3',str(B/'evaluation/check-results.py'),str(f)],capture_output=True)
                self.assertEqual(result.returncode,code)
if __name__=='__main__':unittest.main()
