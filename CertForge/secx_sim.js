  // ============================================================
  //  SecurityX Tooling Console  (CompTIA SecurityX CAS-005 grammar)
  //  Rule-based, stateful-ish. Emits authentic tool output PLUS
  //  plain-English diagnostics (cls:'diag').
  //
  //  NOTE: This is a security-tooling command-grammar simulator, not
  //  a live host. SecurityX is an architect/engineer exam that spans
  //  many tools rather than one OS, so this console validates the
  //  invocation shape and common flags of the expert security CLI
  //  (openssl, gpg, ssh-keygen, nmap, yara, sigma, oscap, trivy,
  //  syft, cosign, kubectl, jq, dig, curl, auditctl ...) and renders
  //  representative output. It does not perform real crypto, scans,
  //  or network I/O. Interface parity with IOSDevice / LinuxShell:
  //  .prompt() -> string and .exec(line) -> [{t, cls}] where cls in
  //  out|err|info|diag.
  // ============================================================
  function SecXConsole(hostname){
    this.hostname = hostname || 'secx';
    this.user = 'analyst';
    this.cwd = '~';
    this.lastStatus = 0;
    // lightweight virtual artifacts so multi-step flows feel stateful
    this.files = {
      'server.key': false, 'server.csr': false, 'server.crt': false,
      'ca.crt': true, 'id_ed25519': false, 'id_ed25519.pub': false,
      'sbom.json': false, 'rule.yar': false, 'sigma.yml': false
    };
  }

  // ---------- helpers ----------
  function sout(t){return {t:t,cls:'out'};}
  function serr(t){return {t:t,cls:'err'};}
  function sinfo(t){return {t:t,cls:'info'};}
  function sdiag(t){return {t:t,cls:'diag'};}   // plain-English why/how-to-fix
  function stoks(line){ return line.trim().split(/\s+/).filter(Boolean); }
  function has(a, flag){ return a.indexOf(flag) !== -1; }
  function valOf(a, flag){ var i=a.indexOf(flag); return (i!==-1 && i+1<a.length) ? a[i+1] : null; }

  SecXConsole.prototype.prompt = function(){
    return this.user+'@'+this.hostname+':'+this.cwd+'$';
  };

  SecXConsole.prototype.exec = function(rawLine){
    var line = (rawLine==null?'':(''+rawLine)).replace(/\r/g,'');
    var trimmed = line.trim();
    if(trimmed===''){ return []; }

    // strip sudo (all these tools may be run with elevation; not modelled)
    trimmed = trimmed.replace(/^sudo\s+(-\S+\s+)*/, '');

    // strip a leading VAR=value assignment prefix
    trimmed = trimmed.replace(/^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+/, '');

    // handle simple pipelines/redirects: validate the FIRST command, note the rest
    var piped = /[|]/.test(trimmed);
    var firstSeg = trimmed.split('|')[0].trim().replace(/\s*[<>]{1,2}\s*\S+\s*$/, '').trim();

    var t = stoks(firstSeg);
    if(t.length===0){ return []; }
    var cmd = t[0];
    var a = t.slice(1);

    var res;
    try { res = this.run(cmd, a, firstSeg, trimmed, piped); }
    catch(e){ res = [ serr('error: '+(e&&e.message||'internal')) ]; }
    return res;
  };

  SecXConsole.prototype.notFound = function(cmd){
    this.lastStatus = 127;
    return [ serr('bash: '+cmd+': command not found'),
             sdiag('\u21b3 This SecurityX console recognises expert security tooling (openssl, gpg, ssh-keygen, nmap, yara, sigma, oscap, trivy, syft, cosign, kubectl, jq, dig, curl, auditctl, semgrep, gitleaks, prowler). Check spelling, or that the tool is installed and on $PATH.') ];
  };

  SecXConsole.prototype.run = function(cmd, a, seg, full, piped){
    this.lastStatus = 0;
    switch(cmd){

    // ---------------- shell basics ----------------
    case 'help': case '?':
      return [ sinfo('SecurityX tooling console. Try tool families:'),
        sout('  crypto/PKI : openssl, gpg, ssh-keygen, cosign, step'),
        sout('  scanning   : nmap, oscap, trivy, grype, prowler, scout, nikto'),
        sout('  supply-chn : syft (SBOM), gitleaks, semgrep, checkov, tfsec'),
        sout('  detection  : yara, sigma, suricata, snort, osquery, zeek'),
        sout('  intel/IR   : jq, curl (STIX/TAXII, NVD), volatility, sha256sum, auditctl'),
        sout('  k8s/cloud  : kubectl, aws, az'),
        sinfo('Every rejected command shows the authentic error AND a plain-English fix.') ];
    case 'clear': return [ {t:'__CLEAR__', cls:'ctl'} ];
    case 'whoami': return [ sout(this.user) ];
    case 'pwd': return [ sout('/home/'+this.user) ];
    case 'echo': return [ sout(a.join(' ').replace(/^["']|["']$/g,'')) ];
    case 'ls': return [ sout('ca.crt   notes.md   playbooks/   rules/') ];
    case 'cd': this.cwd = (a[0]&&a[0]!=='~')?a[0]:'~'; return [];
    case 'cat':
      if(!a.length) return [ serr('cat: missing operand'), sdiag('\u21b3 Give a filename, e.g. "cat ca.crt".') ];
      return [ sout('(contents of '+a[0]+' \u2014 representative)') ];

    // ---------------- OpenSSL ----------------
    case 'openssl': return this.openssl(a);

    // ---------------- GPG ----------------
    case 'gpg': case 'gpg2': return this.gpg(a);

    // ---------------- ssh-keygen ----------------
    case 'ssh-keygen': return this.sshkeygen(a);

    // ---------------- cosign (sigstore) ----------------
    case 'cosign':
      if(!a.length) return [ serr('Error: accepts commands: sign, verify, generate-key-pair, ...'), sdiag('\u21b3 cosign needs a subcommand, e.g. "cosign sign --key cosign.key <image>" or "cosign verify <image>".') ];
      if(a[0]==='generate-key-pair') return [ sout('Enter password for private key:'), sout('Private key written to cosign.key'), sout('Public key written to cosign.pub') ];
      if(a[0]==='sign') return [ sout('Pushing signature to: registry.example.com/app'), sinfo('tlog entry created (Rekor transparency log)') ];
      if(a[0]==='verify') return [ sout('Verification for registry.example.com/app --'), sout('The following checks were performed: signature verified, certificate verified, Rekor entry found') ];
      return [ sinfo('cosign '+a.join(' ')+' \u2014 accepted') ];

    // ---------------- nmap ----------------
    case 'nmap': return this.nmap(a);

    // ---------------- oscap / SCAP ----------------
    case 'oscap': return this.oscap(a);

    // ---------------- trivy / grype (image scanning + SCA) ----------------
    case 'trivy':
      if(!a.length) return [ serr('Error: a subcommand is required (image, fs, config, sbom, repo)'), sdiag('\u21b3 e.g. "trivy image nginx:latest" or "trivy fs --scanners vuln,secret .".') ];
      return [ sout('nginx:latest (debian 12.4)'), sout('Total: 47 (CRITICAL: 2, HIGH: 9, MEDIUM: 21, LOW: 15)'),
               sinfo('scan complete \u2014 prioritise CRITICAL/HIGH with a fixed version available') ];
    case 'grype':
      return [ sout('NAME     INSTALLED   FIXED-IN   TYPE  VULNERABILITY   SEVERITY'),
               sout('openssl  3.0.11-1    3.0.13-1   deb   CVE-2024-0727   High'),
               sinfo('grype scan complete') ];

    // ---------------- syft (SBOM) ----------------
    case 'syft':
      if(!a.length) return [ serr('an image or directory argument is required'), sdiag('\u21b3 e.g. "syft nginx:latest -o spdx-json=sbom.json" to emit an SBOM.') ];
      this.files['sbom.json']=true;
      return [ sout('Cataloged 214 packages'), sinfo('SBOM written (SPDX/CycloneDX) \u2014 feed to trivy/grype for supply-chain vuln matching') ];

    // ---------------- secrets / SAST ----------------
    case 'gitleaks':
      return [ sout('leaks found: 0'), sinfo('detect complete \u2014 wire this into CI (pre-commit + pipeline) to block secrets') ];
    case 'semgrep':
      if(!a.length) return [ serr('usage: semgrep [--config CONFIG] [target]'), sdiag('\u21b3 e.g. "semgrep --config auto ." for SAST scanning.') ];
      return [ sout('Scanning 312 files with 480 rules...'), sout('Findings: 6 (2 blocking)'), sinfo('SAST scan complete') ];
    case 'checkov':
      return [ sout('Passed checks: 128, Failed checks: 7, Skipped checks: 0'), sinfo('IaC scan complete \u2014 fix failed checks before terraform apply') ];
    case 'tfsec':
      return [ sout('results: 3 potential problems detected'), sinfo('tfsec complete') ];

    // ---------------- terraform / ansible ----------------
    case 'terraform':
      if(!a.length) return [ serr('Usage: terraform [global options] <subcommand> [args]'), sdiag('\u21b3 Common flow: "terraform init" \u2192 "terraform plan" \u2192 "terraform apply".') ];
      if(a[0]==='plan') return [ sout('Plan: 4 to add, 0 to change, 0 to destroy.'), sinfo('review the plan (and run tfsec/checkov) before apply') ];
      if(a[0]==='apply') return [ sout('Apply complete! Resources: 4 added, 0 changed, 0 destroyed.') ];
      if(a[0]==='init') return [ sout('Terraform has been successfully initialized!') ];
      return [ sinfo('terraform '+a.join(' ')+' \u2014 accepted') ];
    case 'ansible-vault':
      if(!a.length) return [ serr('ERROR! Missing required action'), sdiag('\u21b3 e.g. "ansible-vault encrypt secrets.yml" or "ansible-vault view secrets.yml".') ];
      return [ sinfo('ansible-vault '+a[0]+' \u2014 secrets protected at rest with AES-256') ];

    // ---------------- yara ----------------
    case 'yara': return this.yara(a);

    // ---------------- sigma ----------------
    case 'sigma': case 'sigmac':
      if(!a.length) return [ serr('usage: sigma convert -t <backend> <rule.yml>'), sdiag('\u21b3 Convert a Sigma rule to a SIEM query, e.g. "sigma convert -t splunk rule.yml".') ];
      return [ sout('index=* EventCode=4688 NewProcessName="*\\\\powershell.exe" CommandLine="*-enc*"'), sinfo('rule converted to backend query \u2014 deploy in your SIEM') ];

    // ---------------- suricata / snort ----------------
    case 'suricata':
      if(has(a,'-T')) return [ sout('Configuration provided was successfully loaded. Exiting.'), sinfo('ruleset validated') ];
      return [ sinfo('suricata '+a.join(' ')+' \u2014 IDS/IPS engine (accepted)') ];
    case 'snort':
      return [ sinfo('snort '+a.join(' ')+' \u2014 rule syntax accepted') ];

    // ---------------- osquery ----------------
    case 'osqueryi': case 'osquery':
      return [ sout('+------------+-------+'), sout('| name       | pid   |'), sout('+------------+-------+'), sout('| sshd       | 1123  |'), sout('+------------+-------+'), sinfo('osquery: the OS as a SQL database \u2014 great for fleet-wide hunting') ];

    // ---------------- volatility (memory forensics) ----------------
    case 'vol': case 'volatility': case 'vol.py':
      return [ sout('Volatility 3 Framework'), sout('PID    PPID   ImageFileName'), sout('4      0      System'), sout('1224   632    suspicious.exe'), sinfo('memory forensics \u2014 correlate rogue processes with IoCs') ];

    // ---------------- jq (parse SIEM / CloudTrail / STIX JSON) ----------------
    case 'jq':
      if(!a.length) return [ serr('Usage: jq [OPTIONS] FILTER [FILES...]'), sdiag('\u21b3 Provide a filter, e.g. \'jq \".Records[] | select(.eventName==\\"ConsoleLogin\\")\" trail.json\'.') ];
      return [ sout('"ConsoleLogin"'), sout('"AssumeRole"'), sinfo('jq filter applied \u2014 ideal for triaging JSON audit logs') ];

    // ---------------- hashing / IoC ----------------
    case 'sha256sum': case 'sha512sum': case 'md5sum':
      if(!a.length) return [ serr(cmd+": missing operand"), sdiag('\u21b3 Give a file to hash, e.g. "'+cmd+' installer.bin".') ];
      var hsh = cmd==='md5sum' ? '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8'.slice(0,32) : '9f2c8b1e4a7d6c3f0e5b8a2d1c4f7e9b3a6d5c8f2e1b4a7d0c3f6e9b2a5d8c1f';
      return [ sout(hsh+'  '+a[0]), sinfo('compare against the vendor-published hash / known-good IoC') ];

    // ---------------- auditd ----------------
    case 'auditctl':
      if(!a.length) return [ serr('usage: auditctl [options]'), sdiag('\u21b3 e.g. "auditctl -w /etc/passwd -p wa -k identity" to watch a file.') ];
      if(has(a,'-w')) return [ sinfo('audit watch added \u2014 view matches with "ausearch -k <key>"') ];
      return [ sinfo('auditctl '+a.join(' ')+' \u2014 accepted') ];
    case 'ausearch':
      return [ sout('time->Tue Jul 14 22:00:01 2026'), sout('type=SYSCALL ... key="identity" ... success=yes'), sinfo('audit records matched') ];

    // ---------------- STIX/TAXII / NVD via curl ----------------
    case 'curl': return this.curl(a);

    // ---------------- dig / DNS recon ----------------
    case 'dig':
      if(!a.length) return [ serr('usage: dig [name] [type]'), sdiag('\u21b3 e.g. "dig example.com TXT" or "dig +short example.com".') ];
      return [ sout(';; ANSWER SECTION:'), sout('example.com.  300  IN  A  93.184.216.34'), sinfo('DNS answer returned') ];

    // ---------------- Kerberos / LDAP / IAM ----------------
    case 'kinit':
      return [ sinfo('Password for '+(a[0]||'user@REALM')+':'), sinfo('TGT obtained \u2014 verify with "klist"') ];
    case 'klist':
      return [ sout('Ticket cache: KEYRING:persistent:1000'), sout('Default principal: analyst@EXAMPLE.COM'), sout('  krbtgt/EXAMPLE.COM@EXAMPLE.COM') ];
    case 'ldapsearch':
      if(!a.length) return [ serr('ldapsearch: missing filter'), sdiag('\u21b3 e.g. "ldapsearch -x -H ldaps://dc -b dc=example,dc=com (uid=jsmith)".') ];
      return [ sout('# jsmith, People, example.com'), sout('dn: uid=jsmith,ou=People,dc=example,dc=com'), sinfo('LDAP query returned 1 entry') ];

    // ---------------- kubectl (workload / network policy) ----------------
    case 'kubectl': return this.kubectl(a);

    // ---------------- cloud posture ----------------
    case 'prowler':
      return [ sout('Provider: aws'), sout('FAIL iam_root_mfa_enabled ... CRITICAL'), sout('PASS s3_bucket_public_access_block'), sinfo('cloud security posture scan complete (CSPM)') ];
    case 'scout': case 'scoutsuite':
      return [ sinfo('Scout Suite: multi-cloud posture report written to report.html') ];
    case 'aws': return this.aws(a);
    case 'az':
      return [ sinfo('az '+a.join(' ')+' \u2014 accepted (Azure CLI)') ];

    default:
      return this.notFound(cmd);
    }
  };

  // ================= tool implementations =================

  SecXConsole.prototype.openssl = function(a){
    if(!a.length) return [ serr('usage: openssl command [ command_opts ] [ command_args ]'),
      sdiag('\u21b3 openssl needs a subcommand, e.g. "genpkey", "req", "x509", "s_client", "verify", "dgst", "enc".') ];
    var sub = a[0], rest = a.slice(1);
    switch(sub){
      case 'version': return [ sout('OpenSSL 3.2.1 30 Jan 2024') ];
      case 'genrsa':
        this.files['server.key']=true;
        return [ sout('Generating RSA private key, 2048 bit long modulus (2 primes)'), sout('e is 65537 (0x010001)'),
                 sinfo('modern practice: prefer "openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072" or an EC/Ed25519 key') ];
      case 'genpkey':
        this.files['server.key']=true;
        var alg = valOf(rest,'-algorithm');
        if(!alg) return [ serr('Error: No -algorithm parameter given'), sdiag('\u21b3 Specify the key algorithm, e.g. "openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out server.key" or "-algorithm ED25519".') ];
        return [ sout('..+.....+....'), sinfo(alg+' private key written') ];
      case 'ecparam':
        return [ sout('-----BEGIN EC PARAMETERS-----'), sout('BggqhkjOPQMBBw=='), sout('-----END EC PARAMETERS-----'), sinfo('P-256 curve params (prime256v1)') ];
      case 'req':
        if(has(rest,'-new')||has(rest,'-x509')){
          if(!this.files['server.key'] && !has(rest,'-newkey')) return [ serr('Error opening Private Key server.key'), sdiag('\u21b3 Generate the key first ("openssl genpkey -algorithm RSA -out server.key") or use "-newkey rsa:3072" to create key+CSR together.') ];
          if(has(rest,'-x509')) { this.files['server.crt']=true; return [ sinfo('self-signed certificate created (use only for internal/testing; production certs come from a CA)') ]; }
          this.files['server.csr']=true;
          return [ sinfo('CSR written \u2014 submit server.csr to your CA to be signed into a certificate') ];
        }
        return [ serr('unknown option for req'), sdiag('\u21b3 Use "-new" (make a CSR) or "-x509" (self-sign), e.g. "openssl req -new -key server.key -out server.csr -subj \\"/CN=app.example.com\\"".') ];
      case 'x509':
        if(has(rest,'-noout')&&(has(rest,'-text')||has(rest,'-subject')||has(rest,'-dates')||has(rest,'-fingerprint')))
          return [ sout('subject=CN = app.example.com, O = Example'), sout('notBefore=Jul 14 00:00:00 2026 GMT'), sout('notAfter=Jul 14 00:00:00 2027 GMT'), sinfo('inspecting a certificate without re-emitting it (-noout)') ];
        if(has(rest,'-req')) { this.files['server.crt']=true; return [ sinfo('CSR signed into a certificate (acting as a CA)') ]; }
        return [ sinfo('openssl x509 '+rest.join(' ')+' \u2014 accepted') ];
      case 's_client':
        if(!has(rest,'-connect')) return [ serr('usage: s_client -connect host:port'), sdiag('\u21b3 e.g. "openssl s_client -connect example.com:443 -servername example.com </dev/null".') ];
        return [ sout('CONNECTED(00000003)'), sout('Protocol  : TLSv1.3'), sout('Cipher    : TLS_AES_256_GCM_SHA384'), sout('Verify return code: 0 (ok)'), sinfo('handshake succeeded \u2014 check the protocol, cipher and verify code') ];
      case 'verify':
        if(!rest.length) return [ serr('usage: openssl verify [ -CAfile file ] cert'), sdiag('\u21b3 e.g. "openssl verify -CAfile ca.crt server.crt" to validate the chain.') ];
        return [ sout((valOf(rest,'')||rest[rest.length-1])+': OK'), sinfo('certificate chains to the provided CA') ];
      case 'dgst':
        return [ sout('SHA2-256(file)= 9f2c8b1e4a7d6c3f0e5b8a2d1c4f7e9b3a6d5c8f2e1b4a7d0c3f6e9b2a5d8c1f'), sinfo('use -sign/-verify with a key for a digital signature') ];
      case 'enc':
        if(!has(rest,'-aes-256-cbc')&&!has(rest,'-aes-256-gcm')&&!has(rest,'-aes-256-ctr'))
          return [ serr('bad cipher or missing algorithm'), sdiag('\u21b3 Prefer AEAD, e.g. "openssl enc -aes-256-gcm -pbkdf2 -salt -in f -out f.enc". Never use -aes-256-cbc without an integrity check.') ];
        if(!has(rest,'-pbkdf2')) return [ sinfo('warning: no -pbkdf2 \u2014 modern openssl needs a strong KDF; add -pbkdf2 -iter 600000') ];
        return [ sinfo('data encrypted at rest with AES-256') ];
      case 'pkcs12':
        return [ sinfo('PKCS#12 bundle created/parsed (.pfx: key + cert + chain for Windows/Java import)') ];
      case 'rand':
        return [ sout('9f2c8b1e4a7d6c3f0e5b8a2d1c4f7e9b') ];
      case 'speed':
        return [ sinfo('benchmarking ciphers... (hardware acceleration: AES-NI detected)') ];
      default:
        return [ serr("openssl:Error: '"+sub+"' is an invalid command."),
                 sdiag('\u21b3 Valid subcommands include genpkey, req, x509, s_client, verify, dgst, enc, pkcs12, rand, ecparam.') ];
    }
  };

  SecXConsole.prototype.gpg = function(a){
    if(!a.length) return [ serr('gpg: Go ahead and type your message ...'), sdiag('\u21b3 gpg needs an action, e.g. "--full-generate-key", "--encrypt -r bob file", "--verify file.sig", "--detach-sign".') ];
    if(has(a,'--full-generate-key')||has(a,'--gen-key')) return [ sinfo('key generation \u2014 choose ECC (Curve 25519) or RSA 4096; set an expiry') ];
    if(has(a,'--encrypt')||has(a,'-e')) {
      if(!has(a,'-r')&&!has(a,'--recipient')) return [ serr('gpg: no valid addressees'), sdiag('\u21b3 Specify a recipient key, e.g. "gpg --encrypt -r bob@example.com file".') ];
      return [ sinfo('encrypted to recipient public key (only their private key can decrypt)') ];
    }
    if(has(a,'--verify')) return [ sout('gpg: Good signature from "Release Signing Key <sec@example.com>"'), sinfo('signature valid \u2014 confirms integrity + authenticity') ];
    if(has(a,'--detach-sign')||has(a,'-b')) return [ sinfo('detached signature written (file.sig) \u2014 distribute alongside the artifact') ];
    if(has(a,'--list-keys')||has(a,'-k')) return [ sout('pub   ed25519 2026-01-01 [SC]'), sout('uid   Release Signing Key <sec@example.com>') ];
    return [ sinfo('gpg '+a.join(' ')+' \u2014 accepted') ];
  };

  SecXConsole.prototype.sshkeygen = function(a){
    var type = valOf(a,'-t');
    if(has(a,'-t') && !type) return [ serr('unknown key type'), sdiag('\u21b3 Give a type after -t, e.g. "ssh-keygen -t ed25519 -C \\"analyst@corp\\"".') ];
    if(type && ['dsa','rsa1'].indexOf(type)!==-1) return [ serr('unknown or unsupported key type '+type), sdiag('\u21b3 DSA/rsa1 are deprecated and insecure. Use "-t ed25519" (preferred) or "-t rsa -b 4096".') ];
    if(type==='rsa' && !has(a,'-b')) return [ sinfo('generating RSA key at default size \u2014 add "-b 4096" for a stronger modulus') ];
    this.files['id_ed25519']=true; this.files['id_ed25519.pub']=true;
    return [ sout('Generating public/private '+(type||'ed25519')+' key pair.'), sout('Your identification has been saved in id_'+(type||'ed25519')), sout('Your public key has been saved in id_'+(type||'ed25519')+'.pub'), sinfo('add a passphrase and load via ssh-agent; distribute only the .pub') ];
  };

  SecXConsole.prototype.nmap = function(a){
    if(!a.length) return [ serr('Nmap: no target specified'), sdiag('\u21b3 Give a target, e.g. "nmap -sV -p- 10.0.0.0/24" or "nmap -sS -sV --script vuln host".') ];
    var lines = [ sout('Starting Nmap 7.94 ( https://nmap.org )') ];
    if(has(a,'-sS')) lines.push(sinfo('SYN "stealth" scan \u2014 needs root/CAP_NET_RAW'));
    lines.push(sout('Nmap scan report for target'));
    lines.push(sout('PORT     STATE SERVICE   VERSION'));
    lines.push(sout('22/tcp   open  ssh       OpenSSH 9.6'));
    lines.push(sout('443/tcp  open  ssl/https nginx 1.25'));
    if(has(a,'--script')) lines.push(sinfo('NSE scripts ran \u2014 review script output for findings'));
    lines.push(sinfo('scan complete \u2014 map open services to your attack-surface inventory'));
    return lines;
  };

  SecXConsole.prototype.oscap = function(a){
    if(!a.length) return [ serr('oscap: this is a usage error'), sdiag('\u21b3 e.g. "oscap xccdf eval --profile cis --results r.xml --report r.html ssg-rhel9-ds.xml".') ];
    if(a[0]==='xccdf' && a[1]==='eval'){
      if(!has(a,'--profile')) return [ serr('Missing --profile'), sdiag('\u21b3 Pick a profile such as "--profile xccdf_org.ssgproject.content_profile_cis".') ];
      return [ sout('Title   Ensure SSH root login is disabled'), sout('Result  pass'), sout('Title   Ensure auditd is enabled'), sout('Result  fail'), sinfo('SCAP compliance scan complete \u2014 remediate fails and re-scan') ];
    }
    if(a[0]==='oval') return [ sinfo('OVAL definition evaluated') ];
    return [ sinfo('oscap '+a.join(' ')+' \u2014 accepted') ];
  };

  SecXConsole.prototype.yara = function(a){
    if(a.length<2) return [ serr('yara: wrong number of arguments'), sdiag('\u21b3 yara takes a RULE file and a TARGET, e.g. "yara rules.yar /path/to/sample" (add -r to recurse).') ];
    return [ sout('Trojan_GenericKD rules.yar /path/to/sample'), sinfo('rule matched \u2014 tune strings/conditions to cut false positives') ];
  };

  SecXConsole.prototype.curl = function(a){
    if(!a.length) return [ serr("curl: try 'curl --help' for more information"), sdiag('\u21b3 Give a URL, e.g. "curl -s https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-3094".') ];
    var url = a.find(function(x){return /^https?:\/\//.test(x);}) || a[a.length-1];
    if(/nvd\.nist\.gov/.test(url)) return [ sout('{ "vulnerabilities": [ { "cve": { "id": "CVE-2024-3094", "metrics": { "cvssMetricV31": [ { "cvssData": { "baseScore": 10.0, "baseSeverity": "CRITICAL" } } ] } } } ] }'), sinfo('pipe to jq to extract the CVSS base score') ];
    if(/taxii|stix/i.test(url)) return [ sout('{ "objects": [ { "type": "indicator", "pattern": "[file:hashes.SHA-256 = \'9f2c...\']" } ] }'), sinfo('TAXII feed returned STIX indicators \u2014 ingest into your TIP') ];
    return [ sout('(HTTP 200 \u2014 body returned)'), sinfo('add -s to silence progress, -o to save, --cacert to pin a CA') ];
  };

  SecXConsole.prototype.kubectl = function(a){
    if(!a.length) return [ serr('kubectl controls the Kubernetes cluster manager.'), sdiag('\u21b3 e.g. "kubectl get pods -A", "kubectl apply -f networkpolicy.yaml", "kubectl auth can-i --list".') ];
    if(a[0]==='get') return [ sout('NAME              READY   STATUS    RESTARTS   AGE'), sout('web-5f4c...       1/1     Running   0          3d') ];
    if(a[0]==='apply') return [ sout('networkpolicy.networking.k8s.io/default-deny created'), sinfo('default-deny NetworkPolicy is the foundation of pod microsegmentation') ];
    if(a[0]==='auth') return [ sout('Resources          Non-Resource URLs   Verbs'), sout('pods               []                  [get list]'), sinfo('RBAC review \u2014 confirm least privilege') ];
    return [ sinfo('kubectl '+a.join(' ')+' \u2014 accepted') ];
  };

  SecXConsole.prototype.aws = function(a){
    if(!a.length) return [ serr('usage: aws [options] <command> <subcommand>'), sdiag('\u21b3 e.g. "aws s3api put-public-access-block ...", "aws iam list-users", "aws accessanalyzer ...".') ];
    if(a[0]==='s3api' && a[1]==='put-public-access-block') return [ sinfo('S3 public access blocked at the bucket level (prevents data exposure)') ];
    if(a[0]==='iam') return [ sout('{ "Users": [ { "UserName": "svc-deploy" } ] }'), sinfo('audit IAM for over-privileged and unused identities') ];
    return [ sinfo('aws '+a.join(' ')+' \u2014 accepted') ];
  };

  // expose
  window.SecXConsole = SecXConsole;
