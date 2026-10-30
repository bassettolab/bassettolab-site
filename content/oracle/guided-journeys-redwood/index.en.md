---
title: "Oracle Cloud Redwood: Guided Journeys and AI-powered agents"
description: "Practical configuration guide for informational Guided Journeys and AI Agent tasks in Redwood Self Service Procurement."
date: 2026-10-28
categories: ["TI", "Oracle", "Cloud"]
tags: ["Oracle Fusion Cloud", "Redwood", "Guided Journeys", "Procurement", "AI Agent Studio", "Visual Builder Studio"]
draft: false
featured: true
type: post
toc: true
---

## Two Guided Journey scenarios

A **Guided Journey** delivers contextual assistance within an Oracle Fusion Cloud Redwood page. The scenarios below are uses of the same feature, rather than separate products.

| Scenario | Purpose | Supported content |
| --- | --- | --- |
| Informational journey | Guide users during a business activity | Documents, BI Publisher reports, OTBI analyses, videos and external URLs |
| AI-agent journey | Provide interactive help in the current page | Agent task connected to an agent published in AI Agent Studio |

This guide uses the Redwood **Self Service Procurement / Purchase Requisitions** homepage as its example. Other Procurement and SCM pages can use this approach **only where a corresponding Guided Journey page or section property is supported**. Journeys do not bypass user permissions.

## Where to use them

- **Self Service Procurement:** requisition instructions, policy documents, reports on pending approvals and training videos.
- **Purchasing and Procurement:** contextual policies and operational instructions on compatible pages.
- **SCM:** guidance on compatible Redwood pages in Inventory, Order Management and related areas.
- **AI in Procurement:** questions about requisition status, pending approvers and approval queues, provided the agent has appropriate tools and access rights.

## Flow 1 — Informational Guided Journey

```text
My Routines > Journeys Setup > Guided Journey
                    |
            Create > Name + Code
                    |
              Create Draft
                    |
           Add Tasks (1..N)
                    |
 Document / Report / Analytics / Video / External URL
                    |
        Save > Preview > Translate
                    |
           Copy Journey Code
                    |
 Redwood > Edit Page in Visual Builder Studio
                    |
       Page Properties > Journey Code
                    |
             Preview > Publish
```

### 1. Create the journey

1. Navigate to **My Routines > Journeys Setup > Guided Journey**.
2. Select **Create**, enter a **Name** and **Code**, and select **Create Draft**.
3. In **Tasks**, select **Add** for each activity.
4. A generic example is `Requisition Guide` with code `REQUISITION_GUIDE`.

For SCM and Procurement implementations, the Oracle documentation also describes **Setup and Maintenance > Application Extensions > Guided Journeys**, within an applicable offering.

### 2. Configure task types

- **Document:** select `Task Type = Document`; enter instructions and attach a PDF. Use **Translation Editor** to localize available text.
- **Report:** select `Task Type = Report` and point to an authorized BI Publisher report, such as `/Custom/Procurement/SAMPLE_REPORT.xdo`.
- **Analytics:** select `Task Type = Analytics`, `Type of Analysis = OTBI Analysis`, and an authorized shared-catalog path, such as `/shared/Custom/Procurement/SAMPLE_ANALYSIS`.
- **Video:** select `Task Type = Video`, `Video Type = Embedded URL`, and a supported embed URL.
- **External URL:** add a reference webpage, such as the [Oracle Procurement 26C videos](https://docs.oracle.com/en/cloud/saas/procurement/26c/videos.html).

The report and analysis paths above are illustrative, not actual deployed resources. Preview each task and verify permissions for the intended audience.

### 3. Associate it with the Redwood page

1. Copy the journey **Code** and open the Redwood Self Service Procurement homepage.
2. Under **Settings and Actions**, select **Edit Page in Visual Builder Studio**.
3. In **Express mode > Page Properties**, locate the supported homepage **Guided Journey Code** property and enter the code.
4. Validate with **Preview** and deploy with **Publish**.

Properties may be named `journeyCode` at page level or `sectionNameJourneyCode` for a section. **Do not create a fictitious property** when the target page does not expose this feature.

## Flow 2 — Guided Journey with an AI agent

```text
Configure AI Agent Studio security and roles
                    |
  AI Agent Studio > Marketplace > Copy Template
                    |
     Customize / Test / Publish Agent
                    |
   Enable Agent tasks in Guided Journeys
                    |
     Guided Journey > Task Type = Agent
                    |
        Select published agent
                    |
       Save > Activate > Preview
                    |
  Redwood > Visual Builder Studio > Journey Code
                    |
             Preview > Publish
```

### 1. Security and prerequisites

In **Setup and Maintenance > Manage Administrator Profile Values**, the documented example uses:

```text
ORA_ASE_SAS_INTEGRATION_ENABLED = Yes (Site)
```

Next, run these processes in **Tools > Scheduled Processes**, in this order:

1. `Import Resource Application Security Data`
2. `Import User and Role Application Security Data`

Grant administrative privileges only to authorized administrators. The example includes the following duties; confirm which are available and required for your release:

| Assignment area | Duty / privilege |
| --- | --- |
| Roles and Privileges | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY` |
| Roles and Privileges — documented variant | `ORA_PO_PRC_AI_AGENT_MANAGEMENT_DUTY_HCM` |
| Roles and Permission Groups | `ORA_DR_FAI_GENERATIVE_AI_AGENT_PRC_ADMINISTRATOR_DUTY` |

A documented end-user chat configuration also refers to `ORA_HCM_VBCS_PWA_ENABLED = Y`, the `HRC_ACCESS_AI_AGENT_CHAT_PRIV` privilege and the `ORA_DR_FAI_GENERATIVE_AI_AGENT_RUNTIME_DUTY` duty. These are examples, **not a universal security matrix**. Apply least privilege and validate with a non-administrative user.

### 2. Create and publish the agent

1. Open **AI Agent Studio > Marketplace**.
2. Find **Purchase Requisition Status Advisor** and select **Copy Template**.
3. Customize starter prompts, data tools and permissions, then test.
4. Select **Publish** for the agent.

Example prompts (all identifiers are fictional):

```text
What is the status of purchase requisition SAMPLE_REQ?
Who is the pending approver for SAMPLE_REQ?
How many requisitions are pending approval under my account?
```

The response depends on configured tools, available records and the user's permissions.

### 3. Enable and add the Agent task

A documented prerequisite in **Manage Administrator Profile Values** is:

```text
ORA_PER_AGENT_TASK_TYPE_GUIDED_JOURNEYS_ENABLED = Y
```

Create a Guided Journey, add a **Task Type = Agent** task, select the published agent, and **Save > Activate**. Test with **Preview**.

### 4. Publish in Redwood

As with the informational journey, paste the journey **Code** into the supported property under **Edit Page in Visual Builder Studio > Page Properties**, validate and **Publish**.

### 5. Optional chat shortcut

Some implementation examples describe an alternate chat navigation shortcut through a **Structure** sandbox and **Create Page Entry**. The following values are environment-dependent and require security and release validation:

```text
Name: AI Chat
Group: Shortcuts
Link Type: VB Studio Page
Focus View ID: /index.html
Web Application: ORA_FSCM_UI
Secured Resource Name: /vbcs/hcm/hcmAgentChat/access
Application Stripe: hcm
```

This shortcut is an alternative navigation mechanism, not a separate Guided Journey. Do not deploy it without validating the HCM-related route and access policies in the SCM/Procurement context.

## Important considerations

- **Two publication layers:** activating a Journey does not publish the Redwood page extension.
- **Page compatibility:** a Journey can only be attached where the corresponding page or section property exists.
- **Security:** report, document, external URL and agent permissions still apply.
- **Release differences:** settings, roles and UI labels can vary. Validate all steps in a test environment first.

## Official Oracle references

- [Guided Journeys in Fusion SCM and Procurement](https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26b/faicf/guided-journeys.html)
- [Redwood SCM AI Agents and Guided Journeys](https://docs.oracle.com/en/cloud/saas/readiness/scm/25a/plm25a/25A-plm-wn-f36914.htm)
- [Extending Redwood Applications Using Visual Builder Studio](https://docs.oracle.com/cd/G55130_01/trans/G34703-05/extending-redwood-applications-for-hcm-and-scm-using-visual-builder-studio.pdf)
- [Redwood Adoption for SCM and Procurement](https://docs.oracle.com/en/cloud/saas/readiness/redwood-adoption/raoac/rw-scm.html)

The sample catalog paths, role names, journey codes and requisition identifiers are generic. Replace them only with authorized values for your environment.
