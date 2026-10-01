"""Test harness: defer the daily slot until real Alloy intake has completed.

Runs only against the isolated lab broker/database. Production gate code and
owner resolver are reused; scheduler timing/TLS are explicitly outside this proof.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from confluent_kafka import Consumer, TopicCollection
from confluent_kafka.admin import AdminClient, NewTopic
from gate import Gate, KafkaPublisher, OwnerResolver, Policy, handler_for


def make_gate():
    settings=json.loads(Path("/code/policy.json").read_text())
    settings["namespaces"]=tuple(settings["namespaces"])
    return Gate(os.environ["DATABASE_URL"],Policy(**settings),OwnerResolver())


def snapshot(gate):
    with gate.connect() as db:
        rows=db.execute("SELECT namespace,reason,count(*) AS groups,bool_and(identity_resolved) AS resolved FROM admission_groups GROUP BY namespace,reason ORDER BY namespace,reason").fetchall()
        records=db.execute("SELECT count(*) AS n FROM admission_seen").fetchone()["n"]
    return {"records":records,"groups":rows}


def prove(gate):
    before=snapshot(gate)
    namespaces=gate.policy.namespaces
    for index,ns in enumerate(namespaces):
        log_groups=sum(r["groups"] for r in before["groups"] if r["namespace"]==ns and r["reason"].startswith("log-"))
        reason="Unhealthy" if index==0 else "OOMKilled"
        event_groups=sum(r["groups"] for r in before["groups"] if r["namespace"]==ns and r["reason"]==reason)
        assert log_groups==5, (ns,"log groups",log_groups)
        assert event_groups==5, (ns,"Warning Event groups",event_groups)
    assert all(r["resolved"] for r in before["groups"]), "live owner resolution failed"
    now=datetime.now(timezone.utc)
    report=gate.report(now)
    limits=[1,2,2]
    assert report["namespace_selected"]==dict(zip(namespaces,limits))
    publisher=KafkaPublisher(allow_plaintext=True)
    while gate.publish_one(publisher,now): pass
    consumer=Consumer({"bootstrap.servers":os.environ["CONFLUENT_BOOTSTRAP"],
        "group.id":"admission-home-proof-"+str(time.time_ns()),"auto.offset.reset":"earliest","enable.auto.commit":False,"isolation.level":"read_committed"})
    consumer.subscribe([gate.policy.triage_topic])
    counts=Counter()
    intents=set()
    messages=[]
    deadline=time.monotonic()+20
    try:
        while time.monotonic()<deadline:
            msg=consumer.poll(1)
            if msg and not msg.error():
                value=json.loads(msg.value())
                counts[value["namespace"]]+=1
                intents.add(dict(msg.headers())["admission-intent-id"])
                messages.append(value)
    finally: consumer.close()
    assert dict(counts)==dict(zip(namespaces,limits)),dict(counts)
    assert len(intents)==sum(limits)
    assert {m["signal_kind"] for m in messages}=={"event","log"},"both lanes must reach Kafka"
    gate.report(now)
    assert not gate.publish_one(publisher,now)
    result={"result":"PASS","path":"Kubernetes pod logs + Warning Events -> Alloy -> Vector OTLP -> HTTP gate/PostgreSQL -> Kafka produce/consume",
        "namespace_limits":limits,"consumed_by_limit":[counts[n] for n in namespaces],
        "consumed_total":sum(counts.values()),"distinct_intents":len(intents),"candidate_total":report["candidate_total"],
        "deferred_total":report["deferred_total"],"received_records":before["records"],"owner_resolution":"all Deployment groups resolved via live Kubernetes API",
        "repeated_dispatch":"zero additional sends","samples":[{"signal_kind":m["signal_kind"],"reason":m["reason"],"severity":m["severity"]} for m in messages],
        "scope":"synthetic signals, isolated broker; no Argo/agent/tickets; manually released report slot; plaintext Kafka only in isolated lab"}
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    gate=make_gate()
    if sys.argv[1]=="serve":
        for attempt in range(30):
            try:
                gate.initialize()
                break
            except Exception: time.sleep(1)
        else: raise RuntimeError("lab database not ready")
        ThreadingHTTPServer(("0.0.0.0",8080),handler_for(gate,"synthetic-home-proof-key-not-a-credential")).serve_forever()
    elif sys.argv[1]=="snapshot": print(json.dumps(snapshot(gate)))
    elif sys.argv[1]=="intake-ready":
        state=snapshot(gate)
        for index,ns in enumerate(gate.policy.namespaces):
            reason="Unhealthy" if index==0 else "OOMKilled"
            assert sum(r["groups"] for r in state["groups"] if r["namespace"]==ns and r["reason"].startswith("log-"))==5
            assert sum(r["groups"] for r in state["groups"] if r["namespace"]==ns and r["reason"]==reason)==5
        print("intake ready: all synthetic log and Warning Event groups retained")
    elif sys.argv[1]=="prove": prove(gate)
    elif sys.argv[1]=="pin-topics":
        admin=AdminClient({"bootstrap.servers":os.environ["CONFLUENT_BOOTSTRAP"]})
        topics=[gate.policy.triage_topic,"admission-pin-proof"]
        for future in admin.create_topics([NewTopic(t,1,1,config={"cleanup.policy":"delete","retention.ms":"172800000","retention.bytes":"-1"}) for t in topics]).values():
            future.result(10)
        print(json.dumps({t:str(f.result(10).topic_id) for t,f in admin.describe_topics(TopicCollection(topics)).items()}))
    elif sys.argv[1]=="broker-ready":
        for attempt in range(20):
            try:
                AdminClient({"bootstrap.servers":os.environ["CONFLUENT_BOOTSTRAP"]}).list_topics(timeout=2)
                print("broker ready")
                break
            except Exception: time.sleep(1)
        else: raise RuntimeError("lab broker did not become ready")
