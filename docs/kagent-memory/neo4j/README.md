# Shared memory for kagent: PostgreSQL, Apache AGE, or Neo4j?

For the kagent use case tested in the local lab, **start with PostgreSQL +
pgvector and relationship tables**. Evaluate Apache AGE when Cypher-style
graph queries would help; add Neo4j only if a fair comparison shows a clear
gain in incident investigation that warrants another stateful service.

This is an architecture recommendation, not a production deployment decision.
The Neo4j work so far is a local kind lab with synthetic data. It proved that
kagent can use bounded graph lookups through MCP and agentgateway; it did not
compare Neo4j with a PostgreSQL implementation on representative incidents or
prove workplace readiness.

## Which option fits?

| Option | Best fit |
|---|---|
| **kagent native memory** | Facts recalled across conversations for one agent and user. Current [kagent memory docs](https://kagent.dev/docs/kagent/1.x/agents/agent-memory/) say it uses external PostgreSQL with pgvector and is **not shared between agents**. Check the installed kagent version before applying 1.x configuration. |
| **Shared PostgreSQL + pgvector** | A common, governed store for incidents, lessons, evidence, and similarity search. Relationship tables and bounded recursive queries can also answer dependency questions. This is already the repo's [production target](../production-target/README.md). |
| **Apache AGE + pgvector** | Graph nodes, edges, and openCypher queries inside PostgreSQL, alongside vector search. It could provide graph traversal without a separate graph database, but it adds an extension, graph model, query integration, and upgrade work. |
| **Neo4j** | A stronger candidate when investigations repeatedly need to follow several relationships—for example, service → dependency → change → incident → runbook. Its [Cypher path queries](https://neo4j.com/docs/cypher-manual/current/patterns/) make that model natural, but it adds another database to operate. |
| **Vector** | If you mean the Vector already in our telemetry pipeline, it [collects, transforms, and routes observability data](https://vector.dev/docs/introduction/); it is not the durable incident-memory store. If you mean *vector search*, pgvector provides that inside PostgreSQL: https://github.com/pgvector/pgvector |

A2A session context carries one conversation or task across turns; it is not
the shared incident store. Keep the agent-facing MCP tools the same whichever
shared-memory backend wins.

The repo's [production memory target](../production-target/README.md) separates
native per-agent memory, shared incident memory, Git runbooks, querydoc search,
and current workflow evidence. Keep Git and querydoc authoritative for
procedures. Treat remembered incidents as hypotheses and verify them against
current read-only cluster and observability evidence.

## Compare the actual alternatives

Use the same curated dataset, embedding model, MCP tool names, result limits,
and questions for all four arms:

1. **PostgreSQL + pgvector:** exact fingerprint filters and similarity search.
2. **PostgreSQL + pgvector + relationship tables:** add bounded recursive
   queries for service dependencies, changes, incidents, and evidence.
3. **PostgreSQL + pgvector + Apache AGE:** use bounded openCypher queries
   over the same entities and relationships, with vector retrieval still in
   PostgreSQL.
4. **Neo4j:** add bounded Cypher traversal over the same entities and
   relationships.

The relational and AGE arms are Neo4j's main competitors. PostgreSQL can
represent a graph using entity and relationship tables; vector search alone
is an unfair comparison. AGE deserves a trial because [Azure Database for
PostgreSQL Flexible Server lists both AGE and
pgvector](https://learn.microsoft.com/en-us/azure/postgresql/extensions/concepts-extensions-versions).
AGE is an Apache extension for PostgreSQL, not a built-in PostgreSQL feature
or a kagent-native memory provider. Azure requires it to be allowlisted and
preloaded, which involves a server restart. Microsoft also warns that AGE is
not supported for every in-place PostgreSQL major-version upgrade path. Check
the actual server version, extension version, access controls, and upgrade path
before using it in the workplace.

Neo4j may earn its place when questions repeatedly cross several relationship
types, such as service to dependency to change to incident to runbook, and
both PostgreSQL approaches are materially less effective.

Evaluate answer correctness on multi-hop questions, negative-case false
matches, source citations, freshness, latency, and operating cost. Include
ambiguous service names, superseded lessons, missing evidence, and backend
failure. Adopt Neo4j only if the improvement is material and its backup,
access-control, HA, and maintenance costs are acceptable.

## Keep the agent boundary stable

Triage agents should call typed, bounded, read-only MCP tools such as
`search_lessons`, `open_lesson`, `find_service_dependencies`,
`find_related_incidents`, and `find_recent_changes`. The MCP service owns
database credentials, query limits, source references, and backend-specific
queries. Do not give triage agents arbitrary SQL or Cypher, direct write tools,
or authority to treat an earlier incident as a current fact.

Only a separate curator workflow should accept proposed lessons, validate
and redact them, write transactionally, and record an audit trail. The current
file-backed `memory-mcp` POC has a documented concurrent-write data-loss risk;
it is not the proposed durable store.

## References

- [Neo4j and kagent team presentation](../neo4j-kagent-team-presentation.html)
- [Durable agent memory production target](../production-target/README.md)
- [Existing memory integration and its concurrency limit](../../memory-integration.md)
- kagent 1.x agent memory: https://kagent.dev/docs/kagent/1.x/agents/agent-memory/
- pgvector: https://github.com/pgvector/pgvector
- PostgreSQL recursive queries: https://www.postgresql.org/docs/current/queries-with.html
- Neo4j Cypher patterns: https://neo4j.com/docs/cypher-manual/current/patterns/
- Apache AGE: https://age.apache.org/
- Azure AGE setup and restart requirement: https://learn.microsoft.com/en-us/azure/postgresql/azure-ai/generative-ai-age-overview
- Azure extension upgrade considerations: https://learn.microsoft.com/en-us/azure/postgresql/extensions/concepts-extensions-considerations
- Vector observability pipeline: https://vector.dev/docs/introduction/
