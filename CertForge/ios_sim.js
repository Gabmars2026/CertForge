  // ============================================================
  //  Enterprise IOS Simulator  (CCNA -> CCNP -> CCIE grammar)
  //  Rule-based. Tracks device state across many features and
  //  emits authentic IOS output PLUS plain-English diagnostics.
  //
  //  NOTE: This is a configuration-grammar + state simulator, not
  //  a full control-plane emulator. It validates syntax, mode,
  //  dependencies and value ranges, tracks configured state, and
  //  renders realistic show output. It does not run real routing
  //  convergence (use CML/GNS3 for protocol FSM behaviour).
  // ============================================================
  function IOSDevice(hostname){
    this.hostname = hostname || 'Router';
    this.mode = 'user';
    this.modeStack = [];         // for nested exit handling
    this.ctx = {};
    this.enableSecret = null;
    this.enablePassword = null;
    this.interfaces = {};
    this.vlans = {1:{name:'default'}};
    this.staticRoutes = [];      // {net,mask,nh,ad,vrf}
    this.staticRoutes6 = [];     // {prefix,nh}
    this.ospf = null;            // {pid,rid,networks:[],passive:[]}
    this.ospf6 = null;
    this.eigrp = null;           // {asn,networks:[],named:false}
    this.bgp = null;             // {asn,rid,neighbors:{ip:{remoteAs,desc,shut,ebgpMh,updateSrc,af}},networks:[]}
    this.rip = null;
    this.lines = {};
    this.acls = {};              // name/num -> {type:'standard|extended', entries:[]}
    this.prefixLists = {};
    this.routeMaps = {};         // name -> [{seq,action,match:[],set:[]}]
    this.classMaps = {};
    this.policyMaps = {};
    this.vrfs = {};              // name -> {rd,rt:[]}
    this.hsrpGroups = [];        // {intf,grp,vip,pri,preempt,ver}
    this.trackObjs = {};
    this.natInside = [];         // interface names
    this.natOutside = [];
    this.natRules = [];          // {type:'static|overload|pool', ...}
    this.dhcpPools = {};
    this.ntpServers = [];
    this.aaa = false;
    this.users = {};
    this.banner = null;
    this.savedConfig = false;
    this.domainName = null;
    this.cryptoKey = false;
    this.spanningTreeMode = 'pvst';
    this.etherchannels = {};     // po# -> {mode,members:[]}
    this.ipRoutingOn = true;
  }

  // ---- interface normalization ----
  var IFRE = /^(g|gi|gig|gigabitethernet|te|tengig|tengigabitethernet|f|fa|fast|fastethernet|e|eth|ethernet|s|se|serial|lo|loopback|vlan|vl|po|port-channel|tu|tunnel|nu|null|bd|bdi)\s*([0-9]+([\/.:][0-9]+)*)$/i;
  function normIf(raw){
    if(!raw) return null;
    var m = raw.trim().match(IFRE);
    if(!m) return null;
    var t=m[1].toLowerCase(), n=m[2];
    var map={g:'GigabitEthernet',gi:'GigabitEthernet',gig:'GigabitEthernet',gigabitethernet:'GigabitEthernet',
      te:'TenGigabitEthernet',tengig:'TenGigabitEthernet',tengigabitethernet:'TenGigabitEthernet',
      f:'FastEthernet',fa:'FastEthernet',fast:'FastEthernet',fastethernet:'FastEthernet',
      e:'Ethernet',eth:'Ethernet',ethernet:'Ethernet',
      s:'Serial',se:'Serial',serial:'Serial',
      lo:'Loopback',loopback:'Loopback',
      vlan:'Vlan',vl:'Vlan',
      po:'Port-channel','port-channel':'Port-channel',
      tu:'Tunnel',tunnel:'Tunnel',nu:'Null',null:'Null'};
    return (map[t]||t)+n;
  }
  function octetsOk(s){ return /^(\d{1,3}\.){3}\d{1,3}$/.test(s) && s.split('.').every(function(o){return +o>=0 && +o<=255;}); }
  function isMask(s){
    if(!octetsOk(s)) return false;
    // must be contiguous
    var bits=s.split('.').map(function(o){return (+o).toString(2).padStart(8,'0');}).join('');
    return /^1*0*$/.test(bits);
  }
  function isIp(s){ return octetsOk(s); }
  function isWildcard(s){ return octetsOk(s); }
  function isIpv6(s){ return /^[0-9a-f:]+(\/\d{1,3})?$/i.test(s) && s.indexOf(':')>=0; }
  function maskToWild(m){ return m.split('.').map(function(o){return 255-(+o);}).join('.'); }
  function looksLikeWildcard(s){
    // heuristic: wildcard masks usually have low-order bits set (e.g. 0.0.0.255)
    if(!octetsOk(s)) return false;
    var bits=s.split('.').map(function(o){return (+o).toString(2).padStart(8,'0');}).join('');
    return /^0*1*$/.test(bits) && !/^1*0*$/.test(bits);
  }

  // ---- result helpers ----
  function out(t){return {t:t,cls:'out'};}
  function err(t){return {t:t,cls:'err'};}
  function info(t){return {t:t,cls:'info'};}
  function diag(t){return {t:t,cls:'diag'};}   // plain-English "why / how to fix"

  // Standard IOS errors + a diagnostic explanation line.
  function invalid(why){ var r=[err("% Invalid input detected at '^' marker.")]; if(why) r.push(diag('\u21b3 '+why)); return r; }
  function incomplete(why){ var r=[err('% Incomplete command.')]; if(why) r.push(diag('\u21b3 '+why)); return r; }
  function ambiguous(why){ var r=[err('% Ambiguous command:')]; if(why) r.push(diag('\u21b3 '+why)); return r; }

  IOSDevice.prototype.prompt = function(){
    var h=this.hostname;
    switch(this.mode){
      case 'user':      return h+'>';
      case 'priv':      return h+'#';
      case 'config':    return h+'(config)#';
      case 'if':        return h+'(config-if)#';
      case 'subif':     return h+'(config-subif)#';
      case 'if-range':  return h+'(config-if-range)#';
      case 'line':      return h+'(config-line)#';
      case 'vlan':      return h+'(config-vlan)#';
      case 'router':    return h+'(config-router)#';
      case 'router-af': return h+'(config-router-af)#';
      case 'acl-std':   return h+'(config-std-nacl)#';
      case 'acl-ext':   return h+'(config-ext-nacl)#';
      case 'route-map': return h+'(config-route-map)#';
      case 'vrf':       return h+'(config-vrf)#';
      case 'class-map': return h+'(config-cmap)#';
      case 'policy-map':return h+'(config-pmap)#';
      case 'pmap-c':    return h+'(config-pmap-c)#';
      case 'dhcp':      return h+'(dhcp-config)#';
      case 'prefix':    return h+'(config)#';
      default:          return h+'#';
    }
  };

  function toks(line){ return line.trim().split(/\s+/).filter(Boolean); }
  function kw(tok, full){ if(!tok) return false; return full.toLowerCase().indexOf(tok.toLowerCase())===0; }
  function eq(tok, full){ return tok && tok.toLowerCase()===full.toLowerCase(); }

  IOSDevice.prototype.exec = function(rawLine){
    var line = rawLine.replace(/\t/g,' ');
    var trimmed = line.trim();
    if(trimmed==='') return [];
    if(trimmed[0]==='!') return [];
    var t = toks(trimmed);
    var c0 = t[0].toLowerCase();

    // universal navigation
    if(kw(c0,'exit') && t.length===1) return this.doExit();
    if(kw(c0,'end') && t.length===1){ if(this.mode!=='user'&&this.mode!=='priv'){ this.mode='priv'; this.ctx={}; this.modeStack=[]; } return []; }
    if(c0==='logout' || (kw(c0,'disable')&&t.length===1&&this.mode==='priv')){ this.mode='user'; this.ctx={}; this.modeStack=[]; return []; }
    if(c0==='do'){
      // "do <cmd>" runs an EXEC command from any config sub-mode; tolerate it in priv too.
      if(this.mode==='user'||this.mode==='priv') return this.exec(t.slice(1).join(' '));
      var saved=this.mode, savedCtx=this.ctx, savedStack=this.modeStack;
      this.mode='priv';
      var r=this.exec(t.slice(1).join(' '));
      this.mode=saved; this.ctx=savedCtx; this.modeStack=savedStack; return r;
    }

    switch(this.mode){
      case 'user':      return this.userMode(t,c0,trimmed);
      case 'priv':      return this.privMode(t,c0,trimmed);
      case 'config':    return this.configMode(t,c0,trimmed);
      case 'if':
      case 'subif':
      case 'if-range':  return this.ifMode(t,c0,trimmed);
      case 'line':      return this.lineMode(t,c0,trimmed);
      case 'vlan':      return this.vlanMode(t,c0,trimmed);
      case 'router':    return this.routerMode(t,c0,trimmed);
      case 'router-af': return this.routerAfMode(t,c0,trimmed);
      case 'acl-std':
      case 'acl-ext':   return this.aclMode(t,c0,trimmed);
      case 'route-map': return this.routeMapMode(t,c0,trimmed);
      case 'vrf':       return this.vrfMode(t,c0,trimmed);
      case 'class-map': return this.classMapMode(t,c0,trimmed);
      case 'policy-map':return this.policyMapMode(t,c0,trimmed);
      case 'pmap-c':    return this.pmapCMode(t,c0,trimmed);
      case 'dhcp':      return this.dhcpMode(t,c0,trimmed);
      default:          return [err('% Unknown mode')];
    }
  };

  IOSDevice.prototype.doExit = function(){
    switch(this.mode){
      case 'user': return [];
      case 'priv': this.mode='user'; return [];
      case 'config': this.mode='priv'; this.ctx={}; return [];
      case 'router-af': this.mode='router'; return [];
      case 'pmap-c': this.mode='policy-map'; return [];
      default:
        // any config sub-mode returns to global config
        this.mode='config'; this.ctx={}; return [];
    }
  };

  // ---------- USER ----------
  IOSDevice.prototype.userMode = function(t,c0,line){
    if(kw(c0,'enable')){ this.mode='priv'; return []; }
    if(kw(c0,'ping'))   return this.doPing(t);
    if(kw(c0,'traceroute')) return this.doTrace(t);
    if(kw(c0,'telnet')||kw(c0,'ssh')) return [out('Trying '+ (t[1]||'') +' ... (simulated session)')];
    if(kw(c0,'show')){
      var s=(t[1]||'').toLowerCase();
      if(kw(s,'version')||kw(s,'clock')||kw(s,'ip')) return this.doShow(t); // user-visible shows
      return [err("% Invalid input detected at '^' marker."), diag('\u21b3 Most show commands need privileged EXEC. Type "enable" first.')];
    }
    return invalid('Unknown user-EXEC command. Try "enable" to reach privileged mode.');
  };

  // ---------- PRIVILEGED ----------
  IOSDevice.prototype.privMode = function(t,c0,line){
    if(kw(c0,'configure')){
      if(t[1] && !kw(t[1],'terminal')) return invalid('Use "configure terminal" to enter global configuration.');
      this.mode='config';
      return [info('Enter configuration commands, one per line.  End with CNTL/Z.')];
    }
    if(kw(c0,'show'))   return this.doShow(t);
    if(kw(c0,'ping'))   return this.doPing(t);
    if(kw(c0,'traceroute')) return this.doTrace(t);
    if(kw(c0,'telnet')||kw(c0,'ssh')) return [out('Trying '+(t[1]||'')+' ... (simulated session)')];
    if(kw(c0,'write')){ this.savedConfig=true; return [out('Building configuration...'), out('[OK]')]; }
    if(kw(c0,'copy')){
      this.savedConfig=true;
      return [out('Destination filename [startup-config]?'), out('Building configuration...'), out('[OK]')];
    }
    if(kw(c0,'erase')) return [out('Erasing the nvram filesystem will remove all configuration files! Continue? [confirm]'), info('(simulated \u2014 running config kept)')];
    if(kw(c0,'reload')) return [info('Proceed with reload? [confirm]  (simulated \u2014 device state kept)')];
    if(kw(c0,'clock')){
      if(t[1]&&kw(t[1],'set')) return [];
      return [out('*'+new Date().toTimeString().slice(0,8)+'.000 UTC Tue Jul 14 2026')];
    }
    if(kw(c0,'terminal')) return [];
    if(kw(c0,'clear')) return [];
    if(kw(c0,'debug')||kw(c0,'undebug')) return [info((kw(c0,'debug')?'':'no ')+'debugging enabled (simulated)')];
    if(kw(c0,'no')&&kw(t[1]||'','debug')) return [info('debugging disabled')];
    return invalid('Unknown privileged command. Use "configure terminal" to change config, or a show/ping/traceroute.');
  };

  // ---------- GLOBAL CONFIG ----------
  IOSDevice.prototype.configMode = function(t,c0,line){
    var neg = (c0==='no'); var h = neg? (t[1]||'').toLowerCase():c0;
    var A = neg? t.slice(1) : t;  // A[0] is the real command keyword

    if(kw(h,'hostname')){ if(!A[1]) return incomplete('hostname requires a name, e.g. "hostname R1".'); this.hostname=A[1]; return []; }

    if(kw(h,'interface')){
      // range?
      if(A[1] && kw(A[1],'range')){
        this.mode='if-range'; this.ctx={range:A.slice(2).join(' ')};
        return [];
      }
      var raw=A.slice(1).join('');
      var name=normIf(raw);
      if(!name) return invalid('Interface name not recognized. Try e.g. "interface gi0/1", "interface vlan 10", "interface lo0".');
      if(!this.interfaces[name]) this.interfaces[name]=this.newIf(name);
      this.mode = /\./.test(name) ? 'subif' : 'if';
      this.ctx={intf:name}; return [];
    }

    if(kw(h,'vlan')){
      var id=parseInt(A[1],10);
      if(isNaN(id)) return invalid('vlan needs a numeric ID 1-4094, e.g. "vlan 10".');
      if(id<1||id>4094) return [err('% Invalid input detected at \'^\' marker.'), diag('\u21b3 VLAN ID '+id+' out of range. Valid VLAN IDs are 1-4094.')];
      if(neg){ if(id!==1) delete this.vlans[id]; return []; }
      if(!this.vlans[id]) this.vlans[id]={name:'VLAN'+(''+id).padStart(4,'0')};
      this.mode='vlan'; this.ctx={vlan:id}; return [];
    }

    if(kw(h,'line')){
      var lt=(A[1]||'').toLowerCase(); var rng=A.slice(2).join(' ');
      if(!/^(con|vty|aux|tty)/.test(lt)) return invalid('line type must be console/vty/aux, e.g. "line vty 0 4".');
      this.mode='line'; this.ctx={line:lt+' '+rng}; if(!this.lines[this.ctx.line])this.lines[this.ctx.line]={}; return [];
    }

    if(kw(h,'enable')){
      if(kw(A[1]||'','secret')){ this.enableSecret=A.slice(2).join(' ')||'<hash>'; return []; }
      if(kw(A[1]||'','password')){ this.enablePassword=A.slice(2).join(' '); return []; }
      return incomplete('Use "enable secret <pw>" (preferred) or "enable password <pw>".');
    }

    // ---- ip ... ----
    if(kw(h,'ip')){
      var s1=(A[1]||'').toLowerCase();
      if(kw(s1,'route')) return this.ipRoute(A,neg);
      if(kw(s1,'domain-name')||eq(s1,'domain-name')){ this.domainName=A[2]; return []; }
      if(kw(s1,'domain')&&kw(A[2]||'','name')){ this.domainName=A[3]; return []; }
      if(kw(s1,'routing')){ this.ipRoutingOn=!neg; return []; }
      if(kw(s1,'access-list')) return this.ipAccessList(A,neg);
      if(kw(s1,'nat')) return this.ipNat(A,neg);
      if(kw(s1,'dhcp')){
        if(kw(A[2]||'','pool')){ var pn=A[3]; if(!pn) return incomplete('DHCP pool needs a name: "ip dhcp pool LAN".'); this.dhcpPools[pn]=this.dhcpPools[pn]||{}; this.mode='dhcp'; this.ctx={pool:pn}; return []; }
        if(kw(A[2]||'','excluded-address')) return [];
        return [];
      }
      if(kw(s1,'prefix-list')){ var pln=A[2]; if(pln){ this.prefixLists[pln]=this.prefixLists[pln]||[]; this.prefixLists[pln].push(A.slice(3).join(' ')); } return []; }
      if(kw(s1,'sla')||kw(s1,'ssh')||kw(s1,'scp')||kw(s1,'name-server')||kw(s1,'forward-protocol')||kw(s1,'cef')) return [];
      return [];  // accept other ip globals silently
    }

    // ---- ipv6 ----
    if(eq(h,'ipv6')||kw(h,'ipv6')){
      var v6=(A[1]||'').toLowerCase();
      if(kw(v6,'unicast-routing')) return [];
      if(kw(v6,'route')){ var pfx=A[2],nh=A[3]; if(!pfx||!nh) return incomplete('ipv6 route <prefix/len> <next-hop>'); this.staticRoutes6.push({prefix:pfx,nh:nh}); return []; }
      if(kw(v6,'router')){ if(kw(A[2]||'','ospf')){ this.ospf6=this.ospf6||{pid:parseInt(A[3],10)||1}; this.mode='router'; this.ctx={proto:'ospfv3'}; return []; } return []; }
      if(kw(v6,'access-list')) return [];
      return [];
    }

    // ---- routing protocols ----
    if(kw(h,'router')) return this.routerCmd(A,neg);

    // ---- route-map ----
    if(kw(h,'route-map')){
      var rn=A[1]; if(!rn) return incomplete('route-map needs a name: "route-map RM permit 10".');
      var action=(A[2]||'permit').toLowerCase(); var seq=parseInt(A[3],10)||10;
      this.routeMaps[rn]=this.routeMaps[rn]||[];
      this.routeMaps[rn].push({seq:seq,action:action,match:[],set:[]});
      this.mode='route-map'; this.ctx={rmap:rn,idx:this.routeMaps[rn].length-1}; return [];
    }

    // ---- vrf ----
    if(kw(h,'vrf')&&kw(A[1]||'','definition') || (eq(h,'ip')&&eq(A[1]||'','vrf'))){
      var vn = kw(h,'vrf')? A[2] : A[2];
      if(!vn) return incomplete('VRF needs a name: "vrf definition CUST_A".');
      this.vrfs[vn]=this.vrfs[vn]||{rd:null,rt:[]}; this.mode='vrf'; this.ctx={vrf:vn}; return [];
    }

    // ---- QoS ----
    if(kw(h,'class-map')){ var cm=A[A.length-1]; if(!cm||cm==='class-map') return incomplete('class-map needs a name.'); this.classMaps[cm]=this.classMaps[cm]||{match:[]}; this.mode='class-map'; this.ctx={cmap:cm}; return []; }
    if(kw(h,'policy-map')){ var pm=A[1]; if(!pm) return incomplete('policy-map needs a name.'); this.policyMaps[pm]=this.policyMaps[pm]||{classes:[]}; this.mode='policy-map'; this.ctx={pmap:pm}; return []; }

    // ---- spanning-tree ----
    if(kw(h,'spanning-tree')){
      if(kw(A[1]||'','mode')){ var mm=(A[2]||'').toLowerCase(); if(/rapid/.test(mm)) this.spanningTreeMode='rapid-pvst'; else if(/mst/.test(mm)) this.spanningTreeMode='mst'; else this.spanningTreeMode='pvst'; return []; }
      return [];
    }

    // ---- username / aaa / crypto / ntp / banner ----
    if(kw(h,'username')){ var u=A[1]; if(u) this.users[u]={priv:A.indexOf('privilege')>=0?A[A.indexOf('privilege')+1]:1}; return []; }
    if(kw(h,'aaa')){ this.aaa=true; return []; }
    if(kw(h,'crypto')){
      if(kw(A[1]||'','key')){
        if(!this.domainName) return [err('% Please define a domain-name first.'), diag('\u21b3 RSA key labels use hostname.domain. Run "ip domain-name <name>" first.')];
        this.cryptoKey=true;
        return [out('The name for the keys will be: '+this.hostname+'.'+this.domainName), out('% The key modulus size is 1024 bits'), out('% Generating 1024 bit RSA keys ...[OK]')];
      }
      return [];
    }
    if(kw(h,'ntp')){ if(kw(A[1]||'','server')&&A[2]) this.ntpServers.push(A[2]); return []; }
    if(kw(h,'banner')){ this.banner=line; return [info('(banner delimiter accepted)')]; }
    if(kw(h,'track')){ var tid=A[1]; if(tid) this.trackObjs[tid]={spec:A.slice(2).join(' ')}; return []; }

    // commonly-accepted globals (silent)
    if(kw(h,'service')||kw(h,'logging')||kw(h,'snmp-server')||kw(h,'clock')||kw(h,'boot')||kw(h,'archive')||kw(h,'errdisable')||kw(h,'vtp')||kw(h,'port-channel')||kw(h,'lldp')||kw(h,'cdp')||kw(h,'mpls')||kw(h,'monitor')||kw(h,'event')||kw(h,'license')||kw(h,'redundancy')||kw(h,'parser')||kw(h,'access-list')) return [];
    if(neg) return [];

    return invalid('Not a recognized global-config command. Supported areas: interface, vlan, line, ip/ipv6, router (ospf/eigrp/bgp/rip), route-map, access-list, vrf, class-map/policy-map, spanning-tree, username, crypto, ntp.');
  };

  IOSDevice.prototype.newIf = function(name){
    var isL3only = name.indexOf('Loopback')===0 || name.indexOf('Serial')===0 || name.indexOf('Tunnel')===0 || name.indexOf('Vlan')===0;
    return {shut:!(name.indexOf('Loopback')===0||name.indexOf('Vlan')===0), swmode:null, accessVlan:1, trunkVlans:'all', native:1, ip:null,mask:null,desc:null, ipv6:[], vrf:null, standby:[], po:null};
  };

  // ---- ip route ----
  IOSDevice.prototype.ipRoute = function(A,neg){
    // ip route [vrf X] net mask nexthop [ad]
    var i=2, vrf=null;
    if(kw(A[2]||'','vrf')){ vrf=A[3]; i=4; }
    var net=A[i],mask=A[i+1],nh=A[i+2],ad=A[i+3];
    if(!net) return incomplete('ip route <network> <mask> <next-hop>');
    if(!isIp(net)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+net+'" is not a valid IPv4 network address.')];
    if(!mask) return incomplete('Missing subnet mask. Example: ip route 10.0.0.0 255.0.0.0 192.168.1.1');
    if(!isMask(mask)){
      if(looksLikeWildcard(mask)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+mask+'" looks like a wildcard mask. Static routes use a SUBNET mask (e.g. 255.255.255.0).')];
      return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+mask+'" is not a valid contiguous subnet mask.')];
    }
    if(!nh) return incomplete('Missing next-hop IP or exit interface. Example: ... 255.255.255.0 192.168.1.1');
    if(neg){ this.staticRoutes=this.staticRoutes.filter(function(r){return !(r.net===net&&r.mask===mask);}); return []; }
    this.staticRoutes.push({net:net,mask:mask,nh:nh,ad:parseInt(ad,10)||1,vrf:vrf}); return [];
  };

  // ---- ip access-list ----
  IOSDevice.prototype.ipAccessList = function(A,neg){
    // ip access-list standard|extended NAME  -> named ACL sub-mode
    var kind=(A[2]||'').toLowerCase();
    if(kw(kind,'standard')||kw(kind,'extended')){
      var nm=A[3]; if(!nm) return incomplete('Named ACL needs a name: "ip access-list extended WEB".');
      var type = kw(kind,'standard')?'standard':'extended';
      this.acls[nm]=this.acls[nm]||{type:type,entries:[]};
      this.mode = type==='standard'?'acl-std':'acl-ext'; this.ctx={acl:nm}; return [];
    }
    return invalid('Use "ip access-list standard <name>" or "ip access-list extended <name>".');
  };

  // ---- ip nat ----
  IOSDevice.prototype.ipNat = function(A,neg){
    var s2=(A[2]||'').toLowerCase();
    if(kw(s2,'inside')){
      if(kw(A[3]||'','source')){
        if(kw(A[4]||'','list')){ this.natRules.push({type:'overload',acl:A[5],intf:A[7]}); return []; }
        if(kw(A[4]||'','static')){ this.natRules.push({type:'static',in:A[5],out:A[6]}); return []; }
        return incomplete('ip nat inside source list <acl> interface <if> overload  (PAT)');
      }
      return [];
    }
    if(kw(s2,'outside')||kw(s2,'pool')) return [];
    return [];
  };

  // ---- router <proto> ----
  IOSDevice.prototype.routerCmd = function(A,neg){
    var proto=(A[1]||'').toLowerCase();
    if(kw(proto,'ospf')){
      var pid=parseInt(A[2],10);
      if(!pid) return incomplete('OSPF needs a process id: "router ospf 1".');
      this.ospf=this.ospf||{pid:pid,rid:null,networks:[],passive:[],redistribute:[]}; this.ospf.pid=pid;
      this.mode='router'; this.ctx={proto:'ospf'}; return [];
    }
    if(kw(proto,'eigrp')){
      var asn=parseInt(A[2],10);
      if(A[2]&&!isNaN(asn)){
        this.eigrp=this.eigrp||{asn:asn,networks:[],named:false,redistribute:[]}; this.eigrp.asn=asn;
        this.mode='router'; this.ctx={proto:'eigrp'}; return [];
      }
      // named mode: router eigrp NAME
      if(A[2]){ this.eigrp=this.eigrp||{name:A[2],networks:[],named:true}; this.mode='router'; this.ctx={proto:'eigrp-named'}; return []; }
      return incomplete('EIGRP needs an AS number: "router eigrp 100".');
    }
    if(kw(proto,'bgp')){
      var as=parseInt(A[2],10);
      if(!as) return incomplete('BGP needs an AS number: "router bgp 65001".');
      if(this.bgp && this.bgp.asn!==as) return [err('% Currently running BGP AS '+this.bgp.asn), diag('\u21b3 A router can run only ONE BGP AS. Remove the existing process first ("no router bgp '+this.bgp.asn+'").')];
      this.bgp=this.bgp||{asn:as,rid:null,neighbors:{},networks:[],redistribute:[]}; this.bgp.asn=as;
      this.mode='router'; this.ctx={proto:'bgp'}; return [];
    }
    if(kw(proto,'rip')){ this.rip=this.rip||{networks:[],version:1}; this.mode='router'; this.ctx={proto:'rip'}; return []; }
    return invalid('Supported routing protocols: ospf, eigrp, bgp, rip.');
  };

  // ---------- INTERFACE ----------
  IOSDevice.prototype.ifMode = function(t,c0,line){
    // if-range applies to a virtual context; we accept commands and note it
    var isRange = this.mode==='if-range';
    var intf = isRange? null : this.interfaces[this.ctx.intf];
    if(!isRange && !intf){ this.mode='config'; return [err('% interface context lost')]; }
    var neg=(c0==='no'); var t0 = neg? (t[1]||'').toLowerCase() : c0; var args = neg? t.slice(2): t.slice(1);
    function setAll(fn){ /* for ranges we no-op state but still validate */ if(intf) fn(intf); }

    if(kw(t0,'ip')){
      var a1=(args[0]||'').toLowerCase();
      if(kw(a1,'address')){
        if(neg){ setAll(function(i){i.ip=null;i.mask=null;}); return []; }
        if(kw(args[1]||'','dhcp')){ setAll(function(i){i.ip='dhcp';}); return []; }
        var ip=args[1],mask=args[2];
        if(!ip) return incomplete('ip address <ip> <mask>');
        if(!isIp(ip)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+ip+'" is not a valid IPv4 address (each octet 0-255).')];
        if(!mask) return incomplete('Missing subnet mask, e.g. "ip address '+ip+' 255.255.255.0".');
        if(!isMask(mask)){
          if(looksLikeWildcard(mask)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+mask+'" is a wildcard mask. Interfaces need a SUBNET mask like 255.255.255.0.')];
          return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+mask+'" is not a valid contiguous subnet mask.')];
        }
        if(intf && intf.swmode) return [err('% IP addresses configured on a Layer2 switchport are ignored.'), diag('\u21b3 This port is a switchport. Run "no switchport" to make it a routed (L3) port before adding an IP.')];
        setAll(function(i){i.ip=ip;i.mask=mask;}); return [];
      }
      if(kw(a1,'ospf')){
        // interface-level OSPF: ip ospf <pid> area <a>  (modern) -- accept
        return [];
      }
      if(kw(a1,'nat')){ var side=(args[1]||'').toLowerCase(); if(kw(side,'inside')) this.natInside.push(this.ctx.intf); else if(kw(side,'outside')) this.natOutside.push(this.ctx.intf); return []; }
      if(kw(a1,'helper-address')||kw(a1,'access-group')||kw(a1,'summary-address')||kw(a1,'mtu')||kw(a1,'proxy-arp')) return [];
      return [];
    }

    if(kw(t0,'ipv6')){
      var v=(args[0]||'').toLowerCase();
      if(kw(v,'address')){ if(intf) intf.ipv6.push(args[1]); return []; }
      if(kw(v,'enable')||kw(v,'ospf')||kw(v,'nd')||kw(v,'rip')||kw(v,'eigrp')) return [];
      return [];
    }

    if(kw(t0,'description')){ var d=line.replace(/^\s*(no\s+)?desc(ription)?\s*/i,''); setAll(function(i){i.desc=neg?null:d;}); return []; }

    if(kw(t0,'shutdown')){
      if(neg){ setAll(function(i){i.shut=false;}); if(intf) return this.linkUp(this.ctx.intf); return []; }
      setAll(function(i){i.shut=true;});
      if(intf) return [info('%LINK-5-CHANGED: Interface '+this.ctx.intf+', changed state to administratively down')];
      return [];
    }

    if(kw(t0,'no')&&false){}

    if(kw(t0,'switchport')){
      var s1=(args[0]||'').toLowerCase();
      if(!args.length){ setAll(function(i){i.swmode=i.swmode||'dynamic auto';}); return []; } // "switchport"
      if(neg && args.length===0){ setAll(function(i){i.swmode=null;}); return []; }
      if(kw(s1,'mode')){
        var m=(args[1]||'').toLowerCase();
        if(kw(m,'access')) setAll(function(i){i.swmode='access';});
        else if(kw(m,'trunk')) setAll(function(i){i.swmode='trunk';});
        else if(kw(m,'dynamic')) setAll(function(i){i.swmode='dynamic';});
        else return invalid('switchport mode {access|trunk|dynamic}');
        return [];
      }
      if(kw(s1,'access')&&kw(args[1]||'','vlan')){
        var vv=parseInt(args[2],10);
        if(isNaN(vv)) return incomplete('switchport access vlan <id>');
        if(vv<1||vv>4094) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 VLAN '+vv+' out of range (1-4094).')];
        if(!this.vlans[vv]) this.vlans[vv]={name:'VLAN'+(''+vv).padStart(4,'0')};
        setAll(function(i){i.accessVlan=vv;}); return [];
      }
      if(kw(s1,'trunk')){
        if(kw(args[1]||'','native')){ setAll(function(i){i.native=parseInt(args[3],10)||1;}); return []; }
        if(kw(args[1]||'','allowed')){ setAll(function(i){i.trunkVlans=args.slice(3).join(' ');}); return []; }
        return [];
      }
      if(kw(s1,'nonegotiate')||kw(s1,'voice')||kw(s1,'port-security')) return [];
      return [];
    }

    if(kw(t0,'no')&&kw(args[0]||'','switchport')){ setAll(function(i){i.swmode=null;}); return []; }
    if(kw(t0,'switchport')===false && t0==='no' && kw(args[0]||'','switchport')){ setAll(function(i){i.swmode=null;}); return []; }

    // EtherChannel
    if(kw(t0,'channel-group')){
      var pg=parseInt(args[0],10);
      if(isNaN(pg)) return incomplete('channel-group <number> mode {active|passive|on|desirable|auto}');
      var modeIdx=args.indexOf('mode'); var cmode=modeIdx>=0?args[modeIdx+1]:'on';
      var poName='Port-channel'+pg;
      if(!this.interfaces[poName]) this.interfaces[poName]=this.newIf(poName);
      this.etherchannels[pg]=this.etherchannels[pg]||{mode:cmode,members:[]};
      if(intf){ intf.po=pg; if(this.etherchannels[pg].members.indexOf(this.ctx.intf)<0) this.etherchannels[pg].members.push(this.ctx.intf); }
      return [];
    }

    // HSRP / VRRP / GLBP
    if(kw(t0,'standby')||kw(t0,'vrrp')||kw(t0,'glbp')){
      var proto = kw(t0,'standby')?'HSRP':(kw(t0,'vrrp')?'VRRP':'GLBP');
      var grp=parseInt(args[0],10);
      var rest=args.slice(1).map(function(x){return x.toLowerCase();});
      if(rest[0]==='ip'||rest.indexOf('ip')>=0){
        var vip = args[args.indexOf('ip')+1] || args[2];
        if(vip && !isIp(vip)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+vip+'" is not a valid virtual IP for '+proto+'.')];
        if(intf) intf.standby.push({proto:proto,grp:isNaN(grp)?0:grp,vip:vip});
        this.hsrpGroups.push({intf:this.ctx.intf,grp:isNaN(grp)?0:grp,vip:vip,proto:proto,pri:100});
        return [];
      }
      // priority / preempt / etc.
      return [];
    }

    if(kw(t0,'encapsulation')){ // subinterface dot1Q
      if(kw(args[0]||'','dot1q')||kw(args[0]||'','isl')){ if(!args[1]) return incomplete('encapsulation dot1Q <vlan-id>'); if(intf) intf.encap=args.join(' '); return []; }
      return [];
    }
    if(kw(t0,'vrf')){ if(kw(args[0]||'','forwarding')||kw(args[0]||'','member')){ if(intf) intf.vrf=args[1]; return []; } return []; }

    // silently-accepted interface commands
    if(kw(t0,'speed')||kw(t0,'duplex')||kw(t0,'mtu')||kw(t0,'bandwidth')||kw(t0,'delay')||kw(t0,'load-interval')||kw(t0,'cdp')||kw(t0,'lldp')||kw(t0,'spanning-tree')||kw(t0,'service-policy')||kw(t0,'mpls')||kw(t0,'keepalive')||kw(t0,'negotiation')||kw(t0,'media-type')||kw(t0,'clock')||kw(t0,'tunnel')||kw(t0,'ospfv3')||kw(t0,'carrier-delay')) return [];
    if(neg) return [];

    return invalid('Not a valid interface command. Common: ip address, description, shutdown/no shutdown, switchport ..., channel-group, standby, encapsulation.');
  };

  IOSDevice.prototype.linkUp = function(name){
    return [info('%LINK-5-CHANGED: Interface '+name+', changed state to up'),
            info('%LINEPROTO-5-UPDOWN: Line protocol on Interface '+name+', changed state to up')];
  };

  // ---------- LINE ----------
  IOSDevice.prototype.lineMode = function(t,c0,line){
    var L=this.lines[this.ctx.line]||{};
    if(kw(c0,'password')){ L.password=t.slice(1).join(' '); return []; }
    if(kw(c0,'login')){ L.login=(t[1]?t.slice(1).join(' '):'password'); return []; }
    if(kw(c0,'transport')){ L.transport=t.slice(1).join(' '); return []; }
    if(kw(c0,'exec-timeout')||kw(c0,'logging')||kw(c0,'access-class')||kw(c0,'privilege')||kw(c0,'history')||kw(c0,'no')) return [];
    return invalid('Line commands: password, login [local], transport input {ssh|telnet|all}, exec-timeout, access-class.');
  };

  // ---------- VLAN ----------
  IOSDevice.prototype.vlanMode = function(t,c0,line){
    var V=this.vlans[this.ctx.vlan];
    if(kw(c0,'name')){ if(!t[1]) return incomplete('vlan name <string>'); V.name=t[1]; return []; }
    if(kw(c0,'state')||kw(c0,'no')||kw(c0,'shutdown')) return [];
    return invalid('VLAN sub-mode accepts: name <string>, state {active|suspend}.');
  };

  // ---------- ROUTER (ospf/eigrp/bgp/rip) ----------
  IOSDevice.prototype.routerMode = function(t,c0,line){
    var proto=this.ctx.proto;
    var neg=(c0==='no'); var h=neg?(t[1]||'').toLowerCase():c0; var A=neg?t.slice(1):t;

    if(kw(h,'network')){
      if(proto==='ospf'){
        var net=A[1],wild=A[2];
        var ai=A.findIndex(function(x){return kw(x,'area');});
        var area = ai>=0? A[ai+1]:null;
        if(!net) return incomplete('OSPF: network <address> <wildcard> area <id>');
        if(!isIp(net)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+net+'" is not a valid address.')];
        if(!wild) return incomplete('OSPF network needs a WILDCARD mask + area, e.g. "network 10.0.0.0 0.0.0.255 area 0".');
        if(!octetsOk(wild)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+wild+'" is not a valid wildcard mask.')];
        if(isMask(wild)&&!looksLikeWildcard(wild)&&wild!=='0.0.0.0') return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+wild+'" looks like a SUBNET mask. OSPF "network" uses a WILDCARD mask (invert it: '+maskToWild(wild)+').')];
        if(area==null) return incomplete('Missing "area <id>". Example: network 10.0.0.0 0.0.0.255 area 0');
        this.ospf.networks.push({net:net,wild:wild,area:area}); return [];
      }
      if(proto==='eigrp'){
        var en=A[1]; if(!en) return incomplete('EIGRP: network <address> [wildcard]');
        if(!isIp(en)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+en+'" is not a valid address.')];
        var ew=A[2];
        if(ew && isMask(ew) && !looksLikeWildcard(ew) && ew!=='0.0.0.0')
          return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+ew+'" looks like a SUBNET mask. EIGRP "network" uses a WILDCARD mask (invert it: '+maskToWild(ew)+').')];
        this.eigrp.networks.push({net:en,wild:ew||null}); return [];
      }
      if(proto==='rip'){ if(!A[1]||!isIp(A[1])) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 RIP network must be a classful IPv4 network.')]; this.rip.networks.push(A[1]); return []; }
      if(proto==='bgp'){
        var bn=A[1]; if(!bn) return incomplete('BGP: network <prefix> mask <mask>');
        if(!isIp(bn)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+bn+'" is not a valid network prefix.')];
        var mi=A.indexOf('mask'); var bmask=mi>=0?A[mi+1]:null;
        if(bmask && octetsOk(bmask) && !isMask(bmask))
          return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+bmask+'" is not a valid contiguous subnet mask (bits must be all 1s then all 0s).')];
        this.bgp.networks.push({net:bn,mask:bmask}); return [];
      }
    }

    if(kw(h,'neighbor')){
      if(proto!=='bgp') return invalid('"neighbor" is a BGP command. You are in '+proto.toUpperCase()+' config.');
      var nip=A[1];
      if(!nip||!isIp(nip)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 neighbor needs a valid peer IP: "neighbor 10.0.0.2 remote-as 65002".')];
      var b=this.bgp.neighbors[nip]=this.bgp.neighbors[nip]||{};
      var sub=(A[2]||'').toLowerCase();
      if(kw(sub,'remote-as')){ var ras=parseInt(A[3],10); if(!ras) return incomplete('neighbor '+nip+' remote-as <asn>'); b.remoteAs=ras; b.type = ras===this.bgp.asn?'iBGP':'eBGP'; return []; }
      if(!b.remoteAs && !kw(sub,'remote-as')) {
        // configuring options before remote-as is an error on real IOS
        return [err('% Specify remote-as or peer-group commands first'), diag('\u21b3 Configure "neighbor '+nip+' remote-as <asn>" BEFORE other neighbor options.')];
      }
      if(kw(sub,'description')){ b.desc=A.slice(3).join(' '); return []; }
      if(kw(sub,'shutdown')){ b.shut=!neg; return []; }
      if(kw(sub,'update-source')){ b.updateSrc=A[3]; return []; }
      if(kw(sub,'ebgp-multihop')){ b.ebgpMh=parseInt(A[3],10)||255; return []; }
      if(kw(sub,'next-hop-self')||kw(sub,'route-reflector-client')||kw(sub,'send-community')||kw(sub,'activate')||kw(sub,'soft-reconfiguration')||kw(sub,'route-map')||kw(sub,'password')||kw(sub,'timers')||kw(sub,'prefix-list')||kw(sub,'filter-list')) return [];
      return [];
    }

    if(kw(h,'address-family')){
      this.mode='router-af'; this.ctx.af=A.slice(1).join(' '); return [];
    }
    if(kw(h,'router-id')){
      if(!A[1]||!isIp(A[1])) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 router-id must be a 32-bit value in dotted format, e.g. "router-id 1.1.1.1".')];
      if(proto==='ospf') this.ospf.rid=A[1]; else if(proto==='bgp') this.bgp.rid=A[1];
      return [];
    }
    if(kw(h,'passive-interface')){ if(proto==='ospf'&&A[1]) this.ospf.passive.push(A[1]); return []; }
    if(kw(h,'redistribute')){
      var src=A[1];
      var rec = (proto==='ospf'?this.ospf:proto==='eigrp'?this.eigrp:proto==='bgp'?this.bgp:null);
      if(rec) (rec.redistribute=rec.redistribute||[]).push(A.slice(1).join(' '));
      if(proto==='ospf' && src && !/connected|static|eigrp|bgp|rip|isis/.test((src||'').toLowerCase()))
        return [err("% Invalid input detected at '^' marker."), diag('\u21b3 redistribute source must be a protocol (connected/static/eigrp/bgp/rip).')];
      return [];
    }
    if(kw(h,'version')){ if(proto==='rip') this.rip.version=parseInt(A[1],10)||2; return []; }
    if(kw(h,'no-auto-summary')||kw(h,'auto-summary')||kw(h,'maximum-paths')||kw(h,'default-information')||kw(h,'area')||kw(h,'bgp')||kw(h,'timers')||kw(h,'metric')||kw(h,'eigrp')||kw(h,'address')||kw(h,'af-interface')||kw(h,'topology')||kw(h,'synchronization')) return [];
    if(neg) return [];
    return invalid(proto.toUpperCase()+' config commands include: network, '+(proto==='bgp'?'neighbor, address-family, ':'')+'router-id, passive-interface, redistribute.');
  };

  IOSDevice.prototype.routerAfMode = function(t,c0,line){
    var neg=(c0==='no'); var h=neg?(t[1]||'').toLowerCase():c0; var A=neg?t.slice(1):t;
    if(kw(h,'neighbor')){ // activate etc. under AF
      return [];
    }
    if(kw(h,'network')||kw(h,'redistribute')||kw(h,'maximum-paths')||kw(h,'exit-address-family')||neg) {
      if(kw(h,'exit-address-family')){ this.mode='router'; return []; }
      return [];
    }
    return invalid('address-family accepts: neighbor <ip> activate, network, redistribute, exit-address-family.');
  };

  // ---------- ACL sub-mode ----------
  IOSDevice.prototype.aclMode = function(t,c0,line){
    var acl=this.acls[this.ctx.acl];
    if(kw(c0,'permit')||kw(c0,'deny')){
      // basic validation
      if(acl.type==='standard'){
        var src=t[1];
        if(!src) return incomplete('standard ACL: {permit|deny} {any|host <ip>|<ip> <wildcard>}');
        if(src!=='any'&&src!=='host'&&!isIp(src)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 Expected any, host <ip>, or <ip> <wildcard>.')];
        acl.entries.push(line); return [];
      } else {
        var proto=t[1];
        if(!proto) return incomplete('extended ACL: {permit|deny} <proto> <src> <dst> [eq <port>]');
        if(!/^(ip|tcp|udp|icmp|gre|esp|ospf|eigrp|\d+)$/i.test(proto)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+proto+'" is not a valid protocol. Use ip/tcp/udp/icmp/... .')];
        acl.entries.push(line); return [];
      }
    }
    if(kw(c0,'remark')||kw(c0,'no')||/^\d+$/.test(c0)){ acl.entries.push(line); return []; }
    return invalid('ACL entries start with permit, deny, or remark.');
  };

  // ---------- route-map ----------
  IOSDevice.prototype.routeMapMode = function(t,c0,line){
    var rm=this.routeMaps[this.ctx.rmap][this.ctx.idx];
    if(kw(c0,'match')){ rm.match.push(t.slice(1).join(' ')); return []; }
    if(kw(c0,'set')){ rm.set.push(t.slice(1).join(' ')); return []; }
    if(kw(c0,'no')) return [];
    return invalid('route-map sub-mode accepts: match ..., set ... .');
  };

  // ---------- vrf ----------
  IOSDevice.prototype.vrfMode = function(t,c0,line){
    var v=this.vrfs[this.ctx.vrf];
    if(kw(c0,'rd')){ v.rd=t[1]; return []; }
    if(kw(c0,'route-target')){ v.rt.push(t.slice(1).join(' ')); return []; }
    if(kw(c0,'address-family')||kw(c0,'no')||kw(c0,'description')) return [];
    return invalid('VRF definition accepts: rd <rd>, route-target {import|export|both} <rt>, address-family ...');
  };

  // ---------- QoS class-map / policy-map ----------
  IOSDevice.prototype.classMapMode = function(t,c0,line){
    var cm=this.classMaps[this.ctx.cmap];
    if(kw(c0,'match')){ cm.match.push(t.slice(1).join(' ')); return []; }
    if(kw(c0,'no')||kw(c0,'description')) return [];
    return invalid('class-map accepts: match {access-group|dscp|protocol|...}.');
  };
  IOSDevice.prototype.policyMapMode = function(t,c0,line){
    var pm=this.policyMaps[this.ctx.pmap];
    if(kw(c0,'class')){ var cn=t[1]; pm.classes.push({name:cn,actions:[]}); this.mode='pmap-c'; this.ctx.cls=pm.classes.length-1; return []; }
    if(kw(c0,'description')||kw(c0,'no')) return [];
    return invalid('policy-map accepts: class <name>.');
  };
  IOSDevice.prototype.pmapCMode = function(t,c0,line){
    var pm=this.policyMaps[this.ctx.pmap]; var cls=pm.classes[this.ctx.cls];
    if(kw(c0,'class')){ var cn=t[1]; pm.classes.push({name:cn,actions:[]}); this.ctx.cls=pm.classes.length-1; return []; }
    if(kw(c0,'bandwidth')||kw(c0,'priority')||kw(c0,'police')||kw(c0,'set')||kw(c0,'shape')||kw(c0,'queue-limit')||kw(c0,'random-detect')||kw(c0,'fair-queue')||kw(c0,'no')){ cls.actions.push(line); return []; }
    return invalid('under class: bandwidth, priority, police, set, shape, ...');
  };

  // ---------- DHCP pool ----------
  IOSDevice.prototype.dhcpMode = function(t,c0,line){
    var p=this.dhcpPools[this.ctx.pool];
    if(kw(c0,'network')){ p.network=t.slice(1).join(' '); return []; }
    if(kw(c0,'default-router')){ p.gw=t[1]; return []; }
    if(kw(c0,'dns-server')){ p.dns=t.slice(1).join(' '); return []; }
    if(kw(c0,'domain-name')||kw(c0,'lease')||kw(c0,'no')) return [];
    return invalid('DHCP pool accepts: network, default-router, dns-server, domain-name, lease.');
  };

  // ---------- PING / TRACE ----------
  IOSDevice.prototype.reachable = function(){
    for(var k in this.interfaces){ var i=this.interfaces[k]; if(i.ip && i.ip!=='dhcp' && !i.shut){ return true; } }
    return false;
  };
  IOSDevice.prototype.doPing = function(t){
    var target=t[1];
    if(!target) return incomplete('ping <ip|hostname>');
    if(!isIp(target) && !isIpv6(target) && !/^[a-z]/i.test(target)) return [err("% Invalid input detected at '^' marker."), diag('\u21b3 "'+target+'" is not a valid IP address or hostname.')];
    var ok=this.reachable();
    return [out('Type escape sequence to abort.'),
            out('Sending 5, 100-byte ICMP Echos to '+target+', timeout is 2 seconds:'),
            out(ok?'!!!!!':'.....'),
            out('Success rate is '+(ok?100:0)+' percent ('+(ok?'5':'0')+'/5)'+(ok?', round-trip min/avg/max = 1/2/4 ms':'')),
            ok?info(''):diag('\u21b3 0% success: no active interface with an IP. Bring an interface up ("no shutdown") and assign an IP.')].filter(function(x){return x.t!=='';});
  };
  IOSDevice.prototype.doTrace = function(t){
    var target=t[1]; if(!target) return incomplete('traceroute <ip|hostname>');
    var ok=this.reachable();
    var o=[out('Type escape sequence to abort.'), out('Tracing the route to '+target)];
    if(ok){ o.push(out('  1  192.168.1.1  4 msec  2 msec  1 msec'), out('  2  '+target+'  8 msec  6 msec  5 msec')); }
    else { o.push(out('  1  * * *'), out('  2  * * *'), diag('\u21b3 No reachable path (no active IP interface).')); }
    return o;
  };

  // ---------- SHOW ----------
  IOSDevice.prototype.doShow = function(t){
    var s=(t[1]||'').toLowerCase(), s2=(t[2]||'').toLowerCase(), s3=(t[3]||'').toLowerCase();
    if(kw(s,'running-config')||kw(s,'run')) return this.showRun();
    if(kw(s,'startup-config')) return this.savedConfig? this.showRun() : [out('startup-config is not present'), diag('\u21b3 Save first with "write memory" or "copy run start".')];
    if(kw(s,'ip')){
      if(kw(s2,'interface')&&kw(s3,'brief')) return this.showIpIntBrief();
      if(kw(s2,'route')) return this.showIpRoute();
      if(kw(s2,'ospf')) return this.showOspf(t);
      if(kw(s2,'protocols')) return this.showIpProtocols();
      if(kw(s2,'bgp')) return this.showBgp(t);
      if(kw(s2,'eigrp')) return this.showEigrp(t);
      if(kw(s2,'nat')) return this.showNat();
      if(kw(s2,'access-lists')||kw(s2,'access-list')) return this.showAcls();
      if(kw(s2,'interface')) return this.showInterfaces(t.slice(3).join(''));
      return [err("% Invalid input detected at '^' marker."), diag('\u21b3 Try: show ip interface brief | ip route | ip ospf | ip bgp | ip protocols | ip nat translations | ip access-lists')];
    }
    if(kw(s,'ipv6')){
      if(kw(s2,'route')) return this.showIpv6Route();
      if(kw(s2,'interface')) return [out('(IPv6 interface brief \u2014 configured addresses shown in running-config)')];
      return [out('(show ipv6 '+s2+' \u2014 simulated)')];
    }
    if(kw(s,'bgp')) return this.showBgp(t);
    if(kw(s,'interfaces')||kw(s,'interface')) return this.showInterfaces(t.slice(2).join(''));
    if(kw(s,'vlan')) return this.showVlan();
    if(kw(s,'etherchannel')) return this.showEtherchannel();
    if(kw(s,'standby')) return this.showStandby();
    if(kw(s,'vrrp')) return this.showStandby();
    if(kw(s,'spanning-tree')) return this.showStp();
    if(kw(s,'vrf')) return this.showVrf();
    if(kw(s,'access-lists')||kw(s,'access-list')) return this.showAcls();
    if(kw(s,'route-map')) return this.showRouteMaps();
    if(kw(s,'cdp')){ if(kw(s2,'neighbor')) return [out('Device ID  Local Intrfce  Holdtme  Capability  Platform  Port ID'), out('(no CDP neighbors in simulator)')]; return [out('Global CDP information: CDP is enabled')]; }
    if(kw(s,'version')) return [out('Cisco IOS Software (simulated), Version 15.7(3)M (Enterprise lab)'), out(this.hostname+' uptime is 2 hours, 5 minutes'), out('System image file is "flash:isr-universalk9.SPA.157-3.M.bin"')];
    if(kw(s,'mac')) return [out('          Mac Address Table'), out('-------------------------------------------'), out('Vlan    Mac Address       Type        Ports'), out('----    -----------       --------    -----'), out('   1    0060.5c2a.1a01    DYNAMIC     Gi0/1')];
    if(kw(s,'clock')) return [out('*'+new Date().toTimeString().slice(0,8)+'.000 UTC Tue Jul 14 2026')];
    if(kw(s,'flash')) return [out('Directory of flash:/'), out('    2  -rwx  108725632  isr-universalk9.SPA.157-3.M.bin')];
    if(kw(s,'users')||kw(s,'sessions')||kw(s,'processes')||kw(s,'inventory')||kw(s,'environment')||kw(s,'logging')) return [out('('+t.slice(1).join(' ')+' \u2014 simulated, no live data)')];
    return [err("% Invalid input detected at '^' marker."), diag('\u21b3 Supported shows: running-config, ip interface brief, ip route, ip ospf, ip bgp, ip eigrp neighbors, ip protocols, interfaces, vlan, etherchannel summary, standby, spanning-tree, vrf, access-lists, route-map, version, cdp neighbors.')];
  };

  IOSDevice.prototype.showRun = function(){
    var self=this;
    var o=[out('Building configuration...'), out(''), out('Current configuration:'), out('!'), out('hostname '+this.hostname), out('!')];
    if(this.enableSecret) o.push(out('enable secret '+this.enableSecret),out('!'));
    for(var u in this.users) o.push(out('username '+u+(this.users[u].priv>1?' privilege '+this.users[u].priv:'')+' secret <hash>'));
    if(this.domainName) o.push(out('ip domain-name '+this.domainName));
    o.push(out('spanning-tree mode '+this.spanningTreeMode),out('!'));
    for(var v in this.vlans){ if(v!=='1'){ o.push(out('vlan '+v)); if(this.vlans[v].name) o.push(out(' name '+this.vlans[v].name)); o.push(out('!')); } }
    for(var vf in this.vrfs){ o.push(out('vrf definition '+vf)); if(this.vrfs[vf].rd) o.push(out(' rd '+this.vrfs[vf].rd)); o.push(out('!')); }
    Object.keys(this.interfaces).forEach(function(n){
      var i=self.interfaces[n];
      o.push(out('interface '+n));
      if(i.desc) o.push(out(' description '+i.desc));
      if(i.vrf) o.push(out(' vrf forwarding '+i.vrf));
      if(i.encap) o.push(out(' encapsulation '+i.encap));
      if(i.swmode==='access'){ o.push(out(' switchport mode access')); o.push(out(' switchport access vlan '+i.accessVlan)); }
      else if(i.swmode==='trunk'){ o.push(out(' switchport mode trunk')); }
      if(i.ip==='dhcp') o.push(out(' ip address dhcp'));
      else if(i.ip) o.push(out(' ip address '+i.ip+' '+i.mask));
      (i.ipv6||[]).forEach(function(a){ o.push(out(' ipv6 address '+a)); });
      (i.standby||[]).forEach(function(s){ o.push(out(' standby '+s.grp+' ip '+s.vip)); });
      if(i.po) o.push(out(' channel-group '+i.po+' mode '+(self.etherchannels[i.po]?self.etherchannels[i.po].mode:'on')));
      o.push(out(i.shut? ' shutdown':' no shutdown'));
      o.push(out('!'));
    });
    for(var an in this.acls){ var a=this.acls[an]; o.push(out('ip access-list '+a.type+' '+an)); a.entries.forEach(function(e){ o.push(out(' '+e.replace(/^\s+/,''))); }); o.push(out('!')); }
    this.staticRoutes.forEach(function(r){ o.push(out('ip route '+(r.vrf?'vrf '+r.vrf+' ':'')+r.net+' '+r.mask+' '+r.nh+(r.ad>1?' '+r.ad:''))); });
    this.staticRoutes6.forEach(function(r){ o.push(out('ipv6 route '+r.prefix+' '+r.nh)); });
    if(this.ospf){ o.push(out('router ospf '+this.ospf.pid)); if(this.ospf.rid)o.push(out(' router-id '+this.ospf.rid)); this.ospf.networks.forEach(function(n){ o.push(out(' network '+n.net+' '+n.wild+' area '+n.area)); }); (this.ospf.redistribute||[]).forEach(function(r){o.push(out(' redistribute '+r));}); o.push(out('!')); }
    if(this.eigrp){ o.push(out('router eigrp '+(this.eigrp.asn||this.eigrp.name))); this.eigrp.networks.forEach(function(n){ o.push(out(' network '+n.net+(n.wild?' '+n.wild:''))); }); o.push(out('!')); }
    if(this.rip){ o.push(out('router rip'),out(' version '+this.rip.version)); this.rip.networks.forEach(function(n){o.push(out(' network '+n));}); o.push(out('!')); }
    if(this.bgp){
      o.push(out('router bgp '+this.bgp.asn));
      if(this.bgp.rid) o.push(out(' bgp router-id '+this.bgp.rid));
      for(var nb in this.bgp.neighbors){ var b=this.bgp.neighbors[nb]; if(b.remoteAs)o.push(out(' neighbor '+nb+' remote-as '+b.remoteAs)); if(b.desc)o.push(out(' neighbor '+nb+' description '+b.desc)); if(b.updateSrc)o.push(out(' neighbor '+nb+' update-source '+b.updateSrc)); if(b.shut)o.push(out(' neighbor '+nb+' shutdown')); }
      this.bgp.networks.forEach(function(n){ o.push(out(' network '+n.net+(n.mask?' mask '+n.mask:''))); });
      o.push(out('!'));
    }
    for(var rmn in this.routeMaps){ this.routeMaps[rmn].forEach(function(e){ o.push(out('route-map '+rmn+' '+e.action+' '+e.seq)); e.match.forEach(function(m){o.push(out(' match '+m));}); e.set.forEach(function(st){o.push(out(' set '+st));}); }); o.push(out('!')); }
    o.push(out('end'));
    return o;
  };

  IOSDevice.prototype.showIpIntBrief = function(){
    var self=this;
    var o=[out('Interface              IP-Address      OK? Method Status                Protocol')];
    var names=Object.keys(this.interfaces);
    if(!names.length){ o.push(out('(no interfaces configured yet)')); return o; }
    names.forEach(function(n){
      var i=self.interfaces[n];
      var ip=i.ip==='dhcp'?'dhcp':(i.ip||'unassigned');
      var status = i.shut? 'administratively down' : 'up';
      var proto = i.shut? 'down' : (i.ip? 'up':'up');
      o.push(out(pad(n,23)+pad(ip,16)+'YES manual '+pad(status,22)+proto));
    });
    return o;
  };

  IOSDevice.prototype.showIpRoute = function(){
    var self=this;
    var o=[out('Codes: L - local, C - connected, S - static, O - OSPF, D - EIGRP, B - BGP, R - RIP'),
           out('       * - candidate default'), out('')];
    var any=false;
    for(var k in this.interfaces){ var i=this.interfaces[k]; if(i.ip&&i.ip!=='dhcp'&&!i.shut){ o.push(out('C        '+netOf(i.ip,i.mask)+' is directly connected, '+k)); o.push(out('L        '+i.ip+'/32 is directly connected, '+k)); any=true; } }
    this.staticRoutes.forEach(function(r){ o.push(out('S        '+r.net+'/'+maskBits(r.mask)+' [1/0] via '+r.nh)); any=true; });
    if(this.ospf&&this.ospf.networks.length){ o.push(out('O        (OSPF process '+this.ospf.pid+' \u2014 routes appear once adjacency forms with a live neighbor)')); }
    if(this.eigrp&&this.eigrp.networks.length){ o.push(out('D        (EIGRP AS '+(this.eigrp.asn||this.eigrp.name)+' \u2014 routes appear once a neighbor is up)')); }
    if(this.bgp&&Object.keys(this.bgp.neighbors).length){ o.push(out('B        (BGP AS '+this.bgp.asn+' \u2014 prefixes appear once a neighbor is Established)')); }
    if(!any) o.push(out('(no routes \u2014 configure interface IPs or ip route statements)'));
    return o;
  };

  IOSDevice.prototype.showIpv6Route = function(){
    var o=[out('IPv6 Routing Table')];
    var any=false;
    (this.staticRoutes6||[]).forEach(function(r){ o.push(out('S   '+r.prefix+' [1/0] via '+r.nh)); any=true; });
    for(var k in this.interfaces){ (this.interfaces[k].ipv6||[]).forEach(function(a){ o.push(out('C   '+a+' [0/0], directly connected, '+k)); any=true; }); }
    if(!any) o.push(out('(no IPv6 routes configured)'));
    return o;
  };

  IOSDevice.prototype.showIpProtocols = function(){
    var o=[];
    if(this.ospf){ o.push(out('Routing Protocol is "ospf '+this.ospf.pid+'"')); if(this.ospf.rid)o.push(out('  Router ID '+this.ospf.rid)); o.push(out('  Routing for Networks:')); this.ospf.networks.forEach(function(n){o.push(out('    '+n.net+' '+n.wild+' area '+n.area));}); o.push(out('')); }
    if(this.eigrp){ o.push(out('Routing Protocol is "eigrp '+(this.eigrp.asn||this.eigrp.name)+'"')); o.push(out('  Routing for Networks:')); this.eigrp.networks.forEach(function(n){o.push(out('    '+n.net));}); o.push(out('')); }
    if(this.bgp){ o.push(out('Routing Protocol is "bgp '+this.bgp.asn+'"')); o.push(out('  Neighbor(s):')); for(var nb in this.bgp.neighbors){ o.push(out('    '+nb+' remote-as '+(this.bgp.neighbors[nb].remoteAs||'?'))); } o.push(out('')); }
    if(this.rip){ o.push(out('Routing Protocol is "rip"')); o.push(out('  Version '+this.rip.version)); o.push(out('')); }
    if(!o.length) o.push(out('(no dynamic routing protocols configured)'));
    return o;
  };

  IOSDevice.prototype.showOspf = function(t){
    if((t[3]||'').toLowerCase()==='neighbor' || (t[2]||'').toLowerCase()==='neighbor'){
      if(!this.ospf) return [out('%OSPF is not running')];
      return [out('Neighbor ID  Pri  State  Dead Time  Address  Interface'), out('(no live neighbors in simulator \u2014 config validated)')];
    }
    if(!this.ospf) return [out(' %OSPF is not running (configure "router ospf <pid>")')];
    var o=[out(' Routing Process "ospf '+this.ospf.pid+'" with ID '+(this.ospf.rid||'derived from highest loopback/interface'))];
    var areas=new Set(this.ospf.networks.map(function(n){return n.area;}));
    o.push(out('  Number of areas in this router is '+areas.size));
    this.ospf.networks.forEach(function(n){ o.push(out('    Network '+n.net+' '+n.wild+' area '+n.area)); });
    return o;
  };

  IOSDevice.prototype.showBgp = function(t){
    if(!this.bgp) return [out('% BGP not active'), diag('\u21b3 Configure with "router bgp <asn>".')];
    var sub=(t[2]||'').toLowerCase();
    if(kw(sub,'summary')|| (t[1]||'').toLowerCase()==='summary'){
      var o=[out('BGP router identifier '+(this.bgp.rid||'0.0.0.0')+', local AS number '+this.bgp.asn), out('')];
      o.push(out('Neighbor        V    AS  MsgRcvd MsgSent  TblVer  InQ OutQ Up/Down  State/PfxRcd'));
      var self=this; var has=false;
      for(var nb in this.bgp.neighbors){ var b=this.bgp.neighbors[nb]; has=true;
        var state = b.shut? 'Idle (Admin)' : 'Idle';
        o.push(out(pad(nb,15)+' 4 '+pad(b.remoteAs||'?',5)+'       0       0        1    0    0 never    '+state)); }
      if(!has) o.push(out('(no neighbors configured)'));
      o.push(diag('\u21b3 Neighbors show "Idle" because this simulator has no live peer. On real gear they would move Idle\u2192Connect\u2192OpenSent\u2192Established.'));
      return o;
    }
    var o=[out('BGP table version is 1, local router ID is '+(this.bgp.rid||'0.0.0.0'))];
    this.bgp.networks.forEach(function(n){ o.push(out(' *> '+n.net+(n.mask?'/'+maskBits(n.mask):'')+'   0.0.0.0   0   32768 i')); });
    if(!this.bgp.networks.length) o.push(out('(no networks advertised)'));
    return o;
  };

  IOSDevice.prototype.showEigrp = function(t){
    if(!this.eigrp) return [out('% EIGRP not running')];
    if((t[3]||'').toLowerCase()==='neighbor'||(t[2]||'').toLowerCase()==='neighbors'){
      return [out('EIGRP-IPv4 Neighbors for AS('+(this.eigrp.asn||this.eigrp.name)+')'), out('H   Address   Interface   Hold  Uptime   SRTT   RTO   Q   Seq'), out('(no live neighbors in simulator)')];
    }
    return [out('EIGRP AS '+(this.eigrp.asn||this.eigrp.name)+' \u2014 networks:'), ].concat(this.eigrp.networks.map(function(n){return out('   '+n.net);}));
  };

  IOSDevice.prototype.showNat = function(){
    var o=[out('Pro Inside global   Inside local    Outside local   Outside global')];
    if(!this.natRules.length) o.push(out('(no NAT translations \u2014 configure "ip nat inside/outside" + "ip nat inside source ...")'));
    else this.natRules.forEach(function(r){ o.push(out('--- '+(r.type)+' rule configured')); });
    return o;
  };

  IOSDevice.prototype.showAcls = function(){
    var o=[]; var self=this; var any=false;
    for(var n in this.acls){ any=true; var a=this.acls[n];
      o.push(out((a.type==='standard'?'Standard':'Extended')+' IP access list '+n));
      a.entries.forEach(function(e){ o.push(out('    '+e.replace(/^\s+/,''))); });
    }
    if(!any) o.push(out('(no access-lists configured)'));
    return o;
  };

  IOSDevice.prototype.showRouteMaps = function(){
    var o=[]; var self=this; var any=false;
    for(var n in this.routeMaps){ any=true; this.routeMaps[n].forEach(function(e){
      o.push(out('route-map '+n+', '+e.action+', sequence '+e.seq));
      e.match.forEach(function(m){o.push(out('  Match clauses:  '+m));});
      e.set.forEach(function(s){o.push(out('  Set clauses:    '+s));});
    }); }
    if(!any) o.push(out('(no route-maps configured)'));
    return o;
  };

  IOSDevice.prototype.showEtherchannel = function(){
    var o=[out('Group  Port-channel  Protocol    Ports')];
    var any=false;
    for(var g in this.etherchannels){ any=true; var e=this.etherchannels[g];
      var proto = /active|passive/.test(e.mode)?'LACP':(/desirable|auto/.test(e.mode)?'PAgP':'-');
      o.push(out(pad(g,7)+pad('Po'+g+'(SU)',14)+pad(proto,12)+e.members.map(function(m){return m+'(P)';}).join(' ')));
    }
    if(!any) o.push(out('(no EtherChannels configured)'));
    return o;
  };

  IOSDevice.prototype.showStandby = function(){
    if(!this.hsrpGroups.length) return [out('(no HSRP/VRRP groups configured)')];
    var o=[];
    this.hsrpGroups.forEach(function(g){
      o.push(out(g.intf+' - Group '+g.grp+' ('+g.proto+')'));
      o.push(out('  State is Active (simulated, single device)'));
      o.push(out('  Virtual IP address is '+(g.vip||'unset')));
      o.push(out('  Priority '+g.pri));
    });
    return o;
  };

  IOSDevice.prototype.showVrf = function(){
    var o=[out('  Name                             Default RD          Interfaces')];
    var any=false, self=this;
    for(var n in this.vrfs){ any=true;
      var ifs=Object.keys(this.interfaces).filter(function(k){return self.interfaces[k].vrf===n;});
      o.push(out('  '+pad(n,33)+pad(this.vrfs[n].rd||'<not set>',20)+ifs.join(', ')));
    }
    if(!any) o.push(out('(no VRFs defined)'));
    return o;
  };

  IOSDevice.prototype.showInterfaces = function(raw){
    var self=this;
    var name=normIf(raw); var n=name&&this.interfaces[name];
    if(name && !n) return [out(name+' is administratively down, line protocol is down (unconfigured)')];
    var o=[]; var list = name? [name] : Object.keys(this.interfaces);
    if(!list.length) return [out('(no interfaces configured yet)')];
    list.forEach(function(k){
      var i=self.interfaces[k];
      var st = i.shut? 'administratively down':'up';
      var pr = i.shut? 'down':'up';
      o.push(out(k+' is '+st+', line protocol is '+pr));
      o.push(out('  Internet address is '+(i.ip&&i.ip!=='dhcp'? i.ip+'/'+maskBits(i.mask):(i.ip==='dhcp'?'(via DHCP)':'not set'))));
      o.push(out('  '+(i.swmode? 'Switchport, mode '+i.swmode : 'Routed port')));
      o.push(out(''));
    });
    return o;
  };

  IOSDevice.prototype.showVlan = function(){
    var self=this;
    var o=[out('VLAN Name                             Status    Ports'),
           out('---- -------------------------------- --------- -------------------------------')];
    Object.keys(this.vlans).sort(function(a,b){return a-b;}).forEach(function(v){
      var ports=[];
      for(var k in self.interfaces){ if(self.interfaces[k].swmode==='access' && self.interfaces[k].accessVlan==v) ports.push(k); }
      o.push(out(pad(v,5)+pad(self.vlans[v].name,33)+pad('active',10)+ports.join(', ')));
    });
    return o;
  };

  IOSDevice.prototype.showStp = function(){
    return [out('Spanning tree mode: '+this.spanningTreeMode.toUpperCase()),
            out('VLAN0001'), out('  Root ID    Priority    32769'),
            out('             Address     0060.5c2a.1a00'),
            out('             This bridge is the root')];
  };

  // ---- utils ----
  function pad(s,n){ s=''+s; while(s.length<n) s+=' '; return s.slice(0,Math.max(n,s.length)); }
  function maskBits(m){ if(!m||m==='dhcp')return ''; return m.split('.').reduce(function(a,o){var b=(+o).toString(2);return a+(b.match(/1/g)||[]).length;},0); }
  function netOf(ip,mask){
    var ipp=ip.split('.').map(Number), mp=mask.split('.').map(Number);
    var net=ipp.map(function(o,i){return o & mp[i];}).join('.');
    return net+'/'+maskBits(mask);
  }
