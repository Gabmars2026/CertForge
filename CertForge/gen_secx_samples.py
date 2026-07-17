#!/usr/bin/env python3
"""Generate secx_samples.js — 100 CompTIA SecurityX (CAS-005) security
command/rule/config "script samples" spanning CORE -> INTER -> ADV across
the four exam domains. Emits window.SECX_SAMPLES = [...]. Mirrors the
structure/format of gen_linux_samples.py (the Linux+ generator) exactly,
including the EXPLAIN label grammar so the existing UI parser (see
template.html ssExplain()) works unchanged:
  WHY IT WORKS: ...   [WHY A VARIANT FAILS: ...]   [WHY IT MATTERS: ...]
"""
import json

S = []  # each: {id,title,level,cat,purpose,config(list of lines),explain}


def add(title, level, cat, purpose, cfg, explain):
    S.append({"id": len(S) + 1, "title": title, "level": level,
              "cat": cat, "purpose": purpose, "config": cfg, "explain": explain})


# =====================================================================
# DOMAIN: Security Engineering (~31) — Cryptography/PKI, secure DevOps,
# code signing/SBOM, container & IaC security scanning, IAM primitives
# =====================================================================

add("Generate an RSA private key and a modern EC key", "CORE", "Security Engineering",
    "Create both a legacy RSA key and a modern elliptic-curve key for comparison.",
    ["openssl genrsa -out rsa4096.key 4096",
     "openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out ec256.key",
     "openssl pkey -in ec256.key -text -noout | head -5"],
    "WHY IT WORKS: `genrsa` produces a traditional RSA keypair (4096-bit is the current minimum for long-lived keys), while `genpkey -algorithm EC` uses the generic PKEY interface to build a much smaller, faster P-256 elliptic-curve key offering comparable security at a fraction of the key size. WHY A VARIANT FAILS: using the legacy `openssl ecparam -genkey` command still works but is deprecated in OpenSSL 3.x in favor of the unified `genpkey` interface — exam answers should reflect the modern command.")

add("Generate a CSR and self-signed certificate with openssl req", "CORE", "Security Engineering",
    "Create a certificate signing request and a throwaway self-signed cert for lab testing.",
    ["openssl req -new -key rsa4096.key -out server.csr -subj \"/C=US/O=Example/CN=app.example.com\"",
     "openssl req -x509 -key rsa4096.key -in server.csr -days 365 -out selfsigned.crt",
     "openssl req -text -noout -in server.csr"],
    "WHY IT WORKS: `req -new` builds a PKCS#10 CSR containing the public key and subject identity for a CA to sign; adding `-x509` instead directly emits a self-signed certificate for the same key, useful for internal testing without a CA round-trip. WHY A VARIANT FAILS: shipping a self-signed cert to production browsers/clients triggers trust warnings because it isn't chained to a trusted root — self-signed certs are only appropriate for internal lab/dev use or explicit pinning scenarios.")

add("Inspect a certificate's fields with openssl x509", "CORE", "Security Engineering",
    "Read the subject, issuer, validity window and SAN entries of a certificate.",
    ["openssl x509 -in server.crt -noout -subject -issuer -dates",
     "openssl x509 -in server.crt -noout -ext subjectAltName",
     "openssl x509 -in server.crt -noout -fingerprint -sha256"],
    "WHY IT WORKS: `x509 -noout` suppresses the PEM blob and prints only the requested fields; `-ext subjectAltName` is essential because modern browsers ignore the legacy CN field and validate hostname only against SAN entries. WHY IT MATTERS: an expired cert (`-dates`) or a missing SAN for the exact hostname being accessed are the two most common real-world TLS outages — always check both before assuming a deeper problem.")

add("Verify a certificate chain against a trust store", "INTER", "Security Engineering",
    "Confirm a leaf certificate chains correctly to a trusted root.",
    ["cat intermediate.crt root.crt > chain.pem",
     "openssl verify -CAfile chain.pem server.crt",
     "openssl verify -CApath /etc/ssl/certs server.crt"],
    "WHY IT WORKS: `openssl verify` walks the certificate's issuer chain up to a self-signed root, checking signatures, validity dates and basic constraints at each hop against the supplied CA bundle. WHY A VARIANT FAILS: verifying only against the root without including the intermediate in the bundle fails with 'unable to get local issuer certificate' — servers must present the full chain (leaf+intermediate) because most clients do not fetch missing intermediates automatically.")

add("Test a live TLS endpoint with openssl s_client", "CORE", "Security Engineering",
    "Inspect the negotiated protocol, cipher and served chain of a remote TLS host.",
    ["openssl s_client -connect app.example.com:443 -servername app.example.com </dev/null",
     "openssl s_client -connect app.example.com:443 -tls1_2 </dev/null | grep -i protocol",
     "echo | openssl s_client -connect app.example.com:443 2>/dev/null | openssl x509 -noout -dates"],
    "WHY IT WORKS: `s_client` performs a real TLS handshake and prints the negotiated protocol/cipher plus the full certificate chain the server actually presents, which is the ground truth versus what config files claim. WHY A VARIANT FAILS: omitting `-servername` skips SNI, so a server hosting multiple TLS vhosts on one IP may return its DEFAULT certificate instead of the one for the requested hostname, producing a misleading mismatch.")

add("Compute and compare file hashes for integrity", "CORE", "Security Engineering",
    "Verify a downloaded artifact matches its published checksum.",
    ["sha256sum app-release-1.4.0.tar.gz",
     "echo \"expectedhash  app-release-1.4.0.tar.gz\" | sha256sum -c -",
     "openssl dgst -sha256 app-release-1.4.0.tar.gz"],
    "WHY IT WORKS: SHA-256 is a one-way cryptographic hash; recomputing it and comparing to a vendor-published value detects any bit-level tampering or corruption in transit. `sha256sum -c` automates the comparison and exits non-zero on mismatch for scripting. WHY A VARIANT FAILS: comparing an MD5 or SHA-1 checksum instead provides false confidence — both are cryptographically broken for collision resistance and should never be relied on for integrity verification of security-relevant artifacts.")

add("Encrypt and decrypt a file symmetrically with openssl enc", "INTER", "Security Engineering",
    "Protect a sensitive file at rest using AES-256-GCM with a derived key.",
    ["openssl enc -aes-256-gcm -pbkdf2 -iter 200000 -salt -in secrets.env -out secrets.env.enc",
     "openssl enc -aes-256-gcm -pbkdf2 -iter 200000 -d -in secrets.env.enc -out secrets.env"],
    "WHY IT WORKS: `-pbkdf2 -iter 200000` derives a strong key from the passphrase with many iterations to resist brute-force/rainbow-table attacks, and AES-256-GCM provides both confidentiality and integrity (authenticated encryption) in one pass. WHY A VARIANT FAILS: using the legacy default KDF (no -pbkdf2) or a non-authenticated mode like plain CBC gives an attacker a padding-oracle or bit-flipping vector — GCM's authentication tag is what catches tampering, and CBC alone provides none.")

add("Rotate a TLS certificate before expiry with zero downtime", "ADV", "Security Engineering",
    "Issue a replacement cert, stage it, then reload the web server without dropping connections.",
    ["openssl x509 -in /etc/nginx/ssl/server.crt -noout -enddate",
     "openssl req -new -key server.key -out renew.csr -subj \"/CN=app.example.com\"",
     "# submit renew.csr to CA, receive renewed.crt",
     "cat renewed.crt intermediate.crt > /etc/nginx/ssl/server.crt.new",
     "mv /etc/nginx/ssl/server.crt.new /etc/nginx/ssl/server.crt",
     "nginx -t && systemctl reload nginx"],
    "WHY IT WORKS: `nginx -s reload`/`systemctl reload` (unlike restart) spawns new worker processes that pick up the new cert while existing connections on old workers drain gracefully, avoiding a service interruption. WHY A VARIANT FAILS: running `systemctl restart` instead of `reload` drops all in-flight TLS connections at once; and reusing the SAME private key across renewals (rather than generating a fresh one) means a prior key compromise persists silently across the 'rotation'.")

add("Generate an ML-KEM (Kyber) post-quantum keypair alongside a classical key", "ADV", "Security Engineering",
    "Build a hybrid classical+post-quantum key exchange for crypto-agility planning.",
    ["openssl list -kem-algorithms",
     "openssl genpkey -algorithm mlkem768 -out pq_mlkem768.key",
     "openssl genpkey -algorithm X25519 -out classical_x25519.key",
     "# Hybrid handshake (X25519+MLKEM768) negotiated automatically by TLS 1.3-capable stacks that support it"],
    "WHY IT WORKS: NIST-standardized ML-KEM (formerly Kyber) is a lattice-based key-encapsulation mechanism resistant to Shor's-algorithm attacks from a future quantum computer; pairing it with a classical X25519 key in a hybrid exchange means an attacker must break BOTH algorithms to recover the shared secret. WHY IT MATTERS: 'harvest now, decrypt later' is the real threat model — traffic encrypted today with classical-only key exchange can be recorded and broken retroactively once quantum computing matures, so migrating long-lived-confidentiality traffic to hybrid PQ key exchange is a current CAS-005 crypto-agility expectation, not a future one.")

add("Sign and verify a container image with cosign (keyless)", "ADV", "Security Engineering",
    "Establish supply-chain provenance using Sigstore's keyless OIDC signing.",
    ["cosign sign --yes registry.example.com/app:1.4.0",
     "cosign verify registry.example.com/app:1.4.0 --certificate-identity=ci@example.com --certificate-oidc-issuer=https://token.actions.githubusercontent.com"],
    "WHY IT WORKS: keyless cosign signing uses short-lived certificates issued by Sigstore's Fulcio CA bound to an OIDC identity (e.g. a CI pipeline's workload identity), with the signature and cert transparency-logged in Rekor — eliminating long-lived private signing keys that could leak. WHY A VARIANT FAILS: verifying with no `--certificate-identity`/`--certificate-oidc-issuer` constraint accepts a valid signature from ANY Sigstore identity, not just your trusted pipeline — always pin the expected identity and issuer or verification is meaningless.")

add("Generate an SSH key pair with hardware-backed protection intent", "CORE", "Security Engineering",
    "Create a modern SSH key and enforce a passphrase for private key protection.",
    ["ssh-keygen -t ed25519 -a 100 -C \"admin@bastion\" -f ~/.ssh/id_ed25519_admin",
     "ssh-add ~/.ssh/id_ed25519_admin",
     "ssh-keygen -lf ~/.ssh/id_ed25519_admin.pub"],
    "WHY IT WORKS: `-a 100` increases the KDF rounds protecting the encrypted private key at rest, raising the cost of offline brute-forcing if the key file is stolen; `ed25519` is smaller and faster to verify than RSA at equivalent security margins. WHY A VARIANT FAILS: generating a key with no passphrase (`-N \"\"`) means anyone who copies the private key file off disk can use it immediately with no additional barrier — privileged admin keys should always require a passphrase or be backed by hardware (YubiKey/FIDO2).")

add("Use gpg to encrypt a file asymmetrically for a specific recipient", "INTER", "Security Engineering",
    "Share a sensitive file securely using the recipient's public key.",
    ["gpg --import colleague_pubkey.asc",
     "gpg --encrypt --recipient colleague@example.com --sign audit_report.pdf",
     "gpg --decrypt audit_report.pdf.gpg > audit_report.pdf"],
    "WHY IT WORKS: `--encrypt --recipient` wraps a session key with the recipient's PUBLIC key so only their matching private key can decrypt it, while `--sign` simultaneously proves the sender's identity to the recipient. WHY A VARIANT FAILS: using symmetric `gpg -c` instead for multi-party sharing requires transmitting the passphrase out-of-band to every recipient — asymmetric encryption avoids that shared-secret distribution problem entirely.")

add("Stand up a private CA with step-ca for short-lived certs", "ADV", "Security Engineering",
    "Bootstrap an internal certificate authority issuing automatically-renewed short-lived certs.",
    ["step ca init --name \"Internal CA\" --dns ca.internal --address :443 --provisioner admin",
     "step-ca $(step path)/config/ca.json &",
     "step ca certificate app.internal app.crt app.key --ca-url https://ca.internal --root root_ca.crt"],
    "WHY IT WORKS: step-ca automates issuance/renewal of short-lived (hours-to-days) certificates via ACME or its own API, shrinking the exposure window if a key or cert leaks compared to traditional 1-year certs. WHY IT MATTERS: short-lived cert architectures shift trust from 'revocation lists nobody checks in time' to 'certs simply expire soon,' which is why modern zero-trust and service-mesh designs (CAS-005 architecture domain) favor them over long-lived PKI.")

add("Harden TLS 1.3 cipher and protocol configuration in nginx", "INTER", "Security Engineering",
    "Restrict a web server to TLS 1.2+/1.3 with strong AEAD ciphers only.",
    ["# nginx.conf inside server block:",
     "ssl_protocols TLSv1.2 TLSv1.3;",
     "ssl_ciphers ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!3DES;",
     "ssl_prefer_server_ciphers off;",
     "nginx -t && systemctl reload nginx"],
    "WHY IT WORKS: disabling TLS 1.0/1.1 removes protocol versions with known weaknesses (BEAST, POODLE-adjacent issues); restricting to AEAD cipher suites (AESGCM/CHACHA20) prevents padding-oracle and MAC-forgery classes of attack that older CBC suites are vulnerable to. WHY A VARIANT FAILS: setting `ssl_prefer_server_ciphers on` made sense for TLS 1.2 to enforce server-preferred strong suites, but TLS 1.3 negotiates ciphers differently and always lets the client pick from an already-vetted list — leaving it on is harmless but no longer meaningful, a common outdated-config carryover.")

add("Scan a container image for known vulnerabilities with trivy", "CORE", "Security Engineering",
    "Identify CVEs in OS packages and application dependencies before deployment.",
    ["trivy image --severity HIGH,CRITICAL registry.example.com/app:1.4.0",
     "trivy image --exit-code 1 --severity CRITICAL registry.example.com/app:1.4.0"],
    "WHY IT WORKS: trivy inspects both OS package manifests and language-specific dependency lockfiles inside image layers against an aggregated vulnerability database, reporting CVE ID, severity and fixed version. `--exit-code 1` lets a CI pipeline fail the build on findings. WHY A VARIANT FAILS: scanning only the final application layer without `image` mode (e.g. scanning just a Dockerfile) misses vulnerabilities baked into base-image OS packages, which is where a large share of real findings live.")

add("Generate a Software Bill of Materials with syft", "INTER", "Security Engineering",
    "Produce a machine-readable inventory of every component in a container image.",
    ["syft registry.example.com/app:1.4.0 -o cyclonedx-json=app-sbom.json",
     "syft registry.example.com/app:1.4.0 -o table | head -20",
     "grype sbom:app-sbom.json"],
    "WHY IT WORKS: syft enumerates packages across every layer (OS packages, language modules, static binaries) into a standard SBOM format (CycloneDX/SPDX); piping that SBOM into grype re-uses it for vulnerability matching without re-scanning the image from scratch. WHY IT MATTERS: an SBOM is what lets you answer 'are we affected by this newly-disclosed CVE' in minutes across your whole fleet — without one, supply-chain incident response means re-scanning every image live, which doesn't scale.")

add("Scan source code for hardcoded secrets before commit", "CORE", "Security Engineering",
    "Prevent API keys and credentials from ever reaching git history.",
    ["gitleaks detect --source . --verbose",
     "gitleaks protect --staged --verbose",
     "git secrets --install && git secrets --register-aws"],
    "WHY IT WORKS: `gitleaks protect --staged` runs as a pre-commit hook scanning ONLY staged changes against regex/entropy-based secret patterns, blocking the commit before the secret ever enters version-control history. WHY A VARIANT FAILS: running `gitleaks detect` only occasionally against the full history AFTER secrets are already committed means the credential is already permanently in git history (recoverable from any clone) and must be treated as compromised and rotated, not just deleted from the latest commit.")

add("Run static application security testing with semgrep", "INTER", "Security Engineering",
    "Find insecure code patterns (SQL injection, hardcoded crypto) across a codebase.",
    ["semgrep --config p/security-audit --config p/owasp-top-ten src/",
     "semgrep --config p/security-audit --error --json src/ > semgrep-results.json"],
    "WHY IT WORKS: semgrep matches syntax-aware patterns (not just regex) across many languages, so rulesets like p/owasp-top-ten catch structural issues (e.g. string-concatenated SQL, unsanitized eval) that plain grep would miss or false-positive on. `--error` makes matches fail CI. WHY A VARIANT FAILS: relying only on generic linting (ESLint/pylint) instead of a security-focused SAST ruleset misses classes of vulnerability those tools were never designed to detect, like taint-tracked injection sinks.")

add("Scan open-source dependencies for known CVEs with OWASP dependency-check", "INTER", "Security Engineering",
    "Audit third-party libraries pulled into a build for published vulnerabilities.",
    ["dependency-check --project \"app\" --scan ./ --format HTML --format JSON --out ./reports",
     "grep -i 'CVE-' reports/dependency-check-report.json | head -20"],
    "WHY IT WORKS: dependency-check fingerprints libraries (via CPE matching against NVD data) even when a package manager lockfile is absent, catching vendored or manually-included JARs/DLLs that manifest-based scanners miss. WHY IT MATTERS: exam scenarios often stress that dependency scanning must run on EVERY build, not just at release time, because a new CVE can be published against a library your code has depended on unchanged for years — the risk appears the day the CVE is disclosed, not the day the code was written.")

add("Scan Terraform IaC for misconfigurations before apply", "CORE", "Security Engineering",
    "Catch insecure cloud resource definitions (open security groups, unencrypted storage) pre-deployment.",
    ["terraform plan -out=tfplan.binary",
     "tfsec .",
     "checkov -d . --framework terraform"],
    "WHY IT WORKS: tfsec and checkov statically analyze Terraform HCL against known-bad patterns (0.0.0.0/0 ingress, unencrypted S3/EBS, public IAM policies) BEFORE any real cloud resource is created, catching the mistake at the cheapest possible point in the pipeline. WHY A VARIANT FAILS: running `terraform apply` first and scanning the live environment afterward with a cloud-native tool means the insecure resource was already provisioned and possibly exposed for some window of time — shifting the scan left of apply is the whole point.")

add("Encrypt secrets at rest in an Ansible repository with ansible-vault", "CORE", "Security Engineering",
    "Store credentials safely inside version-controlled playbooks.",
    ["ansible-vault create group_vars/prod/vault.yml",
     "ansible-vault view group_vars/prod/vault.yml",
     "ansible-playbook site.yml --ask-vault-pass"],
    "WHY IT WORKS: ansible-vault transparently AES-256 encrypts an entire YAML file, so it can be committed to git alongside plaintext playbooks while its contents remain unreadable without the vault password; ansible decrypts it in-memory only at run time. WHY A VARIANT FAILS: putting the vault password itself into a plaintext file committed to the SAME repo (rather than a separate secrets manager or `--vault-password-file` pointed outside version control) defeats the entire purpose — the password must be distributed through a different trust channel than the encrypted content.")

add("Decode and inspect a JWT for claim tampering risk", "INTER", "Security Engineering",
    "Manually decode a bearer token to verify its claims and signing algorithm.",
    ["echo $JWT | cut -d. -f1 | base64 -d 2>/dev/null | jq .",
     "echo $JWT | cut -d. -f2 | base64 -d 2>/dev/null | jq .",
     "# confirm header {\"alg\":\"RS256\"} matches the verifying key type server-side"],
    "WHY IT WORKS: a JWT is three base64url segments (header.payload.signature); decoding the first two reveals the signing algorithm and claims in plaintext without needing the signing key, which is exactly why JWTs must never carry secrets in the payload. WHY A VARIANT FAILS: a server that trusts the `alg` field from the token itself (rather than pinning an expected algorithm server-side) is vulnerable to the classic 'alg:none' or RS256-to-HS256 confusion attack, where an attacker forges a token by switching the algorithm to one the server will verify insecurely.")

add("Register an OIDC relying party and validate the discovery document", "INTER", "Security Engineering",
    "Set up modern federated auth using OpenID Connect discovery.",
    ["curl -s https://idp.example.com/.well-known/openid-configuration | jq .",
     "curl -s https://idp.example.com/.well-known/jwks.json | jq '.keys[0]'",
     "# configure RP: client_id, redirect_uri, and scopes openid profile email"],
    "WHY IT WORKS: the `.well-known/openid-configuration` document publishes the IdP's authorization/token/JWKS endpoints so a relying party can auto-configure trust without manually hardcoding URLs; the JWKS endpoint supplies the current signing keys used to verify ID tokens. WHY IT MATTERS: JWKS keys rotate periodically — a relying party that caches keys forever instead of respecting cache-control/periodic refresh will start rejecting valid tokens the moment the IdP rotates its signing key, a common real-world OIDC outage.")

add("Query and bind to an LDAP directory securely", "CORE", "Security Engineering",
    "Search directory entries over an encrypted LDAP connection.",
    ["ldapsearch -H ldaps://dc01.example.com -D \"cn=svc_reader,ou=service,dc=example,dc=com\" -W -b \"dc=example,dc=com\" \"(uid=jdoe)\"",
     "ldapwhoami -H ldaps://dc01.example.com -D \"cn=svc_reader,ou=service,dc=example,dc=com\" -W"],
    "WHY IT WORKS: `ldaps://` wraps the LDAP session in TLS on connect (port 636), protecting the bind DN/password and query contents from network sniffing; `-W` prompts interactively instead of putting the password on the command line/shell history. WHY A VARIANT FAILS: binding over plain `ldap://` (port 389) without StartTLS sends the service account's bind password in cleartext over the network — anyone able to capture that traffic recovers valid directory credentials.")

add("Administer Keycloak realms and clients from the CLI", "INTER", "Security Engineering",
    "Script IAM configuration changes for repeatability instead of manual console clicks.",
    ["kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password $ADMIN_PW",
     "kcadm.sh create clients -r myrealm -s clientId=app-web -s 'redirectUris=[\"https://app.example.com/*\"]' -s publicClient=false",
     "kcadm.sh get users -r myrealm --fields username,enabled"],
    "WHY IT WORKS: kcadm.sh scripts identity-provider configuration (realms, clients, redirect URIs, client secrets) so IAM settings can be version-controlled and reproducibly applied across environments instead of manually clicked through an admin console. WHY A VARIANT FAILS: setting `publicClient=true` for a confidential server-side app skips client-secret authentication at the token endpoint, letting anyone who obtains the client ID request tokens on the app's behalf — public clients are only appropriate for apps that truly cannot keep a secret (native/mobile/SPA with PKCE).")

add("Enforce PKCE for a public OAuth client", "ADV", "Security Engineering",
    "Mitigate authorization code interception on a mobile/SPA OAuth flow.",
    ["# generate a code verifier and derive the challenge",
     "CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=+/')",
     "CODE_CHALLENGE=$(echo -n $CODE_VERIFIER | openssl dgst -sha256 -binary | base64 | tr -d '=+/' | tr '/+' '_-')",
     "# authorize request: ...&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256",
     "# token request must include: &code_verifier=$CODE_VERIFIER"],
    "WHY IT WORKS: PKCE binds the authorization code to a secret verifier only the legitimate client instance holds; the authorization server checks that SHA-256(verifier) matches the challenge sent earlier, so a stolen authorization code alone is useless to an attacker without the verifier. WHY A VARIANT FAILS: using `code_challenge_method=plain` instead of `S256` sends the verifier itself (unhashed) as the challenge in the front-channel redirect, which can be intercepted the same way the code itself can — defeating the protection PKCE is meant to add.")

add("Enumerate and reduce excessive IAM permissions with a least-privilege audit", "ADV", "Security Engineering",
    "Detect and right-size an overly permissive cloud identity policy.",
    ["aws iam generate-service-last-accessed-details --arn arn:aws:iam::111122223333:role/AppRole",
     "aws iam get-service-last-accessed-details --job-id <job-id>",
     "aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::111122223333:role/AppRole --action-names s3:DeleteBucket"],
    "WHY IT WORKS: `generate/get-service-last-accessed-details` reports which AWS services (and optionally actions) a role has ACTUALLY used over the tracking period, letting you replace an `*`-based policy with only the permissions demonstrably in use; `simulate-principal-policy` dry-runs a specific action against the policy without executing it. WHY IT MATTERS: least-privilege is a continuous CAS-005 governance exercise, not a one-time hardening step — roles accumulate unused permissions over time as responsibilities shift, and periodic access-analyzer review is what catches that drift before an attacker who compromises the role can exploit it.")

add("Enforce commit signing to establish code provenance", "INTER", "Security Engineering",
    "Require cryptographically signed commits so authorship can be verified.",
    ["git config --global commit.gpgsign true",
     "git config --global user.signingkey ABCDEF1234567890",
     "git commit -S -m \"fix: validate input length\"",
     "git log --show-signature -1"],
    "WHY IT WORKS: `-S` signs the commit object itself with the developer's GPG key, so `git log --show-signature` (or a server-side policy) can cryptographically verify who actually authored a commit rather than trusting the easily-spoofed `user.name`/`user.email` fields. WHY A VARIANT FAILS: relying solely on GitHub/GitLab's displayed committer name for accountability is insufficient — `git commit --author` lets anyone claim any name/email with zero cryptographic proof; only signed commits verified against a known public key provide real provenance.")

add("Rotate an exposed API key end-to-end", "INTER", "Security Engineering",
    "Respond to a leaked credential by revoking, reissuing and redeploying safely.",
    ["# 1. Revoke the compromised key immediately at the provider",
     "aws iam delete-access-key --user-name svc-app --access-key-id AKIA_LEAKED",
     "# 2. Issue a new key",
     "aws iam create-access-key --user-name svc-app",
     "# 3. Update the secrets manager entry, NOT a config file in git",
     "aws secretsmanager put-secret-value --secret-id prod/app/api-key --secret-string file://newkey.json",
     "# 4. Force a rolling redeploy so all instances pick up the new key",
     "kubectl rollout restart deployment/app"],
    "WHY IT WORKS: revoking the old key FIRST closes the exposure window immediately, before the replacement even exists, minimizing the time an attacker with the leaked key can act; storing the new value only in the secrets manager (never in git) prevents repeating the same class of exposure. WHY A VARIANT FAILS: issuing a new key and updating configs BEFORE revoking the old one leaves both keys valid simultaneously for longer than necessary — order matters in incident response, and 'revoke first' is the CAS-005-expected sequence even though it risks a brief outage versus a security gap.")

add("Harden a code-signing pipeline against key compromise", "ADV", "Security Engineering",
    "Move a release-signing private key out of CI environment variables into an HSM-backed KMS.",
    ["aws kms create-key --key-usage SIGN_VERIFY --key-spec RSA_4096 --description \"release-signing-key\"",
     "aws kms sign --key-id alias/release-signing --message fileb://artifact.sha256 --message-type DIGEST --signing-algorithm RSASSA_PSS_SHA_256 --output text --query Signature | base64 -d > artifact.sig",
     "aws kms verify --key-id alias/release-signing --message fileb://artifact.sha256 --message-type DIGEST --signature blob://artifact.sig --signing-algorithm RSASSA_PSS_SHA_256"],
    "WHY IT WORKS: KMS/HSM-backed signing keys never leave the hardware boundary and are never exposed as an exportable file or CI secret variable, so even full compromise of the CI runner cannot exfiltrate the private key — only signing requests through the API (auditable and IAM-gated) are possible. WHY A VARIANT FAILS: storing a raw .pem release-signing key as a CI secret variable means anyone who compromises the CI pipeline (a very common real-world supply-chain attack vector, e.g. SolarWinds-style) can exfiltrate the key entirely and sign malicious releases indefinitely, with no way to revoke just the leak.")

add("Configure mutual TLS between two microservices", "ADV", "Security Architecture",
    "Require both client and server to present certificates for service-to-service auth.",
    ["openssl s_client -connect svc-b.internal:8443 -cert client.crt -key client.key -CAfile internal-ca.pem </dev/null",
     "# server config (nginx): ssl_client_certificate internal-ca.pem; ssl_verify_client on;"],
    "WHY IT WORKS: in mTLS, the server additionally validates a client certificate against a trusted internal CA before accepting the connection, so a service cannot even establish a session without proving its own identity — a foundational zero-trust building block between internal services, not just perimeter-facing TLS. WHY A VARIANT FAILS: enabling `ssl_verify_client optional` instead of `on` allows connections WITHOUT a client cert to proceed anyway (the app is then responsible for checking whether one was presented), a common misconfiguration that silently defeats the whole point of mutual authentication for callers that omit a cert.")

add("Encrypt Kubernetes secrets at rest with a KMS-backed provider", "ADV", "Security Architecture",
    "Prevent etcd from storing Secret objects as recoverable base64/plaintext.",
    ["cat <<'EOF' > encryption-config.yaml\napiVersion: apiserver.config.k8s.io/v1\nkind: EncryptionConfiguration\nresources:\n  - resources: [\"secrets\"]\n    providers:\n      - kms:\n          name: aws-kms\n          endpoint: unix:///var/run/kmsplugin/socket.sock\n      - identity: {}\nEOF",
     "# add --encryption-provider-config=encryption-config.yaml to kube-apiserver flags, then restart",
     "kubectl get secrets -A -o json | kubectl replace -f - # force re-encryption of existing secrets"],
    "WHY IT WORKS: without an EncryptionConfiguration, Kubernetes Secret objects are stored in etcd as base64 (NOT encrypted — trivially reversible), so anyone with etcd read access or a snapshot backup can recover every secret; a KMS provider encrypts secret values with a key that never leaves the external KMS. WHY A VARIANT FAILS: adding the encryption config only affects secrets written AFTER the change — existing secrets remain in their old (unencrypted) form in etcd until explicitly rewritten, which is why the `kubectl replace` re-write step is required to actually protect previously-created secrets.")

add("Implement certificate pinning risk-awareness in a mobile client review", "ADV", "Security Architecture",
    "Evaluate the operational tradeoff of pinning a certificate/public key in an app.",
    ["openssl x509 -in pinned-leaf.crt -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | base64",
     "# compare the resulting pin against the value hardcoded in the mobile app's network security config"],
    "WHY IT WORKS: computing the SHA-256 of the SubjectPublicKeyInfo (not the whole cert) produces the exact pin value mobile/network-security-config frameworks expect, and pinning to the PUBLIC KEY (not the leaf cert) survives a routine cert renewal as long as the key is reused. WHY A VARIANT FAILS: pinning to the exact leaf certificate's hash instead of its public key means every routine renewal (even with the identical key) breaks every already-installed app copy until an app update ships — a frequent cause of pinning-related outages, and why key-based or CA-based pinning with a backup pin is the safer pattern.")

add("Validate HSTS and secure header enforcement on a web app", "CORE", "Security Engineering",
    "Confirm the server instructs browsers to always use HTTPS.",
    ["curl -sI https://app.example.com | grep -i strict-transport-security",
     "curl -sI https://app.example.com | egrep -i 'content-security-policy|x-content-type-options|x-frame-options'"],
    "WHY IT WORKS: `Strict-Transport-Security` tells the browser to rewrite all future requests to that domain to HTTPS internally, without a round-trip through an interceptable plaintext redirect, closing the classic HTTP-downgrade attack window entirely for return visitors. WHY A VARIANT FAILS: setting HSTS with a very short `max-age` (or omitting `includeSubDomains`) leaves the protection window tiny or scoped too narrowly — a subdomain without HSTS coverage remains a viable downgrade target even while the main domain looks hardened.")

add("Audit a Docker image build for root-user and privilege risks", "CORE", "Security Architecture",
    "Confirm a container image doesn't run its main process as root.",
    ["docker inspect --format='{{.Config.User}}' app:1.4.0",
     "docker run --rm app:1.4.0 id",
     "# Dockerfile fix: RUN adduser -D appuser && chown -R appuser /app\\nUSER appuser"],
    "WHY IT WORKS: a container without an explicit `USER` directive defaults to root inside the container namespace; if a container-breakout vulnerability is later exploited, a root-inside-container process has a much larger blast radius (capability to remap into host root under certain misconfigurations) than a non-root process would. WHY A VARIANT FAILS: relying only on Kubernetes `runAsNonRoot: true` at the pod spec level without ALSO building the image with a non-root default user creates a brittle dependency — anyone running the raw image directly (docker run, outside the cluster's admission control) still gets root, and some legitimate deployment paths bypass the pod security check.")

# =====================================================================
# DOMAIN: Security Architecture (~27) — cloud/container security config,
# network segmentation, IAM/zero-trust architecture, hardening baselines
# =====================================================================

add("Block public access to an S3 bucket at the account level", "CORE", "Security Architecture",
    "Enforce a hard control preventing any bucket from being made public.",
    ["aws s3api put-public-access-block --bucket app-data-prod --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
     "aws s3api get-public-access-block --bucket app-data-prod"],
    "WHY IT WORKS: the Public Access Block setting is enforced by S3 itself BEFORE evaluating bucket policies or ACLs, so even a future misconfigured policy granting `Principal: *` is overridden and cannot take effect while the block is enabled. WHY A VARIANT FAILS: relying only on reviewing bucket policies manually for `Principal: *` catches today's misconfiguration but not tomorrow's — a preventive account-level control stops the class of mistake permanently instead of relying on catching each instance after the fact.")

add("Write a Kubernetes NetworkPolicy for microsegmentation", "INTER", "Security Architecture",
    "Restrict a namespace to only allow traffic from an explicitly approved source.",
    ["cat <<'EOF' > netpol.yaml\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name: allow-frontend-only\n  namespace: backend\nspec:\n  podSelector: {}\n  policyTypes: [Ingress]\n  ingress:\n    - from:\n        - namespaceSelector:\n            matchLabels:\n              name: frontend\nEOF",
     "kubectl apply -f netpol.yaml",
     "kubectl get networkpolicy -n backend"],
    "WHY IT WORKS: an empty `podSelector: {}` applies the policy to every pod in the namespace, and by default once ANY NetworkPolicy selects a pod, all traffic not explicitly allowed is denied — implementing default-deny microsegmentation between namespaces, a core zero-trust network principle. WHY A VARIANT FAILS: assuming NetworkPolicy is enforced automatically on every cluster is wrong — it requires a CNI plugin that actually implements NetworkPolicy (Calico, Cilium, etc.); on a CNI without enforcement support (like the basic kubenet/flannel setups) these YAML objects are silently accepted but never enforced.")

add("Enforce Kubernetes Pod Security Standards at the namespace level", "INTER", "Security Architecture",
    "Block privileged/root containers from being scheduled in a namespace.",
    ["kubectl label namespace backend pod-security.kubernetes.io/enforce=restricted",
     "kubectl label namespace backend pod-security.kubernetes.io/warn=restricted",
     "kubectl apply -f privileged-pod.yaml  # expect rejection"],
    "WHY IT WORKS: the built-in Pod Security Admission controller evaluates pod specs against the 'restricted' profile (no privileged containers, no host namespaces, non-root, dropped capabilities) at admission time, rejecting non-compliant pods before they're ever scheduled. WHY A VARIANT FAILS: using the deprecated PodSecurityPolicy (removed in Kubernetes 1.25+) instead of Pod Security Admission means the cluster silently has NO pod security enforcement at all on modern versions — a common outdated-knowledge trap.")

add("Design a zero-trust segmentation boundary with an API gateway and mTLS mesh", "ADV", "Security Architecture",
    "Replace implicit network-perimeter trust with per-request identity verification.",
    ["# Service mesh (Istio) enforces mTLS cluster-wide:",
     "kubectl apply -f - <<'EOF'\napiVersion: security.istio.io/v1beta1\nkind: PeerAuthentication\nmetadata:\n  name: default\n  namespace: istio-system\nspec:\n  mtls:\n    mode: STRICT\nEOF",
     "istioctl authn tls-check svc-b.backend.svc.cluster.local"],
    "WHY IT WORKS: `STRICT` mTLS mode rejects any plaintext service-to-service connection cluster-wide, and combined with `AuthorizationPolicy` objects scoping WHICH identities may call WHICH services, this replaces 'anything inside the network perimeter is trusted' with 'every call must present a verified workload identity' — the architectural core of zero trust. WHY IT MATTERS: zero trust is a continuous verification architecture, not a single product — the exam expects candidates to combine strong workload identity (mTLS/SPIFFE), least-privilege authorization policy, and continuous monitoring together, not just 'turn on mTLS' as a complete answer.")

add("Baseline and remediate a host against CIS benchmarks with CIS-CAT", "INTER", "Security Architecture",
    "Score a server's configuration against an industry hardening standard.",
    ["./CIS-CAT.sh -a -i -b benchmarks/CIS_Ubuntu_Linux_22.04_LTS_Benchmark.xml -r reports/",
     "grep -i FAIL reports/CIS-CAT-report.html | head -20"],
    "WHY IT WORKS: CIS-CAT automates checking a live system's configuration against every control in a published CIS Benchmark (password policy, service hardening, filesystem permissions) and scores pass/fail per control, giving a repeatable, auditable baseline instead of a manual checklist walkthrough. WHY IT MATTERS: CIS Benchmarks map directly to compliance frameworks (NIST 800-53, PCI-DSS) referenced elsewhere in GRC audits, so a CIS-CAT score is often directly reusable as compliance evidence, not just an internal hardening metric.")

add("Run an OpenSCAP compliance scan against a hardening profile", "INTER", "Security Architecture",
    "Evaluate a RHEL host against the DISA STIG profile and generate a remediation script.",
    ["oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_stig --results results.xml --report report.html /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml",
     "oscap xccdf generate fix --profile xccdf_org.ssgproject.content_profile_stig --output remediate.sh results.xml"],
    "WHY IT WORKS: oscap evaluates a SCAP data stream containing hundreds of individual XCCDF rules against the live system state and produces a scored, auditable report per control ID; `generate fix` turns failed checks into an executable remediation script rather than requiring manual per-control fixes. WHY A VARIANT FAILS: blindly running the auto-generated `remediate.sh` in production without review can break legitimate functionality (e.g. disabling a protocol a business application still requires) — remediation scripts must be reviewed and tested in staging before being applied to production hosts.")

add("Assess AWS account security posture with Prowler", "INTER", "Security Architecture",
    "Run a broad automated security assessment across an AWS account.",
    ["prowler aws --severity critical,high --compliance cis_2.0_aws",
     "prowler aws -M json-ocsf -M html -o ./prowler-output"],
    "WHY IT WORKS: Prowler runs hundreds of checks across IAM, storage, logging, networking and encryption configuration using the AWS APIs directly, mapping findings to well-known frameworks like CIS AWS Foundations so results are immediately actionable and auditable. WHY IT MATTERS: automated posture assessment tools like Prowler/ScoutSuite are what make continuous compliance monitoring (a CAS-005 GRC expectation) feasible at cloud scale — manual console review of every account setting doesn't scale past a handful of accounts.")

add("Assess multi-cloud security posture with Scout Suite", "INTER", "Security Architecture",
    "Generate a consolidated security findings report across cloud accounts.",
    ["scout aws --profile prod-readonly",
     "scout azure --cli",
     "# open the generated scoutsuite-report/scoutsuite_results_*.js findings in the HTML report"],
    "WHY IT WORKS: Scout Suite normalizes findings across different cloud providers' native security models (IAM policies, storage ACLs, network security groups) into one consistent rule-based report, useful for organizations running true multi-cloud rather than a single provider. WHY IT MATTERS: architecture reviews in multi-cloud environments must account for provider-specific default behaviors — an S3 bucket and an Azure Blob container have different DEFAULT public-access postures, and a tool that normalizes both catches gaps a single-cloud-focused reviewer might miss.")

add("Design network segmentation with security groups and NACLs layered together", "CORE", "Security Architecture",
    "Apply defense-in-depth at both the instance and subnet level in a VPC.",
    ["aws ec2 authorize-security-group-ingress --group-id sg-0123 --protocol tcp --port 443 --cidr 10.0.0.0/16",
     "aws ec2 create-network-acl-entry --network-acl-id acl-0123 --rule-number 100 --protocol tcp --port-range From=443,To=443 --cidr-block 10.0.0.0/16 --rule-action allow --ingress",
     "aws ec2 describe-security-groups --group-ids sg-0123"],
    "WHY IT WORKS: security groups are stateful and instance-level (return traffic auto-allowed), while NACLs are stateless and subnet-level (return traffic needs its own explicit rule) — layering both means a single misconfigured security group doesn't expose the instance if the subnet-level NACL still blocks it, and vice versa. WHY A VARIANT FAILS: forgetting that NACLs are stateless and only adding an inbound allow rule (with no matching outbound allow for the ephemeral return ports) silently drops return traffic — a classic NACL troubleshooting trap that stateful security-group thinking doesn't prepare you for.")

add("Configure a Web Application Firewall rule set for OWASP Top 10 coverage", "CORE", "Security Architecture",
    "Deploy a managed WAF rule group in front of a public application.",
    ["aws wafv2 create-web-acl --name app-waf --scope REGIONAL --default-action Allow={} --rules file://managed-rules.json --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=appWaf",
     "aws wafv2 associate-web-acl --web-acl-arn <arn> --resource-arn <alb-arn>"],
    "WHY IT WORKS: a managed rule group (AWSManagedRulesCommonRuleSet) provides curated, continuously-updated signatures for injection, XSS and other OWASP Top 10 patterns without the team having to author and maintain every rule manually. WHY A VARIANT FAILS: deploying the WAF in `COUNT` mode indefinitely (logging matches without blocking) to 'avoid breaking things' provides zero actual protection — count mode is only a tuning phase and must be switched to `BLOCK` once false positives are resolved.")

add("Design a secrets-free CI/CD pipeline using workload identity federation", "ADV", "Security Architecture",
    "Eliminate long-lived cloud credentials stored as CI secrets entirely.",
    ["# GitHub Actions -> AWS via OIDC, no static keys stored anywhere:",
     "aws iam create-role --role-name gha-deploy-role --assume-role-policy-document file://trust-policy.json",
     "# trust-policy.json restricts sub claim to: repo:example-org/app:ref:refs/heads/main",
     "aws sts get-caller-identity  # inside the pipeline, confirms the federated identity in use"],
    "WHY IT WORKS: OIDC federation lets the CI runner assume a cloud role using a short-lived token tied to the pipeline's own identity (repo+branch claims), so there is no static AWS access key stored in CI secrets at all for an attacker to steal via a compromised dependency or malicious PR. WHY IT MATTERS: this directly closes the exact class of supply-chain attack where a compromised build step exfiltrates a long-lived CI secret — with federation, the credential is scoped, short-lived, and tied to a specific repo/branch/environment condition that a malicious PR from a fork typically cannot satisfy.")

add("Architect a hub-and-spoke cloud network with centralized egress inspection", "ADV", "Security Architecture",
    "Force all outbound traffic from spoke VPCs through a centralized inspection point.",
    ["aws ec2 create-transit-gateway --description \"central-hub-tgw\"",
     "aws ec2 create-transit-gateway-route-table --transit-gateway-id tgw-0123",
     "aws ec2 create-route --route-table-id rtb-spoke1 --destination-cidr-block 0.0.0.0/0 --transit-gateway-id tgw-0123"],
    "WHY IT WORKS: routing every spoke VPC's default route through a Transit Gateway to a shared inspection VPC (running a firewall/IDS appliance) centralizes egress filtering and logging so security policy is enforced and audited in ONE place rather than duplicated (and inevitably drifting) across every spoke account. WHY IT MATTERS: this hub-and-spoke pattern is the standard CAS-005 answer for 'how do you enforce consistent egress security policy across dozens of cloud accounts' — per-account point solutions don't scale and create policy drift.")

add("Harden an AWS IAM policy from wildcard actions to explicit least privilege", "CORE", "Security Architecture",
    "Replace an overly broad policy statement with tightly scoped permissions.",
    ["cat <<'EOF' > policy-bad.json\n{\"Effect\":\"Allow\",\"Action\":\"s3:*\",\"Resource\":\"*\"}\nEOF",
     "cat <<'EOF' > policy-good.json\n{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::app-data-prod/*\"}\nEOF",
     "aws iam put-role-policy --role-name AppRole --policy-name s3-scoped --policy-document file://policy-good.json"],
    "WHY IT WORKS: scoping both `Action` (specific API calls, not `s3:*`) and `Resource` (a specific bucket ARN, not `*`) means a compromised role's blast radius is limited to exactly what the application needs, instead of every S3 action on every bucket in the account. WHY A VARIANT FAILS: scoping `Resource` tightly but leaving `Action: s3:*` still grants dangerous actions like `s3:DeleteBucket` or `s3:PutBucketPolicy` on that one bucket — both dimensions must be narrowed together, not just one.")

add("Design an SDN-based microsegmentation policy using Cilium network policies", "ADV", "Security Architecture",
    "Enforce L7-aware (not just L3/L4) traffic rules between services using eBPF.",
    ["cat <<'EOF' > cnp.yaml\napiVersion: cilium.io/v2\nkind: CiliumNetworkPolicy\nmetadata:\n  name: api-l7-restrict\nspec:\n  endpointSelector:\n    matchLabels: {app: api}\n  ingress:\n    - fromEndpoints:\n        - matchLabels: {app: frontend}\n      toPorts:\n        - ports: [{port: \"8080\", protocol: TCP}]\n          rules:\n            http:\n              - method: \"GET\"\n                path: \"/api/v1/.*\"\nEOF",
     "kubectl apply -f cnp.yaml"],
    "WHY IT WORKS: Cilium's eBPF-based dataplane can enforce policy at L7 (specific HTTP methods/paths), not just IP/port like standard Kubernetes NetworkPolicy, so 'frontend may call GET /api/v1/* on api but nothing else' is enforced directly in the kernel dataplane rather than trusted to application code. WHY IT MATTERS: L7-aware microsegmentation catches lateral movement attempts that pass L3/L4 checks (correct IP/port) but represent clearly abnormal application behavior (e.g. an unexpected DELETE call), which coarse network policy alone cannot distinguish.")

add("Evaluate a Secure Access Service Edge (SASE) architecture for remote access", "INTER", "Security Architecture",
    "Replace a traditional VPN concentrator with identity-aware cloud-delivered access.",
    ["# conceptual CLI check of a ZTNA-connected client posture status:",
     "zscaler-cli status --show-posture",
     "# verify a per-app access policy instead of full-network VPN access",
     "zscaler-cli policy show --app internal-crm"],
    "WHY IT WORKS: SASE/ZTNA architectures broker access per-application after continuous device posture and identity checks, rather than granting a VPN client a routable IP onto the full internal network — so a compromised endpoint can reach only the specific app it was authorized for, not the entire flat network segment a traditional VPN exposes. WHY IT MATTERS: CAS-005 explicitly tests this VPN-vs-ZTNA tradeoff — full-tunnel VPN access is a common root cause of large lateral-movement breaches specifically because of the flat network access it grants once ANY credential is compromised.")

add("Design an API gateway rate-limiting and authentication layer", "CORE", "Security Architecture",
    "Protect a backend API from abuse and enforce token validation at the edge.",
    ["kubectl apply -f - <<'EOF'\napiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: api\n  annotations:\n    nginx.ingress.kubernetes.io/limit-rps: \"20\"\n    nginx.ingress.kubernetes.io/auth-url: \"http://auth-svc.default.svc.cluster.local/validate\"\nspec:\n  rules:\n    - host: api.example.com\nEOF",
     "kubectl apply -f api-ingress.yaml"],
    "WHY IT WORKS: pushing rate-limiting and token validation to the API gateway/ingress layer means every backend service inherits the protection uniformly without each team re-implementing auth checks independently, reducing the chance any one service accidentally exposes an unauthenticated path. WHY A VARIANT FAILS: implementing rate limiting only at the application layer (in each microservice's own code) rather than the gateway means a single unprotected new service added later has zero protection until a developer remembers to add it — centralizing the control at the edge removes that dependency on individual diligence.")

add("Configure envelope encryption for application-layer data protection", "ADV", "Security Architecture",
    "Layer a data-encryption-key/key-encryption-key model instead of one master key encrypting everything directly.",
    ["aws kms generate-data-key --key-id alias/app-master-key --key-spec AES_256",
     "# use the returned Plaintext DEK to encrypt the actual record locally, then store only the CiphertextBlob DEK alongside it",
     "aws kms decrypt --ciphertext-blob fileb://encrypted-dek.bin"],
    "WHY IT WORKS: envelope encryption uses the KMS master key only to wrap/unwrap small per-record data keys rather than encrypting bulk data directly through the KMS API (which has request-size and throughput limits), while still allowing centralized key rotation and access control over the master key. WHY IT MATTERS: rotating the KMS master key under an envelope-encryption design does NOT require re-encrypting every existing record — only future DEK-wrap operations use the new master key version, whereas direct-encryption designs would require a full data re-encryption pass on rotation.")

add("Implement immutable infrastructure to reduce configuration drift risk", "INTER", "Security Architecture",
    "Replace in-place server patching with golden-image redeployment.",
    ["packer build -var 'source_ami=ami-0abcd1234' webserver.pkr.hcl",
     "aws autoscaling start-instance-refresh --auto-scaling-group-name web-asg --preferences MinHealthyPercentage=90"],
    "WHY IT WORKS: building a new hardened AMI with Packer and rolling it out via an instance refresh means every running instance is provably identical to the tested golden image, eliminating the 'it was patched by hand and nobody documented what changed' drift that accumulates on long-lived, in-place-patched servers. WHY IT MATTERS: immutable infrastructure also simplifies incident response — if an instance is suspected compromised, the response is to terminate and replace it from the known-good image rather than trying to forensically clean and trust an in-place-modified host.")

# =====================================================================
# DOMAIN: Security Operations (~22) — threat hunting/detection, SIEM,
# IDS/IPS rules, forensics, vuln scanning, incident response tooling
# =====================================================================

add("Run a targeted Nmap scan to enumerate live services", "CORE", "Security Operations",
    "Discover open ports and fingerprint running services on a target subnet.",
    ["nmap -sV -sC -p- 10.0.1.0/24 -oA subnet_scan",
     "nmap --script vuln 10.0.1.15"],
    "WHY IT WORKS: `-sV` fingerprints service versions via banner/behavior analysis and `-sC` runs default safe NSE scripts, together revealing both what's listening and likely software versions to cross-reference against known CVEs; `-oA` saves normal/XML/grepable output for later diffing or ingestion. WHY A VARIANT FAILS: running an aggressive `--script vuln` sweep against production systems without a change window or authorization can trigger IDS alerts, crash fragile services, or violate scope-of-engagement rules — authorized scanning windows and rules of engagement are a hard CAS-005 requirement, not just courtesy.")

add("Write a Sigma rule to detect suspicious PowerShell execution", "INTER", "Security Operations",
    "Create a SIEM-agnostic detection rule for encoded/obfuscated PowerShell commands.",
    ["cat <<'EOF' > sigma_encoded_ps.yml\ntitle: Suspicious Encoded PowerShell Command\nstatus: stable\nlogsource:\n  category: process_creation\n  product: windows\ndetection:\n  selection:\n    Image|endswith: '\\powershell.exe'\n    CommandLine|contains:\n      - '-EncodedCommand'\n      - '-enc '\n      - 'FromBase64String'\n  condition: selection\nlevel: high\nEOF",
     "sigmac -t splunk sigma_encoded_ps.yml   # convert to a target SIEM query language"],
    "WHY IT WORKS: Sigma is a vendor-neutral YAML detection format that a converter (sigmac / pySigma backends) translates into the query syntax of Splunk, Elastic, Sentinel, etc., so one rule authored once can be deployed across whatever SIEM an organization runs. WHY A VARIANT FAILS: matching only the literal string `-EncodedCommand` without also covering common obfuscation (partial flags like `-enc`, case variation, or string reversal tricks attackers use to evade literal matches) leaves easily-bypassed detection coverage — real rules need broader pattern coverage and behavioral context, not one exact string.")

add("Write a YARA rule to identify a malware family by static signature", "INTER", "Security Operations",
    "Detect a known malicious binary pattern across a filesystem or memory dump.",
    ["cat <<'EOF' > loader_variant.yar\nrule Suspicious_Loader_Variant\n{\n    meta:\n        author = \"SOC\"\n        description = \"Detects known loader strings and PE section anomaly\"\n    strings:\n        $s1 = \"cmd.exe /c powershell -nop -w hidden\" ascii\n        $s2 = { 4D 5A 90 00 03 00 00 00 }\n    condition:\n        $s1 and $s2 at 0\n}\nEOF",
     "yara -r loader_variant.yar /mnt/evidence/"],
    "WHY IT WORKS: YARA matches combinations of string and byte-pattern conditions (here, a suspicious command-line string plus the MZ header at file offset 0) across large sets of files/memory far faster than manual inspection, and the boolean `condition` lets multiple weak indicators combine into one higher-confidence match. WHY IT MATTERS: pure string-based rules are brittle against trivial repacking/obfuscation — mature YARA rules layer in structural conditions (PE section entropy, byte patterns at fixed offsets) specifically so cosmetic changes to a malware sample don't automatically evade detection.")

add("Write a Suricata rule to detect a specific C2 beacon pattern", "ADV", "Security Operations",
    "Create a network-based IDS signature for outbound command-and-control traffic.",
    ["cat <<'EOF' >> local.rules\nalert tls $HOME_NET any -> $EXTERNAL_NET any (msg:\"Possible C2 JA3 Match\"; ja3.hash; content:\"e7d705a3286e19ea42f587b344ee6865\"; sid:1000201; rev:1;)\nEOF",
     "suricata -T -c /etc/suricata/suricata.yaml -v",
     "systemctl reload suricata"],
    "WHY IT WORKS: matching on a JA3 TLS client fingerprint hash detects the specific TLS library/config combination a malware family's C2 stager uses, working even though the traffic itself is encrypted and cannot be content-inspected. WHY A VARIANT FAILS: writing the same detection as a plain `content` match against decrypted payload bytes fails entirely against TLS-encrypted C2 traffic — JA3/JA3S and certificate/SNI-based indicators are what remain visible on the wire when the actual payload is opaque.")

add("Query endpoint state at scale with osquery", "INTER", "Security Operations",
    "Hunt for a specific indicator of compromise across a fleet using SQL-style queries.",
    ["osqueryi \"SELECT pid, name, path, cmdline FROM processes WHERE name = 'powershell.exe';\"",
     "osqueryi \"SELECT address, hostname FROM etc_hosts WHERE address = '10.6.6.6';\"",
     "osqueryi \"SELECT * FROM listening_ports WHERE port = 4444;\""],
    "WHY IT WORKS: osquery exposes OS state (processes, sockets, loaded modules, scheduled tasks, hosts file entries) as SQL-queryable virtual tables, letting a hunter run the SAME query across an entire fleet via a management layer (Fleet/osquery manager) instead of manually inspecting each host. WHY IT MATTERS: a port 4444 listener (a classic default Metasploit handler port) or an unexpected /etc/hosts DNS-sinkhole-bypass entry are exactly the kind of subtle IOC that fleet-wide osquery sweeps catch far faster than host-by-host manual triage during an active hunt.")

add("Parse CloudTrail logs with jq to find anomalous API activity", "CORE", "Security Operations",
    "Extract and filter suspicious IAM activity from raw AWS audit logs.",
    ["cat cloudtrail.json | jq '.Records[] | select(.eventName==\"ConsoleLogin\" and .responseElements.ConsoleLogin==\"Failure\")'",
     "cat cloudtrail.json | jq -r '.Records[] | select(.eventName==\"CreateAccessKey\") | [.eventTime,.userIdentity.arn] | @tsv'"],
    "WHY IT WORKS: `jq` filters and reshapes CloudTrail's deeply nested JSON directly on the command line, letting an analyst pull exactly the field combinations relevant to an investigation (failed console logins, new access-key creation events) without ingesting the whole log into a SIEM first for a quick triage pass. WHY A VARIANT FAILS: grepping the raw JSON for a plain string like 'Failure' instead of using structured field selection can match unrelated fields (error messages, resource names) elsewhere in the same record, producing false positives that a properly-scoped jq `select()` on the exact field avoids.")

add("Investigate a compromised host with auditd file-integrity rules", "INTER", "Security Operations",
    "Detect unauthorized modification of a critical system binary.",
    ["auditctl -w /usr/bin/sudo -p wa -k sudo_binary_watch",
     "ausearch -k sudo_binary_watch -i",
     "aureport --file --summary"],
    "WHY IT WORKS: watching a sensitive binary for write(w)/attribute(a) events and tagging matches with a searchable key (`-k`) lets `ausearch -i` (interpreted output) show exactly which process and user modified it and when — direct evidence of tampering versus a routine package update. WHY IT MATTERS: correlating the audit event's timestamp against the package manager's own update log (dnf/apt history) is what separates 'this was a legitimate patch' from 'this was an attacker replacing a system binary with a trojanized version' — the audit trail alone doesn't prove intent, only that a change occurred.")

add("Hunt through Zeek connection logs for beaconing behavior", "ADV", "Security Operations",
    "Identify a host making suspiciously regular outbound connections consistent with C2 beaconing.",
    ["zcat conn.log.gz | zeek-cut ts id.orig_h id.resp_h id.resp_p duration | grep '203.0.113'",
     "cat conn.log | zeek-cut ts id.orig_h id.resp_h | awk '{print $2,$3}' | sort | uniq -c | sort -rn | head"],
    "WHY IT WORKS: Zeek's conn.log records every network flow's metadata (not full packet capture), so `zeek-cut` extracting timestamp/host pairs and counting occurrences quickly surfaces a host talking to the same external IP with unusually high, regular frequency — a classic beaconing signature. WHY IT MATTERS: beacon intervals are often intentionally jittered by malware to evade simple periodicity detection — mature hunting adds statistical analysis of the delta between connection timestamps (looking for a tight distribution around a jittered mean) rather than relying on exact interval matching alone.")

add("Acquire and triage a memory image with Volatility for incident response", "ADV", "Security Operations",
    "Extract running processes and network connections from a memory dump of a compromised host.",
    ["vol.py -f memory.dmp windows.pslist",
     "vol.py -f memory.dmp windows.netscan",
     "vol.py -f memory.dmp windows.malfind --pid 4212"],
    "WHY IT WORKS: `pslist` reconstructs the process tree directly from kernel memory structures (harder for malware to hide from than live `tasklist`, since it doesn't rely on the compromised OS's own APIs), `netscan` recovers network connection artifacts even after the socket has closed, and `malfind` scans for characteristics of injected/unmapped executable code in a process's memory. WHY A VARIANT FAILS: running live tools like `tasklist`/`netstat` on the still-running compromised host instead of acquiring a memory image first risks the malware (or the responder's own actions) altering volatile evidence before it's captured — memory acquisition should happen before extensive live triage commands are run.")

add("Compute and check a file hash against threat-intel IOC feeds", "CORE", "Security Operations",
    "Determine whether a suspicious file matches a known-malicious hash.",
    ["sha256sum suspicious.exe",
     "curl -s https://www.virustotal.com/api/v3/files/$(sha256sum suspicious.exe | cut -d' ' -f1) -H \"x-apikey: $VT_API_KEY\" | jq '.data.attributes.last_analysis_stats'"],
    "WHY IT WORKS: hashing the file locally and querying a threat-intel platform by hash (rather than uploading the file itself) checks a known-malicious database without exposing potentially sensitive file contents externally, and returns an aggregated multi-engine verdict. WHY A VARIANT FAILS: relying solely on hash-based lookup gives a false sense of coverage against a targeted attacker who trivially modifies a single byte to change the hash entirely (defeating exact-hash matching) — hash IOCs catch only already-known, unmodified samples and must be paired with behavioral/YARA-based detection for anything novel.")

add("Pull threat intelligence indicators from a TAXII 2.1 server", "INTER", "Security Operations",
    "Retrieve current STIX indicator objects from a shared threat-intel feed.",
    ["curl -s -H \"Accept: application/taxii+json;version=2.1\" https://taxii.example.com/api/collections/ | jq .",
     "curl -s -H \"Accept: application/taxii+json;version=2.1\" https://taxii.example.com/api/collections/indicators/objects/ | jq '.objects[] | select(.type==\"indicator\")'"],
    "WHY IT WORKS: TAXII is the transport protocol for exchanging STIX-formatted threat intelligence objects (indicators, malware, attack patterns) between organizations/feeds in a standardized, machine-consumable way, so a SOC can automatically ingest fresh IOCs into detection tooling rather than manually reading vendor blog posts. WHY IT MATTERS: STIX indicators carry structured pattern expressions (e.g. `[file:hashes.'SHA-256' = '...']`) that detection tooling can consume directly, which is what makes automated feed ingestion actually actionable versus just informational reading material.")

add("Triage a phishing email header for spoofing indicators", "CORE", "Security Operations",
    "Determine whether SPF/DKIM/DMARC actually validated for a suspicious message.",
    ["grep -i 'Authentication-Results' phishing.eml",
     "dig txt _dmarc.suspicious-sender.com +short",
     "dig txt suspicious-sender.com +short | grep spf"],
    "WHY IT WORKS: the `Authentication-Results` header records what the RECEIVING mail server itself concluded about SPF/DKIM/DMARC at delivery time, which is more trustworthy than re-checking DNS after the fact (since the sending domain's records could change later); checking the domain's DMARC policy shows whether it even publishes an enforcement policy (`p=reject`) that should have blocked spoofed mail. WHY A VARIANT FAILS: trusting the visible 'From' display name alone is meaningless — attackers routinely spoof the display name while the actual envelope-from/return-path domain is unrelated; only the authentication results and header trace path reveal genuine spoofing.")

add("Build a correlation search for impossible-travel logins in a SIEM", "ADV", "Security Operations",
    "Detect a credential likely being used from two geographically implausible locations in a short window.",
    ["index=auth sourcetype=okta:log | eval city=coalesce(client.geographicalContext.city) | stats earliest(_time) as t1, latest(_time) as t2, values(city) as cities, values(client.ipAddress) as ips by actor.alternateId | where mvcount(cities) > 1"],
    "WHY IT WORKS: grouping authentication events by user identity and comparing geolocation/IP across the SAME short time window flags logins that would require physically impossible travel speed between locations, a strong signal of credential sharing or compromise rather than normal travel. WHY A VARIANT FAILS: alerting on ANY two different cities for a user without a time/distance-implied-velocity threshold produces constant false positives for legitimate VPN/mobile-network IP changes — mature impossible-travel logic calculates plausible travel speed between the two points, not just 'different city' alone.")

add("Contain a compromised endpoint via EDR isolation", "INTER", "Security Operations",
    "Cut network access to a host under active investigation while preserving forensic state.",
    ["# example EDR CLI (CrowdStrike Falcon):",
     "falconctl -g --aid",
     "cs-isolate --host-id 4a1b2c3d --reason 'active IOC match, awaiting forensic triage'"],
    "WHY IT WORKS: network isolation via the EDR agent keeps the host running (preserving volatile memory/process state for later forensic acquisition) while blocking all network I/O except a management channel back to the EDR console — stopping lateral movement/exfiltration without destroying evidence the way a hard power-off would. WHY A VARIANT FAILS: an analyst's first instinct to just power off or unplug the machine destroys volatile memory contents (running processes, injected code, network connections) that a proper memory acquisition would have captured — isolate first, image second, power off last if at all.")

add("Detect lateral movement via unusual RDP/SMB session graphs", "ADV", "Security Operations",
    "Identify a compromised account hopping between hosts it doesn't normally access.",
    ["index=win_security EventCode=4624 LogonType=3 OR LogonType=10 | stats dc(dest) as unique_hosts values(dest) as hosts by user | where unique_hosts > 10",
     "# cross-reference with EventCode=4648 (explicit credential use) for the same account/time window"],
    "WHY IT WORKS: EventCode 4624 with LogonType 3 (network) or 10 (RDP) tracked per account reveals a user authenticating to an abnormally large number of distinct hosts in a short window — a strong lateral-movement signal versus a normal user's typically narrow, stable set of accessed systems. WHY IT MATTERS: pairing this with EventCode 4648 (explicit credential logon) helps distinguish an attacker using pass-the-hash/harvested credentials (which often shows up as 4648) from a legitimate admin's normal broad access pattern, since raw host-count alone can also flag legitimate sysadmins.")

add("Extract IOCs from a phishing document with static analysis tools", "INTER", "Security Operations",
    "Pull embedded macros and URLs from a malicious Office document without executing it.",
    ["olevba suspicious_invoice.doc",
     "oledump.py -s 5 -v suspicious_invoice.doc",
     "strings suspicious_invoice.doc | grep -Ei 'https?://'"],
    "WHY IT WORKS: `olevba` statically parses the OLE/VBA structure to extract and even partially deobfuscate macro code without ever running it, revealing dropped URLs, shell commands, and obfuscation techniques safely. WHY A VARIANT FAILS: opening the document in Office with macros enabled 'just to see what it does' on an analyst workstation (rather than an isolated sandbox/VM) risks actually executing the malicious payload against a real environment — static analysis must always precede any dynamic detonation, and detonation itself belongs only in an isolated sandbox.")

add("Run a vulnerability scan and prioritize findings by exploitability", "CORE", "Security Operations",
    "Scan a subnet for known vulnerabilities and triage which to remediate first.",
    ["nmap --script vulners -sV 10.0.2.0/24 -oX vuln_scan.xml",
     "nmap -sV --script vulners 10.0.2.15 | grep -i CVE"],
    "WHY IT WORKS: the `vulners` NSE script cross-references detected service versions against a CVE database directly during the scan, giving an immediate first-pass severity/CVSS view without a separate manual lookup step per service. WHY A VARIANT FAILS: prioritizing remediation purely by CVSS base score without considering whether a public exploit exists or the asset's actual exposure (internet-facing vs. isolated internal segment) wastes limited remediation cycles on high-CVSS-but-low-real-risk findings while leaving lower-scored, actively-exploited, internet-facing issues unpatched — exploitability and exposure context must weight prioritization, not CVSS alone.")

add("Investigate a suspicious cron/scheduled task persistence mechanism", "INTER", "Security Operations",
    "Identify how an attacker maintains access after initial compromise on a Linux host.",
    ["for u in $(cut -f1 -d: /etc/passwd); do crontab -u $u -l 2>/dev/null; done",
     "cat /etc/cron.d/* /etc/crontab 2>/dev/null",
     "systemctl list-timers --all",
     "find / -xdev -newer /etc/hostname -type f -name '*.sh' 2>/dev/null"],
    "WHY IT WORKS: attackers frequently establish persistence via cron/systemd timers because they blend in with legitimate scheduled maintenance jobs; enumerating EVERY user's crontab (not just root's) plus systemd timers plus recently-modified shell scripts covers the common Linux persistence surface comprehensively. WHY A VARIANT FAILS: checking only `crontab -l` as the current user (or only root's crontab) misses persistence planted under a compromised low-privilege service account's own crontab, which still runs with that account's privileges and can be a foothold even without root.")

add("Build a detection rule for impossible process-parent relationships", "ADV", "Security Operations",
    "Catch a common living-off-the-land technique where Office spawns a shell.",
    ["cat <<'EOF' > sigma_office_spawns_shell.yml\ntitle: Office Application Spawning Command Shell\nlogsource:\n  category: process_creation\n  product: windows\ndetection:\n  selection:\n    ParentImage|endswith:\n      - '\\winword.exe'\n      - '\\excel.exe'\n    Image|endswith:\n      - '\\cmd.exe'\n      - '\\powershell.exe'\n  condition: selection\nlevel: high\nEOF"],
    "WHY IT WORKS: Office applications legitimately spawning a command interpreter is extremely rare in normal business use and is a well-known signature of a malicious macro executing its payload, so a parent/child process-relationship rule catches this technique regardless of exactly what the macro's payload does next. WHY IT MATTERS: this is a textbook 'living off the land' detection — the malicious ACTION is a normal, signed OS binary (cmd.exe/powershell.exe) that traditional signature-based antivirus won't flag; only behavioral/parent-child context reveals the anomaly.")

add("Perform a live response triage script on a suspected-compromised Linux server", "INTER", "Security Operations",
    "Rapidly collect volatile artifacts before deciding whether to isolate or image the host.",
    ["w; last -a | head -20",
     "ss -tulpn",
     "ps auxf",
     "ls -la /tmp /var/tmp /dev/shm",
     "find / -perm -4000 -type f 2>/dev/null   # unexpected SUID binaries"],
    "WHY IT WORKS: this sequence captures who's logged in and from where, active network listeners, the full process tree, world-writable temp directories commonly used to stage payloads, and unexpected SUID binaries (a common privilege-escalation persistence marker) — a fast volatile-first triage before anything changes. WHY A VARIANT FAILS: running a full disk `find /` search or heavy forensic imaging FIRST, before capturing this fast-changing volatile state, risks losing exactly the transient network connections and process list that a slower, disk-focused investigation would miss entirely once the attacker's live session ends.")

add("Search Suricata EVE JSON alerts with jq for a specific signature", "CORE", "Security Operations",
    "Filter high-volume IDS alert logs down to a single investigation's relevant events.",
    ["cat eve.json | jq -c 'select(.event_type==\"alert\") | select(.alert.signature | test(\"C2\"; \"i\"))'",
     "cat eve.json | jq -r 'select(.event_type==\"alert\") | [.timestamp,.src_ip,.dest_ip,.alert.signature] | @tsv' | sort | uniq -c | sort -rn | head"],
    "WHY IT WORKS: EVE JSON is Suricata's structured event format, so `jq` can filter precisely by event type and signature text without brittle text parsing, and counting unique src/dest/signature tuples quickly surfaces the noisiest or most repeated alert pattern worth investigating first. WHY IT MATTERS: high-volume IDS deployments generate far more alerts than a SOC can individually triage — structured querying and aggregation (not reading a scrolling alert feed) is what makes triage at scale feasible.")

# =====================================================================
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


add("Generate a code-signing certificate request for software publishing", "CORE", "Security Engineering",
    "Create the CSR needed to obtain a code-signing certificate from a public CA.",
    ["openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out codesign.key",
     "openssl req -new -key codesign.key -out codesign.csr -subj \"/O=Example Corp/CN=Example Corp Code Signing\"",
     "openssl req -in codesign.csr -noout -text | head -15"],
    "WHY IT WORKS: a code-signing CSR follows the same PKCS#10 structure as a TLS CSR but is submitted to a CA offering code-signing certificate products, which chain to a different trusted root store (OS/browser code-signing trust) than web-server TLS certs use. WHY A VARIANT FAILS: reusing a TLS server certificate to sign software binaries instead of obtaining a proper code-signing certificate fails validation on most platforms — code-signing requires specific extended key usage (codeSigning EKU) that a plain server-auth certificate does not carry.")

add("Check listening services and firewall state before a security baseline review", "CORE", "Security Architecture",
    "Confirm only intended ports are exposed on a newly provisioned host.",
    ["ss -tulpn",
     "sudo firewall-cmd --list-all",
     "sudo nft list ruleset | head -30"],
    "WHY IT WORKS: comparing what's actually listening (`ss -tulpn`) against what the firewall claims to allow catches drift where a service was installed and started but the firewall was never updated (or vice versa) — the two must be checked together, not assumed consistent. WHY A VARIANT FAILS: reviewing only the firewall configuration file without checking actual listening sockets misses services bound to loopback-only or unexpectedly bound to all interfaces despite a restrictive firewall rule set, which still matters for local privilege-escalation paths.")

add("Validate DNSSEC is properly signed for a security-critical domain", "CORE", "Security Architecture",
    "Confirm DNS responses for a domain can be cryptographically validated, preventing cache-poisoning/spoofing.",
    ["dig +dnssec example.com A",
     "delv example.com A",
     "dig DNSKEY example.com +short"],
    "WHY IT WORKS: `delv` performs full DNSSEC validation locally (unlike plain `dig`, which just shows whether RRSIG records are present without verifying them), confirming the chain of trust from the root down to the domain's signed records is intact. WHY A VARIANT FAILS: seeing an RRSIG record present in a `dig +dnssec` response is not proof of a VALID signature chain — an expired signature or a broken chain of trust higher up still shows RRSIG records present while `delv` would report a validation failure that plain dig output does not surface.")

add("Enumerate CVE details for a specific software version with a CPE lookup", "CORE", "Governance, Risk & Compliance",
    "Determine whether an installed software version is affected by known vulnerabilities.",
    ["curl -s \"https://services.nvd.nist.gov/rest/json/cpes/2.0?cpeMatchString=cpe:2.3:a:openssl:openssl:3.0.7\" | jq '.products[].cpe.cpeName'",
     "curl -s \"https://services.nvd.nist.gov/rest/json/cves/2.0?cpeName=cpe:2.3:a:openssl:openssl:3.0.7\" | jq '.vulnerabilities[].cve.id'"],
    "WHY IT WORKS: CPE (Common Platform Enumeration) provides a standardized identifier for exact software product/version combinations, so querying NVD by CPE name returns precisely the CVEs affecting THAT version rather than every CVE ever filed against the product name broadly. WHY A VARIANT FAILS: searching NVD by free-text product name alone returns CVEs for ALL versions of that software ever affected, requiring manual filtering to determine relevance to the specific installed version — CPE-based queries do that version filtering automatically.")

add("Run a quick port and banner grab to validate a hardening change took effect", "CORE", "Security Operations",
    "Confirm a service was actually reconfigured after a remediation ticket was closed.",
    ["nc -zv app01.internal 23",
     "nmap -sV -p 22,80,443 app01.internal",
     "curl -sI http://app01.internal | grep -i server"],
    "WHY IT WORKS: re-scanning after a remediation change is closed (e.g. disabling telnet) directly verifies the fix took effect on the live system, rather than trusting the ticket status alone; a version/banner grab also catches cases where a service was restarted with the OLD config still loaded. WHY A VARIANT FAILS: closing a remediation ticket based solely on the engineer's statement that the config file was edited, without a follow-up scan confirming the service was actually reloaded/restarted with that config, is a common way stale vulnerable services remain exposed despite looking 'remediated' on paper.")

add("Verify multi-factor authentication enrollment coverage across all accounts", "CORE", "Governance, Risk & Compliance",
    "Identify accounts that are not yet enrolled in MFA before enforcing a hard requirement.",
    ["aws iam generate-credential-report",
     "aws iam get-credential-report --query 'Content' --output text | base64 -d | awk -F',' '{print $1,$8}' | grep -v mfa_active,true"],
    "WHY IT WORKS: the IAM credential report gives a point-in-time, auditable snapshot of every user's MFA enrollment status across the whole account in one query, which is what turns 'we require MFA' from a policy statement into a measurable, enforceable compliance metric. WHY A VARIANT FAILS: enforcing an MFA requirement via a conditional IAM policy without first running a coverage check risks immediately locking out legitimate users who were never enrolled — the audit step must precede a hard enforcement rollout so exceptions can be resolved first.")

print("total samples:", len(S))
assert len(S) == 100, f"expected 100 samples, got {len(S)}"
assert all(s.get("explain") for s in S), "missing explanation"
print("explanations:", sum(1 for s in S if s.get("explain")))

js = "window.SECX_SAMPLES = " + json.dumps(S, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
with open("/home/user/workspace/certprep_single/secx_samples.js", "w", encoding="utf-8") as f:
    f.write(js)
print("wrote secx_samples.js", len(js), "bytes")

# level / category breakdown for reporting
from collections import Counter
lvl_counts = Counter(s["level"] for s in S)
cat_counts = Counter(s["cat"] for s in S)
print("levels:", dict(lvl_counts))
print("categories:", dict(cat_counts))
