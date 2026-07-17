# Linux+ XK0-006 (V8) — 100 Script Samples generator spec

Build a Python generator `gen_linux_samples.py` in `/home/user/workspace/certprep_single/` that emits
`window.LINUX_SAMPLES = [...]` to `/home/user/workspace/certprep_single/linux_samples.js`.

## Output contract (MUST MATCH EXACTLY)
Mirror the existing `gen_samples.py` (Cisco) in the same folder. Each sample object:
```
{"id": <int 1..100>, "title": <str>, "level": <"CORE"|"INTER"|"ADV">, "cat": <str>, "purpose": <str>,
 "config": [<str line>, ...], "explain": <str>}
```
- `config` is a list of shell command / script lines (comments start with `#`).
- `explain` uses the SAME label grammar as the Cisco file so the UI parser works:
  Start with `WHY IT WORKS: ...` and optionally add ` WHY A COMMON VARIANT FAILS: ...` or ` WHY IT MATTERS: ...`
  (the UI splits on the literal labels `WHY IT WORKS:` / `WHY A COMMON VARIANT FAILS:` / `WHY IT MATTERS:`).
- Levels map to badges: CORE (foundational), INTER (intermediate/admin), ADV (advanced/automation-cloud).
- Emit compact JSON exactly like gen_samples.py:
  `js = "window.LINUX_SAMPLES = " + json.dumps(S, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"`
- Print totals. Assert exactly 100 samples and every one has a non-empty explain.

## Distribution across the FIVE XK0-006 V8 domains (core-CLI emphasis, but cover all)
Aim ~ CORE 42, INTER 34, ADV 24. Categories should be drawn from:
1. System Management (23%): boot process (GRUB2, initramfs, systemd targets), FHS, kernel modules (lsmod/modprobe),
   partitioning (fdisk/parted/gdisk), filesystems (mkfs, mount, /etc/fstab, UUID), LVM (pvcreate/vgcreate/lvcreate/lvextend),
   RAID (mdadm), swap, hardware listing (lspci/lsusb/lsblk/dmidecode), virtualization concepts (KVM/qemu, virt concepts).
2. Services & User Management (20%): file/dir mgmt (ls/cp/mv/rm/find/ln), permissions (chmod symbolic+octal, chown, chgrp,
   umask, setuid/setgid/sticky, getfacl/setfacl, chattr/lsattr), users/groups (useradd/usermod/userdel/groupadd, passwd,
   /etc/passwd /etc/shadow, id, chage), package mgmt (apt, dnf/yum, rpm, dpkg, snap/flatpak), systemd services
   (systemctl start/stop/enable/status, journalctl), cron/at, process control (ps/top/kill/nice/renice/jobs/bg/fg),
   containers (docker/podman run/ps/build, Dockerfile basics).
3. Security (18%): SSH hardening (sshd_config, key auth, ssh-keygen, ssh-copy-id), sudo/visudo/sudoers, firewalls
   (firewalld firewall-cmd, ufw, nftables/iptables), SELinux (getenforce/setenforce/semanage/restorecon/chcon, booleans),
   AppArmor basics, password policy (chage, PAM concepts), gpg, fail2ban concept, auditd.
4. Automation, Orchestration & Scripting (17%): Bash scripting (shebang, variables, if/for/while/case, functions,
   test/[[ ]], arithmetic, exit codes, positional params, here-docs, command substitution), Python for admin (small scripts),
   Git (init/clone/add/commit/branch/checkout/merge/push/pull/stash/log), Ansible basics (ad-hoc + a small playbook YAML),
   cron-driven automation, IaC concept, AI-assisted scripting best-practice note.
5. Troubleshooting (22%): storage (df/du/lsblk/fsck, LVM issues), performance (top/htop/vmstat/iostat/free/uptime/sar),
   memory/OOM, networking (ip a/ip r, ss, ping, dig/nslookup, traceroute, nmcli, /etc/resolv.conf, curl), logs
   (journalctl -u, /var/log, dmesg, tail -f, grep), process/zombie, permission-denied diagnosis, boot/emergency target.

## Quality bar
- Real, correct, copy-paste-ready commands and short scripts. Prefer modern tooling (systemd, dnf, ip, firewalld, nftables,
  podman) but include classic equivalents where CompTIA still tests them (iptables, yum, ifconfig-as-legacy note).
- Multi-line scripts are welcome for the scripting/automation samples (bash + a couple python + one ansible YAML playbook).
- Explanations must be genuinely instructive and, where relevant, name the common mistake (e.g. `chmod 777` security risk,
  editing sudoers without visudo, forgetting `systemctl daemon-reload`, `rm -rf` danger, forgetting shebang, `==` vs `-eq`).
- Titles concise; purpose one sentence.
- Ensure ids are 1..100 sequential in the emitted order (CORE first, then INTER, then ADV is fine, or interleave by domain — but keep ids contiguous).

## Do NOT
- Do not touch template.html, build_single.py, ios_sim.js, or gen_samples.py.
- Only create gen_linux_samples.py and run it to produce linux_samples.js.
- Verify with: python3 gen_linux_samples.py  → should print "total samples: 100" and write the file.
