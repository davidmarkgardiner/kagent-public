# Showcase Applications to Build

**Purpose:** Demo applications that showcase homelab capabilities while providing real value

---

## Category 1: AI-Native Applications

### 1.1 Multi-Agent Orchestrator Dashboard
**Purpose:** Visual management of all AI agents (Scotty, Gem, Kimi, Codex, Data)

**Features:**
- Real-time agent status and health
- Task queue visualization
- Cross-agent communication logs
- Cost tracking per agent (API usage)
- Agent performance metrics
- Load balancing controls

**Tech Stack:**
- Frontend: React + WebSockets
- Backend: Node.js + Redis
- Integration: Langfuse API, Gitea webhooks

**URL:** `agents.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- KubeAI integration
- Langfuse observability
- Multi-agent coordination
- Real-time K8s operations

---

### 1.2 Smart Document Processor
**Purpose:** AI-powered document analysis using local LLMs

**Features:**
- Upload PDFs, images, scans
- OCR + LLM summarization
- Auto-categorization (bills, contracts, receipts)
- Full-text search
- Integration with Paperless-ngx
- Claude/Gemini/Kimi model selection

**Tech Stack:**
- Frontend: Vue.js
- Backend: Python (FastAPI) + Ollama/KubeAI
- Storage: Longhorn PVC
- Queue: Redis

**URL:** `processor.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Local LLM inference (KubeAI)
- Async job processing
- Document AI pipeline
- Storage performance

---

### 1.3 AI Code Review Assistant
**Purpose:** Automated code review for Gitea repositories

**Features:**
- Gitea webhook integration
- Multi-model analysis (Claude, Gemini, GPT-4)
- Security vulnerability detection
- Performance suggestions
- Style guide compliance
- Inline PR comments

**Tech Stack:**
- GitHub Actions-style runner
- Python + LangChain
- Integration: Gitea API, Langfuse

**Deployment:** K8s CronJob + Event-driven

**Showcases:**
- Gitea integration
- Multi-LLM comparison
- DevOps automation
- Code quality pipeline

---

## Category 2: Homelab Management Tools

### 2.1 Homelab Command Center
**Purpose:** Unified dashboard for all homelab resources

**Features:**
- Service health grid (all 20+ services)
- Resource utilization (CPU/RAM/Storage per node)
- SSL certificate expiry tracker
- Backup status overview
- Cost tracking (power estimation)
- Quick actions (restart, scale, logs)
- Mobile-friendly

**Tech Stack:**
- Frontend: SvelteKit
- Backend: Go
- Data: Prometheus queries
- Actions: K8s API

**URL:** `cmd.lab.{{INGRESS_DOMAIN}}` (or integrate into Glance)

**Showcases:**
- Prometheus metrics
- K8s API mastery
- Real-time monitoring
- Unified operations

---

### 2.2 Infrastructure Drift Detector
**Purpose:** Detect unauthorized/untracked changes

**Features:**
- GitOps state comparison
- Configuration drift alerts
- Unauthorized resource detection
- Compliance reporting
- Slack/Discord notifications

**Tech Stack:**
- Kubernetes operator (Go)
- Comparison: Git vs Live state
- Notifications: n8n integration

**Showcases:**
- K8s operator development
- GitOps best practices
- Security monitoring

---

### 2.3 Service Dependency Mapper
**Purpose:** Visual map of service interconnections

**Features:**
- Auto-discover service dependencies
- Traffic flow visualization
- Latency heat maps
- Dependency impact analysis
- Export as architecture diagrams

**Tech Stack:**
- Network flow analysis (eBPF)
- Visualization: D3.js
- Data: Prometheus + custom exporter

**URL:** `map.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Network observability
- eBPF programming
- Complex visualization

---

## Category 3: Developer Productivity

### 3.1 Internal Developer Platform (IDP)
**Purpose:** Self-service platform for new services

**Features:**
- Service templates (web app, API, worker)
- One-click deployments
- Environment provisioning (dev/staging)
- Database provisioning (PostgreSQL, Redis)
- Secret injection
- Monitoring setup (auto-dashboards)

**Tech Stack:**
- Frontend: React + Material UI
- Backend: Node.js + K8s API
- Templates: Helm charts
- GitOps: Gitea integration

**URL:** `platform.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Platform engineering
- Self-service infrastructure
- Template management
- Full-stack automation

---

### 3.2 API Gateway Management UI
**Purpose:** Visual management of Nginx Proxy Manager

**Features:**
- Drag-drop route configuration
- SSL cert management
- Rate limiting controls
- Analytics dashboard
- A/B testing routes
- API documentation hosting

**Tech Stack:**
- Frontend: React
- Backend: Node.js + NPM API
- Additional: Kong/Traefik integration

**URL:** `gateway.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- API gateway patterns
- Network management
- Reverse proxy expertise

---

### 3.3 Ephemeral Environment Manager
**Purpose:** Spin up temporary environments for testing

**Features:**
- One-click preview environments
- Auto-cleanup after TTL
- Branch-based deployments
- Database cloning
- Cost tracking per environment
- Slack notifications

**Tech Stack:**
- K8s operator
- Namespace templating
- Integration: Gitea webhooks
- Scheduler: CronJobs

**Showcases:**
- Advanced K8s patterns
- Resource management
- GitOps workflows

---

## Category 4: Data & Analytics

### 4.1 Personal Data Warehouse
**Purpose:** Centralized analytics for all homelab data

**Features:**
- Data ingestion from all services
- Unified analytics (Grafana, Ghost, Gitea, etc.)
- Trend analysis
- Predictive insights (resource usage)
- Export to various formats

**Tech Stack:**
- Database: ClickHouse or Apache Druid
- ETL: Apache Airflow or Dagster
- Visualization: Apache Superset
- Storage: Longhorn

**URL:** `analytics.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Data engineering
- ETL pipelines
- Big data analytics
- Time-series analysis

---

### 4.2 Homelab Cost Analyzer
**Purpose:** Track and optimize resource costs

**Features:**
- Power consumption estimation
- Resource utilization trends
- Cost per service
- Right-sizing recommendations
- Cloud comparison ("what if in AWS")
- Monthly reports

**Tech Stack:**
- Data collection: Prometheus metrics
- Analysis: Python (Pandas)
- Frontend: Streamlit
- Reports: PDF generation

**URL:** `costs.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Financial analysis
- Resource optimization
- Reporting automation

---

### 4.3 Log Intelligence Platform
**Purpose:** Advanced log analysis beyond Loki

**Features:**
- Log pattern recognition
- Anomaly detection
- Error clustering
- Root cause analysis
- Natural language queries ("show me auth failures")
- Integration with Langfuse traces

**Tech Stack:**
- Backend: OpenSearch or Elasticsearch
- AI: Local LLM for query parsing
- Frontend: Kibana or custom React
- Ingestion: Fluent Bit (already deployed)

**URL:** `logs.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Log analytics
- NLP integration
- Observability expertise

---

## Category 5: Home & Personal

### 5.1 Smart Home Dashboard
**Purpose:** Enhanced Home Assistant companion

**Features:**
- Room-based controls
- Energy monitoring visualization
- Security camera feed wall
- Voice control integration
- Automation rule editor
- Mobile-optimized

**Tech Stack:**
- Frontend: React + WebSockets
- Integration: Home Assistant API
- Charts: D3.js

**URL:** `home.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- IoT integration
- Real-time data
- Mobile UX

---

### 5.2 Family Media Center
**Purpose:** Unified media management (complement to VidAuto)

**Features:**
- Video library management
- Photo album organization
- AI-powered tagging
- Cast to TV (Chromecast/DLNA)
- Request system (Ombi-style)
- Watch together sync

**Tech Stack:**
- Frontend: React
- Backend: Node.js
- Media: Jellyfin API integration
- AI: Auto-tagging with local LLM

**URL:** `media.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Media streaming
- AI content analysis
- Family UX design

---

### 5.3 Personal Finance Visualizer
**Purpose:** Enhanced Ghostfolio with more insights

**Features:**
- Portfolio performance vs benchmarks
- Dividend tracking
- Tax reporting helpers
- Scenario modeling
- AI-powered investment insights
- Integration with bank APIs (via GoCardless)

**Tech Stack:**
- Frontend: Svelte
- Backend: Python
- Data: Ghostfolio API + additional sources
- Charts: TradingView charts

**URL:** `finance.lab.{{INGRESS_DOMAIN}}`

**Showcases:**
- Financial data analysis
- Third-party API integration
- Complex calculations

---

## Quick Wins (Build in 1-2 Days)

| App | Effort | Impact | Priority |
|-----|--------|--------|----------|
| Agent Status Dashboard | 1 day | High | ⭐⭐⭐ |
| SSL Expiry Checker | 4 hours | High | ⭐⭐⭐ |
| Homelab Resource Monitor | 1 day | Medium | ⭐⭐ |
| Gitea PR Summary Bot | 6 hours | Medium | ⭐⭐ |
| Backup Status Dashboard | 1 day | High | ⭐⭐⭐ |

---

## Portfolio-Grade Projects (Build for Showcasing Skills)

### Recommended for External Demonstration:

1. **Multi-Agent Orchestrator** - Shows distributed systems + AI
2. **Internal Developer Platform** - Shows platform engineering
3. **Log Intelligence Platform** - Shows observability + AI
4. **Ephemeral Environment Manager** - Shows K8s mastery
5. **Infrastructure Drift Detector** - Shows security + GitOps

---

## Technology Matrix

| App Category | Primary Language | Database | AI Component | Complexity |
|--------------|------------------|----------|--------------|------------|
| Agent Orchestrator | Node.js | Redis | KubeAI | Medium |
| Document Processor | Python | PostgreSQL | KubeAI/Ollama | High |
| Code Review Bot | Python | SQLite | Multi-LLM | Medium |
| Homelab Command Center | Go + Svelte | Prometheus | None | Medium |
| Drift Detector | Go | etcd | None | High |
| IDP | Node.js | PostgreSQL | None | High |
| Data Warehouse | Python | ClickHouse | Local LLM | Very High |
| Media Center | Node.js | MongoDB | KubeAI | Medium |

---

## Deployment Priority

```
Phase 1 (This Month):
├── Agent Status Dashboard
├── SSL Expiry Checker
└── Backup Status Dashboard

Phase 2 (Next Month):
├── Document Processor
├── Homelab Command Center
└── Code Review Bot

Phase 3 (Quarter):
├── IDP (Internal Developer Platform)
├── Drift Detector
└── Log Intelligence Platform

Phase 4 (Ongoing):
├── Media Center
├── Data Warehouse
└── Cost Analyzer
```

---

*Ready for team review and prioritization*
