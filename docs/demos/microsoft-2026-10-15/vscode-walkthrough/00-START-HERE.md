# Present from VS Code

1. Open `Microsoft-agent-journey.code-workspace`.
2. Keep the numbered YAML files on the left. Begin with `01-agent.yaml`, then use `02` and `03` to explain how we extend that same Agent.
3. In the second Explorer root, right-click a slide PNG and choose **Open to the Side**. YAML stays on the left; the visual is on the right. The PDF is an alternative if your VS Code already supports PDF preview.
4. Click the numbered YAML files in order. Read the SAY comment and point to the indicated block. Keep the source code, comments and filenames visible.

## Suggested route for a short meeting

| Stop | YAML files | Visual on the right |
| --- | --- | --- |
| Build the agent and its capabilities | 01-06 | [01 journey](slides/01-journey.png) |
| Connect and isolate the components | 07-10 | [02 isolation](slides/02-isolation.png) |
| Establish Entra identity and permission checks | 11-14 | [03 Entra blueprint](slides/03-entra-blueprint.png) |
| Control, monitor and evaluate | 15-20 | [04 triage outcome](slides/04-triage.png) |
| Explain the operational use cases | 04 and the optional demo guide | [05 connected systems](slides/05-connected-systems.png), [06 SRE chatbot](slides/06-sre-chatbot.png), [07 SDLC](slides/07-sdlc.png) |
| Supporting runtime work and close | No additional YAML | [08 runtime](slides/08-runtime.png), [09 journeys](slides/09-journeys.png) |

## The sentence to use about tokens

“We use Microsoft Entra-issued access tokens. For our registered agent and MCP APIs, those tokens have signed JWT format. Entra issues them; the gateway validates them and checks permissions.”

The application-to-agent token and the agent-to-MCP token are distinct API access tokens with different audiences and grants. JWT is their format, not an extra gateway credential.

Files 02 and 03 extend file 01. They are deliberately labelled `.patch.yaml`. Files 12 and 13 are separate policies because they protect different request boundaries. File 20 is an evaluation case, not a gateway or Kubernetes resource.

The static slides omit every code slide; the original interactive deck remains available separately in its existing location. You can run the entire file-and-slide walkthrough without cluster access, a model request or tenant credentials.
