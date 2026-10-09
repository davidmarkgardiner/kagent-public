# DICE journey: your first SharePoint video collection

This guide takes you from the emailed MP4s to a connected chapter collection that your selected colleagues can watch, discuss and extend. No coding or YouTube is needed. It contains no employer-specific names, addresses or tenant details.

The click paths below describe modern SharePoint Online. Your organisation's settings may change the labels or available actions. If a button is missing, ask the site owner rather than changing policy or using another sharing route.

## Start with one video

For your first session, follow sections 2, 3 and 4 with the BYOA video only. You should finish with one published page that a selected colleague can open and play. Check that an excluded colleague cannot open the page or its direct video URL.

Then use the same layout for the other four chapters. Section 6 builds the index. Section 7 supplies the text to paste. Section 8 shows how other authors can add stories. Finish with the checks in section 9 before sharing the collection link.

## 1. The result we are building

One restricted site, one video library, one journey index, and one page per chapter.

```text
DICE journey — index page
  ├─ 01 · Bring Your Own Agent
  ├─ 02 · Entra Agent ID + agentgateway
  ├─ 03 · Grafana MCP
  ├─ 04 · GitLab MCP
  ├─ 05 · Kubernetes MCP
  └─ Contribute a chapter

Each chapter: short introduction → playable video → takeaways
              → discussion prompt → previous / index / next links
```

The story is: bring an agent → establish its identity and boundaries → connect observability → preserve findings and proposed changes → inspect the cluster. Readers can follow that path or jump directly to a tool chapter. These are editorial chapter numbers, not deployment steps.

Start with these five finished exports. Triage, the wider SDLC workflow, vector knowledge base and PostgreSQL can join later when their final MP4s are available. Do not add a dead video link or describe an unexported chapter as ready.

| Chapter | MP4 attachment | Approx. length | File size, decimal MB |
|---|---|---:|---:|
| 01 · Bring Your Own Agent | `dice-journey-byoa-security-harness-v1.mp4` | 1:50 | 6.0 |
| 02 · Entra Agent ID + agentgateway | `dice-journey-entra-agent-id-v1.mp4` | 2:00 | 7.5 |
| 03 · Grafana MCP | `dice-journey-grafana-mcp-v1.mp4` | 1:50 | 6.7 |
| 04 · GitLab MCP | `dice-journey-gitlab-mcp-v1.mp4` | 1:57 | 6.9 |
| 05 · Kubernetes MCP | `dice-journey-kubernetes-mcp-v1.mp4` | 2:00 | 7.0 |

Lengths are rounded up from the actual files. The films are presenter-free, with narration and presentation visuals. Email transfer is separate from publication: nothing becomes a SharePoint page simply because it was emailed.

## 2. Before you start: get the right site and permissions

Ask your site owner for a **dedicated restricted site**, named **DICE journey**. A communication site is a useful fit for a small publishing team and a larger read-only audience. If your team must use an existing Team-connected site, have its owner check the actual membership and permissions first; a link to a page does not narrow a broadly accessible site.

Suggested roles for a communication site:

| Role | Who | What they should do |
|---|---|---|
| Owners | You and one backup owner | Manage access and the site |
| Members / editors | Selected chapter authors | Upload files and create or edit pages |
| Visitors / readers | Your pod and selected viewers | Read pages and watch videos |

Ask the owner to confirm there is no organisation-wide reader group, unwanted guest access or existing broad sharing link. Group-connected Team sites give their members editing capabilities by default; private/shared channel membership is managed in Teams. Do not add every viewer as an editor just to make playback work. [Microsoft: site permissions](https://learn.microsoft.com/en-us/sharepoint/modern-experience-sharing-permissions)

**Copy this request to your site owner:**

```text
Please help me set up a restricted SharePoint site called DICE journey.

I need a small group of owners/editors who can add chapter pages and MP4s,
and a selected reader group who can view the pages and play the videos.

Please check existing and inherited permissions and sharing links so the
site, chapter pages and video files are not accessible organisation-wide.
Please also confirm whether page comments and video transcripts are enabled.
```

Use your organisation's approved classification and content-sharing rules. If external email attachments are blocked, use its approved transfer process; do not bypass mail or security controls.

## 3. Save and upload the videos

1. Open each chapter delivery email on your work device.
2. Save the MP4 attachments and this guide into an approved local folder. Keep the MP4 filenames unchanged so the table above stays accurate.
3. Open the restricted SharePoint site supplied by the owner.
4. Go to **Settings → Site contents → New → Document library**. Depending on the site, **New → Document library** may appear directly. Name it **Journey Videos**.
5. Open **Journey Videos** and choose **Upload → Files**, or drag the MP4s into the library.
6. Wait for uploads to finish. Open one file and check playback and sound before building the pages.

You need suitable library permissions to upload. If creation or upload is unavailable, ask the owner for help. [Create a library](https://support.microsoft.com/en-us/sharepoint/documents-and-library/create-a-document-library-in-sharepoint), [upload files](https://support.microsoft.com/en-us/sharepoint/documents-and-library/upload-files-and-folders-to-a-library)

Keep videos in this shared site library rather than your personal OneDrive. That makes the collection easier for the team to maintain when ownership changes.

Optional library columns, added using **+ Add column**:

| Column | Type | Purpose |
|---|---|---|
| Chapter order | Number | 1, 2, 3, 4, 5; consistent journey order |
| Story | Choice | Agent onboarding; Identity and access; Investigation; Delivery |
| Topic | Choice | BYOA; Entra; agentgateway; Grafana; GitLab; Kubernetes |
| Chapter owner | Person | Who maintains the chapter |
| Summary | Multiple lines of text | One-sentence description from section 7 |
| Content status | Choice | Draft; Ready for review; Published |
| Reviewed on | Date | Date a named owner checked the content |

Use these as ordinary metadata. Hashtags in a paragraph are not a substitute for searchable library columns or access controls.

## 4. Make the first chapter page

A **page** is what viewers read. A **library** holds the MP4 files. A **web part** is a block you add to a page, such as text, a player or navigation.

1. On the site home page choose **New → Page**. Pick a simple blank page.
2. Enter the title **01 · Bring Your Own Agent**.
3. Use a light background and a simple title area. Avoid a large decorative banner that pushes the player below the first screen.
4. Add a **Text** web part below the title. Paste the chapter 01 introduction from section 7.
5. Add a **File and Media** web part. Choose the BYOA MP4 already uploaded to **Journey Videos**.
6. Add another **Text** block for the takeaways and discussion question.
7. Add **Quick links** below the text. Eventually these will point to the journey index and the next chapter page.
8. If available, leave the page **Comments** switch on. If comments are disabled by policy, use an approved discussion channel linked from the page.
9. Save the draft. When it has been checked, choose **Publish**. Later edits normally use **Republish**.

Modern pages are assembled from web parts and published separately from drafts. [Microsoft: create and use pages](https://support.microsoft.com/en-us/sharepoint/pages-in-sharepoint/create-and-use-modern-pages-on-a-sharepoint-site)

**Important video sharing warning:** the player setup may offer to create a sharing link that lets people across your organisation view the video. For this restricted collection, choose **Don't create** / leave that option unchecked. If offered to copy an external video and create a link, do not accept without checking the resulting permissions. Select the file from the restricted library instead. [Microsoft: embedding videos and sharing prompts](https://support.microsoft.com/en-us/sharepoint/pages-in-sharepoint/using-videos-on-sharepoint-pages)

Comments and publishing controls depend on your tenant configuration. Reader access to a page must also be sufficient for the underlying MP4; fixing a playback problem by creating an organisation-wide link is not the answer.

Keep chapter pages as ordinary pages, not site home pages. SharePoint does not show comments, likes or view counts on a site home page. The journey index can be the home page without losing discussion on the separate chapter pages.

## 5. Give every chapter the same clean layout

Use the approved films' light red, grey, white and black visual language without copying an employer's logo or website assets. Keep the site's approved theme; ask the owner before introducing a custom theme.

Recommended layout:

- White page, short title, one short introductory paragraph.
- Wide 16:9 player in a single-column section.
- Underneath, three short takeaways and one discussion question.
- A quiet light-grey navigation section: **Previous chapter · All chapters · Next chapter**.
- The same headings, thumbnail treatment and spacing on every page.

Do not cram five players into one long home page. Use the index for browsing and chapter pages for watching. Give links descriptive titles instead of “click here”. For the last chapter, replace Next with **Suggest the next story**, linking to the contribution page.

Add text summaries and a reviewed transcript or captions when available. Do not label automatically generated captions as reviewed without checking technical names. A copied script can be a useful text alternative, but compare it with the final narration before publishing it as a verbatim transcript.

## 6. Build the connected journey index

Create another page called **DICE journey**. Use a short introduction followed by **Quick links**, with one tile per chapter page. Choose a consistent tile or list layout, put the links in chapter order, and show each chapter title and duration. Link to the **page**, not just the bare MP4, so viewers get the story and discussion around it. [Microsoft: Quick links](https://support.microsoft.com/en-us/sharepoint/sites-pages/use-the-quick-links-web-part)

**Copy-ready index introduction:**

```text
DICE journey

Bring an agent. Connect approved tools. Keep people in control.

These short chapters show how agent onboarding, identity and scoped tool
access fit together. Follow the journey from the beginning, or jump to
the tool or problem that matters to you.

Each chapter connects a practical capability to its boundaries and human
handoff. Share a question, suggest an improvement, or contribute the next
story using the same chapter format.

Start with Bring Your Own Agent, then explore identity, Grafana, GitLab
and Kubernetes.
```

Suggested tile subtitles:

| Chapter page | Subtitle |
|---|---|
| 01 · Bring Your Own Agent | Your agent, shared security controls · 1:50 |
| 02 · Entra Agent ID + agentgateway | Identity is not permission · 2:00 |
| 03 · Grafana MCP | Turn an alert into focused evidence · 1:50 |
| 04 · GitLab MCP | Keep findings and proposed changes reviewable · 1:57 |
| 05 · Kubernetes MCP | Inspect the cluster; keep changes separate · 2:00 |
| Contribute a chapter | Add the next problem, capability or lesson |

Once chapter pages exist, edit each page's Quick links and insert the actual published page URLs. Use **Copy link → People with existing access** where offered. Never paste localhost, personal file paths or YouTube links into this collection. Keep the index linked in the site's navigation; only make it the site home page if the owner agrees.

## 7. Copy-ready text for the five chapter pages

Paste titles into the page title area. Put introductions above the player and the takeaways and question below it. The navigation lines describe the links to create; they are not already functioning links.

### 01 · Bring Your Own Agent

**Introduction**

Bring your own agent without rebuilding the security controls around it. This chapter follows a small onboarding request through a reusable platform security profile, the deployment review path and scoped connections to approved tools.

**What this chapter explains**

- The developer owns the agent; the platform defines its boundaries.
- Identity, runtime boundaries and approved model and tool routes belong to the security harness.
- Connecting a tool does not give an agent unrestricted access or permission to make changes.

**Join the discussion**

Which agent would you bring first, and what is the smallest useful tool set it needs?

**Story connection**

Start here. Next, see how Entra Agent ID and agentgateway separate identity from permission.

**Navigation:** All chapters → DICE journey; Next → 02 · Entra Agent ID + agentgateway.

**Suggested metadata:** Story = Agent onboarding; Topic = BYOA; related topic = agentgateway.

### 02 · Entra Agent ID + agentgateway

**Introduction**

Knowing who an agent is does not decide what it can do. This chapter connects the identity blueprint, separate caller and agent token boundaries, gateway policy and resource-owner permissions.

**What this chapter explains**

- Authentication, authorisation and human approval answer different questions.
- Gateway access must match the approved agent, API role and requested tool.
- Grafana, GitLab and Kubernetes still enforce their own backend permissions.

**Join the discussion**

For a new agent, who should approve its identity, its tool access and any resource-changing action?

**Story connection**

The onboarding chapter establishes the harness. This chapter explains its identity and access boundaries. Next, apply those boundaries to observability.

**Navigation:** Previous → 01 · Bring Your Own Agent; All chapters → DICE journey; Next → 03 · Grafana MCP.

**Suggested metadata:** Story = Identity and access; Topic = Entra; related topic = agentgateway.

### 03 · Grafana MCP

**Introduction**

An alert is the start of an investigation, not the answer. Grafana MCP gives an agent scoped access to the metrics, logs and dashboard context it needs to return focused evidence to the SRE.

**What this chapter explains**

- The agent's gateway identity and Grafana's backend service account are separate boundaries.
- Investigation tools should expose the approved queries and resources, not automatic dashboard changes.
- Findings should include the query, time window, gaps and a useful link for human review.

**Join the discussion**

Which alert would benefit most from an evidence pack before an SRE picks it up?

**Story connection**

Identity establishes the caller and scope. Grafana provides observability evidence. Next, preserve that evidence and any proposed action in GitLab.

**Navigation:** Previous → 02 · Entra Agent ID + agentgateway; All chapters → DICE journey; Next → 04 · GitLab MCP.

**Suggested metadata:** Story = Investigation; Topic = Grafana; related topic = Observability.

### 04 · GitLab MCP

**Introduction**

Keep the investigation and proposed change in a work record people can review. GitLab MCP connects an agent to bounded issue, repository and delivery operations while leaving the decision to merge with the human.

**What this chapter explains**

- Choose a read-only or bounded delivery profile before connecting the agent.
- Tool scope, project restrictions, backend credentials and branch protection work together.
- A draft merge request and passing checks do not grant authority to merge or deploy.

**Join the discussion**

What evidence should every agent-prepared issue update or draft merge request include before you review it?

**Story connection**

Grafana supplies the observability findings. GitLab makes them durable and reviewable. Next, add current Kubernetes resource state to the investigation.

**Navigation:** Previous → 03 · Grafana MCP; All chapters → DICE journey; Next → 05 · Kubernetes MCP.

**Suggested metadata:** Story = Delivery; Topic = GitLab; related topic = SDLC.

### 05 · Kubernetes MCP

**Introduction**

Give an investigating agent the current cluster facts it needs, not a cluster-administrator toolbox. This chapter starts with a minimal namespace-scoped pod-list profile and explains how gateway checks and Kubernetes permissions bound access.

**What this chapter explains**

- The agent's gateway identity and the MCP workload's cluster credential are not the same identity.
- The minimal profile lists pods; logs, events and other reads require separately approved extensions.
- Investigation remains separate from mutation, command execution and remediation authority.

**Join the discussion**

Which namespace-scoped read would help your team next, and what must remain outside the agent's access?

**Story connection**

Kubernetes adds current state to Grafana's telemetry and GitLab's durable record. Together, those facts support a human decision. Suggest the next chapter to extend the story.

**Navigation:** Previous → 04 · GitLab MCP; All chapters → DICE journey; Next → Contribute a chapter.

**Suggested metadata:** Story = Investigation; Topic = Kubernetes; related topic = Scoped tools.

Editorial note: these pages explain the chapter content. Do not add claims about measured savings, completed workplace deployments, automatic remediation or live enforcement that are not supported by the actual evidence. Tool names and vendors may be mentioned; employer identities should not be included.

## 8. Let other people add chapters

Give selected authors editor access through the site owner. Everyone else can suggest stories through comments or the team's approved request channel. Do not open site editing to all readers merely to collect suggestions.

On a finished chapter page, use the available **Save as template** option from the page save menu. New authors can choose that template under **New → Page**, usually in the **Saved on this site** group. Templates stay with their site. If template controls are unavailable, use the site's copy-page option or ask the owner to supply a reusable page. [Microsoft: page templates](https://support.microsoft.com/en-us/sharepoint/sites-pages/page-templates-in-sharepoint)

**Copy-ready contribution page:**

```text
Contribute the next DICE story

Show one practical problem, the capability that helps solve it, and the
boundary that keeps responsibility clear. Aim for a one-to-two-minute
chapter with a short explanation and a focused demonstration.

Before recording, agree the beginning, middle and end with the chapter
owner. Use the chapter page template so readers can move easily between
stories.

Send your proposal with:
• Chapter title and owner
• Problem and audience
• What the agent does and what the human still decides
• Tools and approved access scope
• Demonstration or supporting evidence
• Three takeaways and one discussion question
• Previous and next chapter suggestions

Use generic organisation names and redacted screenshots. Do not include
employer names, email addresses, secrets, internal endpoints or private
ticket/customer data.
```

**Author checklist**

1. Agree the story outline before producing the full chapter.
2. Upload the reviewed MP4 to Journey Videos; complete its metadata.
3. Create a draft from the template. Replace the title, text, player and any copied chapter links; check that it no longer plays the old video.
4. Add a reviewed text alternative and captions where available.
5. Ask a chapter owner to review facts, privacy, sound, links and access.
6. Publish after that review. This is a manual editorial step unless your site owner has configured a formal approval workflow.
7. Add it to the index and update the neighbouring pages' Previous/Next links. Check those pages again after republishing.
8. Keep an owner and review date so the chapter can be maintained.

## 9. Verify before sending the collection link

- [ ] An intended reader opens the published index and all five chapter pages.
- [ ] That reader plays each MP4 and can hear the narration.
- [ ] An excluded colleague, using a genuinely different account, cannot open the index, chapter page or **direct MP4 URL**. A private browser window using the same account is not an excluded-user test.
- [ ] The owner checks site, page and library permissions plus existing file sharing links. A restrictive new link does not remove earlier access. [Microsoft: manage access](https://support.microsoft.com/en-us/onedrive/sharepoint/manage-sharing-and-permissions-in-onedrive-and-sharepoint)
- [ ] No Anyone or organisation-wide video links were created during player setup.
- [ ] Previous / All chapters / Next links work in both directions.
- [ ] Selected authors can add a draft; ordinary readers cannot edit approved pages or files.
- [ ] Comments or the linked discussion route work for the intended readers.
- [ ] All placeholder URLs, sensitive screenshots and employer-identifying text are removed.

Hiding a link, targeting an audience or choosing a navigation label does not secure a file. [Microsoft: audience targeting is not a security measure](https://learn.microsoft.com/en-us/SharePoint/homesites/use-audience-targeting-sharepoint-app-in-teams)

Site permissions restrict ordinary users, not authorised tenant administration/compliance functions. Read access may also permit downloading or recording; do not promise that an allowed viewer cannot redistribute a copy. Ask the owner about approved controls if that matters.

## 10. Troubleshooting your first upload

| What you see | What to do |
|---|---|
| No New / Edit / Upload action | Ask the site owner to check your role. Do not change to a broadly shared site. |
| Page works but video says Access denied | Have the owner check the video's actual library/file access for the reader. Do not create a broad link to fix it. |
| A newly uploaded video does not play yet | Check the upload completed, reopen the file, and allow any service processing to finish. Escalate persistent errors with the filename and error text. |
| Email attachment is blocked | Use the organisation's approved file-transfer process. Do not rename the file to evade filtering. |
| A chapter link opens only for you | Check that the page is published and the intended reader has page **and** video access. |
| No comments or template option | The feature may be disabled or your role may not allow it. Ask the owner; use an approved alternative. |
| Copying this Markdown shows raw formatting | Copy only the text for each block into a Text web part, then apply headings/bullets in SharePoint. This guide is not a page-import package. |

## 11. Copy-ready launch message

Replace the bracketed link with the **published index URL** after the access checks pass.

```text
The DICE journey is now available to our selected group: [DICE journey link]

Five short chapters connect agent onboarding, identity and scoped access
to Grafana, GitLab and Kubernetes. Start at the beginning or jump straight
to the chapter relevant to your work.

Each page includes a video, key takeaways and a question for discussion.
Please add your questions and suggest the next problem or capability we
should cover. Selected authors can use the chapter template to extend
the journey.
```

Optional later: link these same chapter pages from a private Viva Engage community for richer conversation. Verify both community membership and SharePoint access before sharing; one does not automatically make the other private. You do not need Engage to launch this first collection.
