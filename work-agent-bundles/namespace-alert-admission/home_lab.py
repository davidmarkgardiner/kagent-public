"""Generate isolated Alloy/Vector/gate/Kafka proof resources, no Argo objects."""
import argparse
import json
import re
from pathlib import Path

import yaml
from render_vector import render


def resource(kind, name, namespace, **fields):
    version = {"Deployment": "apps/v1", "Role": "rbac.authorization.k8s.io/v1",
               "RoleBinding": "rbac.authorization.k8s.io/v1",
               "NetworkPolicy": "networking.k8s.io/v1"}.get(kind, "v1")
    return {"apiVersion": version, "kind": kind, "metadata": {"name": name, "namespace": namespace}, **fields}


def deployment(name, ns, image, args=None, env=None, volumes=None, mounts=None, service_account=None, init=None):
    container = {"name": name, "image": image,
                 "resources": {"requests": {"cpu": "25m", "memory": "64Mi"},
                               "limits": {"cpu": "1", "memory": "768Mi"}}}
    for key, value in (("args", args), ("env", env), ("volumeMounts", mounts)):
        if value: container[key] = value
    spec = {"containers": [container]}
    if volumes: spec["volumes"] = volumes
    if service_account: spec["serviceAccountName"] = service_account
    if init: spec["initContainers"] = init
    return resource("Deployment", name, ns, spec={"replicas": 1,
        "selector": {"matchLabels": {"app": name}},
        "template": {"metadata": {"labels": {"app": name}}, "spec": spec}})


def service(name, ns, port):
    return resource("Service", name, ns, spec={"selector": {"app": name},
                    "ports": [{"port": port, "targetPort": port}]})


def generate(ns, fixture_namespaces, bundle):
    docs = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": n,
             "labels": {"app.kubernetes.io/part-of": "namespace-alert-admission-proof"}}}
            for n in [ns, *fixture_namespaces]]
    docs += [resource("ServiceAccount", "alloy", ns), resource("ServiceAccount", "gate", ns)]
    for target in fixture_namespaces:
        docs += [resource("Role", "alloy-reader", target, rules=[{
            "apiGroups": [""], "resources": ["pods", "pods/log", "events"], "verbs": ["get", "list", "watch"]}]),
            resource("RoleBinding", "alloy-reader", target,
                     subjects=[{"kind": "ServiceAccount", "name": "alloy", "namespace": ns}],
                     roleRef={"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "alloy-reader"}),
            resource("Role", "owner-reader", target, rules=[
                {"apiGroups": [""], "resources": ["pods"], "verbs": ["get"]},
                {"apiGroups": ["apps"], "resources": ["replicasets", "deployments"], "verbs": ["get"]}]),
            resource("RoleBinding", "owner-reader", target,
                     subjects=[{"kind": "ServiceAccount", "name": "gate", "namespace": ns}],
                     roleRef={"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "owner-reader"})]
    source_root = bundle.parent / "homelab-verified-triage-replication/config"
    alloy = next(d for d in yaml.safe_load_all((source_root / "01-alloy.yaml").read_text()) if d and d["kind"]=="ConfigMap")
    config = alloy["data"]["config.alloy"]
    config = config.replace('level = "error"', 'level = "info"')
    config = config.replace('role = "pod"', 'role = "pod"\n      namespaces { names = '+json.dumps(fixture_namespaces)+' }')
    config = re.sub(r'regex = "aks-istio-ingress[^"\n]+"', 'regex = "'+"|".join(fixture_namespaces)+'"', config)
    config = re.sub(r'namespaces = \[[^\n]+\]', 'namespaces = '+json.dumps(fixture_namespaces), config)
    config = config.replace("http://vector-telemetry-triage.argo-events.svc.cluster.local:4318", "http://vector:4318")
    docs += [resource("ConfigMap", "alloy-config", ns, data={"config.alloy": config})]
    alloy_deployment = deployment("alloy", ns, "grafana/alloy:v1.18.0",
        args=["run", "/etc/alloy/config.alloy", "--server.http.listen-addr=0.0.0.0:12345", "--storage.path=/tmp/alloy"],
        env=[{"name":"TRIAGE_CLUSTER_NAME","value":"admission-home-proof"},{"name":"TRIAGE_ENVIRONMENT","value":"lab"}],
        service_account="alloy", volumes=[{"name":"config","configMap":{"name":"alloy-config"}}],
        mounts=[{"name":"config","mountPath":"/etc/alloy","readOnly":True}])
    alloy_deployment["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
        "httpGet":{"path":"/-/ready","port":12345},"initialDelaySeconds":5}
    docs.append(alloy_deployment)
    vector_docs = list(yaml.safe_load_all(render((source_root/"02-vector.yaml").read_text(), "http://gate:8080/signals", True)))
    vector_config = next(d["data"]["vector.yaml"] for d in vector_docs if d and d["kind"]=="ConfigMap")
    vector_config = vector_config.replace('?? "red"', '?? "admission-home-proof"')
    docs += [resource("ConfigMap", "vector-config", ns, data={"vector.yaml":vector_config}),
             deployment("vector", ns, "timberio/vector:0.45.0-debian", args=["--config","/etc/vector/vector.yaml"],
                        env=[{"name":"ADMISSION_AUTH_KEY","value":"synthetic-home-proof-key-not-a-credential"}],
                        volumes=[{"name":"config","configMap":{"name":"vector-config"}}],
                        mounts=[{"name":"config","mountPath":"/etc/vector","readOnly":True}]), service("vector",ns,4318)]
    docs += [deployment("pg", ns, "postgres:16-alpine", env=[
        {"name":"POSTGRES_USER","value":"admission"}, {"name":"POSTGRES_DB","value":"admission"},
        {"name":"POSTGRES_HOST_AUTH_METHOD","value":"trust"}],
        volumes=[{"name":"data","emptyDir":{}}], mounts=[{"name":"data","mountPath":"/var/lib/postgresql/data"}]),
        service("pg",ns,5432)]
    kafka_env = {"KAFKA_NODE_ID":"1", "KAFKA_PROCESS_ROLES":"broker,controller",
                 "KAFKA_LISTENERS":"PLAINTEXT://:9092,CONTROLLER://:9093",
                 "KAFKA_ADVERTISED_LISTENERS":"PLAINTEXT://kafka:9092",
                 "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP":"CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
                 "KAFKA_CONTROLLER_LISTENER_NAMES":"CONTROLLER", "KAFKA_INTER_BROKER_LISTENER_NAME":"PLAINTEXT",
                 "KAFKA_CONTROLLER_QUORUM_VOTERS":"1@localhost:9093", "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR":"1",
                 "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR":"1", "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR":"1"}
    broker = deployment("kafka",ns,"apache/kafka-native:3.9.1",env=[{"name":k,"value":v} for k,v in kafka_env.items()])
    broker["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
        "tcpSocket":{"port":9092},"initialDelaySeconds":5,"periodSeconds":5}
    docs += [broker,service("kafka",ns,9092)]
    policy = {"cluster":"admission-home-proof", "namespaces":fixture_namespaces, "mode":"enforce",
              "limit":2, "overrides":dict(zip(fixture_namespaces,[1,2,2])), "report_hour":0,
              "triage_topic":"admission-home-proof-v1"}
    code = {name:(bundle/name).read_text() for name in ("gate.py","schema.sql","requirements.txt","home_lab_runtime.py","strict_soak.py")}
    code["policy.json"] = json.dumps(policy)
    docs += [resource("ConfigMap","gate-code",ns,data=code)]
    gate_deployment = deployment("gate",ns,"python:3.12-slim-bookworm",args=["python","/code/home_lab_runtime.py","serve"],
        env=[{"name":"PYTHONPATH","value":"/deps"}, {"name":"PYTHONDONTWRITEBYTECODE","value":"1"},
             {"name":"DATABASE_URL","value":"postgresql://admission@pg/admission"},
             {"name":"CONFLUENT_BOOTSTRAP","value":"kafka:9092"}],
        service_account="gate", volumes=[{"name":"code","configMap":{"name":"gate-code"}},{"name":"deps","emptyDir":{}}],
        mounts=[{"name":"code","mountPath":"/code","readOnly":True},{"name":"deps","mountPath":"/deps","readOnly":True}],
        init=[{"name":"dependencies","image":"python:3.12-slim-bookworm",
               "command":["pip","install","--no-cache-dir","--target","/deps","-r","/code/requirements.txt"],
               "volumeMounts":[{"name":"code","mountPath":"/code","readOnly":True},{"name":"deps","mountPath":"/deps"}]}])
    gate_deployment["spec"]["template"]["spec"]["containers"][0]["readinessProbe"] = {
        "httpGet":{"path":"/health","port":8080},"initialDelaySeconds":5}
    docs += [gate_deployment, service("gate",ns,8080), resource("NetworkPolicy","isolated-test-ingress",ns,spec={
        "podSelector":{},"policyTypes":["Ingress"],"ingress":[{"from":[{"podSelector":{}}]}]})]
    return docs


def fixtures(namespaces):
    docs = []
    for ns in namespaces:
        for i in range(5):
            name = f"signal-{i}"
            d = deployment(name,ns,"busybox:1.37.0",args=["sh","-c",
                'for n in $(seq 1 12); do echo "ERROR synthetic timeout admission-proof sequence=$n"; sleep 1; done; sleep 3600'])
            d["spec"]["template"]["spec"]["containers"][0]["resources"] = {
                "requests":{"cpu":"5m","memory":"8Mi"},"limits":{"cpu":"50m","memory":"32Mi"}}
            docs.append(d)
    return docs


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("namespace")
    p.add_argument("output",type=Path)
    args=p.parse_args()
    if not re.fullmatch(r"admission-proof-[a-z0-9-]+",args.namespace):
        p.error("namespace must use admission-proof- prefix")
    args.output.mkdir(parents=True,exist_ok=False)
    namespaces=[args.namespace+f"-n{i}" for i in (1,2,3)]
    bundle=Path(__file__).resolve().parent
    (args.output/"pipeline.yaml").write_text(yaml.safe_dump_all(generate(args.namespace,namespaces,bundle),sort_keys=False))
    (args.output/"fixtures.yaml").write_text(yaml.safe_dump_all(fixtures(namespaces),sort_keys=False))
    (args.output/"namespaces.json").write_text(json.dumps([args.namespace,*namespaces]))
