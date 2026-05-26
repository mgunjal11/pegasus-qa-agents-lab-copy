---
name: jira-msc-bug
description: >-
  Files Jira Bug issues in the MSC (Media Supply Chain) project on WBD Streaming
  Jira using Atlassian MCP. Shows a full draft (summary, description, key fields)
  and waits for explicit user approval before creating. Applies MSC QA-style
  description structure and typical field defaults. Use when the user asks to
  create or file a Jira bug, defect, MSC ticket, or wants an issue created in
  project MSC on wbdstreaming.atlassian.net.
---

# Jira MSC bug filing

## Preconditions

- Atlassian MCP is enabled and authenticated (user can access `wbdstreaming.atlassian.net`).
- Prefer MCP tools over guessing: resolve **cloud/site id**, **required fields**, and **valid option payloads** before creating an issue.

## Defaults (confirm or override with the user)

| Item | Default |
|------|---------|
| Site | `wbdstreaming.atlassian.net` |
| Project key | `MSC` |
| Issue type | `Bug` |
| Reporter | Current user (via Jira; do not impersonate) |

**Do not assume** without asking: **parent issue**, **Epic Link**, **Fix version / Affects version**, **Sprint**, **assignee**, **target dates**. These change per ticket and sprint.

## Workflow

1. **Clarify** one-line intent: product area, environment, and whether this is production, INT, staging, or QA.
2. **Search for duplicates** using JQL (summary keywords, error string, component/feature area). Suggest linking or commenting on an existing issue if it matches.
3. **Resolve cloud context** using Atlassian MCP (e.g. accessible resources / visible projects) so `cloudId` is correct.
4. **Fetch create metadata** for `MSC` + `Bug` (required fields, allowed values). Map any defaults below to the API shape Jira expects (`additional_fields` / custom field ids). Option ids in this skill are **hints** from a sample issue; **re-validate** if creation fails.
5. **Draft** summary + description from the template below. Use clear, quotable error text in the summary when applicable.
6. **Redact** secrets, tokens, internal URLs with credentials, and personal data. Use placeholders if needed.
7. **Show the user a complete draft before creating.** Do **not** call the Jira create API until the user has reviewed and approved. The draft must include at minimum:
   - **Summary** (final title line)
   - **Description** (full body as it will appear in Jira, using the template sections)
   - **Field plan**: issue type, project key, and every non-default field you intend to set (priority, fix/affects version, parent, epic, sprint, assignee, and each planned `additional_fields` / custom field with human-readable value names)
   - **Duplicate check**: note any similar existing issues found, or state that none were found
8. **Wait for explicit approval.** The user must confirm (e.g. “create it”, “yes”, “approved”, “go ahead”) or request edits. If they ask for changes, update the draft and show it again; repeat until approved.
9. **Create** the issue via MCP only after step 8. Return the **issue key** and **browse URL** to the user.

**Exception:** If the user already approved a draft **in the same conversation** and only asked for a trivial fix (e.g. one typo), you may show a short “updated draft” diff then create after they confirm the fix—still no create without a clear go-ahead.

## Description template (markdown)

Use these headings in the issue body (order preserved):

```markdown
## Summary
[Short narrative: what fails and under what circumstances]

## Steps to Reproduce
1.
2.
3.

## Expected Behavior


## Actual Behavior


## Impact
-

## Environment
- Environment name (e.g. QA / Staging / Prod):
- Relevant services, pipelines, or step functions (if any):
- Code pointers (file/function) if known:
```

For intermittent failures, explicitly state **non-deterministic / flaky** behavior and whether **retry** changes the outcome.

## Typical MSC QA field defaults (when metadata allows)

Apply only when the create screen lists these fields and values are still valid. If unsure, omit and let the user set in Jira UI, or ask.

| Field (display name) | Typical value | Custom field id (hint) |
|----------------------|---------------|-------------------------|
| Client Platforms | Other | `customfield_10053` |
| CoE Status | New | `customfield_15313` |
| Environments | Staging (or match user env) | `customfield_11743` |
| Event Stream | No | `customfield_10136` |
| Feature Area | MSC General Media Supply Chain | `customfield_10054` |
| Group | MSC AdStellar | `customfield_10111` |
| Org | GT COMPASS | `customfield_10116` |
| Pillars | Media Supply Chain | `customfield_10172` |
| Priority Approval | Not Applicable | `customfield_12336` |
| Products | N/A | `customfield_10112` |
| Projects | MSC | `customfield_10132` |
| Regions | NORTH AMERICA | `customfield_10110` |
| Regression | No | `customfield_10138` |
| Reporter Group | MSC QA | `customfield_12237` |
| ScriptRunner Actions | Select Automation to Run | `customfield_10125` |
| Severity | Sev-3 | `customfield_10090` |
| Team / Team Name | MSC AdStellar | `customfield_10001`, `customfield_10155` |
| Test Execution Type | Manual | `customfield_10137` |
| Test Type | E2E Testing (when applicable) | `customfield_10146` |
| Work Driver | Product | `customfield_15725` |
| XLT/SLT Approval | Not Applicable | `customfield_12445` |

**Epic Link** (`customfield_10014`), **Sprint** (`customfield_10020`), **Global Sprints** / **Target Sprint End** labels, and **version** fields: set only from explicit user input or team sprint context.

## Summary line style

- Prefer: `[Component or flow] fails with 'Exact error' when [condition]`
- Keep under ~120 characters when possible; no trailing period required.

## After creation

- If the user asked to relate work: add a **comment** linking the user story or related ticket (see style in historical MSC bugs).
- Do not transition or close issues unless the user explicitly asks.
