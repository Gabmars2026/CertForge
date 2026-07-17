  // ============================================================
  //  Linux Shell Simulator  (CompTIA Linux+ XK0-006 / V8 grammar)
  //  Rule-based, stateful. Emits authentic shell/error output PLUS
  //  plain-English diagnostics (cls:'diag').
  //
  //  NOTE: This is a command-grammar + state simulator, not a real
  //  kernel or userland. It validates command existence, argument
  //  shape, permissions, and common dependencies; tracks a virtual
  //  filesystem, users/groups, services and packages; and renders
  //  realistic output. It does not execute real binaries (use a VM,
  //  container, or WSL for true runtime behaviour).
  //  Interface parity with IOSDevice: .prompt() and .exec(line) ->
  //  [{t, cls}] where cls in out|err|info|diag.
  // ============================================================
  function LinuxShell(hostname){
    this.hostname = hostname || 'linuxlab';
    this.user = 'student';
    this.uid = 1000;
    this.cwd = '/home/student';
    this.env = { HOME:'/home/student', USER:'student', SHELL:'/bin/bash', PWD:'/home/student', PATH:'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' };
    this.lastStatus = 0;
    // virtual filesystem: path -> {type:'dir'|'file', mode, owner, group, content}
    this.fs = {};
    this.mkNode('/', 'dir', 0o755, 'root', 'root');
    ['/home','/etc','/var','/var/log','/tmp','/usr','/usr/bin','/usr/local','/opt','/mnt','/root','/boot','/dev','/proc','/sys','/srv']
      .forEach(function(p){ this.mkNode(p,'dir',0o755,'root','root'); }, this);
    this.mkNode('/home/student','dir',0o755,'student','student');
    this.mkNode('/root','dir',0o700,'root','root');
    this.mkNode('/tmp','dir',0o1777,'root','root');
    this.mkNode('/etc/passwd','file',0o644,'root','root');
    this.mkNode('/etc/shadow','file',0o640,'root','shadow');
    this.mkNode('/etc/fstab','file',0o644,'root','root');
    this.mkNode('/etc/hosts','file',0o644,'root','root');
    this.mkNode('/etc/ssh','dir',0o755,'root','root');
    this.mkNode('/etc/ssh/sshd_config','file',0o644,'root','root');
    this.mkNode('/etc/sudoers','file',0o440,'root','root');
    this.mkNode('/var/log/syslog','file',0o640,'root','adm');
    this.mkNode('/var/log/messages','file',0o640,'root','root');
    // known users / groups
    this.users = { root:{uid:0,home:'/root',shell:'/bin/bash',groups:['root']},
                   student:{uid:1000,home:'/home/student',shell:'/bin/bash',groups:['student','sudo']} };
    this.groups = { root:[ 'root' ], student:['student'], sudo:['student'], wheel:[], docker:[], adm:[], shadow:[] };
    // services: name -> {active, enabled}
    this.services = { 'sshd':{active:true,enabled:true}, 'ssh':{active:true,enabled:true},
                      'cron':{active:true,enabled:true}, 'crond':{active:true,enabled:true},
                      'firewalld':{active:false,enabled:false}, 'nginx':{active:false,enabled:false},
                      'httpd':{active:false,enabled:false}, 'docker':{active:false,enabled:false},
                      'NetworkManager':{active:true,enabled:true} };
    // installed packages
    this.pkgs = { bash:true, coreutils:true, 'openssh-server':true, systemd:true, vim:true, curl:true, git:true };
    this.pm = null;       // detected package manager 'apt'|'dnf'|'yum'
    this.selinux = 'enforcing';
    this.firewall = { running:false, zones:{public:{services:['ssh'],ports:[]}} };
    this.gitRepo = false; // cwd git-initialised (simplified: single global flag)
    this.gitStaged = [];
    this.gitCommits = 0;
    this.gitBranch = 'main';
  }

  // ---------- helpers ----------
  function lout(t){return {t:t,cls:'out'};}
  function lerr(t){return {t:t,cls:'err'};}
  function linfo(t){return {t:t,cls:'info'};}
  function ldiag(t){return {t:t,cls:'diag'};}   // plain-English why/how-to-fix
  function ltoks(line){ return line.trim().split(/\s+/).filter(Boolean); }

  LinuxShell.prototype.prompt = function(){
    var tag = this.uid===0 ? '#' : '$';
    var short = this.cwd===this.env.HOME ? '~' : this.cwd;
    return this.user+'@'+this.hostname+':'+short+tag;
  };

  LinuxShell.prototype.mkNode = function(path, type, mode, owner, group, content){
    this.fs[path] = { type:type, mode:(mode==null?(type==='dir'?0o755:0o644):mode),
                      owner:owner||this.user, group:group||this.user, content:content||'' };
  };
  LinuxShell.prototype.exists = function(p){ return Object.prototype.hasOwnProperty.call(this.fs, p); };
  // resolve a possibly-relative path to an absolute normalized path
  LinuxShell.prototype.resolve = function(p){
    if(!p) return this.cwd;
    if(p==='~') return this.env.HOME;
    if(p.indexOf('~/')===0) p = this.env.HOME + p.slice(1);
    var abs = (p[0]==='/') ? p : (this.cwd==='/'?'':this.cwd) + '/' + p;
    var parts = abs.split('/'), stack = [];
    for(var i=0;i<parts.length;i++){
      var seg = parts[i];
      if(seg===''||seg==='.') continue;
      if(seg==='..'){ stack.pop(); continue; }
      stack.push(seg);
    }
    return '/'+stack.join('/');
  };
  LinuxShell.prototype.parent = function(p){ var i=p.lastIndexOf('/'); return i<=0?'/':p.slice(0,i); };
  LinuxShell.prototype.isPriv = function(){ return this.uid===0; };

  // administrative command that normally needs root
  LinuxShell.prototype.needRoot = function(what){
    if(this.isPriv()) return null;
    return [ lerr(what+': Permission denied'),
             ldiag('\u21b3 This action needs root. Prefix with "sudo" (your user is in the sudo group) or switch with "sudo -i".') ];
  };

  // ---------- main dispatch ----------
  LinuxShell.prototype.exec = function(rawLine){
    var line = (rawLine||'').replace(/\t/g,' ');
    var trimmed = line.trim();
    if(trimmed==='') return [];
    if(trimmed[0]==='#') return [];                       // comment / shebang

    // handle a leading "sudo"
    var elevated = false;
    if(/^sudo(\s|$)/.test(trimmed)){
      elevated = true;
      trimmed = trimmed.replace(/^sudo\s*/,'');
      if(trimmed===''){ return [ lerr('usage: sudo command'), ldiag('\u21b3 sudo needs a command to run, e.g. "sudo systemctl restart sshd".') ]; }
    }
    // ignore trailing redirections / pipes for validation purposes but keep the head command
    var pipeHead = trimmed.split(/\s*\|\s*/)[0];
    var redirClean = pipeHead.replace(/\s*[12]?>>?\s*\S+/g,'').replace(/\s*<\s*\S+/g,'').trim();

    var t = ltoks(redirClean);
    var cmd = t[0];

    // environment/simple assignments  VAR=value
    if(/^[A-Za-z_][A-Za-z0-9_]*=/.test(cmd) && t.length===1){
      var eqp = cmd.split('='); this.env[eqp[0]] = eqp.slice(1).join('='); this.lastStatus=0; return [];
    }

    var savedUid = this.uid;
    if(elevated){ this.uid = 0; this.user = (this.user==='root'?'root':this.user); }

    var res;
    try { res = this.run(cmd, t.slice(1), t, trimmed); }
    catch(e){ res = [ lerr('bash: internal error') ]; }

    if(elevated){ this.uid = savedUid; }   // sudo elevates for one command only
    return res || [];
  };

  var KNOWN = {}; // command name -> handler key (for "command not found" vs real)
  LinuxShell.prototype.run = function(cmd, a, t, raw){
    switch(cmd){
      // ---- navigation & files ----
      case 'pwd':   this.lastStatus=0; return [ lout(this.cwd) ];
      case 'cd':    return this.cCd(a);
      case 'ls':    return this.cLs(a);
      case 'mkdir': return this.cMkdir(a);
      case 'rmdir': return this.cRmdir(a);
      case 'touch': return this.cTouch(a);
      case 'rm':    return this.cRm(a);
      case 'cp':    return this.cCp(a);
      case 'mv':    return this.cMv(a);
      case 'cat':   return this.cCat(a);
      case 'echo':  return this.cEcho(a, raw);
      case 'find':  return this.cFind(a);
      case 'ln':    return this.cLn(a);
      case 'head': case 'tail': case 'less': case 'more': return this.cPager(cmd,a);
      case 'grep':  return this.cGrep(a);
      case 'ln-s':  break;

      // ---- permissions & ownership ----
      case 'chmod': return this.cChmod(a);
      case 'chown': return this.cChown(a);
      case 'chgrp': return this.cChgrp(a);
      case 'umask': return this.cUmask(a);
      case 'getfacl': case 'setfacl': return this.cAcl(cmd,a);
      case 'chattr': case 'lsattr': return [ lout('') ];

      // ---- identity ----
      case 'whoami': this.lastStatus=0; return [ lout(this.user) ];
      case 'id':     return this.cId(a);
      case 'who': case 'w': return [ lout(this.user+'   pts/0        '+'  (:0)') ];
      case 'hostname': return [ lout(this.hostname) ];
      case 'su':     return this.cSu(a);

      // ---- users & groups ----
      case 'useradd': case 'adduser':   return this.cUseradd(a);
      case 'usermod':  return this.cUsermod(a);
      case 'userdel': case 'deluser':   return this.cUserdel(a);
      case 'groupadd': return this.cGroupadd(a);
      case 'groupdel': return this.cGeneric(cmd,a,true);
      case 'passwd':   return this.cPasswd(a);
      case 'chage':    return this.cGeneric(cmd,a,true);

      // ---- packages ----
      case 'apt': case 'apt-get': return this.cApt(cmd,a);
      case 'dnf': case 'yum':     return this.cDnf(cmd,a);
      case 'rpm':  return this.cRpm(a);
      case 'dpkg': return this.cDpkg(a);
      case 'snap': case 'flatpak': return this.cGeneric(cmd,a,false);

      // ---- services (systemd) ----
      case 'systemctl': return this.cSystemctl(a);
      case 'service':   return this.cServiceLegacy(a);
      case 'journalctl':return this.cJournalctl(a);

      // ---- process control ----
      case 'ps':   return [ lout('    PID TTY          TIME CMD'), lout('   1024 pts/0    00:00:00 bash'), lout('   1099 pts/0    00:00:00 ps') ];
      case 'top': case 'htop': return [ linfo('(interactive '+cmd+' \u2014 press q to quit in a real terminal)') ];
      case 'kill':  return this.cKill(a,false);
      case 'killall': case 'pkill': return this.cKill(a,true);
      case 'nice': case 'renice': return this.cGeneric(cmd,a,false);
      case 'jobs': return [ lout('') ];
      case 'bg': case 'fg': return [ lout('') ];
      case 'free': return [ lout('               total        used        free'), lout('Mem:        8039112     2113440     3922244'), lout('Swap:       2097148           0     2097148') ];
      case 'uptime': return [ lout(' 21:30:01 up 3 days,  4:12,  1 user,  load average: 0.08, 0.03, 0.01') ];
      case 'vmstat': case 'iostat': case 'sar': case 'mpstat': return [ lout('('+cmd+' performance stats \u2014 sampled)') ];

      // ---- storage ----
      case 'df':    return [ lout('Filesystem     1K-blocks    Used Available Use% Mounted on'), lout('/dev/mapper/vg-root 51473920 8123456  40732288  17% /'), lout('/dev/sda1        1038336  204800    833536  20% /boot') ];
      case 'du':    return [ lout('4.0K\t'+this.cwd) ];
      case 'lsblk': return [ lout('NAME          MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT'), lout('sda             8:0    0  100G  0 disk'), lout('\u251c\u2500sda1          8:1    0    1G  0 part /boot'), lout('\u2514\u2500sda2          8:2    0   99G  0 part'), lout('  \u2514\u2500vg-root     253:0    0   99G  0 lvm  /') ];
      case 'mount':  return this.cMount(a);
      case 'umount': return this.cGeneric(cmd,a,true);
      case 'mkfs': return this.cGeneric(cmd,a,true);
      case 'fsck': return this.cGeneric(cmd,a,true);
      case 'fdisk': case 'parted': case 'gdisk': return this.cDiskTool(cmd,a);
      case 'blkid': return [ lout('/dev/sda1: UUID="1b2c-3d4e" TYPE="ext4"') ];
      case 'swapon': case 'swapoff': case 'mkswap': return this.cGeneric(cmd,a,true);
      // LVM
      case 'pvcreate': case 'vgcreate': case 'lvcreate': case 'lvextend': case 'vgextend':
      case 'pvs': case 'vgs': case 'lvs': case 'pvdisplay': case 'vgdisplay': case 'lvdisplay':
        return this.cLvm(cmd,a);
      case 'mdadm': return this.cGeneric(cmd,a,true);
      case 'resize2fs': case 'xfs_growfs': return this.cGeneric(cmd,a,true);

      // ---- kernel / hardware ----
      case 'lsmod': return [ lout('Module                  Size  Used by'), lout('xfs                  1552384  1') ];
      case 'modprobe': case 'insmod': case 'rmmod': return this.cGeneric(cmd,a,true);
      case 'lscpu': return [ lout('Architecture:        x86_64'), lout('CPU(s):              4') ];
      case 'lspci': return [ lout('00:02.0 VGA compatible controller: ...') ];
      case 'lsusb': return [ lout('Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub') ];
      case 'dmidecode': return this.needRoot('dmidecode') || [ lout('# dmidecode 3.x') ];
      case 'uname': return this.cUname(a);
      case 'dmesg': return this.isPriv()? [ lout('[    0.000000] Linux version 6.x ...') ] : (this.needRoot('dmesg') || []);
      case 'sysctl': return this.cGeneric(cmd,a,true);

      // ---- boot / targets ----
      case 'grub2-mkconfig': case 'grub-mkconfig': case 'update-grub': case 'mkinitrd': case 'dracut':
        return this.cGeneric(cmd,a,true);

      // ---- networking ----
      case 'ip':    return this.cIp(a);
      case 'ss': case 'netstat': return this.cSs(a);
      case 'ping':  return this.cPing(a);
      case 'dig': case 'nslookup': case 'host': return this.cDns(cmd,a);
      case 'traceroute': case 'tracepath': return [ lout(' 1  gateway (192.168.1.1)  0.512 ms') ];
      case 'nmcli': return this.cNmcli(a);
      case 'curl': case 'wget': return this.cCurl(cmd,a);
      case 'ifconfig': return [ linfo('ifconfig is deprecated on modern distros.'), ldiag('\u21b3 Use "ip addr" / "ip link" (iproute2) instead \u2014 CompTIA V8 expects the ip suite.') ];

      // ---- security ----
      case 'ssh-keygen': return this.cSshKeygen(a);
      case 'ssh-copy-id': case 'ssh': case 'scp': case 'sftp': return this.cGeneric(cmd,a,false);
      case 'visudo': return this.needRoot('visudo') || [ linfo('(opens /etc/sudoers safely with syntax checking)') ];
      case 'getenforce': return [ lout(this.selinux.charAt(0).toUpperCase()+this.selinux.slice(1)) ];
      case 'setenforce': return this.cSetenforce(a);
      case 'sestatus': return [ lout('SELinux status:                 enabled'), lout('Current mode:                   '+this.selinux) ];
      case 'semanage': case 'restorecon': case 'chcon': case 'setsebool': case 'getsebool': return this.cGeneric(cmd,a, cmd!=='getsebool'&&cmd!=='getenforce');
      case 'firewall-cmd': return this.cFirewallCmd(a);
      case 'ufw': return this.cUfw(a);
      case 'nft': case 'iptables': return this.cNftIptables(cmd,a);
      case 'gpg': return this.cGeneric(cmd,a,false);
      case 'fail2ban-client': case 'auditctl': case 'ausearch': return this.cGeneric(cmd,a,true);

      // ---- containers ----
      case 'docker': case 'podman': return this.cContainer(cmd,a);

      // ---- scheduling ----
      case 'crontab': return this.cCrontab(a);
      case 'at': case 'atq': case 'atrm': return this.cGeneric(cmd,a,false);

      // ---- scripting / dev ----
      case 'bash': case 'sh': return this.cGeneric(cmd,a,false);
      case 'python3': case 'python': return this.cPython(a);
      case 'pip': case 'pip3': return this.cGeneric(cmd,a,false);
      case 'git':  return this.cGit(a);
      case 'ansible': case 'ansible-playbook': return this.cAnsible(cmd,a);
      case 'make': case 'gcc': case 'vim': case 'nano': case 'vi': case 'sed': case 'awk': case 'cut': case 'sort':
      case 'uniq': case 'wc': case 'tr': case 'tee': case 'xargs': case 'tar': case 'gzip': case 'gunzip':
      case 'date': case 'which': case 'type': case 'export': case 'alias': case 'source': case 'test':
      case 'true': case 'false': case 'sleep': case 'clear': case 'history': case 'env': case 'printenv':
      case 'df-h':
        return this.cGeneric(cmd,a,false);

      default:
        this.lastStatus=127;
        return [ lerr('bash: '+cmd+': command not found'),
                 ldiag('\u21b3 Unknown command. Check spelling, ensure the package that provides it is installed (e.g. "sudo dnf install ...") and that it is on your $PATH.') ];
    }
  };

  // A generic accepter for well-formed admin commands we don't model in depth.
  LinuxShell.prototype.cGeneric = function(cmd,a,rootish){
    if(rootish){ var nr=this.needRoot(cmd); if(nr) return nr; }
    this.lastStatus=0; return [];
  };

  // ================= file / navigation =================
  LinuxShell.prototype.cCd = function(a){
    var target = a[0] ? this.resolve(a[0]) : this.env.HOME;
    if(a[0]==='-'){ target=this.env.OLDPWD||this.env.HOME; }
    if(!this.exists(target)){ this.lastStatus=1; return [ lerr('bash: cd: '+(a[0]||'')+': No such file or directory') ]; }
    if(this.fs[target].type!=='dir'){ this.lastStatus=1; return [ lerr('bash: cd: '+a[0]+': Not a directory') ]; }
    this.env.OLDPWD=this.cwd; this.cwd=target; this.env.PWD=target; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cLs = function(a){
    var flags = a.filter(function(x){return x[0]==='-';}).join('');
    var pathArg = a.filter(function(x){return x[0]!=='-';})[0];
    var dir = pathArg ? this.resolve(pathArg) : this.cwd;
    if(!this.exists(dir)){ this.lastStatus=2; return [ lerr('ls: cannot access \''+pathArg+'\': No such file or directory') ]; }
    var self=this, prefix = dir==='/'?'/':dir+'/';
    var kids = Object.keys(this.fs).filter(function(p){ return p!==dir && p.indexOf(prefix)===0 && p.slice(prefix.length).indexOf('/')<0; });
    var names = kids.map(function(p){ return p.slice(prefix.length); });
    if(this.fs[dir].type==='file'){ names=[pathArg]; }
    if(flags.indexOf('l')>=0){
      var rows = kids.map(function(p){ var n=self.fs[p]; return self.modeStr(n)+' 1 '+n.owner+' '+n.group+'   4096 Jul 14 21:30 '+p.slice(prefix.length); });
      this.lastStatus=0; return rows.length?rows.map(lout):[ lout('total 0') ];
    }
    this.lastStatus=0; return [ lout(names.sort().join('  ')) ];
  };
  LinuxShell.prototype.modeStr = function(n){
    var t = n.type==='dir'?'d':'-';
    var m = n.mode & 0o777;
    function rwx(x){ return (x&4?'r':'-')+(x&2?'w':'-')+(x&1?'x':'-'); }
    return t+rwx((m>>6)&7)+rwx((m>>3)&7)+rwx(m&7);
  };
  LinuxShell.prototype.cMkdir = function(a){
    if(!a.length) return [ lerr('mkdir: missing operand'), ldiag('\u21b3 Provide a directory name, e.g. "mkdir project" or "mkdir -p a/b/c".') ];
    var p = this.resolve(a[a.length-1]);
    var parents = a.indexOf('-p')>=0;
    var par = this.parent(p);
    if(!parents && !this.exists(par)) { this.lastStatus=1; return [ lerr('mkdir: cannot create directory \u2018'+a[a.length-1]+'\u2019: No such file or directory'), ldiag('\u21b3 A parent directory is missing. Add -p to create the whole path: "mkdir -p '+a[a.length-1]+'".') ]; }
    if(this.exists(p) && !parents){ this.lastStatus=1; return [ lerr('mkdir: cannot create directory \u2018'+a[a.length-1]+'\u2019: File exists') ]; }
    this.mkNode(p,'dir',0o755,this.user,this.user); this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cRmdir = function(a){
    if(!a.length) return [ lerr('rmdir: missing operand') ];
    var p=this.resolve(a[0]);
    if(!this.exists(p)){ this.lastStatus=1; return [ lerr('rmdir: failed to remove \''+a[0]+'\': No such file or directory') ]; }
    var prefix=p+'/'; var hasKids=Object.keys(this.fs).some(function(x){return x.indexOf(prefix)===0;});
    if(hasKids){ this.lastStatus=1; return [ lerr('rmdir: failed to remove \''+a[0]+'\': Directory not empty'), ldiag('\u21b3 rmdir only removes empty dirs. Use "rm -r '+a[0]+'" to remove a non-empty directory (carefully).') ]; }
    delete this.fs[p]; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cTouch = function(a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(!files.length) return [ lerr('touch: missing file operand') ];
    for(var i=0;i<files.length;i++){ var p=this.resolve(files[i]); if(!this.exists(this.parent(p))){ this.lastStatus=1; return [ lerr('touch: cannot touch \''+files[i]+'\': No such file or directory') ]; } if(!this.exists(p)) this.mkNode(p,'file',0o644,this.user,this.user); }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cRm = function(a){
    var flags=a.filter(function(x){return x[0]==='-';}).join('');
    var files=a.filter(function(x){return x[0]!=='-';});
    if(!files.length) return [ lerr('rm: missing operand') ];
    var rec = /r/.test(flags), force=/f/.test(flags);
    // guardrail
    if(files.some(function(x){return x==='/';}) && rec){ return [ lerr('rm: it is dangerous to operate recursively on \'/\''), ldiag('\u21b3 "rm -rf /" would wipe the system. Modern rm blocks this with --no-preserve-root off by default. Never run it.') ]; }
    for(var i=0;i<files.length;i++){
      var p=this.resolve(files[i]);
      if(!this.exists(p)){ if(force) continue; this.lastStatus=1; return [ lerr('rm: cannot remove \''+files[i]+'\': No such file or directory') ]; }
      if(this.fs[p].type==='dir' && !rec){ this.lastStatus=1; return [ lerr('rm: cannot remove \''+files[i]+'\': Is a directory'), ldiag('\u21b3 Add -r to remove a directory and its contents: "rm -r '+files[i]+'".') ]; }
      var prefix=p+'/'; var self=this; Object.keys(this.fs).forEach(function(x){ if(x===p||x.indexOf(prefix)===0) delete self.fs[x]; });
    }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cCp = function(a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(files.length<2) return [ lerr('cp: missing destination file operand'), ldiag('\u21b3 cp needs a source AND a destination: "cp source dest". Use -r to copy directories.') ];
    var src=this.resolve(files[0]), dst=this.resolve(files[files.length-1]);
    if(!this.exists(src)){ this.lastStatus=1; return [ lerr('cp: cannot stat \''+files[0]+'\': No such file or directory') ]; }
    if(this.fs[src].type==='dir' && a.indexOf('-r')<0 && a.indexOf('-a')<0 && a.indexOf('-R')<0){ this.lastStatus=1; return [ lerr('cp: -r not specified; omitting directory \''+files[0]+'\''), ldiag('\u21b3 Add -r (recursive) to copy a directory.') ]; }
    var n=this.fs[src]; this.mkNode(dst,n.type,n.mode,this.user,this.user,n.content); this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cMv = function(a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(files.length<2) return [ lerr('mv: missing destination file operand') ];
    var src=this.resolve(files[0]), dst=this.resolve(files[files.length-1]);
    if(!this.exists(src)){ this.lastStatus=1; return [ lerr('mv: cannot stat \''+files[0]+'\': No such file or directory') ]; }
    this.fs[dst]=this.fs[src]; delete this.fs[src]; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cCat = function(a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(!files.length) return [ linfo('(cat waits for stdin \u2014 press Ctrl-D to end)') ];
    var out=[];
    for(var i=0;i<files.length;i++){ var p=this.resolve(files[i]); if(!this.exists(p)){ this.lastStatus=1; return [ lerr('cat: '+files[i]+': No such file or directory') ]; } if(this.fs[p].type==='dir'){ this.lastStatus=1; return [ lerr('cat: '+files[i]+': Is a directory') ]; }
      var m=this.fs[p]; if(!this.canRead(m)){ this.lastStatus=1; return [ lerr('cat: '+files[i]+': Permission denied'), ldiag('\u21b3 You lack read permission (file is '+this.modeStr(m)+', owner '+m.owner+'). Use sudo or adjust perms with chmod.') ]; }
      out.push(lout(m.content||'')); }
    this.lastStatus=0; return out.length?out:[ lout('') ];
  };
  LinuxShell.prototype.canRead = function(n){
    if(this.isPriv()) return true;
    var m=n.mode;
    if(n.owner===this.user) return !!(m&0o400);
    var inGrp=(this.users[this.user]&&this.users[this.user].groups||[]).indexOf(n.group)>=0;
    if(inGrp) return !!(m&0o040);
    return !!(m&0o004);
  };
  LinuxShell.prototype.cEcho = function(a, raw){
    // strip the leading "echo"
    var s = raw.replace(/^echo\s?/,'');
    // handle a redirect to a file: echo "x" > file
    var redir = raw.match(/>>?\s*(\S+)\s*$/);
    if(redir){ var p=this.resolve(redir[1]); if(!this.exists(this.parent(p))){ this.lastStatus=1; return [ lerr('bash: '+redir[1]+': No such file or directory') ]; } if(!this.exists(p)) this.mkNode(p,'file',0o644,this.user,this.user); this.lastStatus=0; return []; }
    s = s.replace(/^["']|["']$/g,'');
    this.lastStatus=0; return [ lout(s) ];
  };
  LinuxShell.prototype.cGrep = function(a){
    var pat=a.filter(function(x){return x[0]!=='-';});
    if(pat.length<1) return [ lerr('Usage: grep [OPTION]... PATTERNS [FILE]...'), ldiag('\u21b3 grep needs a pattern: "grep error /var/log/syslog".') ];
    this.lastStatus=0; return [ lout('') ];
  };
  LinuxShell.prototype.cFind = function(a){
    if(!a.length) return [ lout(this.cwd) ];
    var start=this.resolve(a[0]==='.'||a[0][0]!=='-'?a[0]:'.');
    if(a[0][0]!=='-' && !this.exists(start)){ this.lastStatus=1; return [ lerr('find: \u2018'+a[0]+'\u2019: No such file or directory') ]; }
    this.lastStatus=0; return [ lout(start) ];
  };
  LinuxShell.prototype.cLn = function(a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(files.length<2) return [ lerr('ln: missing file operand') ];
    var src=this.resolve(files[0]), dst=this.resolve(files[1]);
    if(a.indexOf('-s')<0 && !this.exists(src)){ this.lastStatus=1; return [ lerr('ln: failed to access \''+files[0]+'\': No such file or directory'), ldiag('\u21b3 Hard links need an existing target. Use "ln -s" for a symbolic link, which can point anywhere.') ]; }
    this.mkNode(dst,'file',0o777,this.user,this.user,'-> '+files[0]); this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cPager = function(cmd,a){
    var files=a.filter(function(x){return x[0]!=='-';});
    if(files.length){ var p=this.resolve(files[files.length-1]); if(!this.exists(p)){ this.lastStatus=1; return [ lerr(cmd+': cannot open \''+files[files.length-1]+'\' for reading: No such file or directory') ]; } var m=this.fs[p]; this.lastStatus=0; return [ lout(m.content||'') ]; }
    this.lastStatus=0; return [ lout('') ];
  };

  // ================= permissions =================
  LinuxShell.prototype.cChmod = function(a){
    var args=a.filter(function(x){return x[0]!=='-'||/^-?[0-7]/.test(x)===false;});
    var real=a.filter(function(x){return !(x[0]==='-'&&/^[Rrvc]+$/.test(x.slice(1)));});
    if(real.length<2) return [ lerr('chmod: missing operand'), ldiag('\u21b3 chmod needs a mode and a target: octal "chmod 640 file" or symbolic "chmod u+x script.sh".') ];
    var mode=real[0], target=real[real.length-1];
    var p=this.resolve(target);
    if(!this.exists(p)){ this.lastStatus=1; return [ lerr('chmod: cannot access \''+target+'\': No such file or directory') ]; }
    // validate mode
    var octal=/^[0-7]{3,4}$/.test(mode);
    var symbolic=/^[ugoa]*[+\-=][rwxXst]+$/.test(mode);
    if(!octal && !symbolic){ this.lastStatus=1; return [ lerr('chmod: invalid mode: \u2018'+mode+'\u2019'), ldiag('\u21b3 Mode must be octal (0-7 per digit, e.g. 755) or symbolic (u+x, g-w, o=r). "chmod 8xx" or "chmod rwx" are invalid.') ]; }
    var out=[];
    if(octal && mode==='777'){ out.push(ldiag('\u21b3 Note: 777 grants everyone full read/write/execute \u2014 a security risk. Prefer least privilege (e.g. 644 files, 755 dirs, 750 for private scripts).')); }
    if(octal){ this.fs[p].mode = parseInt(mode,8); }
    this.lastStatus=0; return out;
  };
  LinuxShell.prototype.cChown = function(a){
    var real=a.filter(function(x){return !(x[0]==='-'&&/^[Rrvc]+$/.test(x.slice(1)));});
    if(real.length<2) return [ lerr('chown: missing operand'), ldiag('\u21b3 Usage: "chown user:group file". Changing ownership needs root.') ];
    var nr=this.needRoot('chown'); if(nr) return nr;
    var spec=real[0], target=real[real.length-1], p=this.resolve(target);
    if(!this.exists(p)){ this.lastStatus=1; return [ lerr('chown: cannot access \''+target+'\': No such file or directory') ]; }
    var parts=spec.split(':'); var u=parts[0], g=parts[1];
    if(u && !this.users[u]){ this.lastStatus=1; return [ lerr('chown: invalid user: \u2018'+spec+'\u2019'), ldiag('\u21b3 User "'+u+'" does not exist. Create it first with useradd, or check the spelling.') ]; }
    if(g && !this.groups[g]){ this.lastStatus=1; return [ lerr('chown: invalid group: \u2018'+spec+'\u2019') ]; }
    if(u) this.fs[p].owner=u; if(g) this.fs[p].group=g; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cChgrp = function(a){
    var nr=this.needRoot('chgrp'); if(nr) return nr;
    if(a.length<2) return [ lerr('chgrp: missing operand') ];
    var g=a[0], p=this.resolve(a[a.length-1]);
    if(!this.groups[g]){ this.lastStatus=1; return [ lerr('chgrp: invalid group: \u2018'+g+'\u2019') ]; }
    if(!this.exists(p)){ this.lastStatus=1; return [ lerr('chgrp: cannot access \''+a[a.length-1]+'\': No such file or directory') ]; }
    this.fs[p].group=g; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cUmask = function(a){
    if(!a.length){ this.lastStatus=0; return [ lout('0022') ]; }
    if(!/^[0-7]{3,4}$/.test(a[0])){ this.lastStatus=1; return [ lerr('umask: '+a[0]+': octal number out of range'), ldiag('\u21b3 umask takes an octal value (e.g. 022 \u2192 new files 644, dirs 755).') ]; }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cAcl = function(cmd,a){
    if(cmd==='setfacl'){ var nr=this.needRoot('setfacl'); }
    this.lastStatus=0; return cmd==='getfacl'? [ lout('# file: '+(a[a.length-1]||'.')), lout('user::rw-'), lout('group::r--'), lout('other::r--') ] : [];
  };

  // ================= identity / users =================
  LinuxShell.prototype.cId = function(a){
    var who=a[0]||this.user; var u=this.users[who];
    if(!u){ this.lastStatus=1; return [ lerr('id: \u2018'+who+'\u2019: no such user') ]; }
    var grps=(u.groups||[who]).join(',');
    this.lastStatus=0; return [ lout('uid='+u.uid+'('+who+') gid='+u.uid+'('+who+') groups='+grps) ];
  };
  LinuxShell.prototype.cSu = function(a){
    var target=a.filter(function(x){return x[0]!=='-';})[0]||'root';
    if(!this.users[target]){ this.lastStatus=1; return [ lerr('su: user '+target+' does not exist') ]; }
    this.user=target; this.uid=this.users[target].uid; this.env.HOME=this.users[target].home; this.cwd=this.users[target].home; this.env.USER=target;
    this.lastStatus=0; return [ linfo('(switched to '+target+')') ];
  };
  LinuxShell.prototype.cUseradd = function(a){
    var nr=this.needRoot('useradd'); if(nr) return nr;
    var name=a.filter(function(x){return x[0]!=='-';}).pop();
    if(!name) return [ lerr('useradd: missing operand'), ldiag('\u21b3 Provide a username: "sudo useradd -m -s /bin/bash alice".') ];
    if(this.users[name]){ this.lastStatus=9; return [ lerr('useradd: user \''+name+'\' already exists') ]; }
    var uid=1001; while(Object.keys(this.users).some(function(u){return this.users[u].uid===uid;},this)) uid++;
    this.users[name]={uid:uid,home:'/home/'+name,shell:(a.indexOf('-s')>=0?a[a.indexOf('-s')+1]:'/bin/bash'),groups:[name]};
    this.groups[name]=[name];
    if(a.indexOf('-m')>=0) this.mkNode('/home/'+name,'dir',0o755,name,name);
    var out=[];
    if(a.indexOf('-m')<0) out.push(ldiag('\u21b3 Tip: without -m no home directory is created. Add -m (and -s /bin/bash) for an interactive login user.'));
    this.lastStatus=0; return out;
  };
  LinuxShell.prototype.cUsermod = function(a){
    var nr=this.needRoot('usermod'); if(nr) return nr;
    var name=a.filter(function(x){return x[0]!=='-';}).pop();
    if(!name || !this.users[name]){ this.lastStatus=6; return [ lerr('usermod: user \''+(name||'')+'\' does not exist') ]; }
    // -aG group  (append to supplementary groups)
    var gi=a.indexOf('-aG'); if(gi<0) gi=a.indexOf('-G');
    if(gi>=0){ var gname=a[gi+1]; (gname||'').split(',').forEach(function(g){ if(!this.groups[g]){ this.groups[g]=[]; } if(this.users[name].groups.indexOf(g)<0) this.users[name].groups.push(g); this.groups[g].push(name); },this);
      var warn=[]; if(a.indexOf('-G')>=0 && a.indexOf('-aG')<0){ warn.push(ldiag('\u21b3 Careful: "-G" WITHOUT "-a" REPLACES all supplementary groups. Use "-aG" to append, or you will drop the user from other groups.')); }
      this.lastStatus=0; return warn;
    }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cUserdel = function(a){
    var nr=this.needRoot('userdel'); if(nr) return nr;
    var name=a.filter(function(x){return x[0]!=='-';}).pop();
    if(!this.users[name]){ this.lastStatus=6; return [ lerr('userdel: user \''+(name||'')+'\' does not exist') ]; }
    delete this.users[name]; this.lastStatus=0;
    return a.indexOf('-r')<0 ? [ ldiag('\u21b3 Tip: add -r to also remove the user\u2019s home directory and mail spool.') ] : [];
  };
  LinuxShell.prototype.cGroupadd = function(a){
    var nr=this.needRoot('groupadd'); if(nr) return nr;
    var name=a.filter(function(x){return x[0]!=='-';}).pop();
    if(!name) return [ lerr('groupadd: missing operand') ];
    if(this.groups[name]){ this.lastStatus=9; return [ lerr('groupadd: group \''+name+'\' already exists') ]; }
    this.groups[name]=[]; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cPasswd = function(a){
    var target=a.filter(function(x){return x[0]!=='-';})[0]||this.user;
    if(target!==this.user && !this.isPriv()){ this.lastStatus=1; return [ lerr('passwd: You may not view or modify password information for '+target+'.'), ldiag('\u21b3 Only root can change another user\u2019s password. Use sudo.') ]; }
    if(!this.users[target]){ this.lastStatus=1; return [ lerr('passwd: user \''+target+'\' does not exist') ]; }
    this.lastStatus=0; return [ linfo('Changing password for user '+target+'. (enter new password twice)') ];
  };

  // ================= packages =================
  LinuxShell.prototype.cApt = function(cmd,a){
    this.pm='apt';
    var sub=a[0];
    var subs=['update','upgrade','install','remove','purge','autoremove','search','show','list','full-upgrade','dist-upgrade'];
    if(!sub){ this.lastStatus=1; return [ lerr(cmd+': missing subcommand'), ldiag('\u21b3 e.g. "sudo apt update", "sudo apt install nginx".') ]; }
    if(subs.indexOf(sub)<0){ this.lastStatus=1; return [ lerr('E: Invalid operation '+sub), ldiag('\u21b3 Valid apt subcommands: update, upgrade, install, remove, purge, search, show.') ]; }
    if(['update','upgrade','install','remove','purge','autoremove','full-upgrade','dist-upgrade'].indexOf(sub)>=0){ var nr=this.needRoot('apt'); if(nr) return nr; }
    if(sub==='install'){ var pkg=a[1]; if(!pkg) return [ lerr('E: You must give at least one package name') ]; this.pkgs[pkg]=true; return [ lout('Reading package lists... Done'), lout('Setting up '+pkg+' ...') ]; }
    if(sub==='update'){ return [ lout('Hit:1 http://deb.debian.org/debian stable InRelease'), lout('Reading package lists... Done') ]; }
    this.lastStatus=0; return [ lout('Reading package lists... Done') ];
  };
  LinuxShell.prototype.cDnf = function(cmd,a){
    this.pm=cmd;
    var sub=a[0];
    var subs=['install','remove','update','upgrade','search','info','list','provides','makecache','autoremove','group'];
    if(!sub){ this.lastStatus=1; return [ lerr(cmd+': no subcommand'), ldiag('\u21b3 e.g. "sudo dnf install httpd", "dnf search nginx".') ]; }
    if(subs.indexOf(sub)<0){ this.lastStatus=1; return [ lerr('No such command: '+sub+'.'), ldiag('\u21b3 Valid: install, remove, update, search, info, list, provides.') ]; }
    if(['install','remove','update','upgrade','autoremove'].indexOf(sub)>=0){ var nr=this.needRoot(cmd); if(nr) return nr; }
    if(sub==='install'){ var pkg=a[1]; if(!pkg) return [ lerr('Error: Need to pass a list of pkgs to install') ]; this.pkgs[pkg]=true; return [ lout('Dependencies resolved.'), lout('Complete!') ]; }
    this.lastStatus=0; return [ lout('Complete!') ];
  };
  LinuxShell.prototype.cRpm = function(a){
    var flags=a.filter(function(x){return x[0]==='-';}).join('');
    if(/i/.test(flags) && !/q/.test(flags)){ var nr=this.needRoot('rpm'); if(nr) return nr; }
    this.lastStatus=0;
    if(/qa/.test(flags)) return [ lout('bash-5.1.8-6.el9.x86_64'), lout('systemd-252-14.el9.x86_64') ];
    return [];
  };
  LinuxShell.prototype.cDpkg = function(a){
    this.lastStatus=0;
    if(a.indexOf('-l')>=0) return [ lout('ii  bash        5.1-6   amd64  GNU Bourne Again SHell') ];
    if(a.indexOf('-i')>=0){ var nr=this.needRoot('dpkg'); if(nr) return nr; }
    return [];
  };

  // ================= systemd =================
  LinuxShell.prototype.cSystemctl = function(a){
    var sub=a[0], svc=(a[1]||'').replace(/\.service$/,'');
    if(!sub){ this.lastStatus=0; return [ lout('UNIT                 LOAD   ACTIVE SUB     DESCRIPTION'), lout('sshd.service         loaded active running OpenSSH server daemon') ]; }
    var mutating=['start','stop','restart','reload','enable','disable','mask','unmask','daemon-reload'];
    if(mutating.indexOf(sub)>=0 && sub!=='daemon-reload'){
      if(!svc){ this.lastStatus=1; return [ lerr('Too few arguments.'), ldiag('\u21b3 Name the unit: "sudo systemctl '+sub+' sshd".') ]; }
      var nr=this.needRoot('systemctl'); if(nr) return nr;
      if(!this.services[svc] && !this.pkgs[svc]){ this.lastStatus=5; return [ lerr('Failed to '+sub+' '+svc+'.service: Unit '+svc+'.service not found.'), ldiag('\u21b3 That unit is not installed. Check the exact name with "systemctl list-units", or install the package that provides it.') ]; }
      if(!this.services[svc]) this.services[svc]={active:false,enabled:false};
      if(sub==='start'||sub==='restart'||sub==='reload') this.services[svc].active=true;
      if(sub==='stop') this.services[svc].active=false;
      if(sub==='enable') this.services[svc].enabled=true;
      if(sub==='disable') this.services[svc].enabled=false;
      this.lastStatus=0; return [];
    }
    if(sub==='daemon-reload'){ var nr2=this.needRoot('systemctl'); if(nr2) return nr2; this.lastStatus=0; return []; }
    if(sub==='status'){ if(!svc){ this.lastStatus=0; return [ lout('\u25cf running') ]; } var s=this.services[svc]; if(!s){ this.lastStatus=4; return [ lerr('Unit '+svc+'.service could not be found.') ]; }
      this.lastStatus = s.active?0:3;
      return [ lout('\u25cf '+svc+'.service - '+svc), lout('     Loaded: loaded (/usr/lib/systemd/system/'+svc+'.service; '+(s.enabled?'enabled':'disabled')+')'), lout('     Active: '+(s.active?'active (running)':'inactive (dead)')) ]; }
    if(sub==='is-active'){ var s2=this.services[svc]; this.lastStatus=(s2&&s2.active)?0:3; return [ lout(s2&&s2.active?'active':'inactive') ]; }
    if(sub==='is-enabled'){ var s3=this.services[svc]; this.lastStatus=(s3&&s3.enabled)?0:1; return [ lout(s3&&s3.enabled?'enabled':'disabled') ]; }
    if(sub==='list-units'||sub==='list-unit-files'){ this.lastStatus=0; return [ lout('sshd.service    loaded active running') ]; }
    if(sub==='get-default'){ this.lastStatus=0; return [ lout('graphical.target') ]; }
    if(sub==='set-default'||sub==='isolate'){ var nr3=this.needRoot('systemctl'); if(nr3) return nr3; this.lastStatus=0; return []; }
    this.lastStatus=1; return [ lerr('Unknown operation '+sub+'.'), ldiag('\u21b3 Common verbs: start, stop, restart, enable, disable, status, is-active, daemon-reload.') ];
  };
  LinuxShell.prototype.cServiceLegacy = function(a){
    var svc=a[0], sub=a[1];
    if(!svc||!sub) return [ lerr('Usage: service <name> start|stop|restart|status'), ldiag('\u21b3 On systemd distros prefer "systemctl '+(sub||'status')+' '+(svc||'<unit>')+'".') ];
    this.lastStatus=0; return [ linfo('(legacy wrapper \u2192 systemctl '+sub+' '+svc+')') ];
  };
  LinuxShell.prototype.cJournalctl = function(a){
    this.lastStatus=0;
    return [ lout('-- Logs begin at Mon 2026-07-13 --'), lout('Jul 14 21:30:01 '+this.hostname+' sshd[1099]: Server listening on 0.0.0.0 port 22.') ];
  };

  // ================= process =================
  LinuxShell.prototype.cKill = function(a,byName){
    var target=a.filter(function(x){return x[0]!=='-';})[0];
    if(!target){ this.lastStatus=1; return [ lerr((byName?'killall':'kill')+': missing operand'), ldiag('\u21b3 kill needs a PID (e.g. "kill 1234" or "kill -9 1234"); killall/pkill take a process name.') ]; }
    if(!byName && !/^\d+$/.test(target)){ this.lastStatus=1; return [ lerr('kill: '+target+': arguments must be process or job IDs'), ldiag('\u21b3 kill expects a numeric PID. To kill by name use "pkill '+target+'" or "killall '+target+'".') ]; }
    this.lastStatus=0; return [];
  };

  // ================= storage =================
  LinuxShell.prototype.cMount = function(a){
    if(!a.length){ this.lastStatus=0; return [ lout('/dev/mapper/vg-root on / type ext4 (rw,relatime)'), lout('/dev/sda1 on /boot type ext4 (rw,relatime)') ]; }
    var nr=this.needRoot('mount'); if(nr) return nr;
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cDiskTool = function(cmd,a){
    var nr=this.needRoot(cmd); if(nr) return nr;
    if(cmd==='fdisk' && a.indexOf('-l')>=0){ this.lastStatus=0; return [ lout('Disk /dev/sda: 100 GiB, 107374182400 bytes') ]; }
    this.lastStatus=0; return [ linfo('(interactive '+cmd+' session)') ];
  };
  LinuxShell.prototype.cLvm = function(cmd,a){
    var display=/s$|display$/.test(cmd);
    if(!display){ var nr=this.needRoot(cmd); if(nr) return nr; }
    this.lastStatus=0;
    if(cmd==='vgs') return [ lout('  VG   #PV #LV #SN Attr   VSize   VFree'), lout('  vg     1   1   0 wz--n- <99.00g    0 ') ];
    if(cmd==='lvs') return [ lout('  LV   VG Attr       LSize'), lout('  root vg -wi-ao---- <99.00g') ];
    if(cmd==='pvs') return [ lout('  PV         VG Fmt  Attr PSize   PFree'), lout('  /dev/sda2  vg lvm2 a--  <99.00g    0 ') ];
    return [];
  };

  // ================= kernel =================
  LinuxShell.prototype.cUname = function(a){
    if(a.indexOf('-a')>=0) return [ lout('Linux '+this.hostname+' 6.6.0-lab #1 SMP x86_64 GNU/Linux') ];
    if(a.indexOf('-r')>=0) return [ lout('6.6.0-lab') ];
    this.lastStatus=0; return [ lout('Linux') ];
  };

  // ================= networking =================
  LinuxShell.prototype.cIp = function(a){
    var obj=a[0];
    if(!obj){ this.lastStatus=1; return [ lerr('Usage: ip [ OPTIONS ] OBJECT { COMMAND | help }'), ldiag('\u21b3 Try "ip addr" (show IPs), "ip route" (routing table), "ip link" (interfaces).') ]; }
    if(/^a/.test(obj)) return [ lout('1: lo: <LOOPBACK,UP> mtu 65536'), lout('    inet 127.0.0.1/8 scope host lo'), lout('2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500'), lout('    inet 192.168.1.50/24 brd 192.168.1.255 scope global eth0') ];
    if(/^r/.test(obj)) return [ lout('default via 192.168.1.1 dev eth0 proto dhcp'), lout('192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.50') ];
    if(/^l/.test(obj)) return [ lout('1: lo: <LOOPBACK,UP> mtu 65536'), lout('2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500') ];
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cSs = function(a){
    this.lastStatus=0; return [ lout('State   Recv-Q  Send-Q  Local Address:Port'), lout('LISTEN  0       128           0.0.0.0:22') ];
  };
  LinuxShell.prototype.cPing = function(a){
    var host=a.filter(function(x){return x[0]!=='-';})[0];
    if(!host){ this.lastStatus=1; return [ lerr('ping: usage error: Destination address required') ]; }
    this.lastStatus=0; return [ lout('PING '+host+' 56(84) bytes of data.'), lout('64 bytes from '+host+': icmp_seq=1 ttl=64 time=0.42 ms'), lout('--- '+host+' ping statistics ---'), lout('1 packets transmitted, 1 received, 0% packet loss') ];
  };
  LinuxShell.prototype.cDns = function(cmd,a){
    var host=a.filter(function(x){return x[0]!=='-';})[0]||'example.com';
    this.lastStatus=0; return [ lout(';; ANSWER SECTION:'), lout(host+'.  300  IN  A  93.184.216.34') ];
  };
  LinuxShell.prototype.cNmcli = function(a){
    if(!a.length){ this.lastStatus=0; return [ lout('eth0: connected to eth0') ]; }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cCurl = function(cmd,a){
    var url=a.filter(function(x){return x[0]!=='-';})[0];
    if(!url){ this.lastStatus=2; return [ lerr(cmd+': try \''+cmd+' --help\' for more information'), ldiag('\u21b3 Provide a URL: "curl https://example.com". Add -O to save, -I for headers only.') ]; }
    this.lastStatus=0; return [ lout('<!DOCTYPE html><html>... (response body)') ];
  };

  // ================= security =================
  LinuxShell.prototype.cSshKeygen = function(a){
    this.lastStatus=0; return [ lout('Generating public/private '+(a.indexOf('-t')>=0?a[a.indexOf('-t')+1]:'rsa')+' key pair.'), lout('Your identification has been saved in /home/'+this.user+'/.ssh/id_'+(a.indexOf('-t')>=0?a[a.indexOf('-t')+1]:'rsa')), lout('Your public key has been saved in .../id.pub') ];
  };
  LinuxShell.prototype.cSetenforce = function(a){
    var nr=this.needRoot('setenforce'); if(nr) return nr;
    var v=a[0];
    if(v!=='0'&&v!=='1'&&!/^(enforcing|permissive)$/i.test(v||'')){ this.lastStatus=1; return [ lerr('usage:  setenforce [ Enforcing | Permissive | 1 | 0 ]'), ldiag('\u21b3 1/Enforcing turns SELinux on; 0/Permissive only logs. This is temporary \u2014 edit /etc/selinux/config for a persistent change.') ]; }
    this.selinux = (v==='1'||/enforcing/i.test(v))?'enforcing':'permissive'; this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cFirewallCmd = function(a){
    var nr; var joined=a.join(' ');
    if(/--reload|--add-|--remove-|--set-|--permanent/.test(joined)){ nr=this.needRoot('firewall-cmd'); if(nr) return nr; }
    if(/--state/.test(joined)){ this.lastStatus=this.firewall.running?0:252; return [ lout(this.firewall.running?'running':'not running') ]; }
    if(/--list-all/.test(joined)){ this.lastStatus=0; return [ lout('public (active)'), lout('  services: ssh dhcpv6-client'), lout('  ports:') ]; }
    if(/--add-service/.test(joined)){ var m=joined.match(/--add-service=(\S+)/); this.firewall.zones.public.services.push(m?m[1]:'svc');
      var extra=[]; if(!/--permanent/.test(joined)) extra.push(ldiag('\u21b3 Without --permanent this rule is lost on reload/reboot. Add --permanent then run "firewall-cmd --reload".')); this.lastStatus=0; return extra; }
    if(/--reload/.test(joined)){ this.lastStatus=0; return []; }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cUfw = function(a){
    var nr=this.needRoot('ufw'); if(nr) return nr;
    var sub=a[0];
    if(sub==='status'){ this.lastStatus=0; return [ lout('Status: active') ]; }
    if(['enable','disable','allow','deny','reject','default','reset'].indexOf(sub)<0 && sub){ this.lastStatus=1; return [ lerr('ERROR: Invalid syntax'), ldiag('\u21b3 e.g. "sudo ufw allow 22/tcp", "sudo ufw enable".') ]; }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cNftIptables = function(cmd,a){
    var nr=this.needRoot(cmd); if(nr) return nr;
    this.lastStatus=0; return [];
  };

  // ================= containers =================
  LinuxShell.prototype.cContainer = function(cmd,a){
    var sub=a[0];
    var subs=['run','ps','build','pull','push','images','stop','start','rm','rmi','exec','logs','network','volume','compose','inspect','tag'];
    if(!sub){ this.lastStatus=1; return [ lerr('"'+cmd+'" requires a command'), ldiag('\u21b3 e.g. "'+cmd+' run -d -p 8080:80 nginx", "'+cmd+' ps".') ]; }
    if(subs.indexOf(sub)<0){ this.lastStatus=1; return [ lerr(cmd+': \''+sub+'\' is not a '+cmd+' command.'), ldiag('\u21b3 Common subcommands: run, ps, build, pull, images, stop, rm, exec, logs.') ]; }
    if(cmd==='docker' && !this.isPriv() && (this.users[this.user]&&this.users[this.user].groups||[]).indexOf('docker')<0){
      this.lastStatus=1; return [ lerr('permission denied while trying to connect to the Docker daemon socket'), ldiag('\u21b3 Add your user to the "docker" group ("sudo usermod -aG docker '+this.user+'") and re-login, or use sudo. (podman is rootless and avoids this.)') ]; }
    if(sub==='ps'){ this.lastStatus=0; return [ lout('CONTAINER ID   IMAGE     COMMAND   STATUS         PORTS     NAMES') ]; }
    if(sub==='run'){ this.lastStatus=0; return [ lout('(container started)') ]; }
    if(sub==='images'){ this.lastStatus=0; return [ lout('REPOSITORY   TAG       IMAGE ID       SIZE'), lout('nginx        latest    abc123def456   187MB') ]; }
    this.lastStatus=0; return [];
  };

  // ================= scheduling =================
  LinuxShell.prototype.cCrontab = function(a){
    if(a.indexOf('-l')>=0){ this.lastStatus=0; return [ lout('0 2 * * * /usr/local/bin/backup.sh') ]; }
    if(a.indexOf('-e')>=0){ this.lastStatus=0; return [ linfo('(opens your crontab in $EDITOR)'), ldiag('\u21b3 Format: "min hour dom mon dow command". e.g. "0 2 * * * /path/script.sh" runs daily at 02:00.') ]; }
    this.lastStatus=0; return [];
  };

  // ================= scripting / dev =================
  LinuxShell.prototype.cPython = function(a){
    if(a.indexOf('-c')>=0){ this.lastStatus=0; return [ lout('(python one-liner executed)') ]; }
    var f=a.filter(function(x){return x[0]!=='-';})[0];
    if(f){ var p=this.resolve(f); if(!this.exists(p)){ this.lastStatus=2; return [ lerr('python3: can\'t open file \''+f+'\': [Errno 2] No such file or directory') ]; } this.lastStatus=0; return [ lout('(ran '+f+')') ]; }
    this.lastStatus=0; return [ linfo('Python 3.11 (interactive) \u2014 type exit() to quit') ];
  };
  LinuxShell.prototype.cGit = function(a){
    var sub=a[0];
    if(!sub){ this.lastStatus=1; return [ lout('usage: git [--version] [--help] <command> [<args>]') ]; }
    var subs=['init','clone','add','commit','status','log','branch','checkout','switch','merge','push','pull','stash','remote','diff','reset','rm','tag','fetch','rebase','restore','config'];
    if(subs.indexOf(sub)<0){ this.lastStatus=1; return [ lerr('git: \''+sub+'\' is not a git command. See \'git --help\'.'), ldiag('\u21b3 Common: init, clone, add, commit, status, branch, checkout, merge, push, pull, stash, log.') ]; }
    if(sub==='init'){ this.gitRepo=true; this.lastStatus=0; return [ lout('Initialized empty Git repository in '+this.cwd+'/.git/') ]; }
    if(sub==='clone'){ this.gitRepo=true; this.lastStatus=0; return [ lout('Cloning into \''+((a[1]||'repo').split('/').pop().replace(/\.git$/,''))+'\'...'), lout('done.') ]; }
    if(!this.gitRepo && ['add','commit','status','log','branch','checkout','switch','merge','push','pull','stash','diff','reset','rm','tag','fetch','rebase','restore'].indexOf(sub)>=0){
      this.lastStatus=128; return [ lerr('fatal: not a git repository (or any of the parent directories): .git'), ldiag('\u21b3 Run "git init" here first, or "cd" into an existing repository.') ]; }
    if(sub==='add'){ if(!a[1]){ this.lastStatus=1; return [ lerr('Nothing specified, nothing added.'), ldiag('\u21b3 Stage files: "git add file" or "git add ." for everything.') ]; } this.gitStaged.push(a[1]); this.lastStatus=0; return []; }
    if(sub==='commit'){ if(a.indexOf('-m')<0){ this.lastStatus=0; return [ linfo('(opens editor for commit message)'), ldiag('\u21b3 Faster: "git commit -m \"message\"".') ]; } if(!this.gitStaged.length){ this.lastStatus=1; return [ lout('nothing to commit, working tree clean'), ldiag('\u21b3 Stage changes with "git add" before committing.') ]; } this.gitCommits++; this.gitStaged=[]; this.lastStatus=0; return [ lout('[main '+(this.gitCommits)+'] '+(a[a.indexOf('-m')+1]||'commit')), lout(' 1 file changed') ]; }
    if(sub==='status'){ this.lastStatus=0; return [ lout('On branch '+this.gitBranch), lout(this.gitStaged.length?'Changes to be committed:':'nothing to commit, working tree clean') ]; }
    if(sub==='log'){ this.lastStatus=0; return this.gitCommits? [ lout('commit a1b2c3 (HEAD -> '+this.gitBranch+')'), lout('    latest change') ] : [ lerr('fatal: your current branch \''+this.gitBranch+'\' does not have any commits yet') ]; }
    if(sub==='branch'){ if(a[1]){ this.lastStatus=0; return []; } this.lastStatus=0; return [ lout('* '+this.gitBranch) ]; }
    if(sub==='checkout'||sub==='switch'){ if(a.indexOf('-b')>=0||sub==='switch'&&a.indexOf('-c')>=0){ this.gitBranch=a[a.length-1]; } this.lastStatus=0; return [ lout('Switched to branch \''+(a[a.length-1]||this.gitBranch)+'\'') ]; }
    if(sub==='push'||sub==='pull'||sub==='fetch'){ this.lastStatus=0; return [ lout('Everything up-to-date') ]; }
    if(sub==='stash'){ this.lastStatus=0; return [ lout('Saved working directory and index state WIP on '+this.gitBranch) ]; }
    this.lastStatus=0; return [];
  };
  LinuxShell.prototype.cAnsible = function(cmd,a){
    if(cmd==='ansible-playbook'){ var f=a.filter(function(x){return x[0]!=='-';})[0]; if(!f){ this.lastStatus=1; return [ lerr('ERROR! You must specify a playbook file to run'), ldiag('\u21b3 e.g. "ansible-playbook -i inventory site.yml".') ]; } this.lastStatus=0; return [ lout('PLAY [all] ***'), lout('TASK [Gathering Facts] ***'), lout('PLAY RECAP ***  ok=2  changed=1  failed=0') ]; }
    if(!a.length){ this.lastStatus=1; return [ lerr('usage: ansible <host-pattern> [options]'), ldiag('\u21b3 e.g. "ansible all -m ping -i inventory".') ]; }
    this.lastStatus=0; return [ lout('host | SUCCESS => {"changed": false, "ping": "pong"}') ];
  };

  // expose (parity with ios_sim.js injection style)
  // (LinuxShell is referenced by the app IIFE after injection)
