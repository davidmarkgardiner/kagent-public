"""Adversarial in-process virtual-day tests; actual PostgreSQL and Kafka.

Transport fixture is separate. This script never submits Kubernetes writes,
Argo workflows, agent invocations or tickets. Seven days are accelerated clocks.
"""
import concurrent.futures
import json
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from confluent_kafka import Consumer, KafkaError, TopicCollection, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
from gate import Gate, KafkaPublisher, Policy, identity

BOOTSTRAP=os.environ['CONFLUENT_BOOTSTRAP']
SETTINGS=json.loads(Path('/code/policy.json').read_text())
SETTINGS['namespaces']=tuple(SETTINGS['namespaces'])
SETTINGS['cluster']='admission-strict-proof'
POLICY=Policy(**SETTINGS)
GATE=Gate(os.environ['DATABASE_URL'],POLICY,lambda p: ('Deployment',p['pod'],True))
NOW=datetime.now(timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0)


def read_topic(topic):
    admin=AdminClient({'bootstrap.servers':BOOTSTRAP})
    desc=admin.describe_topics(TopicCollection([topic]))[topic].result(10)
    c=Consumer({'bootstrap.servers':BOOTSTRAP,'group.id':'strict-proof-'+str(time.time_ns()),
        'enable.auto.commit':False,'isolation.level':'read_committed','enable.partition.eof':True})
    records=[]
    targets={}; positions={}; assignment=[]
    try:
        for p in desc.partitions:
            low,high=c.get_watermark_offsets(TopicPartition(topic,p.id),timeout=5)
            positions[p.id]=low; targets[p.id]=high
            assignment.append(TopicPartition(topic,p.id,low))
        c.assign(assignment)
        deadline=time.monotonic()+15
        while any(positions[p]<high for p,high in targets.items()):
            assert time.monotonic()<deadline,'consumer failed to reach captured high-watermark'
            m=c.poll(.2)
            if m is None: continue
            if m.error():
                assert m.error().code()==KafkaError._PARTITION_EOF,m.error()
                positions[m.partition()]=m.offset(); continue
            positions[m.partition()]=m.offset()+1
            headers={k:v.decode() for k,v in (m.headers() or [])}
            records.append((headers,json.loads(m.value())))
        return records
    finally: c.close()


def signal(day, ns, n):
    return {'schema_version':'observability.triage.v2','cluster':POLICY.cluster,
        'namespace':ns,'pod':'synthetic-workload-'+str(n),'reason':'OOMKilled',
        'severity':'critical','signal_kind':'event','automation_allowed':False,
        'observed_timestamp':day.isoformat(),'dedupe_key':identity(ns,n),
        'delivery_key':identity(day.isoformat(),ns,n),'object_kind':'Pod','event_count':1,
        'evidence':{'event_summary':'Synthetic sustained critical alert proof'}}


def drain(now):
    publisher=KafkaPublisher(allow_plaintext=True)
    while GATE.publish_one(publisher,now): pass


def counts():
    return Counter((h['admission-local-day'],h['admission-namespace']) for h,v in read_topic(POLICY.triage_topic)
        if h.get('admission-cluster')==POLICY.cluster)


results=[]
for d in range(7):
    now=NOW+timedelta(days=d)
    payloads=[signal(now,ns,d*100+n) for ns in POLICY.namespaces for n in range(32)]
    # Repeat each record three times with concurrent intake callers.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p:GATE.ingest(p,now),payloads*3))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:GATE.report(now),range(8)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:drain(now),range(4)))
    GATE.report(now)
    assert not GATE.publish_one(KafkaPublisher(allow_plaintext=True),now)
    day=str(POLICY.local_day(now)); actual=counts()
    expected=[POLICY.overrides.get(ns,POLICY.limit) for ns in POLICY.namespaces]
    assert [actual[(day,ns)] for ns in POLICY.namespaces]==expected,actual
    if d==0:
        # Simulate a restore losing report, send and budget state. Broker and
        # independently pinned topic IDs remain. Enqueue NEW intents as well.
        with GATE.connect() as db:
            for table in ('admission_reports','admission_outbox','admission_budget','admission_binding'):
                db.execute(f'DELETE FROM {table} WHERE cluster=%s',(POLICY.cluster,))
            for ns in POLICY.namespaces:
                GATE.enqueue(db,'post-restore-new-intent',ns,'routine',signal(now,ns,999),POLICY.triage_topic,now)
        drain(now)
        GATE.report(now); drain(now)
        assert counts()==actual,'database rollback refunded an allowance'
    results.append({'virtual_day':d+1,'consumed_by_namespace_limit':expected})

try: GATE.report(NOW)
except RuntimeError: pass
else: raise AssertionError('backward local day did not fail closed')

# An old uncommitted/ambiguous Kafka transaction must be fenced before a
# restored database can publish. Committed consumers see only the new record.
A=Policy('ambiguous-proof',(POLICY.namespaces[0],),mode='enforce',limit=1,report_hour=0,triage_topic=POLICY.triage_topic)
AG=Gate(os.environ['DATABASE_URL'],A)
row={'topic':A.triage_topic,'cluster':A.cluster,'namespace':A.namespaces[0],
    'local_day':A.local_day(NOW),'intent_id':'old-ambiguous-intent'}
old=KafkaPublisher(allow_plaintext=True)
assert old.check(row,A,NOW,1)=='available'
old.client.begin_transaction()
old.client.produce(A.triage_topic,value=json.dumps(signal(NOW,A.namespaces[0],1002)).encode(),
    headers={'admission-intent-id':row['intent_id'],'admission-cluster':A.cluster,
        'admission-namespace':A.namespaces[0],'admission-local-day':str(A.local_day(NOW))})
assert old.client.flush(5)==0
# Post-restore state has no knowledge of the old reservation.
with AG.connect() as db: AG.enqueue(db,'restored-new-intent',A.namespaces[0],'routine',signal(NOW,A.namespaces[0],1003),A.triage_topic,NOW)
assert AG.publish_one(KafkaPublisher(allow_plaintext=True),NOW)
assert sum(h.get('admission-cluster')==A.cluster for h,v in read_topic(A.triage_topic))==1

# Replacement of a broker topic must not reset the allowance.
PIN_TOPIC='admission-pin-proof'
P=Policy('pin-proof',(POLICY.namespaces[0],),mode='enforce',limit=2,report_hour=0,triage_topic=PIN_TOPIC)
PG=Gate(os.environ['DATABASE_URL'],P)
with PG.connect() as db: PG.enqueue(db,'first',P.namespaces[0],'routine',signal(NOW,P.namespaces[0],1000),PIN_TOPIC,NOW)
assert PG.publish_one(KafkaPublisher(allow_plaintext=True),NOW)
assert len(read_topic(PIN_TOPIC))==1
admin=AdminClient({'bootstrap.servers':BOOTSTRAP})
admin.delete_topics([PIN_TOPIC])[PIN_TOPIC].result(10)
for attempt in range(30):
    if PIN_TOPIC not in admin.list_topics(timeout=2).topics: break
    time.sleep(.2)
else: raise AssertionError('topic not deleted')
admin.create_topics([NewTopic(PIN_TOPIC,1,1,config={'cleanup.policy':'delete','retention.ms':'172800000','retention.bytes':'-1'})])[PIN_TOPIC].result(10)
with PG.connect() as db: PG.enqueue(db,'replacement',P.namespaces[0],'routine',signal(NOW,P.namespaces[0],1001),PIN_TOPIC,NOW)
assert PG.publish_one(KafkaPublisher(allow_plaintext=True),NOW)
assert len(read_topic(PIN_TOPIC))==0,'replaced topic received another investigation'
with PG.connect() as db:
    assert db.execute("SELECT status FROM admission_outbox WHERE cluster='pin-proof' AND status='unknown'").fetchone()

print(json.dumps({'result':'PASS','accelerated_days':7,'real_elapsed_days':0,
    'attempted_intake_deliveries':7*3*32*3,'unique_synthetic_signals':7*3*32,
    'concurrent_intake_callers':4,'concurrent_report_calls_per_day':8,'concurrent_publishers':4,
    'consumed_total':sum(counts().values()),'days':results,'database_rollback':'zero extra records',
    'ambiguous_transaction_after_restore':'prior transaction fenced; one committed record',
    'clock_regression':'fails closed','topic_recreation':'fails closed; zero records in replacement topic',
    'scope':'actual PostgreSQL and Kafka; in-process synthetic signals and accelerated day clock; no tickets or agents'},sort_keys=True))
