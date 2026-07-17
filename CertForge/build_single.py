#!/usr/bin/env python3
"""Build a single self-contained CertForge HTML file:
- all 8 question banks embedded inline (JSON in a <script> tag)
- left sidebar where each cert is a collapsible dropdown of question sets
- hash-based client-side routing so every 'page' lives in one file
- dark theme default + light toggle
"""
import json, os, html

QBANK = "/home/user/workspace/qbank"
BOOKBANK = "/home/user/workspace/bookbank"
PBQBANK = "/home/user/workspace/pbqbank"
OUT = "/home/user/workspace/certprep_single/index.html"

CERTS = [
    {"id": "aplus",        "name": "CompTIA A+",        "code": "220-1201 / 220-1202", "desc": "V15 (launched March 25, 2025): Core 1 \u2014 mobile devices, networking, hardware, virtualization/cloud, and hardware/network troubleshooting; Core 2 \u2014 operating systems, security, software troubleshooting, and operational procedures. Updated for modern IT with expanded networking, cloud, and AI-assisted support content."},
    {"id": "networkplus",  "name": "CompTIA Network+",  "code": "N10-009",  "desc": "Networking concepts, infrastructure, operations, security, and troubleshooting."},
    {"id": "ccna",         "name": "Cisco CCNA",        "code": "200-301",  "desc": "Network fundamentals, IP connectivity and services, security fundamentals, and automation."},
    {"id": "securityplus", "name": "CompTIA Security+", "code": "SY0-701",  "desc": "Threats and mitigations, security architecture, operations, and program management."},
    {"id": "cysaplus",     "name": "CompTIA CySA+",     "code": "CS0-004",  "desc": "V4 (launched June 23, 2026): security operations, vulnerability management, incident response and management, and reporting and communication \u2014 with expanded AI-in-SOC, cloud-native monitoring, and zero trust content."},
    {"id": "linuxplus",    "name": "CompTIA Linux+",    "code": "XK0-006",  "desc": "System management, services & user management, security, automation/orchestration/scripting, and troubleshooting (V8 \u2014 Bash, Python, Git, containers, IaC)."},
    {"id": "pentestplus",  "name": "CompTIA PenTest+",  "code": "PT0-003",  "desc": "Engagement management, reconnaissance, attacks and exploits, and post-exploitation."},
    {"id": "cloudplus",    "name": "CompTIA Cloud+",    "code": "CV0-004",  "desc": "Cloud architecture, deployments, operations, security, DevOps, and troubleshooting."},
    {"id": "securityx",    "name": "CompTIA SecurityX",   "code": "CAS-005",  "desc": "Expert-level security: governance/risk/compliance, security architecture, security engineering (incl. advanced & post-quantum cryptography), and security operations across cloud, on-prem, and hybrid \u2014 with zero trust, automation, and AI security (formerly CASP+)."},
    {"id": "itil5",        "name": "ITIL 5 Foundation",   "code": "ITIL V5", "desc": "Digital product & service management (DPSM): key terms, the four dimensions, the seven guiding principles, the Service Value System, the eight-activity service value chain, the product & service lifecycle and service journey, ITIL management practices, and Responsible AI governance (PeopleCert, launched 2026)."},
    {"id": "ms102",        "name": "Microsoft 365 Administrator", "code": "MS-102", "desc": "Deploy and manage a Microsoft 365 tenant, implement and manage Microsoft Entra identity and access, manage security and threats with Microsoft Defender XDR, and manage compliance with Microsoft Purview \u2014 the qualifying exam for the Microsoft 365 Certified: Administrator Expert credential."},
    {"id": "az802",        "name": "Administering Windows Server", "code": "AZ-802", "desc": "Administer Windows Server across on-premises, hybrid, and Azure environments per the current official skills outline: deploy and manage AD DS, manage server instances and workloads in a hybrid environment (Azure Arc, Windows Admin Center, Update Manager), manage virtual machines (Hyper-V and Azure), on-premises and hybrid networking, storage and file services, secure Windows Server infrastructure, and monitor and troubleshoot Windows Server environments."},
    {"id": "az900",        "name": "Azure Fundamentals",   "code": "AZ-900", "desc": "Foundational cloud knowledge: cloud concepts (IaaS/PaaS/SaaS, public/private/hybrid), core Azure architecture and services (compute, networking, storage, databases), and Azure management and governance (cost management, SLAs, Entra ID, Zero Trust, policy and compliance)."},
]

def load_bank(cid):
    out = []
    with open(os.path.join(QBANK, cid + ".jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

def load_book(cid):
    path = os.path.join(BOOKBANK, cid + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_pbq(cid):
    path = os.path.join(PBQBANK, cid + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_domains(cid):
    # Domain classification produced by qbank/gen_domains.py -> qbank/_domains/<cid>.json
    path = os.path.join(QBANK, "_domains", cid + ".json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = {}
    meta = []
    books = {}
    pbqs = {}
    domains = {}
    for c in CERTS:
        bank = load_bank(c["id"])
        data[c["id"]] = bank
        m = dict(c)
        m["count"] = len(bank)
        meta.append(m)
        bk = load_book(c["id"])
        pq = load_pbq(c["id"])
        dm = load_domains(c["id"])
        if dm and len(dm.get("map", [])) == len(bank):
            domains[c["id"]] = dm
        elif dm:
            print(f"  WARNING {c['id']}: domain map length {len(dm.get('map', []))} != bank {len(bank)} \u2014 skipping domains for this cert")
        npbq = 0
        if pq:
            pbqs[c["id"]] = pq
            npbq = len(pq)
        if bk:
            books[c["id"]] = bk
            nterm = sum(1 for ch in bk["chapters"] for b in ch["blocks"] if b["type"] == "terminal")
            print(f"  {c['id']}: {len(bank)} questions | book {len(bk['chapters'])} ch, {nterm} terminals | {npbq} PBQs")
        else:
            print(f"  {c['id']}: {len(bank)} questions | NO BOOK | {npbq} PBQs")

    # JSON embedded safely (escape </script>)
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    books_json = json.dumps(books, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pbqs_json = json.dumps(pbqs, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    domains_json = json.dumps(domains, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        tpl = f.read()
    tpl = tpl.replace("/*__META__*/", "window.CERT_META = " + meta_json + ";")
    tpl = tpl.replace("/*__DATA__*/", "window.CERT_DATA = " + data_json + ";")
    tpl = tpl.replace("/*__BOOKS__*/", "window.CERT_BOOKS = " + books_json + ";")
    tpl = tpl.replace("/*__PBQS__*/", "window.CERT_PBQS = " + pbqs_json + ";")
    tpl = tpl.replace("/*__DOMAINS__*/", "window.CERT_DOMAINS = " + domains_json + ";")
    print("  injected domain classification for", len(domains), "certs")
    # Inject the IOS simulator engine
    sim_path = os.path.join(os.path.dirname(OUT), "ios_sim.js")
    with open(sim_path, encoding="utf-8") as f:
        sim_src = f.read()
    tpl = tpl.replace("/*__IOSSIM__*/", sim_src)
    print("  injected IOS simulator (", len(sim_src), "bytes )")
    # Inject the 100 script-sample library
    samp_path = os.path.join(os.path.dirname(OUT), "script_samples.js")
    with open(samp_path, encoding="utf-8") as f:
        samp_src = f.read()
    tpl = tpl.replace("/*__SCRIPTSAMPLES__*/", samp_src)
    print("  injected script samples (", len(samp_src), "bytes )")
    # Inject the Linux shell simulator engine
    lsim_path = os.path.join(os.path.dirname(OUT), "linux_sim.js")
    with open(lsim_path, encoding="utf-8") as f:
        lsim_src = f.read()
    tpl = tpl.replace("/*__LINUXSIM__*/", lsim_src)
    print("  injected Linux simulator (", len(lsim_src), "bytes )")
    # Inject the 100 Linux script-sample library
    lsamp_path = os.path.join(os.path.dirname(OUT), "linux_samples.js")
    with open(lsamp_path, encoding="utf-8") as f:
        lsamp_src = f.read()
    tpl = tpl.replace("/*__LINUXSAMPLES__*/", lsamp_src)
    print("  injected Linux samples (", len(lsamp_src), "bytes )")
    # Inject the SecurityX tooling console engine
    xsim_path = os.path.join(os.path.dirname(OUT), "secx_sim.js")
    with open(xsim_path, encoding="utf-8") as f:
        xsim_src = f.read()
    tpl = tpl.replace("/*__SECXSIM__*/", xsim_src)
    print("  injected SecurityX console (", len(xsim_src), "bytes )")
    # Inject the 100 SecurityX command/rule sample library
    xsamp_path = os.path.join(os.path.dirname(OUT), "secx_samples.js")
    with open(xsamp_path, encoding="utf-8") as f:
        xsamp_src = f.read()
    tpl = tpl.replace("/*__SECXSAMPLES__*/", xsamp_src)
    print("  injected SecurityX samples (", len(xsamp_src), "bytes )")
    # Inject the Atlassian JSM / ITIL 5 CLI console engine
    jsim_path = os.path.join(os.path.dirname(OUT), "jsm_sim.js")
    with open(jsim_path, encoding="utf-8") as f:
        jsim_src = f.read()
    tpl = tpl.replace("/*__JSMSIM__*/", jsim_src)
    print("  injected JSM console (", len(jsim_src), "bytes )")
    # Inject the 100 JSM CLI / config sample library
    jsamp_path = os.path.join(os.path.dirname(OUT), "jsm_samples.js")
    with open(jsamp_path, encoding="utf-8") as f:
        jsamp_src = f.read()
    tpl = tpl.replace("/*__JSMSAMPLES__*/", jsamp_src)
    print("  injected JSM samples (", len(jsamp_src), "bytes )")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(tpl)
    print("Wrote", OUT, f"({os.path.getsize(OUT)/1024/1024:.2f} MB)")

TEMPLATE_PATH = "/home/user/workspace/certprep_single/template.html"

if __name__ == "__main__":
    main()
