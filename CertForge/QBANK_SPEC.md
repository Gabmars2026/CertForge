# CompTIA Linux+ XK0-006 (V8) — Question Bank Spec

Generate multiple-choice exam-practice questions for CompTIA Linux+ **XK0-006 (V8)**.
Total target across all domains: **1000 questions**, weighted to the official domain distribution.

## Output format (STRICT)
One JSON object per line (JSONL), no blank lines, no trailing commas. Each object:
```json
{"q": "question text", "options": ["A","B","C","D"], "answer": 2, "explanation": "1-2 sentence rationale for the correct answer and why it fits."}
```
- Exactly **4 options** per question.
- `answer` = zero-based index (0-3) of the correct option.
- **Vary the correct-answer position** roughly evenly across 0/1/2/3 (do NOT cluster on one index).
- `q` must be self-contained (no "which of the following from the diagram").
- Distractors must be **plausible and same-category** (e.g. all real commands, all real paths) — never obviously wrong filler.
- Mix formats: "which command…", scenario/troubleshooting, config-file, conceptual, output-interpretation, best-practice.
- Difficulty spread: ~40% recall, ~40% applied/scenario, ~20% analysis/troubleshooting.
- Use **current V8 tooling**: systemd (systemctl/journalctl/timers), dnf (not just yum), nftables/firewalld/ufw, ip/ss/nmcli (not ifconfig/netstat unless as a distractor), podman + docker, Python 3, git, Ansible/Puppet, LVM, SELinux/AppArmor.
- Keep explanations technically accurate and concise. No markdown inside strings.
- Do NOT duplicate question stems. Each question stem must be unique.

## V8-specific emphasis (MUST be well represented)
XK0-006 newly elevates these — ensure strong coverage where the domain calls for it:
- **Python 3 basics** (venv, pip, data types, argparse, file I/O, shebang) — Automation domain.
- **Git workflows** (branch/merge/rebase, tags, remotes, .gitignore, resolving conflicts) — Automation domain.
- **AI best practices** (responsible AI-assisted code generation, prompt engineering, reviewing/validating generated code, security of AI output) — Automation domain.
- **Containers** (podman rootless vs docker, images, registries, networks, volumes, Containerfile/Dockerfile) — Services & User Management domain.
- **IaC / orchestration** (Ansible playbooks/inventory/modules, Puppet manifests, CI/CD, cloud-init) — Automation domain.
- **Virtualization & cloud/hybrid** (KVM/QEMU, libvirt, virt-install, disk images, cloud-init) — System Management domain.

## Domain subtopics (from official objectives)

### System Management (230 questions)
Linux basics (boot process, GRUB2, kernel, initramfs, filesystems ext4/xfs/btrfs, FHS, architectures); device management (kernel modules lsmod/modprobe, udev, lspci/lsusb, /proc /sys); storage management (LVM pvcreate/vgcreate/lvcreate/lvextend, RAID mdadm, partitions parted/gdisk, mount/fstab, swap); network configuration (nmcli, ip addr/route, DNS /etc/resolv.conf, /etc/hosts, netplan, hostnamectl); shell operations (navigation, redirection, pipes, globbing, env vars, aliases, vim/nano); backups & restores (tar, rsync, dd, gzip/xz/bzip2, cpio); virtualization (KVM/QEMU, libvirt, virsh, virt-install, qcow2 disk images, cloud-init).

### Services and User Management (200 questions)
Files & directories (permissions rwx/octal/symbolic, chmod/chown/chgrp, setuid/setgid/sticky, ACLs getfacl/setfacl, hard vs symbolic links, special files); account management (useradd/usermod/userdel, groupadd, /etc/passwd /etc/shadow /etc/group, passwd, id, gpasswd); process control (ps, top, htop, nice/renice, kill/signals, jobs/bg/fg, nohup, systemd cgroups); software management (dnf/yum, apt, rpm, dpkg, flatpak, snap, repositories, GPG keys); systems management (systemctl start/stop/enable/status, journalctl, systemd units/targets/timers, /etc/systemd); containers (podman, docker, images, registries, podman run/ps/images, volumes, networks, rootless containers, Containerfile).

### Security (180 questions)
Auth & accounting (PAM /etc/pam.d, LDAP/sssd, Kerberos, auditd/auditctl, /etc/nsswitch.conf); firewalls (iptables, nftables, firewalld firewall-cmd zones, ufw); OS hardening (file permissions, sudo /etc/sudoers visudo, SSH hardening sshd_config, disabling root login, fail2ban); account security (password policies /etc/login.defs chage, pwquality, restricted shells, MFA/Google Authenticator PAM, faillock); cryptography (gpg encrypt/sign, openssl, hashing sha256sum/md5sum, TLS certificates, LUKS disk encryption cryptsetup, SSH keys); compliance (AIDE/tripwire integrity, OpenSCAP scans, CIS benchmarks, SELinux/AppArmor policies).

### Automation, Orchestration, and Scripting (170 questions)
Automation (Ansible playbooks/inventory/ad-hoc/modules, Puppet manifests, CI/CD pipelines, cron/at, systemd timers); shell scripting (bash variables, quoting, conditionals if/case, loops for/while, functions, exit codes, positional params, test [[ ]], arithmetic, here-docs, getopts); Python basics (python3, venv, pip/pip3, data types, lists/dicts, file I/O, argparse, shebang, modules); version control (git init/clone/add/commit/branch/merge/rebase/tag/remote/push/pull, .gitignore, resolving conflicts, git log); AI best practices (AI-assisted code generation, prompt engineering, validating/reviewing generated code, not leaking secrets to AI tools, security review of AI output).

### Troubleshooting (220 questions)
System monitoring (uptime, load average, dmesg, journalctl, /var/log, sar, vmstat, top); hardware/storage (boot failures GRUB rescue, fsck, mount issues, disk full df/du, inode exhaustion, smartctl, LVM recovery); networking (ping/traceroute/mtr, dig/nslookup/host, ss, DNS resolution, routing, firewall blocking, MTU, nmcli); security (SELinux denials ausearch/setenforce/restorecon/audit2allow, permission errors, AppArmor, expired certs, sudo issues); performance (CPU/memory/IO bottlenecks, iostat/iotop, free, swap thrashing, ulimit, tuning, OOM killer).

## Quality bar
Questions should read like real CompTIA exam items — practical, current, scenario-driven where possible. Avoid trivia. Avoid deprecated tools as the "correct" answer.
