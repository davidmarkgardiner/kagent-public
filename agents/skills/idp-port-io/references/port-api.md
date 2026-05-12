# Port.io API Reference

Base URL: `https://api.getport.io`

## Authentication

```bash
# Get access token (expires in 24h)
curl -s -X POST "https://api.getport.io/v1/auth/access_token" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"CLIENT_ID","clientSecret":"CLIENT_SECRET"}'
# Returns: {"accessToken":"...","expiresIn":86400,"tokenType":"Bearer"}

# Use in subsequent requests:
-H "Authorization: Bearer $TOKEN"
```

## Blueprints

### Create Blueprint
```bash
curl -s -X POST "https://api.getport.io/v1/blueprints" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @blueprint-namespace.json
```

### Get Blueprint
```bash
curl -s "https://api.getport.io/v1/blueprints/namespace" \
  -H "Authorization: Bearer $TOKEN"
```

### Blueprint Schema
```json
{
  "identifier": "namespace",
  "title": "Namespace",
  "icon": "Namespace",
  "schema": {
    "properties": {
      "field_name": {"type": "string", "title": "Display Name"}
    },
    "required": ["field_name"]
  },
  "relations": {
    "cluster": {"target": "cluster", "required": true, "many": false}
  }
}
```

Supported property types: `string`, `number`, `boolean`, `object`, `array`.
String formats: `email`, `date-time`, `url`, `entity` (for relations in actions).

## Entities

### Create/Upsert Entity
```bash
curl -s -X POST "https://api.getport.io/v1/blueprints/namespace/entities?upsert=true&merge=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "identifier": "platform-dev-api",
    "title": "platform-dev-api",
    "properties": {"namespace": "platform-dev-api", "status": "Active"},
    "relations": {"cluster": "homelab"}
  }'
```

- `upsert=true`: create if not exists, update if exists
- `merge=true`: merge properties instead of replacing all

### Delete Entity
```bash
curl -s -X DELETE "https://api.getport.io/v1/blueprints/namespace/entities/platform-dev-api" \
  -H "Authorization: Bearer $TOKEN"
```

## Actions

### Create Action
**IMPORTANT**: Use `/v1/actions`, NOT `/v1/blueprints/{id}/actions`.

```bash
curl -s -X POST "https://api.getport.io/v1/actions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @action-create-namespace.json
```

### Action Structure
```json
{
  "identifier": "create_namespace",
  "title": "Create Namespace",
  "trigger": {
    "type": "self-service",
    "operation": "CREATE",          // CREATE | DELETE | DAY-2
    "blueprintIdentifier": "namespace"
  },
  "invocationMethod": {
    "type": "WEBHOOK",
    "url": "https://your-endpoint/namespace-action",
    "agent": true,                  // use Port agent (if deployed)
    "method": "POST",
    "body": {
      "namespace": "{{ .inputs.namespace }}",
      "owner": "{{ .trigger.by.user.email }}"
    }
  },
  "userInputs": {
    "properties": {
      "namespace": {"type": "string", "pattern": "^[a-z][a-z0-9-]{2,62}$"},
      "environment": {"type": "string", "enum": ["dev", "staging", "prod"]}
    },
    "required": ["namespace"],
    "order": ["namespace", "environment"]
  },
  "requiredApproval": false
}
```

### Template Variables in Action Body
- `{{ .inputs.field_name }}` — user input values
- `{{ .trigger.by.user.email }}` — triggering user's email
- `{{ .entity.properties.field }}` — entity properties (for DAY-2/DELETE)
- `{{ .entity.relations.relation }}` — entity relations
- `{{ .payload.action.invocation.runId }}` — action run ID for status updates

### Update Action Run Status
```bash
curl -s -X PATCH "https://api.getport.io/v1/actions/runs/$RUN_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"status":"SUCCESS","message":"Namespace created"}'
# status: SUCCESS | FAILURE
```

## Scorecards

### Create Scorecard
```bash
curl -s -X POST "https://api.getport.io/v1/blueprints/namespace/scorecards" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @scorecard-namespace.json
```

### Scorecard Structure
```json
{
  "identifier": "namespace_compliance",
  "title": "Namespace Compliance",
  "rules": [
    {
      "identifier": "has_resource_quota",
      "title": "Has Resource Quota",
      "level": "Gold",           // Bronze | Silver | Gold
      "query": {
        "combinator": "and",
        "conditions": [
          {"property": "has_resource_quota", "operator": "=", "value": true}
        ]
      }
    }
  ]
}
```

Operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `doesNotContain`, `isNotEmpty`, `isEmpty`.

## Rate Limits
- Free tier: 10 requests/second
- Token valid for 24 hours
- Upsert is idempotent — safe to retry
