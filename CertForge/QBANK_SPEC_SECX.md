# CompTIA SecurityX CAS-005 (V5) — Question Bank Spec

Generate multiple-choice exam-practice questions for CompTIA **SecurityX (CAS-005)** — the expert-level cert that replaced CASP+.
Total across all domains: **1000 questions**, weighted to the official four-domain distribution.

## Output format (STRICT)
One JSON object per line (JSONL), no blank lines, no trailing commas, no markdown fences, no commentary. Each object:
```json
{"q": "question text", "options": ["A","B","C","D"], "answer": 2, "explanation": "1-2 sentence rationale for the correct answer and why it fits."}
```
- Exactly **4 options**; `answer` = zero-based index (0-3) of the correct option.
- **Vary the correct-answer position evenly** across 0/1/2/3 (do NOT cluster).
- Unique, self-contained `q` stems. Options must be unique within a question.
- Distractors must be **plausible and same-category** (all real frameworks / all real controls / all real tools) — never obvious filler.
- **SecurityX is an EXPERT, scenario-driven exam (~74% scenario-based).** Favor "An enterprise architect must… which approach BEST…" / "A CISO needs… which control…" style over simple recall. Test applied judgment, tradeoffs, and BEST/MOST-appropriate choices.
- No markdown inside strings. Explanations concise and technically accurate.
- Use current CAS-005 concepts and tooling (zero trust, SASE, CASB/CWPP/CSPM, post-quantum crypto, SBOM/SCA, SOAR, MITRE ATT&CK, STRIDE, Sigma/YARA, STIX/TAXII, NIST CSF 2.0/RMF, ISO 27001, compliance-as-code, IaC security, AI/ML security).

## Domain subtopics (from official CAS-005 objectives)

### Security Engineering (310 questions) — LARGEST DOMAIN
- **Automation & orchestration:** scripting (PowerShell, Bash, Python), event triggers, IaC (Terraform/Ansible), cloud APIs, SOAR playbooks, patch automation, workflow automation, generative AI in automation, containerization security.
- **Advanced cryptography:** post-quantum cryptography (lattice-based, hash-based), key stretching, homomorphic encryption, forward secrecy, hardware acceleration/HSM, key management & rotation.
- **Cryptographic use cases & techniques:** data at rest/in transit/in use, secure email (S/MIME, PGP), blockchain, certificate-based auth, PKI, tokenization, code signing, cryptographic erase, digital signatures, hashing, symmetric vs asymmetric, TLS 1.3, OCSP/CRL.
- **IAM engineering:** federation (SAML, OIDC, OAuth2), SSO, MFA, PAM, RBAC/ABAC/MAC/DAC, directory services, conditional access.
- **Endpoint & infrastructure security:** EDR/XDR, hardening baselines (CIS), secure boot, TPM, network security appliances, secure device provisioning.
- **Specialized/legacy systems:** SCADA/ICS, OT, IoT, embedded systems, secure enclaves.
- **Secure DevOps / SDLC:** CI/CD pipeline security, SAST/DAST/IAST, dependency scanning, secrets management, supply-chain security.

### Security Architecture (270 questions)
- **Cloud capabilities:** shared responsibility model, CASB (API vs proxy), CWPP, CSPM, shadow IT detection, serverless security, container orchestration security (Kubernetes), CI/CD, Terraform/Ansible.
- **Cloud data security:** data exposure/leakage/remanence, insecure storage, encryption key management, DLP.
- **Network architecture:** segmentation, microsegmentation, VPN / always-on VPN, API gateways/integration, secure network design, resilient/high-availability design.
- **Deperimeterization:** SASE, SD-WAN, software-defined networking (SDN).
- **Zero trust:** never-trust-always-verify, subject-object relationships, ZTNA (replace VPN), SDP, microsegmentation, continuous verification, device posture, least privilege (JIT/JEA), policy enforcement points/decision points.
- **Security boundaries & attestation:** asset identification/management, data perimeters, secure zones, trust boundaries, remote attestation.
- **Resilient systems:** component placement, availability & integrity design, redundancy, fault tolerance.
- **Emerging tech:** AI/ML threats and controls, quantum-readiness.

### Security Operations (220 questions)
- **Monitoring & data analysis:** SIEM (event parsing, retention, tuning false positives/negatives), log aggregation & correlation, prioritization, trend analysis, behavior baselines (UEBA), EPSS.
- **Vulnerability & attack surface:** scanning, SCAP (OVAL/XCCDF/CPE/CVE/CVSS), SCA, SBOM, prioritization, injection/XSS/insecure config/outdated software/weak ciphers and mitigations (input validation, patching, defense-in-depth).
- **Threat hunting:** internal intel (honeypots, UBA), external intel (OSINT, dark web, ISACs), TIPs, IoC sharing (STIX/TAXII), rule languages (Sigma, YARA, Snort), MITRE ATT&CK-based hunts.
- **Incident response:** IR lifecycle, malware analysis (sandboxing, IoC extraction, code stylometry), reverse engineering, metadata analysis, digital forensics, chain of custody, data recovery, root cause analysis.
- **Detection engineering:** alert tuning, correlation rules, playbook design.

### Governance, Risk, and Compliance (200 questions)
- **Security program:** documentation (policies, procedures, standards, guidelines), program management (security/phishing/privacy training, communication, reporting, RACI matrix).
- **Frameworks & governance:** COBIT, ITIL, NIST CSF 2.0, NIST RMF, ISO/IEC 27001/27000, CSA, configuration/asset management (CMDB, asset lifecycle, inventory), GRC tools (mapping, automation, compliance tracking), data governance (prod/dev/test/QA).
- **Risk management:** impact analysis, quantitative (SLE/ALE/ARO) vs qualitative risk assessment, third-party/supply-chain risk, CIA considerations, privacy risk, crisis management, risk appetite/tolerance/treatment.
- **Threat modeling:** actor characteristics, attack patterns, frameworks (MITRE ATT&CK, CAPEC, STRIDE), attack surface determination, trust boundaries/data-flow (architecture reviews).
- **Compliance:** PCI DSS, GDPR, HIPAA, SOX, industry standards, audits vs assessments vs certifications, privacy regulations, cross-jurisdictional requirements, legal holds, compliance-as-code.
- **AI security challenges:** legal/privacy implications, threats to the model (poisoning, evasion, inversion), AI-enabled attacks, risks of AI usage, AI assistants/digital workers.

## Quality bar
Read like real expert-level CompTIA scenario items: applied judgment, BEST/MOST-appropriate answers, enterprise context. Avoid trivia and avoid deprecated concepts as the "correct" answer.
