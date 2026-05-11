# Claude Daily OS

David's executive assistant context layer. These files power the daily briefing workflow and keep Claude context-aware across sessions.

## Folder Structure

```
claude/
├── README.md           <- This file
├── context/
│   ├── profile.md      <- Who David is, preferences, goals
│   ├── portfolio.md    <- Stock tickers to track
│   └── projects.md     <- Active projects and status
├── schedule.md         <- Weekly/monthly recurring items
├── inbox/              <- Drop files here for processing
├── outbox/
│   └── daily/          <- Generated daily briefings (YYYY-MM-DD.md)
└── logs/               <- Session logs
```

## How It Works

### Morning Routine

Trigger: "let's start our day" / "morning" / "daily briefing"

1. Claude reads all context files
2. Asks 3 adaptive questions (#1 priority, todo list, fires)
3. Fetches live data (weather, stocks, news, K8s status)
4. Generates briefing to `outbox/daily/YYYY-MM-DD.md`
5. Logs session to `logs/`

### End of Day

Trigger: "wrap up" / "end of day" / "done for today"

1. Summarises what got done
2. Notes incomplete items
3. Updates `context/projects.md`
4. Suggests tomorrow's priorities

## Daily Briefing Sections

| Section | Sources |
|---------|---------|
| Edinburgh Weather | Web search, bike ride + dog walk verdicts |
| Markets & Stocks | Tickers from `context/portfolio.md` |
| Streaming | Netflix, Prime, Disney+ new releases |
| AI & Tech News | Past 24-48 hours |
| Kubernetes & Azure | AKS updates, CNCF news |
| Sports | Scotland Rugby, Celtic FC, FIFA World Cup |
| Edinburgh Events | Local happenings |

## Context Files

### profile.md
Preferences, location (Edinburgh/Stockbridge), role, goals. Claude adapts tone and recommendations based on this.

### portfolio.md
Stock tickers and crypto to track. Format:
```
QQQ, AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
BTC
```

### projects.md
Active projects with status. Claude asks about blockers for in-progress items during morning routine.

### schedule.md
Recurring items. Monday = weekly planning mode. Friday = wrap-up mode. Claude adapts questions based on day of week.

## Integration with Homelab

The daily briefing can pull live data from homelab services:

- **Uptime Kuma** - Service health summary
- **Grafana** - Cluster resource usage
- **Ghostfolio** - Portfolio performance (replaces manual ticker lookup)
- **Vikunja** - Outstanding tasks
- **Home Assistant** - Home status

## Automation (Planned)

Future: n8n workflow on the Proxmox cluster runs at 07:00, fetches all data sources, writes the briefing automatically, and sends a summary notification.
