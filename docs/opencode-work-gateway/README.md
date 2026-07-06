# OpenCode Work Gateway Setup

This note shows how to run OpenCode against a work-hosted OpenAI-compatible
gateway with an API token, using the closest OpenCode equivalent of YOLO mode.

Use placeholders in this repo. Do not commit real gateway hosts, tokens, tenant
IDs, internal model names, or other environment-specific values.

## When To Use This

Use this when:

- Kilo Code works against a work gateway but keeps asking for permissions.
- You want to move the same gateway/token/model setup to OpenCode.
- You want OpenCode to run with auto-approved permissions for a trusted working
  copy.

## Configuration

Create a project-local `opencode.json` in the repository where you want OpenCode
to run:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "work-gateway/{{MODEL_ID}}",
  "provider": {
    "work-gateway": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Work Gateway",
      "options": {
        "baseURL": "https://{{GATEWAY_HOST}}/v1",
        "apiKey": "{env:WORK_GATEWAY_API_KEY}"
      },
      "models": {
        "{{MODEL_ID}}": {
          "name": "{{MODEL_ID}}"
        }
      }
    }
  },
  "permission": "allow"
}
```

Replace:

- `https://{{GATEWAY_HOST}}/v1` with the OpenAI-compatible gateway base URL.
- `{{MODEL_ID}}` with the model ID exposed by the gateway.
- `WORK_GATEWAY_API_KEY` with the environment variable name approved for the
  work setup.

Do not paste the token into `opencode.json`. Keep it in an environment variable
or a local secret file outside Git.

## Run In Auto Mode

Set the token in your shell:

```bash
export WORK_GATEWAY_API_KEY='{{WORK_GATEWAY_API_TOKEN}}'
```

Start the OpenCode TUI with auto-approved permission prompts:

```bash
opencode --auto
```

For a one-shot task:

```bash
opencode run --auto "Summarize this repository and identify the main test command."
```

## YOLO-Style Permissions

OpenCode uses permission config rather than a dedicated `--yolo` flag. The
closest equivalent is:

```json
{
  "permission": "allow"
}
```

Combined with `opencode --auto`, this avoids permission prompts for normal
tool use.

This is intentionally broad. Use it only in a trusted working copy. For safer
day-to-day use, keep shell commands on approval and allow edits:

```json
{
  "permission": {
    "*": "ask",
    "read": "allow",
    "glob": "allow",
    "grep": "allow",
    "edit": "allow",
    "bash": {
      "*": "ask",
      "rg *": "allow",
      "sed *": "allow",
      "git status*": "allow",
      "git diff*": "allow",
      "npm test*": "allow",
      "pytest*": "allow",
      "rm *": "deny",
      "git push*": "deny"
    }
  }
}
```

## Quick Verification

Check the gateway before starting OpenCode:

```bash
curl -fsS \
  -H "Authorization: Bearer ${WORK_GATEWAY_API_KEY}" \
  "https://{{GATEWAY_HOST}}/v1/models" | jq .
```

Then run a small OpenCode smoke test:

```bash
opencode run --auto "Print the current working directory and list the top-level files."
```

Expected result:

- OpenCode starts without asking for the gateway token.
- The selected model is `work-gateway/{{MODEL_ID}}`.
- Tool permission prompts are auto-approved.
- No real token or internal host is written to the repository.

## Troubleshooting

If the model does not appear, verify `{{MODEL_ID}}` exactly matches the gateway
model ID returned by `/v1/models`.

If authentication fails, verify the token is exported in the same shell where
OpenCode is running:

```bash
env | rg '^WORK_GATEWAY_API_KEY='
```

If OpenCode still asks for permissions, confirm the active config file is the
project-local `opencode.json` and that it contains either:

```json
{
  "permission": "allow"
}
```

or a granular permission block that allows the requested tool.

If the gateway needs a provider login instead of `apiKey` in config, start
OpenCode and run:

```text
/connect
```

Choose the custom provider name `Work Gateway` and paste the token into
OpenCode's credential store.

## References

- OpenCode provider config supports OpenAI-compatible providers with
  `@ai-sdk/openai-compatible` and `options.baseURL`.
- OpenCode config supports project-local `opencode.json` and `{env:VAR}`
  substitution.
- OpenCode permissions support `permission: "allow"` and `--auto` for
  auto-approving non-denied permission prompts.
