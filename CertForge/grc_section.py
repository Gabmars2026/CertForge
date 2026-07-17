#!/usr/bin/env python3
"""Append the GRC domain section to gen_secx_samples.py, replacing the trailing marker comment."""

MARKER = "# print a running count for sanity while writing (not required by spec, harmless)"

GRC_SECTION = r'''# =====================================================================
# DOMAIN: Governance, Risk & Compliance (~20) — compliance-as-code,
# vulnerability/CVE scoring, SBOM/supply-chain governance, audit evidence
# =====================================================================

add("Run an OpenSCAP compliance scan and export audit evidence", "CORE", "Governance, Risk & Compliance",
    "Produce a scored compliance report suitable for an auditor.",
    ["oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_pci-dss --results-arf results-arf.xml --report report.html ssg-rhel9-ds.xml",
     "oscap info results-arf.xml"],
    "WHY IT WORKS: the ARF (Asset Reporting Format) results file bundles the full evaluated system state, not just the pass/fail summary, so an auditor can independently verify HOW each control was checked, not just trust a headline score. WHY IT MATTERS: PCI-DSS and similar frameworks require demonstrable, repeatable evidence of control testing, not a one-time verbal assurance — an ARF/XCCDF results file with a timestamp is exactly the kind of artifact auditors expect to see attached to a control's evidence.")

add("Assess infrastructure-as-code compliance with InSpec profiles", "INTER", "Governance, Risk & Compliance",
    "Codify a compliance control as an executable test instead of a manual checklist item.",
    ["cat <<'EOF' > controls/sshd_hardening.rb\ncontrol 'sshd-01' do\n  impact 1.0\n  title 'SSH root login must be disabled'\n  describe sshd_config do\n    its('PermitRootLogin') { should cmp 'no' }\n  end\nend\nEOF",
     "inspec exec . -t ssh://admin@10.0.1.20 --reporter cli json:inspec-results.json"],
    "WHY IT WORKS: compliance-as-code expresses each control as a machine-executable test with a pass/fail result and an impact score, so the SAME profile can run against every host in the fleet on a schedule, turning point-in-time manual audits into continuous compliance monitoring. WHY A VARIANT FAILS: maintaining the InSpec profile only in a local analyst's laptop instead of a version-controlled repo means the control definition itself has no change history or peer review — the compliance-as-code approach's real value (auditable, versioned control logic) is lost if the code isn't itself governed.")

add("Calculate a CVSS 3.1 base score for a newly discovered vulnerability", "CORE", "Governance, Risk & Compliance",
    "Quantify vulnerability severity consistently for risk-based prioritization.",
    ["# Vector: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
     "curl -s \"https://www.first.org/cvss/calculator/3.1#CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H\"",
     "# resulting base score: 9.8 (Critical)"],
    "WHY IT WORKS: each CVSS metric (attack vector, complexity, privileges required, user interaction, scope, and the CIA impact triad) captures a specific dimension of exploitability and impact, and the standardized formula turns them into one comparable score usable across an entire vulnerability backlog. WHY A VARIANT FAILS: scoring a vulnerability using only the base metrics and ignoring the Temporal and Environmental metric groups (exploit code maturity, remediation level, and the asset's actual criticality) can misprioritize a technically severe but practically low-risk finding above a lower-base-score issue that is being actively exploited in the wild against your exact asset profile.")

add("Query the NVD API for a specific CVE's details", "CORE", "Governance, Risk & Compliance",
    "Pull authoritative vulnerability metadata programmatically for a risk register entry.",
    ["curl -s \"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-3094\" | jq '.vulnerabilities[0].cve.metrics.cvssMetricV31[0].cvssData'",
     "curl -s \"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-3094\" | jq -r '.vulnerabilities[0].cve.descriptions[0].value'"],
    "WHY IT WORKS: querying the NVD REST API directly pulls the authoritative, continuously-updated CVSS vector, description and reference links for a specific CVE ID, which can then be piped into a risk register or ticketing system automatically rather than manually copy-pasting from a webpage. WHY IT MATTERS: NVD analysis and even CVSS scores for a CVE can be revised after initial publication as more is learned — a risk register that only snapshots the score once at discovery time can drift from the current, more accurate assessment unless it's periodically re-queried.")

add("Generate an SBOM for supply-chain risk governance", "INTER", "Governance, Risk & Compliance",
    "Produce a standardized component inventory to satisfy a customer's supply-chain security requirement.",
    ["syft dir:. -o cyclonedx-json=sbom.cdx.json",
     "cyclonedx-cli validate --input-file sbom.cdx.json",
     "grype sbom:sbom.cdx.json --fail-on high"],
    "WHY IT WORKS: CycloneDX/SPDX are standardized, machine-readable SBOM formats increasingly REQUIRED by regulation (e.g. US Executive Order 14028 for federal software suppliers) and customer contracts, so validating the SBOM's schema and then scanning it for known vulnerabilities produces both a compliance artifact and an actionable risk finding from one pipeline step. WHY A VARIANT FAILS: generating an SBOM once at release and never regenerating it means it silently goes stale as dependencies are patched or added — SBOM generation belongs in the CI pipeline on every build, not as a one-time compliance checkbox exercise.")

add("Track third-party vendor risk with a security questionnaire and evidence request", "CORE", "Governance, Risk & Compliance",
    "Establish and document due diligence before onboarding a new SaaS vendor.",
    ["# request and file: SOC 2 Type II report, latest penetration test summary, and data flow diagram",
     "curl -s https://vendor.example.com/.well-known/security.txt",
     "# log outcome in the vendor risk register with review date and residual-risk rating"],
    "WHY IT WORKS: a SOC 2 Type II report attests to controls operating effectively over a period of time (not just designed correctly at a point in time, as a Type I report does), which is why it's the standard evidence artifact requested during vendor due diligence for anything handling sensitive data. WHY A VARIANT FAILS: accepting a vendor's self-attestation questionnaire alone with no independent evidence (SOC 2 report, pen test summary) provides no real assurance — governance requires verifiable third-party evidence, not just a vendor's own claims about their controls.")

add("Perform a business impact analysis input calculation for RTO/RPO", "INTER", "Governance, Risk & Compliance",
    "Quantify acceptable downtime and data loss to drive backup/DR architecture decisions.",
    ["# Interview finding: order-processing DB revenue impact = $50,000/hour of downtime",
     "# Backup cadence: full nightly + incremental every 4 hours",
     "# Derived RPO = 4 hours (max data loss); Derived RTO = 2 hours (per DR runbook test)",
     "aws backup describe-backup-job --backup-job-id <id>   # verify last successful backup timestamp for RPO validation"],
    "WHY IT WORKS: RTO (how fast must it come back) and RPO (how much data loss is tolerable) are business-impact-driven numbers, not IT-arbitrary ones — the BIA interview with business stakeholders is what sets the target, and the actual backup/replication architecture must then be engineered to MEET that target, not the reverse. WHY IT MATTERS: a common governance failure is setting an aggressive RPO/RTO in a policy document without validating that the actual backup infrastructure can achieve it — periodically checking the last successful backup timestamp against the stated RPO is what proves the control is actually operating, not just documented.")

add("Map security controls to a compliance framework with a crosswalk", "INTER", "Governance, Risk & Compliance",
    "Demonstrate that one technical control satisfies multiple overlapping regulatory requirements.",
    ["# Example crosswalk entry:",
     "# Control: MFA enforced on all admin accounts",
     "# Maps to: NIST 800-53 IA-2(1), PCI-DSS 8.4.2, ISO 27001 A.9.4.2, SOC2 CC6.1",
     "grep -r 'MFA' compliance/crosswalk.csv"],
    "WHY IT WORKS: many overlapping frameworks (NIST 800-53, PCI-DSS, ISO 27001, SOC 2) require conceptually similar controls phrased differently, so a maintained crosswalk lets one implemented control and one piece of evidence satisfy multiple audits simultaneously instead of re-proving the same control from scratch for each framework separately. WHY IT MATTERS: this is the practical mechanism behind 'compliance consolidation' programs — without a crosswalk, an organization subject to 4 frameworks effectively runs 4x the audit evidence-gathering work for substantially overlapping requirements.")

add("Run a CIS benchmark scan and map findings to risk register entries", "CORE", "Governance, Risk & Compliance",
    "Convert a technical hardening gap into a tracked, owned risk item.",
    ["oscap xccdf eval --profile cis --results cis-results.xml ssg-rhel9-ds.xml",
     "oscap xccdf generate report cis-results.xml > cis-report.html",
     "# for each FAIL: create risk register entry with owner, likelihood, impact, and remediation due date"],
    "WHY IT WORKS: a technical scan finding alone (e.g. 'password minlen not set to 14') has no owner or deadline attached; formally logging it in the risk register with an accountable owner and a due date converts a scan result into a governed, trackable risk item that leadership can actually manage. WHY A VARIANT FAILS: treating scan output itself as the compliance artifact (just filing the raw XML/HTML report) without tracking remediation ownership and status over time means failed controls can silently persist scan after scan with nobody accountable for closing them.")

add("Evaluate residual risk after applying a compensating control", "ADV", "Governance, Risk & Compliance",
    "Document why a control gap is acceptable given an alternate mitigation, per PCI-DSS compensating control worksheet logic.",
    ["# Gap: legacy payment terminal cannot support TLS 1.2 (PCI-DSS req 4.2.1)",
     "# Compensating control: terminal isolated on a dedicated VLAN with no internet route, monitored by IDS, compensating for the crypto gap",
     "# Document: constraint, objective met, identified risk, compensating control, validation method"],
    "WHY IT WORKS: PCI-DSS's compensating-control worksheet format requires proving the ALTERNATE control meets the intent and rigor of the original requirement, not just documenting an excuse for non-compliance — network isolation plus monitoring can legitimately substitute for a crypto control the legacy hardware cannot support. WHY A VARIANT FAILS: documenting the gap and compensating control once at initial assessment but never re-validating that the VLAN isolation and IDS monitoring are STILL in place at the next audit cycle is a common audit finding — compensating controls require the same ongoing validation as the original control would have.")

add("Automate SOC 2 evidence collection with a continuous compliance tool", "INTER", "Governance, Risk & Compliance",
    "Reduce manual screenshot-based audit evidence gathering to automated, continuous checks.",
    ["vanta-cli tests run --framework soc2",
     "vanta-cli tests list --status failing",
     "# each passing test auto-attaches timestamped API evidence to the corresponding control"],
    "WHY IT WORKS: continuous compliance platforms poll cloud/IAM/HR-system APIs directly (e.g. confirming MFA is actually enforced account-by-account) rather than relying on a human periodically taking screenshots, so evidence is fresher, harder to falsify, and updates automatically between audit cycles. WHY IT MATTERS: auditors increasingly prefer system-generated, timestamped API evidence over manually curated screenshots specifically because screenshots can be stale, cropped selectively, or from a different environment than the one being certified — automated evidence collection addresses that trust gap directly.")

add("Perform a data classification tagging pass across cloud storage", "CORE", "Governance, Risk & Compliance",
    "Identify and label sensitive data locations to drive appropriate handling controls.",
    ["aws macie2 create-classification-job --job-type ONE_TIME --s3-job-definition '{\"bucketDefinitions\":[{\"accountId\":\"111122223333\",\"buckets\":[\"app-data-prod\"]}]}' --name pii-discovery",
     "aws macie2 get-findings-statistics"],
    "WHY IT WORKS: automated data-discovery classification (Macie uses pattern/ML detection for PII, financial and credential-like data) finds sensitive data in buckets that were never explicitly documented as containing it, which is common when data accumulates over years across many teams. WHY IT MATTERS: classification is a governance PREREQUISITE for correctly applying downstream controls (encryption requirements, retention policy, access restrictions, breach-notification scope) — you cannot correctly govern data you haven't first identified and classified.")

add("Conduct a third-party penetration test scoping and rules-of-engagement review", "INTER", "Governance, Risk & Compliance",
    "Formalize authorization boundaries before any offensive testing begins.",
    ["# Rules of engagement document must specify:",
     "# - exact IP ranges/domains in scope, explicitly EXCLUDED systems",
     "# - testing window (date/time) and emergency stop contact",
     "# - authorized techniques (no DoS, no social engineering unless separately authorized)",
     "# - signed authorization letter referencing the specific scope"],
    "WHY IT WORKS: a written, signed rules-of-engagement document is the legal authorization that converts what would otherwise be unauthorized computer access (a crime under most jurisdictions' computer-fraud statutes) into sanctioned testing, and explicit exclusions/emergency-stop contacts prevent scope creep from accidentally impacting production systems or third-party-owned infrastructure. WHY A VARIANT FAILS: a verbal 'go ahead, test whatever you can reach' authorization without a signed, scoped document leaves both the tester and the organization exposed if testing causes an outage or touches a system outside intended scope — CAS-005 governance expects written, specific authorization for any offensive activity.")

add("Track patch management SLA compliance across the environment", "CORE", "Governance, Risk & Compliance",
    "Measure whether critical vulnerabilities are actually remediated within policy-defined timeframes.",
    ["nessus-cli scan export --scan-id 42 --format csv > scan_results.csv",
     "awk -F',' '$5==\"Critical\" {print $1,$2,$8}' scan_results.csv   # host, vuln, first-detected date",
     "# compare first-detected date against policy SLA (e.g. Critical = 15 days) to compute overdue count"],
    "WHY IT WORKS: a patch-management policy that states 'Critical vulnerabilities remediated within 15 days' is unenforceable without measuring TIME SINCE FIRST DETECTION against actual remediation date per finding — tracking that delta across scans is what turns a policy statement into a measured, reportable KPI for governance oversight. WHY IT MATTERS: SLA compliance percentage (not just raw vulnerability count) is the metric auditors and leadership actually care about, because raw count fluctuates with scan scope while SLA adherence directly reflects whether the remediation PROCESS itself is working.")

add("Evaluate a cloud provider's shared responsibility model for a specific service", "INTER", "Governance, Risk & Compliance",
    "Determine which party is accountable for a given control before assuming coverage.",
    ["aws artifact get-report --report-id <soc2-report-id> --output document.pdf",
     "# document which controls are 'inherited' (provider-managed) vs 'customer-managed' for the specific service tier in use (IaaS vs PaaS vs SaaS)"],
    "WHY IT WORKS: the shared responsibility boundary shifts materially between IaaS (customer patches the OS), PaaS (provider patches the OS/runtime, customer secures the app/data), and SaaS (customer largely only controls identity/data governance) — misunderstanding which model applies to a specific service leads directly to unpatched or unmonitored controls nobody actually owns. WHY A VARIANT FAILS: assuming a cloud provider's general SOC 2 report covers a specific service's customer-managed controls (like IAM policy configuration or data classification) is a common governance gap — the provider's attestation only covers what THEY manage; customer-managed controls still require the customer's own audit evidence.")

add("Automate CVE feed ingestion into a vulnerability management platform", "ADV", "Governance, Risk & Compliance",
    "Continuously enrich internal asset inventory with newly disclosed vulnerability data.",
    ["curl -s \"https://services.nvd.nist.gov/rest/json/cves/2.0?lastModStartDate=2026-07-13T00:00:00.000&lastModEndDate=2026-07-14T00:00:00.000\" | jq '.vulnerabilities[].cve.id' > new_cves.txt",
     "while read cve; do ./match_against_asset_inventory.sh \"$cve\"; done < new_cves.txt"],
    "WHY IT WORKS: polling NVD's `lastModStartDate`/`lastModEndDate` window on a schedule (rather than re-downloading the entire database) efficiently captures newly published and newly REVISED CVEs, which can then be automatically cross-referenced against a software/version asset inventory (fed by the SBOMs generated during CI) to surface exposure the moment a relevant CVE appears. WHY A VARIANT FAILS: relying on manual, periodic (e.g. monthly) review of vulnerability bulletins rather than automated near-real-time feed ingestion means an actively-exploited zero-day affecting deployed software can go unnoticed by the organization for weeks after public disclosure — automation closes that governance gap in detection lag.")

add("Document a risk acceptance decision with executive sign-off", "CORE", "Governance, Risk & Compliance",
    "Formally record a deliberate decision NOT to remediate an identified risk.",
    ["# Risk register entry fields:",
     "# risk_id: RISK-2026-0142",
     "# description: legacy ERP system cannot be patched for CVE-2025-XXXX without vendor-certified update (unavailable)",
     "# decision: ACCEPT, compensating control = network segmentation + enhanced monitoring",
     "# accepted_by: CISO, date: 2026-07-14, review_date: 2027-01-14"],
    "WHY IT WORKS: formally documenting risk acceptance with a named accountable executive and a mandatory review date converts an informal 'we'll deal with it later' into a governed decision with a paper trail — essential for demonstrating due diligence to auditors, regulators, or in the event of a future incident tied to that exact risk. WHY A VARIANT FAILS: leaving a known, unremediated risk finding open in a scan report indefinitely with no formal acceptance decision looks — to an auditor or in litigation discovery — indistinguishable from simple negligence, whereas a signed, time-bound risk acceptance demonstrates the organization consciously weighed and accepted the risk.")

add("Verify encryption-at-rest compliance evidence for a regulated data store", "INTER", "Governance, Risk & Compliance",
    "Confirm and document that a database satisfies an encryption requirement, not just assume it.",
    ["aws rds describe-db-instances --db-instance-identifier prod-orders --query 'DBInstances[0].StorageEncrypted'",
     "aws kms describe-key --key-id $(aws rds describe-db-instances --db-instance-identifier prod-orders --query 'DBInstances[0].KmsKeyId' --output text)"],
    "WHY IT WORKS: querying the actual resource configuration (not a design document or ticket claiming encryption was enabled) is what constitutes real audit evidence; confirming the specific KMS key backing the encryption also lets an auditor verify key rotation policy and access control are correctly scoped to that regulated data. WHY A VARIANT FAILS: citing the organization's general encryption POLICY document as evidence that a specific database is encrypted is insufficient for audit purposes — policy documents describe intent, while a live API query against the actual resource is what proves the control is implemented and operating for that specific asset.")

add("Conduct a tabletop exercise to validate the incident response plan", "INTER", "Governance, Risk & Compliance",
    "Test whether the documented IR plan actually works before a real incident forces it.",
    ["# Scenario injected: ransomware detected on 3 file servers at 2am Saturday",
     "# Track: time-to-detection-acknowledgement, time-to-decision-maker-notification, whether the documented escalation contacts were actually reachable",
     "# Output: after-action report with specific plan gaps and corrective actions with owners"],
    "WHY IT WORKS: a tabletop exercise deliberately stress-tests the PLAN itself (not the technology) against a realistic scenario, and structured timing/metric tracking during the exercise reveals gaps like outdated contact lists or unclear decision authority that a plan review alone (reading the document) would never surface. WHY IT MATTERS: regulatory frameworks (e.g. NYDFS Cybersecurity Regulation, PCI-DSS) increasingly mandate periodic IR plan TESTING, not just plan existence — an untested plan with confident-sounding language is a common audit finding precisely because plans that look complete on paper routinely fail in their first real exercise.")

add("Establish a vulnerability disclosure and CVE assignment workflow for in-house software", "ADV", "Governance, Risk & Compliance",
    "Govern how externally-reported vulnerabilities in your own product are triaged and disclosed.",
    ["cat security.txt\nContact: mailto:security@example.com\nEncryption: https://example.com/pgp-key.txt\nPreferred-Languages: en\nCanonical: https://example.com/.well-known/security.txt\nPolicy: https://example.com/security-policy",
     "# upon confirmed finding: request a CVE ID from a CNA (CVE Numbering Authority), draft a security advisory with CVSS score and remediation guidance"],
    "WHY IT WORKS: publishing a `security.txt` gives external researchers a clear, authenticated channel to report findings responsibly instead of disclosing publicly out of frustration; a defined CNA relationship and advisory template ensures every confirmed vulnerability gets a consistent CVSS score, CVE ID and remediation timeline communicated to affected customers. WHY IT MATTERS: an organization with no formal vulnerability disclosure program often finds out about a serious flaw in its own product via a public tweet or a full 0-day blog post — the governance investment in a disclosure program buys advance notice and a coordinated response window instead.")
'''

with open("/home/user/workspace/certprep_single/gen_secx_samples.py") as f:
    content = f.read()

assert MARKER in content
content = content.replace(MARKER, GRC_SECTION, 1)

with open("/home/user/workspace/certprep_single/gen_secx_samples.py", "w") as f:
    f.write(content)

print("GRC section appended")
