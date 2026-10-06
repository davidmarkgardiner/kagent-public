import importlib.util,unittest
from pathlib import Path
B=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('renderer',B/'scripts/render.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class Tests(unittest.TestCase):
    def setUp(self):self.v={'INTERNAL_PROMPTFOO_EVAL_IMAGE_WITH_SHA256_DIGEST':'registry.example.com/promptfoo@sha256:'+'a'*64,'INTERNAL_OPENAI_COMPATIBLE_BASE_URL':'https://gateway.example.com/v1','MODEL_DEPLOYMENT_NAME':'test-model','JUDGE_DEPLOYMENT_NAME':'test-judge','MODEL_AUTH_SECRET':'test-auth','STORAGE_CLASS':'test-storage','EVALUATION_SUITE':'quality'}
    def test_both_modes_share_image_but_separate_storage(self):
        d=r.render(self.v);server=next(o for o in d['server.yaml'] if o['kind']=='Deployment');job=d['job.yaml'][0]
        self.assertEqual(server['spec']['replicas'],1);self.assertEqual(server['spec']['strategy']['type'],'Recreate')
        a=server['spec']['template']['spec'];b=job['spec']['template']['spec']
        self.assertEqual(a['containers'][0]['image'],b['containers'][0]['image']);self.assertNotEqual(a['volumes'][0],b['volumes'][0])
        for p in [a,b]:self.assertFalse(p['automountServiceAccountToken']);self.assertEqual(p['securityContext']['runAsUser'],1000)
        self.assertEqual(job['spec']['backoffLimit'],0)
    def test_unpinned_image_and_invalid_suite_rejected(self):
        for key,value in [('INTERNAL_PROMPTFOO_EVAL_IMAGE_WITH_SHA256_DIGEST','image:latest'),('EVALUATION_SUITE','bogus')]:
            v=dict(self.v);v[key]=value
            with self.assertRaises(ValueError):r.render(v)
if __name__=='__main__':unittest.main()
