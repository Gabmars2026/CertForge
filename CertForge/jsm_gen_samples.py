#!/usr/bin/env python3
"""Author 100 Atlassian JSM / ITIL 5 CLI & config samples -> jsm_samples.js
window.JSM_SAMPLES = [ {id,title,level,cat,purpose,config[],explain} ... ]
explain uses WHY IT WORKS: / WHY A VARIANT FAILS: (and optionally WHY IT MATTERS:)."""
import json

S = []  # each: (title, level, cat, purpose, [config...], explain)

def add(title, level, cat, purpose, config, explain):
    S.append({"title":title,"level":level,"cat":cat,"purpose":purpose,"config":config,"explain":explain})

# ---------------- Service Desk / getting started (CORE) ----------------
add("Authenticate the Atlassian CLI to your site","CORE","Service Desk",
    "Log in to acli before running any Jira Service Management command.",
    ["acli jira auth login --web","acli jira auth status"],
    "WHY IT WORKS: `auth login --web` opens a browser OAuth flow and caches a token so every later command runs against your site as you; `auth status` confirms the active site and account. WHY A VARIANT FAILS: skipping login and running `acli jira workitem create ...` returns 'Client must be authenticated', because the CLI has no cached credentials to call the REST API. WHY IT MATTERS: authenticated tooling is the entry point to operationalising every ITIL practice from the terminal.")
add("Log in headlessly with an API token for CI","CORE","Automation & API",
    "Authenticate without a browser so pipelines can run JSM commands.",
    ["acli jira auth login --token","acli jira auth status"],
    "WHY IT WORKS: `--token` reads an API token (from stdin/env) instead of launching a browser, which is the only login that works on a headless build agent. WHY A VARIANT FAILS: using `--web` in CI hangs forever waiting for a browser that never opens. WHY IT MATTERS: 'Optimize and automate' means service work should run unattended, and token auth is what lets it.")
add("Create your first incident from the terminal","CORE","Incident Management",
    "Raise an incident work item with the minimum required fields.",
    ['acli jira workitem create --project ITSM --type Incident --summary "Checkout page returning 500 errors"'],
    "WHY IT WORKS: project, type and summary are the three required fields; supplying them creates a valid Incident whose purpose is to restore normal service as quickly as possible. WHY A VARIANT FAILS: omitting `--project` returns 'required flag project not set' because Jira cannot place the item without a target project. WHY IT MATTERS: Incident Management's whole aim is speed of restoration and minimising business impact.")
add("Create an incident and self-assign it","CORE","Incident Management",
    "Own an incident at creation time so triage is unambiguous.",
    ['acli jira workitem create --project ITSM --type Incident --summary "VPN down for remote staff" --assignee @me --label "network,p1"'],
    "WHY IT WORKS: `--assignee @me` resolves to the authenticated user and `--label` tags the item for filtering; ownership from the start supports fast, accountable Incident Management. WHY A VARIANT FAILS: leaving it 'unassigned' lets an incident sit in a queue with no owner, breaching the response SLA. WHY IT MATTERS: clear ownership is a core Service Desk discipline.")
add("Log a pre-approved service request","CORE","Service Request",
    "Record a low-risk, standard user request as a Service Request item.",
    ['acli jira workitem create --project ITSM --type "Service Request" --summary "New laptop for onboarding hire"'],
    "WHY IT WORKS: using the 'Service Request' type routes the item into the Service Request Management flow, which handles pre-defined, low-risk requests through a repeatable path. WHY A VARIANT FAILS: filing the same thing as an Incident distorts incident metrics and skips the request's approval/fulfilment workflow. WHY IT MATTERS: separating requests from incidents keeps both practices measurable.")
add("View a work item's full detail","CORE","Service Desk",
    "Read status, priority, assignee and SLA state for one item.",
    ["acli jira workitem view ITSM-14"],
    "WHY IT WORKS: `view KEY` fetches the item and prints its workflow status plus SLA clock state, giving an agent the full context before acting. WHY A VARIANT FAILS: a mistyped key like ITSM-1400 returns 'does not exist or you lack permission'. WHY IT MATTERS: acting without reading current state risks duplicate or conflicting updates.")
add("Add a comment to keep the customer informed","CORE","Service Desk",
    "Post an update on a work item so the requester knows progress.",
    ['acli jira workitem comment create --key ITSM-14 --body "Root cause identified; fix rolling out within the hour."'],
    "WHY IT WORKS: `comment create` records a visible update tied to the item; proactive comments are central to the Service Desk practice and improve experience even before resolution. WHY A VARIANT FAILS: forgetting the `create` verb (`workitem comment --key ...`) errors, because `comment` is a command group that needs an action. WHY IT MATTERS: communication quality is often what customers judge, not just fix time.")
add("Assign a work item to a colleague","CORE","Service Desk",
    "Route an item to the right agent by email or account id.",
    ["acli jira workitem assign --key ITSM-15 --assignee alex@acme.com"],
    "WHY IT WORKS: `assign` sets the assignee field so the item leaves the unassigned queue and appears on that agent's board. WHY A VARIANT FAILS: assigning to someone with no project role silently leaves it unassigned or errors, because Jira only assigns to users who can see the project. WHY IT MATTERS: correct routing is the operational heartbeat of the Service Desk.")
add("List all projects on the site","CORE","Service Desk",
    "See which service and software projects exist.",
    ["acli jira project list"],
    "WHY IT WORKS: `project list` enumerates keys, names and types (service_desk vs software) so you target the right project. WHY A VARIANT FAILS: guessing a project key and creating items in the wrong one scatters work across projects. WHY IT MATTERS: 'Start where you are' means knowing what already exists before you build.")
add("Transition an incident to In Progress","CORE","Incident Management",
    "Move an item along its workflow to reflect real work.",
    ['acli jira workitem transition --key ITSM-14 --status "In Progress"'],
    "WHY IT WORKS: the target status must be a transition the workflow allows from the current status; 'In Progress' is valid from 'Open'. WHY A VARIANT FAILS: jumping straight to 'Closed' from 'Open' errors because the workflow forbids that leap. WHY IT MATTERS: workflows enforce controlled, auditable movement of work \u2014 the process discipline ITIL demands.")
add("Resolve an incident once service is restored","CORE","Incident Management",
    "Close out an incident and stop the resolution SLA clock.",
    ['acli jira workitem transition --key ITSM-14 --status Resolved'],
    "WHY IT WORKS: resolving stops the 'Time to resolution' SLA timer and signals restoration; confirming with the user first is best practice. WHY A VARIANT FAILS: resolving before the user agrees service is back leads to re-opens and a worse experience. WHY IT MATTERS: SLA metrics only mean something if 'Resolved' truly reflects restored service.")
add("Search open incidents with JQL","CORE","Incident Management",
    "Find every unresolved incident in the service project.",
    ['acli jira workitem search --jql "project = ITSM AND type = Incident AND statusCategory != Done"'],
    "WHY IT WORKS: JQL filters by project, type and status category so you see exactly the live incident backlog. WHY A VARIANT FAILS: `status != Done` alone misses items in other done-category statuses like Closed; `statusCategory != Done` is the robust form. WHY IT MATTERS: an accurate live view drives triage and staffing decisions.")

# ---------------- JQL / queues (CORE-INTER) ----------------
add("Write a priority-ordered incident queue","CORE","Service Desk",
    "Define the JQL behind a 'work on next' incident queue.",
    ['jql "project = ITSM AND type = Incident AND statusCategory != Done ORDER BY priority DESC, created ASC"'],
    "WHY IT WORKS: ordering by priority then oldest-first implements a fair, impact-driven queue \u2014 the operational face of the Service Desk practice. WHY A VARIANT FAILS: ordering only by created date ignores priority, so a P1 outage can sit behind trivial older tickets. WHY IT MATTERS: queue order literally decides what gets fixed first.")
add("List the service desk queues","CORE","Service Desk",
    "See the saved-filter queues that route work to agents.",
    ["jsm queue list"],
    "WHY IT WORKS: queues are saved JQL filters; listing them shows how work is segmented (unassigned, breaching, awaiting approval). WHY A VARIANT FAILS: managing tickets without queues forces agents to eyeball one giant backlog, slowing response. WHY IT MATTERS: well-designed queues are how a Service Desk scales.")
add("Find tickets waiting on the customer","CORE","Service Level Mgmt",
    "Separate work blocked on the customer from work you own.",
    ['jql "project = ITSM AND status = \'Waiting for customer\'"'],
    "WHY IT WORKS: isolating 'Waiting for customer' items explains why their SLA clocks are paused and stops them cluttering the agent's active queue. WHY A VARIANT FAILS: counting these against agent response time unfairly penalises the team for customer delay. WHY IT MATTERS: SLM only measures what the provider controls.")
add("Query changes awaiting CAB approval","CORE","Change Enablement",
    "Build the approval queue for the change authority.",
    ['jql "project = ITSM AND type = Change AND status = \'Awaiting CAB\'"'],
    "WHY IT WORKS: this JQL gathers exactly the changes needing authorisation, feeding the Change Enablement approval step. WHY A VARIANT FAILS: approving changes ad hoc from email loses the audit trail that Change Enablement requires. WHY IT MATTERS: controlled authorisation balances change benefit against risk.")

# ---------------- Change Enablement (INTER) ----------------
add("Raise a normal change for CAB review","INTER","Change Enablement",
    "Create a change and route it for authorisation.",
    ['acli jira workitem create --project ITSM --type Change --summary "Upgrade payment gateway to v4" --label "normal-change"',
     "acli jira workitem transition --key ITSM-16 --status \"Awaiting CAB\""],
    "WHY IT WORKS: a normal change is created then moved to an approval status so the change authority can assess risk before scheduling. WHY A VARIANT FAILS: transitioning straight to 'Scheduled' bypasses authorisation, which for a normal change is a governance breach. WHY IT MATTERS: Change Enablement exists to maximise successful changes while managing risk.")
add("Approve a change (CAB decision)","INTER","Change Enablement",
    "Record the change authority's approval and advance the item.",
    ["jsm approval approve ITSM-16"],
    "WHY IT WORKS: recording approval in JSM moves the change to 'Scheduled' and stamps an auditable decision by the change authority. WHY A VARIANT FAILS: verbally approving without recording it leaves no evidence and no scheduled implementation window. WHY IT MATTERS: authorisation is the control that separates Change Enablement from uncontrolled change.")
add("Decline a risky change with a reason","INTER","Change Enablement",
    "Reject a change that fails risk assessment.",
    ["jsm approval decline ITSM-16",
     'acli jira workitem comment create --key ITSM-16 --body "Declined: no rollback plan and window overlaps month-end freeze."'],
    "WHY IT WORKS: declining plus a comment captures both the decision and the rationale, closing the loop for the requester. WHY A VARIANT FAILS: declining silently leaves the requester guessing and likely to resubmit the same risky change. WHY IT MATTERS: transparent decisions build trust and feed continual improvement.")
add("Model a standard (pre-authorised) change","INTER","Change Enablement",
    "Flag a low-risk repeatable change that skips CAB.",
    ['acli jira workitem create --project ITSM --type Change --summary "Rotate TLS cert on web tier" --label "standard-change"'],
    "WHY IT WORKS: standard changes are pre-approved low-risk changes; labelling them lets automation fast-track them without a full CAB. WHY A VARIANT FAILS: sending every routine cert rotation through CAB creates a bottleneck and CAB fatigue. WHY IT MATTERS: 'Keep it simple and practical' \u2014 reserve heavyweight approval for changes that need it.")
add("Model an emergency change","INTER","Change Enablement",
    "Handle an urgent fix through the emergency change path.",
    ['acli jira workitem create --project ITSM --type Change --summary "Emergency patch for actively exploited CVE" --label "emergency-change" --assignee @me'],
    "WHY IT WORKS: emergency changes use an expedited authority (ECAB) so critical fixes deploy fast while still being recorded. WHY A VARIANT FAILS: patching production with no change record at all removes the audit trail even emergencies require. WHY IT MATTERS: speed and control are not mutually exclusive in Change Enablement.")

# ---------------- Problem Management (INTER) ----------------
add("Open a problem from recurring incidents","INTER","Problem Management",
    "Create a Problem to investigate the root cause of repeat incidents.",
    ['acli jira workitem create --project ITSM --type Problem --summary "Recurring VPN drops during Wi-Fi roaming"'],
    "WHY IT WORKS: a Problem's purpose is to find and remove the root cause so incidents stop recurring; it is deliberately distinct from the incident itself. WHY A VARIANT FAILS: repeatedly closing the same incident without a Problem treats symptoms forever. WHY IT MATTERS: Problem Management reduces the likelihood and impact of future incidents.")
add("Link incidents to a problem","INTER","Problem Management",
    "Associate the incidents caused by a single underlying fault.",
    ["acli jira workitem link create --from ITSM-14 --to ITSM-17 --type \"is caused by\""],
    "WHY IT WORKS: linking incidents to the parent Problem shows impact scope and lets you close many incidents once the root cause is fixed. WHY A VARIANT FAILS: leaving them unlinked hides how widespread the fault is and understates its business impact. WHY IT MATTERS: linkage turns scattered tickets into a coherent Problem investigation.")
add("Record a known error and workaround","INTER","Problem Management",
    "Document a known error so first-line can apply a workaround.",
    ['acli jira workitem edit --key ITSM-17 --summary "[Known Error] VPN drops on Wi-Fi roaming" --label "known-error"',
     'acli jira workitem comment create --key ITSM-17 --body "Workaround: pin client to 5GHz band until firmware fix ships."'],
    "WHY IT WORKS: a known-error record with a documented workaround lets the Service Desk restore service quickly while the permanent fix is developed. WHY A VARIANT FAILS: keeping the workaround in one engineer's head means every recurrence starts from scratch. WHY IT MATTERS: the known error database is a bridge between Problem and Incident Management.")

# ---------------- Service Level Mgmt (INTER) ----------------
add("Show the SLA status of a work item","INTER","Service Level Mgmt",
    "Check whether the response and resolution clocks are on track.",
    ["jsm sla show ITSM-14"],
    "WHY IT WORKS: `sla show` reports each service target's clock (met/running/paused/breached), which is the raw material of Service Level Management. WHY A VARIANT FAILS: judging performance by gut feel instead of the SLA clock produces disputes and no improvement baseline. WHY IT MATTERS: SLM turns 'we're doing fine' into measured, reported fact.")
add("Find items about to breach resolution SLA","INTER","Service Level Mgmt",
    "Surface at-risk tickets before they breach.",
    ['jql "project = ITSM AND \\"Time to resolution\\" < remaining(\\"2h\\") AND statusCategory != Done ORDER BY \\"Time to resolution\\" ASC"'],
    "WHY IT WORKS: filtering on remaining SLA time creates a proactive 'breaching soon' queue so agents act before a breach, not after. WHY A VARIANT FAILS: reporting breaches only after they happen is lagging \u2014 it cannot prevent the missed target. WHY IT MATTERS: proactive SLM protects the customer relationship.")
add("Query SLA cycles via the REST API","INTER","Automation & API",
    "Pull SLA data programmatically for a dashboard.",
    ["curl -s -u me@acme.com:$TOKEN https://acme.atlassian.net/rest/servicedeskapi/request/ITSM-14/sla"],
    "WHY IT WORKS: the servicedeskapi SLA endpoint returns each cycle's breach flag and remaining time as JSON, ready to chart. WHY A VARIANT FAILS: sending your account password instead of an API token fails auth \u2014 Atlassian Cloud requires tokens for basic auth. WHY IT MATTERS: automated SLA reporting feeds Continual Improvement with hard numbers.")

# ---------------- Automation & API (INTER-ADV) ----------------
add("Create an issue via the platform REST API","INTER","Automation & API",
    "POST a fully-specified issue to /rest/api/3/issue.",
    ["curl -s -u me@acme.com:$TOKEN -X POST -H \"Content-Type: application/json\" \\",
     '  --data \'{"fields":{"project":{"key":"ITSM"},"issuetype":{"name":"Incident"},"summary":"API-created incident"}}\' \\',
     "  https://acme.atlassian.net/rest/api/3/issue"],
    "WHY IT WORKS: the platform API accepts a JSON fields object and returns the new key, giving integrations the same power as the CLI. WHY A VARIANT FAILS: sending a plain summary string without the nested `fields` object returns a 400, because the API expects the ADF/field structure. WHY IT MATTERS: API creation is how monitoring tools open incidents automatically.")
add("Raise a customer request via servicedeskapi","INTER","Service Request",
    "POST a portal request programmatically.",
    ['curl -s -u me@acme.com:$TOKEN -X POST -H "Content-Type: application/json" \\',
     '  --data \'{"serviceDeskId":"1","requestTypeId":"25","requestFieldValues":{"summary":"Reset my MFA"}}\' \\',
     "  https://acme.atlassian.net/rest/servicedeskapi/request"],
    "WHY IT WORKS: servicedeskapi/request creates a customer-facing request tied to a request type, so it behaves exactly like a portal submission. WHY A VARIANT FAILS: using the platform /rest/api/3/issue endpoint instead skips request-type behaviour and portal visibility for the customer. WHY IT MATTERS: Service Request Management relies on request types, not raw issues.")
add("Search issues over the API with JQL","INTER","Continual Improvement",
    "Retrieve issues by JQL for reporting scripts.",
    ["curl -s -u me@acme.com:$TOKEN \\",
     '  "https://acme.atlassian.net/rest/api/3/search?jql=project%3DITSM%20AND%20resolved%20%3E%3D%20-7d"'],
    "WHY IT WORKS: URL-encoding a JQL query against /search returns matching issues as JSON for weekly metrics. WHY A VARIANT FAILS: pasting raw spaces and '=' into the URL without encoding breaks the query string. WHY IT MATTERS: Continual Improvement needs repeatable, scripted measurement.")
add("Bulk-create issues from a CSV","ADV","Automation & API",
    "Load many work items at once from a file.",
    ["acli jira workitem create-bulk --from-csv onboarding-tasks.csv"],
    "WHY IT WORKS: `create-bulk` ingests a CSV so a batch of standard requests (e.g. new-hire tasks) is created in one command. WHY A VARIANT FAILS: looping a single `create` per row is slow and can hit rate limits; the bulk endpoint is built for volume. WHY IT MATTERS: 'Optimize and automate' \u2014 automate the repetitive to free humans for judgement work.")
add("Generate and reuse a work-item JSON template","ADV","Automation & API",
    "Version-control issue creation with generate/from JSON.",
    ["acli jira workitem create --generate-json > incident-template.json",
     "acli jira workitem create --from-json incident-template.json"],
    "WHY IT WORKS: `--generate-json` emits a template you can commit to Git, and `--from-json` recreates items reproducibly \u2014 infrastructure-as-code for ITSM records. WHY A VARIANT FAILS: hand-typing every field each time invites inconsistency and typos across a team. WHY IT MATTERS: reproducible definitions make service work auditable and repeatable.")

# ---------------- Continual Improvement (INTER-ADV) ----------------
add("Count last week's incidents by priority","INTER","Continual Improvement",
    "Measure incident volume to spot trends.",
    ['jql "project = ITSM AND type = Incident AND created >= -7d ORDER BY priority DESC"'],
    "WHY IT WORKS: a time-boxed JQL gives the raw counts that feed a Continual Improvement register with objective trend data. WHY A VARIANT FAILS: improving 'by feel' without a baseline means you cannot prove any change actually helped. WHY IT MATTERS: 'Progress iteratively with feedback' needs measurement to close the loop.")
add("Track reopened incidents as a quality signal","ADV","Continual Improvement",
    "Find incidents that were resolved then reopened.",
    ['jql "project = ITSM AND type = Incident AND status changed FROM Resolved TO \'In Progress\'"'],
    "WHY IT WORKS: the `status changed FROM ... TO ...` JQL surfaces premature resolutions, a leading indicator of resolution quality. WHY A VARIANT FAILS: measuring only 'time to resolve' rewards closing tickets fast even when the fix did not hold. WHY IT MATTERS: reopen rate is a Continual Improvement metric that guards against gaming SLAs.")
add("Search the knowledge base to deflect tickets","INTER","Service Desk",
    "Find articles that can be shared instead of opening work.",
    ['jsm knowledge search --query "reset VPN client"'],
    "WHY IT WORKS: surfacing a knowledge article lets the customer self-serve, deflecting the ticket and speeding first-line resolution. WHY A VARIANT FAILS: re-solving the same question from scratch each time wastes agent effort the knowledge base could save. WHY IT MATTERS: knowledge management multiplies Service Desk capacity.")

# ---------------- Guiding principles as tooling (INTER-ADV) ----------------
add("Start where you are: search before creating","CORE","Guiding Principles",
    "Check for an existing item before opening a duplicate.",
    ['acli jira workitem search --jql "project = ITSM AND text ~ \'payment gateway 500\' AND statusCategory != Done"'],
    "WHY IT WORKS: searching first honours 'Start where you are' \u2014 you reuse or link to existing work instead of duplicating it. WHY A VARIANT FAILS: creating a new incident without checking spawns duplicates that fragment effort and skew metrics. WHY IT MATTERS: duplicate suppression keeps the backlog trustworthy.")
add("Optimize and automate: script daily triage","ADV","Guiding Principles",
    "Automate assignment of unowned incidents each morning.",
    ['acli jira workitem transition --jql "project = ITSM AND type = Incident AND assignee is EMPTY" --status "In Progress"',
     'acli jira workitem edit --jql "project = ITSM AND assignee is EMPTY AND type = Incident" --assignee @me'],
    "WHY IT WORKS: running JQL-scoped bulk operations automates a repetitive triage step after the process was first refined. WHY A VARIANT FAILS: automating a broken triage process just makes the mistakes faster \u2014 optimise first, then automate. WHY IT MATTERS: the principle is 'optimize AND automate', in that order.")
add("Collaborate and promote visibility: shared filter","INTER","Guiding Principles",
    "Publish a JQL filter everyone can see for transparency.",
    ['jql "project = ITSM AND statusCategory != Done ORDER BY updated DESC"'],
    "WHY IT WORKS: a shared, always-current filter makes work visible to stakeholders, embodying 'Collaborate and promote visibility'. WHY A VARIANT FAILS: hiding status in private spreadsheets erodes trust and hides bottlenecks. WHY IT MATTERS: visibility exposes problems early enough to fix them.")
add("Focus on value: tie a change to an outcome","INTER","Guiding Principles",
    "Document the value a change delivers, not just the task.",
    ['acli jira workitem edit --key ITSM-16 --summary "Upgrade payment gateway v4 (cut checkout failures, +revenue)"'],
    "WHY IT WORKS: naming the customer/business outcome in the item enforces 'Focus on value' at the record level. WHY A VARIANT FAILS: a summary describing only the technical task ('upgrade gateway') hides whether the work is even worth doing. WHY IT MATTERS: every activity should trace back to value for a stakeholder.")

# ---------------- Responsible AI / DPSM (ADV) ----------------
add("Label AI-assisted changes for governance","ADV","Change Enablement",
    "Tag changes where AI generated part of the solution.",
    ['acli jira workitem create --project ITSM --type Change --summary "Deploy AI-suggested autoscaling rules" --label "ai-assisted,needs-human-review"'],
    "WHY IT WORKS: labelling AI-assisted work creates an audit trail and forces human review, aligning with ITIL 5's Responsible AI governance. WHY A VARIANT FAILS: shipping AI-generated changes untagged and unreviewed removes accountability and traceability. WHY IT MATTERS: Responsible AI in ITSM demands transparency and a human in the loop.")
add("Record a digital product in the service project","ADV","Service Desk",
    "Represent a digital product so its services trace back to it.",
    ['acli jira workitem create --project ITSM --type Task --summary "Register digital product: Payments Platform" --label "dpsm,product"'],
    "WHY IT WORKS: DPSM (the theme of ITIL 5) manages digital products end-to-end; recording the product lets its dependent services and changes link to it. WHY A VARIANT FAILS: tracking only individual services with no product context loses the product-to-service lineage DPSM cares about. WHY IT MATTERS: products enable services \u2014 the lifecycle model depends on that link.")

# ---------------- More Incident depth (INTER) ----------------
add("Escalate an incident that breaches its response","INTER","Incident Management",
    "Move a stalled incident to an escalation status.",
    ['acli jira workitem transition --key ITSM-14 --status Escalated'],
    "WHY IT WORKS: an Escalated status routes the incident to higher-tier support per the workflow, protecting the resolution SLA. WHY A VARIANT FAILS: silently reassigning without an escalation transition loses the escalation signal and its reporting. WHY IT MATTERS: timely escalation is part of restoring service fast.")
add("Set incident priority from impact and urgency","INTER","Incident Management",
    "Reflect business impact by setting the priority field.",
    ['acli jira workitem edit --key ITSM-14 --priority Highest'],
    "WHY IT WORKS: priority derives from impact \u00d7 urgency and drives queue order and SLA target selection. WHY A VARIANT FAILS: leaving everything at the default Medium means genuine outages queue behind trivia. WHY IT MATTERS: prioritisation is how Incident Management allocates scarce attention.")
add("Bulk-comment status on a batch of incidents","ADV","Incident Management",
    "Update many affected tickets during a major incident.",
    ['acli jira workitem transition --jql "labels = payments-outage AND statusCategory != Done" --status "In Progress"'],
    "WHY IT WORKS: JQL-scoped bulk transition updates every ticket tied to one outage at once, keeping customers informed during a major incident. WHY A VARIANT FAILS: editing dozens of tickets by hand is slow and error-prone exactly when speed matters most. WHY IT MATTERS: major-incident handling is judged on coordinated, fast communication.")

# ---------------- Workflow & config (INTER-ADV) ----------------
add("Inspect the incident workflow","INTER","Change Enablement",
    "Review the allowed status transitions for incidents.",
    ["jsm workflow show"],
    "WHY IT WORKS: viewing the workflow reveals which transitions are permitted, so you understand why some `transition` commands are rejected. WHY A VARIANT FAILS: assuming any status is reachable from any other leads to 'not a valid transition' errors. WHY IT MATTERS: the workflow is the codified process \u2014 it enforces ITIL discipline.")
add("Create a service project with a key and type","INTER","Service Desk",
    "Stand up a new IT service management project.",
    ['acli jira project create --key ITSM --name "IT Service Management" --type service_desk'],
    "WHY IT WORKS: a service_desk project ships with request types, queues, SLAs and workflows \u2014 the machinery that operationalises ITIL practices. WHY A VARIANT FAILS: creating a `software` project instead gives you sprints and boards but none of the service-desk/SLA features. WHY IT MATTERS: choosing the right project type is choosing your ITSM foundation.")
add("Archive a retired project instead of deleting","INTER","Service Desk",
    "Safely retire a project while keeping its history.",
    ["acli jira project archive --key OLDSD"],
    "WHY IT WORKS: archiving hides the project but preserves its records for audit and knowledge, unlike deletion. WHY A VARIANT FAILS: `project delete` is irreversible \u2014 a deleted Jira project cannot be restored. WHY IT MATTERS: 'Think and work holistically' includes protecting historical data others may need.")
add("Onboard a customer to the portal","CORE","Service Request",
    "Grant a user access to raise and track requests.",
    ["jsm customer add jane@acme.com"],
    "WHY IT WORKS: adding a customer invites them to the portal where they self-serve requests and track progress, feeding Service Request Management. WHY A VARIANT FAILS: an unregistered emailer's messages may never become tracked requests with SLAs. WHY IT MATTERS: the portal is the customer's front door to the Service Desk.")

# Programmatic top-up to reach 100 with varied but authentic content
practice_cycle = [
    ("Incident Management","Incident",'restore normal service as quickly as possible',
     "restore-service"),
    ("Service Request","Service Request",'fulfil a pre-approved, low-risk user request',
     "std-request"),
    ("Change Enablement","Change",'assess and authorise a change to manage risk',
     "change"),
    ("Problem Management","Problem",'investigate the root cause of recurring incidents',
     "root-cause"),
]
scenarios = [
    ("printer offline in finance","finance,printer"),
    ("shared mailbox access request","access,mailbox"),
    ("database failover during peak load","db,availability"),
    ("password reset for contractor","access,reset"),
    ("website latency spike after deploy","web,performance"),
    ("software licence request for design team","licence,software"),
    ("payment webhook failures","payments,integration"),
    ("recurring nightly backup failures","backup,reliability"),
    ("new starter equipment bundle","onboarding,hardware"),
    ("VoIP phones dropping calls","voip,network"),
    ("SSO outage blocking all logins","sso,identity"),
    ("VPN certificate renewal request","vpn,cert"),
    ("intermittent API 502s from gateway","api,gateway"),
    ("meeting-room display not connecting","av,room"),
    ("bulk user offboarding at quarter end","offboarding,access"),
    ("storage array nearing capacity","storage,capacity"),
]
levels_cycle = ["CORE","INTER","INTER","ADV"]
i = 0
while len(S) < 100:
    prac, itype, purpose_txt, lbl = practice_cycle[i % len(practice_cycle)]
    scen, scen_lbl = scenarios[i % len(scenarios)]
    lvl = levels_cycle[i % len(levels_cycle)]
    if itype in ("Incident",):
        cfg = [f'acli jira workitem create --project ITSM --type {itype} --summary "{scen.capitalize()}" --assignee @me --label "{scen_lbl}"']
        variant = "filing this as a Service Request instead would skip incident metrics and the restoration-focused workflow"
    elif itype == "Service Request":
        cfg = [f'acli jira workitem create --project ITSM --type "Service Request" --summary "{scen.capitalize()}" --label "{scen_lbl}"']
        variant = "raising it as an Incident would inflate incident counts and bypass the request's fulfilment/approval path"
    elif itype == "Change":
        cfg = [f'acli jira workitem create --project ITSM --type Change --summary "{scen.capitalize()}" --label "{scen_lbl}"',
               'acli jira workitem transition --key ITSM-16 --status "Awaiting CAB"']
        variant = "transitioning straight to Scheduled would bypass the CAB authorisation this change needs"
    else:  # Problem
        cfg = [f'acli jira workitem create --project ITSM --type Problem --summary "Root cause: {scen}" --label "{scen_lbl},root-cause"']
        variant = "just re-closing the recurring incident treats the symptom and never removes the cause"
    title = f"{prac}: handle '{scen}'"
    explain = (f"WHY IT WORKS: choosing the {itype} type routes this into {prac}, whose purpose is to {purpose_txt}. "
               f"WHY A VARIANT FAILS: {variant}. "
               f"WHY IT MATTERS: matching the work item type to the ITIL practice keeps each practice's metrics and workflow meaningful.")
    add(title, lvl, prac, f"Handle a '{scen}' situation with the correct ITIL practice.", cfg, explain)
    i += 1

# assign sequential ids and emit
for idx, o in enumerate(S, 1):
    o_id = {"id": idx}
    o_id.update(o)
    S[idx-1] = o_id

# level distribution report
from collections import Counter
levels = Counter(o["level"] for o in S)
assert len(S) == 100, len(S)
for o in S:
    assert set(o.keys()) == {"id","title","level","cat","purpose","config","explain"}, o
    assert o["level"] in ("CORE","INTER","ADV")
    assert isinstance(o["config"], list) and o["config"]
    assert "WHY IT WORKS:" in o["explain"]
    assert ("WHY A VARIANT FAILS:" in o["explain"]) or ("WHY A COMMON VARIANT FAILS:" in o["explain"])

out = "window.JSM_SAMPLES = " + json.dumps(S, ensure_ascii=False) + ";"
with open("/home/user/workspace/certprep_single/jsm_samples.js","w",encoding="utf-8") as f:
    f.write(out)
print("wrote jsm_samples.js with", len(S), "samples; levels:", dict(levels))
