# ITIL 5 Foundation (Version 5) — Question Bank Spec (1000 questions)

**Cert:** ITIL 5 Foundation (Version 5) · PeopleCert · launched February 2026 · 40 MCQs, 60 min, pass 65% (26/40), closed-book, no prerequisites. ~70% scenario/application, ~30% knowledge recall. Tests conceptual understanding, not technical skills.

**What's new in Version 5 (must be well represented):** Digital Product & Service Management (DPSM), the Product & Service Lifecycle Model, the Service Relationship Model, the Service Journey (seven steps), the **eight-activity service value chain** (V5 adds an 8th activity to V4's six), **Responsible AI / AI governance**, tighter DevOps and PRINCE2 integration, value streams, and continuous/digital delivery.

## Output format (STRICT)
- One cert file per domain in `/home/user/workspace/qbank_gen_itil5/<domain>.jsonl`.
- One JSON object per line, no blank lines, no markdown fences.
- Keys EXACTLY: `q` (string), `options` (array of EXACTLY 4 unique strings), `answer` (int 0-3, zero-based index of correct option), `explanation` (string, 1-3 sentences, teaches the concept).
- Every stem unique. Distractors must be plausible and same-category (real ITIL terms/practices/principles — never obviously wrong filler).
- Scenario style: many stems should be short workplace scenarios ("A service desk analyst... Which guiding principle applies?"). Mix in direct definition-recall items too.
- Answer index must be spread roughly evenly across 0/1/2/3 within each file (rebalance by rotating options if needed — do NOT change option content).

## Domain weighting → 1000 total (7 syllabus areas)
1. **Key ITIL Terms & Definitions** → 150
   (service, product, value, outcome/output, cost, risk, utility & warranty, customer/user/sponsor, value co-creation, service offering, service relationships: provision/consumption/management, value streams)
2. **The Four Dimensions of Product & Service Management** → 130
   (1 Organizations & People, 2 Information & Technology, 3 Partners & Suppliers, 4 Value Streams & Processes; plus PESTLE external factors)
3. **The Seven Guiding Principles** → 160
   (Focus on value; Start where you are; Progress iteratively with feedback; Collaborate & promote visibility; Think & work holistically; Keep it simple & practical; Optimize & automate — with scenario "which principle applies" items)
4. **The Service Value System (SVS)** → 150
   (SVS components: guiding principles, governance, service value chain, practices, continual improvement; inputs=opportunity/demand, output=value; the four dimensions surrounding the SVS)
5. **The Service Value Chain (eight activities, V5)** → 130
   (Plan, Improve, Engage, Design & Transition, Obtain/Build, Deliver & Support — plus the V5 additions/emphasis; value streams as combinations of value-chain activities)
6. **ITIL Management Practices** → 180
   (General mgmt: Continual Improvement, Information Security Mgmt, Relationship Mgmt, Supplier Mgmt; Service mgmt: Incident Mgmt, Problem Mgmt, Change Enablement, Service Request Mgmt, Service Desk, Service Level Mgmt, Service Configuration Mgmt, IT Asset Mgmt, Monitoring & Event Mgmt, Release Mgmt, Deployment Mgmt; Technical: Deployment Mgmt. Definitions, purpose, key activities, and when each applies)
7. **V5 New Concepts: DPSM, Lifecycle, Service Journey & Responsible AI** → 100
   (Digital Product & Service Management model; Product & Service Lifecycle Model idea→product→service; Service Relationship Model; the seven-step Service Journey: Explore, Engage, Offer, Agree, Onboard, Co-create, Realize; Responsible AI governance & ethics; DevOps/PRINCE2 integration; digital products vs digital services)

## Quality bar
- Foundation level: no deep technical/tooling questions — this is a framework/concept exam.
- Guiding-principle scenario items: give a short situation, ask which principle BEST applies; distractors are the other principles.
- Practice items: test purpose and correct practice name for a scenario (e.g. "restore normal service asap" = Incident Management).
- Keep terminology current to V5 (say "eight-activity value chain", "DPSM", "Responsible AI").
- No web search needed — rely on ITIL knowledge; verify counts and schema with a validation script before finishing.
