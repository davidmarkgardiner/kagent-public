#!/usr/bin/env python3
"""Build the same diagrams and annotated source into HTML, Markdown and PDF."""
import argparse
import hashlib
import html
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
YAML = ROOT.parent.parent / 'yaml-walkthrough'
E = html.escape
# Approved DICE palette: DESIGN.md.
INK, PAPER, RED, BLUE, GREEN, LINE = '#1C1C1C', '#F4F3EE', '#E60000', '#5A5D5C', '#1C1C1C', '#CCCABC'
FILES = {p.name[:2]: p.name for p in sorted(YAML.glob('[0-9][0-9]-*.yaml'))}


def node(key, x, y, title, sub='', file=None, tone='blue', w=225, h=88):
    return dict(key=key, x=x, y=y, title=title, sub=sub, file=file, tone=tone, w=w, h=h)


def edge(a, b, label='', start='right', end='left', via=None, dashed=False):
    return dict(a=a, b=b, label=label, start=start, end=end, via=via, dashed=dashed)


SLIDES = []


def slide(id, title, cue, nodes, edges, files=(), note='', sources=(), phase='Walkthrough', status='Configuration pattern'):
    SLIDES.append(dict(id=id, title=title, cue=cue, nodes=nodes, edges=edges,
                       files=list(files), note=note, sources=list(sources), phase=phase, status=status))


slide('platform', 'Where agents fit in our platform', 'Define an agent. Connect its context. Govern its access. Embed it in work.', [
    node('human', 50, 150, 'SRE / application', 'Question or event'),
    node('front', 385, 150, 'Agentgateway', 'Identity + route + policy', '08'),
    node('agent', 865, 150, 'Platform agents', 'Instructions + skills + model', '01'),
    node('a2a', 865, 340, 'Specialist agents', 'A2A delegation', '04'),
    node('tools', 385, 340, 'Approved MCP tools', 'Read scoped evidence', '06'),
    node('kb', 50, 515, 'Knowledge base', 'Reviewed platform articles', w=225, h=74),
    node('obs', 335, 515, 'Telemetry', 'Metrics, logs, events', w=225, h=74),
    node('k8s', 620, 515, 'Kubernetes / AKS', 'Workload and fleet state', w=225, h=74),
    node('git', 905, 515, 'Delivery systems', 'Issues, PRs and checks', w=225, h=74),
], [edge('human','front'), edge('front','agent','A2A entry'), edge('agent','a2a','delegate', 'bottom','top'),
    edge('a2a','tools','MCP via gateway','left','right'), edge('tools','kb',start='bottom',end='top',via=470),
    edge('tools','obs',start='bottom',end='top',via=470), edge('tools','k8s',start='bottom',end='top',via=470),
    edge('tools','git',start='bottom',end='top',via=470)], files=('01','04','06','08'),
    note='Use this as the opening map. Agent configuration defines behaviour; A2A delegates tasks; MCP exposes tools. The front-door route does not establish that every native specialist delegation traverses agentgateway. Tool calls use their separately governed route.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/README.md',))

slide('anatomy', 'This is where the agent works', 'One Agent resource, extended with reviewed skills and selected tools.', [
    node('prompt', 55, 155, 'Instructions', 'Purpose + output contract', '01'),
    node('skill', 55, 330, 'Skills', 'Reviewed procedures in Git', '02'),
    node('agent', 480, 245, 'SRE triage Agent', '01 + patches 02 and 03', '01', 'red', w=250, h=110),
    node('model', 905, 155, 'ModelConfig', 'Model route via gateway', '05'),
    node('mcp', 905, 330, 'Selected MCP tools', 'Explicit operation allowlist', '03'),
    node('kb', 480, 500, 'Retrieved knowledge', 'Relevant passages + sources', w=250),
], [edge('prompt','agent'), edge('skill','agent'), edge('agent','model'), edge('agent','mcp'),
    edge('kb','agent',start='top',end='bottom')], files=('01','02','03','05'),
    note='Open file 01, then the two patches. They form one Agent. Skills tell it how to investigate; retrieved articles provide context; tools read systems. The knowledge integration is separate from the Kubernetes-only binding shown in file 03.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/kustomization.yaml',))

slide('connections', 'This is where we connect the agents', 'A2A asks a specialist to do work. MCP lets that specialist call a tool.', [
    node('sre',50,155,'SRE Lens','One operator conversation'),
    node('chat',440,155,'Orchestration Agent','Select + delegate + synthesize','04',w=260),
    node('answer',900,155,'Cited answer','Combined specialist findings',w=250),
    node('graf',50,345,'Grafana specialist','Metrics and application logs','04',w=250),
    node('data',440,345,'Data / incident specialist','Approved operational context','04',w=260),
    node('kube',900,345,'Kubernetes specialist','Workload state and events','04',w=250),
    node('mcp',900,515,'MCP route + backend','Identity, tools and data scope','07',w=250),
], [edge('sre','chat'), edge('chat','answer'),edge('chat','graf','A2A','bottom','top'),
    edge('chat','kube','A2A','bottom','top'), edge('chat','data','A2A','bottom','top'),
    edge('kube','mcp','MCP','bottom','top')], files=('04','06','07','09'),
    note='Specialists keep their own permissions. Point at type: Agent and allowedNamespaces in file 04. Namespace opt-in is separate from Entra authorization. The minimal Grafana object is an example with real tools supplied separately. Return to this map when opening Lens.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/guides/03-sre-orchestration-demo.md',))

slide('knowledge', 'Knowledge becomes evidence the agent can cite', 'Reviewed articles remain the source. Retrieval supplies the relevant passages.', [
    node('docs',50,175,'Platform articles','Runbooks reviewed in Git'),
    node('indexer',440,175,'doc2vec indexer','Chunk + embed + index'),
    node('index',880,175,'platform-kb.db','Passages + vectors + sources'),
    node('agent',50,435,'Knowledge Agent','Question → cited answer'),
    node('mcp',440,435,'querydoc MCP','query_documentation'),
    node('read',880,435,'Retrieve passages','Approved corpus + version'),
], [edge('docs','indexer'),edge('indexer','index'),edge('agent','mcp','tool call'),edge('mcp','read','search'),
    edge('index','read',start='bottom',end='top')], files=('02','06'),
    note='Repository POC: docs/platform-kb → doc2vec → SQLite index → standalone querydoc MCP → knowledge Agent. The tool contract uses productName platform-kb, version current and dbName platform-kb.db. Skills and vector retrieval have different jobs. This diagram describes the packaged POC; no new retrieval request was run while preparing the meeting.',
    sources=('ai-platform/kagent-knowledge-base/README.md','docs/platform-kb/INDEX.md'),status='Repository knowledge-base POC')

slide('catalogue', 'What the MCP integrations let an agent do', 'The Agent selects operations. The gateway and backend enforce access.', [
    node('kube',45,165,'Kubernetes / AKS','k8s_get_resources|k8s_describe_resource|k8s_get_pod_logs','03',w=345,h=150),
    node('kb',430,165,'Knowledge base','query_documentation|Retrieve articles with sources',w=345,h=150),
    node('pg',815,165,'PostgreSQL','get_namespace_count|get_namespace_summary|get_inventory_data_product_details',w=345,h=150),
    node('obs',45,385,'Grafana','Metrics + logs investigation|Specialist tools configured separately',w=345,h=135),
    node('git',430,385,'GitLab SDLC','Issue → branch → files → pipeline|Draft MR + review notes',w=345,h=135),
    node('denodo',815,385,'Denodo','Approved VDP views via JDBC|Identity / driver canary pending',w=345,h=135),
], [], files=('03','06','07','13'),
    note='These are repository integrations with different proof states, not a live inventory. Kubernetes and PostgreSQL tool names are from source. The GitLab SDLC rig exposes no merge/delete/arbitrary API tool. Denodo remains a separate adapter and needs its real driver, network and UAMI canary. PostgreSQL defaults: 50 rows, 32 KiB, 512 characters per cell and 5 seconds; no arbitrary SQL export.',
    sources=('work-agent-bundles/postgres-fastmcp-entra-uami/adapter/server.py', 'work-agent-bundles/postgres-fastmcp-entra-uami/WORK-AGENT-TOKEN-EFFICIENCY-HANDOFF.md', 'work-agent-bundles/kind-kagent-sdlc-rig/README.md', 'docs/demos/microsoft-2026-10-15/meeting-walkthrough/vscode-presentation/REFERENCE-NOTES.md', 'docs/ai-grafana/kagent-grafana-mcp-demo.md'), status='Repository integrations; individual proof varies')

slide('identity', 'Microsoft Entra objects make access accountable', 'Two API boundaries. Two audiences. Separate grants.', [
    node('caller',45,165,'Calling app / UAMI','Entra A2A access token','12',w=245),
    node('in',455,165,'Gateway A2A policy','Caller + audience + app role','12',w=280,tone='red'),
    node('agent',925,165,'Named SRE Agent','Only the allowed route','08',w=235),
    node('child',45,350,'Child Agent ID','Entra MCP access token','11',w=245),
    node('out',455,350,'Gateway MCP policy','Agent ID + role + tool','13',w=280,tone='red'),
    node('mcp',925,350,'MCP backend','Scoped downstream access','07',w=235),
    node('sa',45,535,'AKS ServiceAccount','Projected workload identity','11',w=245,h=75),
    node('blueprint',455,535,'Agent identity blueprint','Federated token exchange','11',w=280,h=75),
    node('mint',925,535,'Child token','Issued by Entra','10',w=235,h=75),
], [edge('caller','in','A2A audience'),edge('in','agent'),edge('child','out','MCP audience'),edge('out','mcp'),
    edge('sa','blueprint'),edge('blueprint','mint')],files=('10','11','12','13','14'),
    note='Entra issues signed JWT access tokens; the gateway validates signature, issuer, expiry, audience and authorization claims. An agent identity blueprint creates child agent identities with separate API permissions. File 11 shows the token-holder workload/ServiceAccount pattern; the full federated exchange is in the identity guide. Kubernetes objects, ReferenceGrant and NetworkPolicy enforce different boundaries.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/guides/01-entra-agent-blueprint-setup.md',))

slide('lgtm', 'LGTM shows token usage and agent performance', 'Correlate model usage, tool calls and runtime behaviour with the same investigation.', [
    node('runtime',45,155,'Agents + agentgateway','Model / MCP calls|Run and request telemetry','17',w=260,h=110),
    node('collect',45,395,'Alloy / OTel collector','Collect + forward telemetry','18',w=260,h=110),
    node('metrics',440,155,'Mimir / Prometheus','Input + output tokens|Latency, rates, errors','19',w=285,h=110),
    node('logs',440,330,'Loki','Gateway / agent logs|Identity + route + status','17',w=285,h=100),
    node('traces',440,500,'Tempo','Model + MCP + A2A spans|Trace the investigation','17',w=285,h=100),
    node('grafana',925,330,'Grafana','Usage + performance|Drill into logs and traces','19',w=235,h=110,tone='red'),
], [edge('runtime','collect',start='bottom',end='top'),edge('collect','metrics'),edge('collect','logs'),
    edge('collect','traces'),edge('metrics','grafana'),edge('logs','grafana'),edge('traces','grafana')],
    files=('17','18','19'),
    note='LGTM is Loki for logs, Grafana for visualisation, Tempo for traces and Mimir for metrics. Gateway model usage, timing and errors complement agent/tool telemetry and evaluator outputs. Use shared run/trace correlation when available. Gateway native model-level token aggregates do not establish per-agent attribution; verify identity/run correlation before claiming agent-specific usage. Missing token telemetry is missing evidence. This is the repository monitoring pattern, not a freshly inspected dashboard or a cost-in-currency calculation. Do not put raw tokens, unrestricted prompts or tool results into routine logs.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/guides/02-gateway-security-monitoring-evaluation.md','observability/agent-evals/FLEET-DASHBOARD.md'),
    status='Monitoring design · verify telemetry attribution on the target')

slide('evaluation', 'Evaluation checks whether the agent did the job', 'Compare captured behaviour with a known case and its expected outcome.', [
    node('case',45,165,'Golden evaluation case','Scenario + expected result|Required tools + boundaries','20',w=260,h=110),
    node('run',45,430,'Captured agent run','Answer + tool arguments|Trace + latency + tokens',w=260,h=110),
    node('score',440,270,'Deterministic evaluator','Diagnosis + evidence + tools|Namespace + safety gates|Token and latency budgets','20',w=285,h=150,tone='red'),
    node('result',925,165,'Pass / fail + evidence','Hard failures override score|Check expected capabilities',w=235,h=110),
    node('judge',440,500,'DeepEval · optional','Semantic quality + faithfulness|Supplemental judge layer',w=285,h=110),
    node('dashboard',925,440,'Grafana + CI / audit','Scores + regression trends|Review before promotion','19',w=235,h=110),
], [edge('case','score'),edge('run','score'),edge('score','result'),edge('result','dashboard',start='bottom',end='top'),
    edge('run','judge',dashed=True),edge('judge','dashboard',dashed=True)],files=('19','20'),
    note='The implemented repository baseline is the local deterministic AgentEvalCase / lifecycle scorer over captured runs. It checks required and forbidden tools, namespace, diagnosis/evidence/output and available latency/token budgets. Lifecycle cases also check human approval, verification and incident update. DeepEval is documented as an optional supplemental semantic layer, not an installed or exercised judge in this pack. A term score alone does not prove semantic correctness. Require fresh complete receipts for promotion; missing dimensions may be not_scored in the scorer. Evaluator metrics are separate from native gateway metrics. Illustrative file-20 budgets: score 0.85, latency 90 seconds and 5,000 tokens.',
    sources=('observability/agent-evals/README.md','observability/agent-evals/LIFECYCLE-EVALUATION.md','observability/agent-evals/deepeval/README.md'),
    status='Implemented deterministic scorecard · optional semantic evaluation')

slide('policies', 'Now show the gateway policies', 'Switch to Chrome for the gateway UI, then return here for the visual walkthrough.', [
    node('request',55,160,'Incoming request','Verified identity + route','08',w=235),
    node('identity',465,160,'Identity + authorization','JWT, caller/child ID, role','12',w=280,tone='red'),
    node('tools',925,160,'Tool policy','Named MCP operations','13',w=235),
    node('network',55,390,'Backend isolation','Gateway-only ingress','14',w=235),
    node('limits',465,390,'Model controls','Timeout + request/token limits','15',w=280),
    node('observe',925,390,'Telemetry','Traces, metrics and alerts','17',w=235),
], [edge('request','identity'),edge('identity','tools'),edge('network','request',start='top',end='bottom'),
    edge('identity','limits',start='bottom',end='top'),edge('limits','observe')],
    files=('08','12','13','14','15','16','17','18','19','20'),phase='Chrome · gateway UI',
    note='In Chrome, show the actual routes, backend references and accepted/effective policies. Then inspect one allowed tool and its corresponding request telemetry. Examples 15/16 are version-dependent, illustrative controls; local request/token limits are per proxy, not a fleet-wide monetary budget. File 20 is local scorer input, not a Kubernetes resource. No dashboard URL was supplied and none is invented.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/guides/02-gateway-security-monitoring-evaluation.md',))

slide('triage', 'From telemetry to an accountable incident', 'Kafka carries evidence. Argo coordinates the work. The agent investigates.', [
    node('alloy',50,165,'Alloy','Logs + Kubernetes events',w=225),
    node('vector',440,165,'Vector','Redact, normalize, bound',w=225),
    node('kafka',900,165,'Kafka','Evidence topic',w=225),
    node('issue',50,440,'GitLab issue','Diagnosis + evidence + next step',w=225,tone='green'),
    node('agent',440,440,'Read-only specialist','Selected MCP evidence','03',w=225),
    node('argo',900,440,'Argo Events / Workflow','Trigger, claim, retry, record',w=225),
], [edge('alloy','vector'),edge('vector','kafka'),edge('kafka','argo',start='bottom',end='top'),
    edge('argo','agent','investigate','left','right'),edge('agent','issue','return diagnosis','left','right')],
    files=('01','03','04'),phase='Visual presentation',status='Recorded evidence-first lab path',
    note='This is the retained logs/events evidence-first path. Metric alerts have a distinct Alertmanager route. Argo owns durable admission/retry/ticketing; Vector short-window dedupe is not durable incident memory. The read-only agent returns evidence and a proposal; execution authority belongs to separately scoped workflows.',
    sources=('work-agent-bundles/evidence-first-worker-triage/next-phase-end-to-end/evidence/phase5-value.md', 'docs/observability/dual-source-kafka-triage-routing.md'))

slide('workflow', 'Build agents into the delivery workflow', 'The output is a reviewable change with checks and verification.', [
    node('request',50,170,'Request / incident','Issue + acceptance criteria',w=225),
    node('plan',445,170,'Plan + investigate','Scoped evidence and skills',w=250),
    node('build',925,170,'Prepare change','Isolated branch / draft PR',w=225),
    node('verify',50,450,'Verify outcome','Health + telemetry + receipts',w=225,tone='green'),
    node('human',445,450,'Human decision','Approve exact PR / action',w=250,tone='red'),
    node('check',925,450,'Independent checks','CI + review + evidence',w=225),
], [edge('request','plan'),edge('plan','build'),edge('build','check',start='bottom',end='top'),
    edge('check','human','ready for review','left','right'),edge('human','verify','approved delivery','left','right')],
    phase='Visual presentation',status='Workflow pattern; implementation varies',
    note='Use this to connect triage, fleet operations and SDLC. The bounded GitLab rig prepares draft MRs and leaves the human decision explicit. A separately scoped workflow executes approved changes. This diagram is a workflow pattern, not evidence that every depicted route is installed.',
    sources=('work-agent-bundles/kind-kagent-sdlc-rig/README.md',))

slide('durable', 'An event starts a durable piece of work', 'The embedded classifier decides when to hand over. Substrate starts or resumes the work environment.', [
    node('signals',40,165,'Process signals','K8s events · logs|Trades · database changes',w=250,h=110),
    node('classify',440,165,'Embedded classification','Decide + classify + hand over',w=285,h=110),
    node('substrate',925,165,'Substrate','Create / resume environment',w=235,h=110),
    node('observe',40,460,'Continue observing','No task needed',w=250,h=100),
    node('state',440,450,'Task context','State + environment|Knowledge + workflow + goal',w=285,h=120),
    node('durable',925,450,'Durable agent','Investigate + prepare work',w=235,h=120,tone='red'),
], [edge('signals','classify'),edge('classify','substrate','dispatch task'),edge('classify','observe','no work','bottom','top'),
    edge('substrate','durable',start='bottom',end='top'),edge('state','durable','load / persist')],
    phase='Visual presentation',status='PoC direction · broader event sources proposed',
    note='Describe the architecture David is building. The classifier is embedded in the process; it hands a bounded task to a durable agent running in an environment managed by Substrate. The task carries a goal, workflow and available knowledge. Logs/events motivate the first use case. Trades and database changes are proposed inputs. Persistence/resume semantics depend on the runtime and storage configuration; this slide makes no exactly-once or complete-host-loss recovery claim.',
    sources=('work-agent-bundles/agent-substrate/README.md',))

slide('board', 'The human comes back to completed work', 'One task stays visible across execution, pause/resume and the approval decision.', [
    node('queued',40,175,'Classified','Task + goal|Evidence attached',w=245,h=120),
    node('running',330,175,'Working','Durable environment|Scoped tools + knowledge',w=245,h=120),
    node('review',620,175,'Ready for approval','PR / proposed action|Checks + evidence',w=245,h=120,tone='red'),
    node('done',910,175,'Verified','Approved execution|Outcome receipt',w=245,h=120,tone='green'),
    node('saved',330,450,'Persist / resume','Task + environment state|Continue the same work',w=245,h=110),
    node('decision',720,450,'Human approval','Approve exact PR / action|Or return it for revision',w=340,h=110,tone='red'),
], [edge('queued','running'),edge('running','review'),
    dict(a='decision',b='done',label='',start='right',end='bottom',via=None,dashed=False,
         points=[(1060,505),(1175,505),(1175,355),(1032,355),(1032,295)]),
    edge('running','saved',start='bottom',end='top'),edge('review','decision',start='bottom',end='top'),
    edge('decision','running','revise','left','bottom',via=390,dashed=True)],
    phase='Visual presentation',status='Conceptual UI board · no live task state',
    note='This is a visual representation of the intended board, not a connected dashboard. The agent works within scope and returns with the result, evidence and a reviewable PR or action. Approval releases the separately authorized executor; verification then supplies a receipt. The board should make waiting, failures and requests for input visible. No task or approval is submitted by these slides.',
    sources=('work-agent-bundles/agent-substrate/README.md',))

slide('lens', 'The SRE lens brings the evidence together', 'Finish in Chrome with a question and the actual specialist handoffs.', [
    node('human',50,170,'SRE question','Approved workload + time window',w=250),
    node('lens',445,170,'SRE Lens orchestrator','Route + correlate + synthesize','04',w=285,tone='red'),
    node('answer',925,170,'One cited answer','Timeline + gaps + next action',w=235,tone='green'),
    node('obs',50,445,'Grafana specialist','Metrics + application logs',w=250),
    node('kube',445,445,'Kubernetes specialist','Resources + events + health','03',w=285),
    node('context',925,445,'Data / incident specialist','Approved context + history',w=235),
], [edge('human','lens'),edge('lens','answer'),edge('lens','obs','A2A','bottom','top'),
    edge('lens','kube','A2A','bottom','top'),edge('lens','context','A2A','bottom','top')],files=('04',),
    phase='Chrome · SRE Lens',status='Prepared live prompts · environment not rehearsed',
    note='Open the existing SRE Lens in Chrome. Use one of the prepared read-only prompts and point at actual specialist/tool receipts. Show the cited timeline and any missing evidence. A plausible synthesized answer alone does not prove specialist delegation. No Lens URL was supplied; this pack does not invoke any agent.',
    sources=('docs/demos/microsoft-2026-10-15/yaml-walkthrough/guides/03-sre-orchestration-demo.md',))

PROMPTS = [
    'Investigate the reported latency in {{APPROVED_NAMESPACE}}/{{APPROVED_WORKLOAD}} over {{TIME_WINDOW}}. Ask the permitted Grafana specialist for application metrics and logs, the Kubernetes specialist for runtime health and events, and the data/incident specialist for approved context. Return one cited timeline, observations, hypotheses, missing evidence and a proposed next action. Keep the investigation read-only.',
    'For {{APPROVED_NAMESPACE}}/{{APPROVED_WORKLOAD}}, correlate recent Kubernetes events, application errors and the approved incident or change history over {{TIME_WINDOW}}. Show which permitted specialists supplied each finding. State what the evidence supports, what is uncertain and what a human should review next. Do not change resources, incidents or code.'
]


def anchor(n, side):
    x,y,w,h = (n[k] for k in ('x','y','w','h'))
    return {'right':(x+w,y+h/2),'left':(x,y+h/2),'top':(x+w/2,y),'bottom':(x+w/2,y+h)}[side]


def svg(s, number):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" role="img" aria-labelledby="title desc"><title id="title">{E(s["title"])}</title><desc id="desc">{E(s["cue"])}</desc>',
         f'<rect width="1200" height="680" fill="{PAPER}"/><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{RED}"/></marker></defs>',
         '<style>text{font-family:Arial,Helvetica,sans-serif}a:hover rect{stroke-width:3}a:focus{outline:3px solid #9f352b}</style>',
         f'<text x="40" y="65" font-size="34" font-weight="600" fill="{INK}">{E(s["title"])}</text>',
         f'<text x="40" y="105" font-size="18" fill="{BLUE}">{E(s["cue"])}</text>']
    bykey={n['key']:n for n in s['nodes']}
    for e in s['edges']:
        x1,y1=anchor(bykey[e['a']],e['start']); x2,y2=anchor(bykey[e['b']],e['end'])
        if e['start'] in ('top','bottom') or e['end'] in ('top','bottom'):
            mid=e['via'] if e['via'] is not None else round((y1+y2)/2)
            d=f'M {x1} {y1} V {mid} H {x2} V {y2}'
            lx,ly=(x1+x2)/2,mid-8
        else:
            mid=round((x1+x2)/2); d=f'M {x1} {y1} H {mid} V {y2} H {x2}'
            lx,ly=mid,round((y1+y2)/2)-10
        if e.get('points'):
            d='M '+' L '.join(f'{x} {y}' for x,y in e['points'])
        dash=' stroke-dasharray="6 5"' if e['dashed'] else ''
        out.append(f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="2"{dash} marker-end="url(#arrow)"/>')
        if e['label']:
            text=e['label']; tw=len(text)*8+12
            out.append(f'<rect x="{round(lx-tw/2)}" y="{ly-15}" width="{tw}" height="21" fill="{PAPER}"/><text x="{lx}" y="{ly}" text-anchor="middle" font-size="15" fill="{INK}">{E(text)}</text>')
    for n in s['nodes']:
        x,y,w,h=(n[k] for k in ('x','y','w','h')); color={'blue':BLUE,'red':RED,'green':GREEN}[n['tone']]
        link=n['file']
        if link:
            file=FILES[link]
            out.append(f'<a href="../../../yaml-walkthrough/{E(file)}" data-file="{E(file)}" aria-label="Open {E(file)}">')
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#FFFFFF" stroke="{LINE}" stroke-width="1.5"/>')
        if n['tone']=='red': out.append(f'<path d="M{x} {y} H{x+w}" stroke="{RED}" stroke-width="3"/>')
        title_size=min(20,round((w-32)/(len(n['title'])*0.59),1))
        out.append(f'<text x="{x+16}" y="{y+31}" font-size="{title_size}" font-weight="600" fill="{INK}">{E(n["title"])}</text>')
        for j,line in enumerate(n['sub'].split('|')):
            size=min(16,round((w-32)/max(1,len(line)*0.53),1))
            out.append(f'<text x="{x+16}" y="{y+57+j*24}" font-size="{size}" fill="{INK}">{E(line)}</text>')
        if link: out.append('</a>')
    out.append(f'<path d="M40 634 H1160" stroke="{LINE}"/><text x="40" y="660" font-size="14" fill="{BLUE}">{E(s["status"])}</text><text x="1160" y="660" text-anchor="end" font-size="14" fill="{BLUE}">{number:02d} / {len(SLIDES):02d}</text></svg>')
    result=''.join(out)
    import re
    result=re.sub(r'\b(\d+)\.0\b', r'\1', result)
    for name in ('arrow', 'title', 'desc'):
        result=result.replace(f'id="{name}"',f'id="{s["id"]}-{name}"').replace(f'#{name})',f'#{s["id"]}-{name})')
    return result.replace('aria-labelledby="title desc"', f'aria-labelledby="{s["id"]}-title {s["id"]}-desc"')


def build():
    diagrams=ROOT/'diagrams'; diagrams.mkdir(exist_ok=True)
    expected={f'{i:02d}-{s["id"]}.svg' for i,s in enumerate(SLIDES,1)}
    for generated in diagrams.glob('*.svg'):
        if generated.name not in expected: generated.unlink()
    content=[]; md=['# Microsoft meeting: agents in our workflows', '',
        'Open this Markdown in VS Code with **Markdown: Open Preview to the Side**. The diagrams render as images; expand the annotated YAML under each stop. The interactive HTML presenter opens the real files in the left editor.', '',
        'Agent and security walkthrough → gateway UI in Chrome → workflow diagrams → SRE Lens in Chrome.', '',
        '## Meeting stops', '']
    for i,s in enumerate(SLIDES,1): md.append(f'{i}. [{s["title"]}](#{s["id"]})')
    for i,s in enumerate(SLIDES,1):
        image=svg(s,i); (diagrams/f'{i:02d}-{s["id"]}.svg').write_text(image)
        refs=[]
        for key in s['files']:
            file=FILES[key]; refs.append(f'<button data-file="{file}">{E(file)}</button>')
        sources=''.join(f'<li><button data-source="{E(p)}">Source {j}: {E(Path(p).stem.replace("kagent", "agent").replace("-", " "))}</button></li>' for j,p in enumerate(s['sources'],1))
        prompts=''
        if s['id']=='lens':
            prompts=''.join(f'<div class="prompt"><p>{E(p)}</p><button data-copy="{j}">Copy prompt {j+1}</button></div>' for j,p in enumerate(PROMPTS))
        handoff='<button data-chrome="gateway">Open gateway in Chrome</button>' if s['id']=='policies' else '<button data-chrome="lens">Open SRE Lens in Chrome</button>' if s['id']=='lens' else ''
        content.append(f'<section id="{s["id"]}" class="slide" aria-label="{E(s["title"])}">{image}<div class="file-links">{"".join(refs)}{handoff}</div>{prompts}<details class="notes"><summary>Presenter notes and sources</summary><p>{E(s["note"])}</p><ul>{sources}</ul></details></section>')
        md.extend(['',f'<a id="{s["id"]}"></a>', '', f'## {i:02d}. {s["title"]}', '',
                   f'![{s["title"]}](diagrams/{i:02d}-{s["id"]}.svg)', '', f'*{s["status"]}*', ''])
        if s['files']:
            md.append(' · '.join(f'[{FILES[k]}](../../yaml-walkthrough/{FILES[k]})' for k in s['files']))
            for key in s['files']:
                file=FILES[key]
                md.extend(['', '<details>', f'<summary>Annotated YAML: {file}</summary>', '', '```yaml',
                           (YAML/file).read_text().rstrip(), '```','', '</details>',''])
        md.extend(['<details>', '<summary>Presenter notes and sources</summary>', '',s['note'],''])
        md.extend(f'- [{p}](../../../../../{p})' for p in s['sources'])
        md.extend(['','</details>',''])
        if s['id']=='lens':
            for p in PROMPTS: md.extend(['> '+p,''])
        md.append('[Back to meeting stops](#meeting-stops)')
    (ROOT/'PRESENTATION.md').write_text('\n'.join(md)+'\n')
    template=(ROOT/'presenter-template.html').read_text()
    options=''.join(f'<option value="{i}">{i+1:02d} · {E(s["title"])}</option>' for i,s in enumerate(SLIDES))
    template=template.replace('<!--SLIDES-->','\n'.join(content)).replace('<!--OPTIONS-->',options).replace('/*PROMPTS*/',json.dumps(PROMPTS)).replace('/*PHASES*/',json.dumps([s['phase'] for s in SLIDES]))
    (ROOT/'index.html').write_text(template)
    manifest=[dict(id=s['id'],title=s['title'],phase=s['phase'],status=s['status'],diagram=f'diagrams/{i:02d}-{s["id"]}.svg',files=[FILES[k] for k in s['files']],sources=s['sources']) for i,s in enumerate(SLIDES,1)]
    (ROOT/'slides.json').write_text(json.dumps(manifest,indent=2)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in YAML.glob('[0-9][0-9]-*.yaml')}
    (ROOT/'yaml-source-hashes.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
    print(f'Built {len(SLIDES)} diagrams, HTML presenter and Markdown with exact YAML source.')


def pdf():
    with tempfile.TemporaryDirectory(prefix='microsoft-slides-') as temp:
        pages=[]
        for s in json.loads((ROOT/'slides.json').read_text()):
            p=ROOT/s['diagram']
            dest=Path(temp)/(p.stem+'.pdf')
            subprocess.run(['rsvg-convert','--format=pdf','--output',str(dest),str(p)],check=True)
            pages.append(str(dest))
        subprocess.run(['pdfunite',*pages,str(ROOT/'meeting-visuals.pdf')],check=True)
    print('Built meeting-visuals.pdf from the same vector diagrams.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--pdf',action='store_true'); args=parser.parse_args()
    build()
    if args.pdf: pdf()
