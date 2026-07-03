# GitHub Copilot Agent Usage Smoke Test

## Purpose

Use this lightweight exercise to measure how quickly GitHub Copilot Agent consumes usage credits on simple engineering tasks.

This is not a model-quality benchmark. It is a small, repeatable way to collect evidence for tasks that should be cheap: finding one code path, proposing one docs correction, or changing one string.

## Before You Start

Record these values before each task:

| Field | Value |
|---|---|
| Date and time | `{{DATE_TIME}}` |
| Copilot plan or organisation policy | `{{COPILOT_PLAN_OR_POLICY}}` |
| IDE | `{{IDE_NAME_AND_VERSION}}` |
| Copilot mode | Chat / Agent / Edit / Review |
| Model selected | `{{MODEL_NAME}}` |
| Starting usage or remaining credits | `{{STARTING_USAGE}}` |
| Repository | `{{REPOSITORY_NAME}}` |
| Branch | `{{BRANCH_NAME}}` |
| Repo already open or indexed | Yes / No |

Run one task at a time. Stop after the agent answers. Do not let it continue improving, testing, refactoring, or exploring unless the task explicitly asks for that.

## Guardrail Prompt

Paste this before each task:

```text
Keep this task intentionally small.
Read only the files needed to answer.
Do not perform broad repository scans unless necessary.
Do not refactor unrelated code.
Do not run tests unless the task explicitly asks for tests.
Do not make changes unless the task explicitly asks for changes.

At the end, report:
- files read
- commands run
- files changed
- whether you think the task was small, medium, or large
- any reason the task required more context than expected
```

## Small Task 1: Locate And Explain

Prompt:

```text
Find where the application's main configuration is loaded.
Do not change any files.
Read the minimum files needed.

Give me:
- the file path
- the function, component, or class involved
- a three sentence explanation
- files read and commands run
```

Expected size: small.

Record after completion:

| Field | Value |
|---|---|
| Ending usage or remaining credits | `{{ENDING_USAGE}}` |
| Credits used | `{{CREDITS_USED}}` |
| Time taken | `{{TIME_TAKEN}}` |
| Files read | `{{FILES_READ}}` |
| Commands run | `{{COMMANDS_RUN}}` |
| Was the result useful? | Yes / No |

## Small Task 2: Tiny Documentation Fix

Prompt:

```text
Find one README or docs file that explains how to run the project locally.
If there is an obvious typo or outdated command, propose the smallest correction.
Do not edit the file yet.
Give me the exact before and after text only.
```

Expected size: small.

Record the same usage fields after completion.

## Small Task 3: Minimal Code Change

Prompt:

```text
Make the smallest possible code change to improve the wording of one user-facing error message.
Only change one string.
Do not refactor.
Do not run the full test suite.
After editing, show the diff summary and list files changed.
```

Expected size: small.

Record the same usage fields after completion.

## Results Table

| Task | Model | Mode | Start usage | End usage | Credits used | Files read | Commands run | Files changed | Time | Notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Locate config | `{{MODEL_NAME}}` | `{{MODE}}` | `{{START}}` | `{{END}}` | `{{USED}}` | `{{FILES}}` | `{{COMMANDS}}` | `{{CHANGED}}` | `{{TIME}}` | `{{NOTES}}` |
| Docs typo | `{{MODEL_NAME}}` | `{{MODE}}` | `{{START}}` | `{{END}}` | `{{USED}}` | `{{FILES}}` | `{{COMMANDS}}` | `{{CHANGED}}` | `{{TIME}}` | `{{NOTES}}` |
| One string edit | `{{MODEL_NAME}}` | `{{MODE}}` | `{{START}}` | `{{END}}` | `{{USED}}` | `{{FILES}}` | `{{COMMANDS}}` | `{{CHANGED}}` | `{{TIME}}` | `{{NOTES}}` |

## Summary To Send To Copilot Administrators

```text
We ran three intentionally small Copilot Agent tasks with explicit constraints:
- read only the files needed
- avoid broad repository scans
- avoid unrelated refactors
- avoid full test runs unless requested

Measured usage:
- total credits used: {{TOTAL_CREDITS_USED}}
- average credits per small task: {{AVERAGE_CREDITS_PER_TASK}}
- most expensive small task: {{MOST_EXPENSIVE_TASK}}
- credits used by that task: {{MOST_EXPENSIVE_TASK_CREDITS}}

If this is representative, an allowance of {{MONTHLY_ALLOWANCE}} credits would support roughly {{ESTIMATED_SMALL_TASK_COUNT}} similarly small tasks per month.

Please confirm:
1. Which Copilot credit or token accounting model applies to our organisation.
2. Whether Agent mode adds context, tool-call, or repository-index overhead compared with normal chat.
3. Whether administrators can provide per-request, per-session, or per-model usage logs.
4. Whether cheaper default models or agent limits can be configured for simple tasks.
```

## Notes

Copilot usage may be reported as credits rather than raw tokens, depending on the plan and organisation policy. Treat the agent's own estimate as advisory only. The strongest evidence is a before-and-after usage screenshot paired with the exact prompt, selected model, mode, files touched, and commands run.
