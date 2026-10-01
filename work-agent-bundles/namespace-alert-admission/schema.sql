CREATE TABLE IF NOT EXISTS admission_seen (
  cluster text NOT NULL, record_id text NOT NULL, received_at timestamptz NOT NULL,
  PRIMARY KEY(cluster, record_id)
);
CREATE TABLE IF NOT EXISTS admission_groups (
  cluster text NOT NULL, group_id text NOT NULL, namespace text NOT NULL,
  owner_kind text NOT NULL, owner_name text NOT NULL, reason text NOT NULL,
  first_seen timestamptz NOT NULL, last_seen timestamptz NOT NULL,
  severity text NOT NULL, payload jsonb NOT NULL, identity_resolved boolean NOT NULL,
  PRIMARY KEY(cluster, group_id)
);
CREATE TABLE IF NOT EXISTS admission_counts (
  cluster text NOT NULL, group_id text NOT NULL, bucket timestamptz NOT NULL,
  records bigint NOT NULL CHECK(records > 0),
  PRIMARY KEY(cluster, group_id, bucket)
);
CREATE TABLE IF NOT EXISTS admission_reports (
  cluster text NOT NULL, local_day date NOT NULL, mode text NOT NULL,
  body jsonb NOT NULL, created_at timestamptz NOT NULL,
  PRIMARY KEY(cluster, local_day, mode)
);
CREATE TABLE IF NOT EXISTS admission_outbox (
  intent_id text PRIMARY KEY, cluster text NOT NULL, local_day date NOT NULL,
  namespace text NOT NULL, lane text NOT NULL, group_id text NOT NULL,
  topic text NOT NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','sending','sent','unknown','expired')),
  updated_at timestamptz NOT NULL,
  UNIQUE(cluster, local_day, namespace, lane, group_id)
);
CREATE INDEX IF NOT EXISTS admission_outbox_pending ON admission_outbox(status, created_at);
CREATE TABLE IF NOT EXISTS admission_budget (
  cluster text NOT NULL, local_day date NOT NULL, namespace text NOT NULL,
  ceiling integer NOT NULL CHECK (ceiling IN (1,2)),
  used integer NOT NULL DEFAULT 0 CHECK (used >= 0 AND used <= ceiling),
  PRIMARY KEY(cluster,local_day,namespace)
);
CREATE TABLE IF NOT EXISTS admission_binding (
  cluster text PRIMARY KEY, timezone_name text NOT NULL, triage_topic text NOT NULL,
  last_day date NOT NULL
);
