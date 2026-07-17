  // ============================================================
  //  Atlassian JSM Console  (Jira Service Management / ITIL 5)
  //  Rule-based, stateful-ish. Emits authentic tool output PLUS
  //  plain-English diagnostics (cls:'diag').
  //
  //  NOTE: ITIL is a service-management FRAMEWORK, not an operating
  //  system, so there is no "ITIL CLI". This console instead models
  //  the tooling an ITIL 5 practitioner actually drives day to day:
  //  the Atlassian CLI (acli jira ...), Jira Service Management
  //  request/queue/SLA/workflow administration, JQL queries, and
  //  curl calls to the Jira Service Management Cloud REST API. It
  //  validates the invocation shape and common flags and renders
  //  representative output tied back to ITIL practices (Incident,
  //  Change Enablement, Problem, Service Request, Service Desk,
  //  Service Level Management, Continual Improvement). It does not
  //  reach a real Atlassian site. Interface parity with the other
  //  consoles: .prompt() -> string and .exec(line) -> [{t, cls}]
  //  where cls in out|err|info|diag.
  // ============================================================
  function JSMConsole(site){
    this.site = site || 'acme';
    this.user = 'agent';
    this.authed = true;                 // acli jira auth status
    this.project = 'ITSM';              // default service project key
    this.seq = 42;                      // next issue number
    this.lastStatus = 0;
    // a tiny virtual backlog so create/view/transition feel stateful
    this.issues = {
      'ITSM-14': {type:'[System] Incident', summary:'Email delivery delayed for Sales', status:'In Progress', pri:'High',  assignee:'agent', sla:'Time to resolution', slaState:'PAUSED'},
      'ITSM-15': {type:'[System] Service Request', summary:'New laptop for onboarding hire', status:'Waiting for approval', pri:'Medium', assignee:'unassigned', sla:'Time to first response', slaState:'MET'},
      'ITSM-16': {type:'[System] Change', summary:'Upgrade payment gateway to v4', status:'Awaiting CAB', pri:'High', assignee:'change-mgr', sla:'—', slaState:'—'},
      'ITSM-17': {type:'[System] Problem', summary:'Recurring VPN drops root-cause', status:'Under investigation', pri:'Medium', assignee:'problem-mgr', sla:'—', slaState:'—'}
    };
  }

  // ---------- helpers ----------
  function jout(t){return {t:t,cls:'out'};}
  function jerr(t){return {t:t,cls:'err'};}
  function jinfo(t){return {t:t,cls:'info'};}
  function jdiag(t){return {t:t,cls:'diag'};}   // plain-English why/how-to-fix
  function jtoks(line){ return line.trim().split(/\s+/).filter(Boolean); }
  // tokenizer that respects "double" and 'single' quotes so --summary "a b" is one token
  function jtokq(line){
    var out=[], re=/"([^"]*)"|'([^']*)'|(\S+)/g, m;
    while((m=re.exec(line))!==null){ out.push(m[1]!==undefined?m[1]:(m[2]!==undefined?m[2]:m[3])); }
    return out;
  }
  function has(a, flag){ return a.indexOf(flag) !== -1; }
  function valOf(a, flag){
    var i=a.indexOf(flag);
    if(i!==-1 && i+1<a.length && String(a[i+1]).indexOf('--')!==0) return a[i+1];
    // support --flag=value form
    for(var k=0;k<a.length;k++){ if(a[k].indexOf(flag+'=')===0) return a[k].slice(flag.length+1); }
    return null;
  }

  JSMConsole.prototype.prompt = function(){
    return this.user+'@'+this.site+':jsm$';
  };

  JSMConsole.prototype.exec = function(rawLine){
    var line = (rawLine==null?'':(''+rawLine)).replace(/\r/g,'');
    var trimmed = line.trim();
    if(trimmed===''){ return []; }

    // strip a leading VAR=value assignment prefix (e.g. TOKEN=xyz acli ...)
    trimmed = trimmed.replace(/^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+/, '');

    // handle simple pipelines/redirects: validate the FIRST command, note the rest
    var piped = /[|]/.test(trimmed);
    var firstSeg = trimmed.split('|')[0].trim().replace(/\s*[<>]{1,2}\s*\S+\s*$/, '').trim();

    var t = jtokq(firstSeg);
    if(t.length===0){ return []; }
    var cmd = t[0];
    var a = t.slice(1);

    var res;
    try { res = this.run(cmd, a, firstSeg, trimmed, piped); }
    catch(e){ res = [ jerr('error: '+(e&&e.message||'internal')) ]; }
    return res;
  };

  JSMConsole.prototype.notFound = function(cmd){
    this.lastStatus = 127;
    return [ jerr("jsm: '"+cmd+"' is not a recognised command."),
             jdiag('\u21b3 This console models the Jira Service Management toolchain: acli (Atlassian CLI), jira, jsm, jql, curl to the JSM REST API, plus itil for a framework cheat-sheet. Type "help" to list command families, or check the verb spelling.') ];
  };

  JSMConsole.prototype.run = function(cmd, a, seg, full, piped){
    this.lastStatus = 0;
    switch(cmd){

    // ---------------- console basics ----------------
    case 'help': case '?':
      return [ jinfo('Jira Service Management console \u2014 ITIL 5 tooling. Command families:'),
        jout('  acli jira ...   Atlassian CLI: auth / project / workitem create|search|view|transition|assign|comment'),
        jout('  jira ...        short alias for issue create/list/transition/comment (maps to ITIL practices)'),
        jout('  jsm ...         service desk: request create, queue list, sla show, approval, workflow, customer'),
        jout('  jql "<query>"   run a Jira Query Language search against the service project'),
        jout('  curl ...        call the Jira Service Management Cloud REST API (/rest/servicedeskapi, /rest/api/3)'),
        jout('  itil <topic>    quick framework reference (practices, principles, value chain, dimensions)'),
        jinfo('Every rejected command shows the authentic tool error AND a plain-English fix.') ];
    case 'clear': return [ {t:'__CLEAR__', cls:'ctl'} ];
    case 'whoami': return [ jout(this.user+' (Jira Service Management agent on '+this.site+'.atlassian.net)') ];
    case 'echo': return [ jout(a.join(' ')) ];

    // ---------------- Atlassian CLI ----------------
    case 'acli': return this.acli(a);

    // ---------------- short jira alias ----------------
    case 'jira': return this.jira(a);

    // ---------------- JSM service-desk admin ----------------
    case 'jsm': return this.jsm(a);

    // ---------------- JQL ----------------
    case 'jql': return this.jql(a, seg);

    // ---------------- REST API ----------------
    case 'curl': return this.curl(a, seg);

    // ---------------- framework reference ----------------
    case 'itil': return this.itil(a);

    default:
      return this.notFound(cmd);
    }
  };

  // ---------------- acli (Atlassian CLI) ----------------
  JSMConsole.prototype.acli = function(a){
    if(!a.length) return [ jinfo('The Atlassian command line interface.'),
      jout('Usage:  acli <product> <command> [subcommand] [flags]'),
      jout('Products: jira'),
      jdiag('\u21b3 Try "acli jira auth status", "acli jira workitem create --project ITSM --type Incident --summary \"...\"", or "acli jira --help".') ];
    if(a[0]!=='jira') return [ jerr('Error: unknown product "'+a[0]+'" for "acli"'),
      jdiag('\u21b3 The simulated ACLI supports the "jira" product. Example: "acli jira workitem search --jql \"project = ITSM\"".') ];

    var sub = a[1];
    var rest = a.slice(2);
    if(!sub) return [ jinfo('acli jira \u2014 manage Jira / Jira Service Management from the terminal.'),
      jout('Commands: auth, project, workitem'),
      jdiag('\u21b3 e.g. "acli jira workitem create ...", "acli jira project create ...", "acli jira auth login --web".') ];

    if(sub==='auth')     return this.acliAuth(rest);
    if(sub==='project')  return this.acliProject(rest);
    if(sub==='workitem') return this.acliWorkitem(rest);
    return [ jerr('Error: unknown command "'+sub+'" for "acli jira"'),
      jdiag('\u21b3 Valid commands are auth, project and workitem. Check the verb after "acli jira".') ];
  };

  JSMConsole.prototype.acliAuth = function(a){
    var v = a[0];
    if(v==='status'){
      if(this.authed) return [ jout('\u2714 Logged in to '+this.site+'.atlassian.net as '+this.user+'@'+this.site+'.com'), jinfo('Auth token cached \u2014 subsequent commands run against this site.') ];
      return [ jerr('\u2717 Not logged in.'), jdiag('\u21b3 Run "acli jira auth login --web" (browser) or "acli jira auth login --token" (API token) before other commands.') ];
    }
    if(v==='login'){
      this.authed = true;
      return [ jout('Opening browser to authenticate\u2026'), jout('\u2714 Authenticated to '+this.site+'.atlassian.net as '+this.user+'@'+this.site+'.com'),
        jinfo('Use --token with an API token for headless/CI login instead of --web.') ];
    }
    if(v==='logout'){ this.authed=false; return [ jout('\u2714 Logged out of '+this.site+'.atlassian.net') ]; }
    if(v==='switch'){ return [ jout('Active site set to '+(a[1]||this.site)+'.atlassian.net') ]; }
    return [ jerr('Error: unknown command "'+(v||'')+'" for "acli jira auth"'),
      jdiag('\u21b3 Valid auth commands: login, logout, status, switch. Most people start with "acli jira auth login --web".') ];
  };

  JSMConsole.prototype.acliProject = function(a){
    var v = a[0];
    if(v==='create'){
      var key = valOf(a,'--key'); var name = valOf(a,'--name');
      if(has(a,'--generate-json')) return [ jout('Wrote project-template.json \u2014 edit it, then run: acli jira project create --from-json project-template.json'), jinfo('--generate-json / --from-json lets you version-control project setup (Infrastructure as Code for ITSM).') ];
      if(!key || !name) return [ jerr('Error: required flag(s) "key", "name" not set'),
        jdiag('\u21b3 A project needs a key and a name: acli jira project create --key ITSM --name "IT Service Management" --type service_desk.') ];
      return [ jout('\u2714 Project "'+name+'" ('+key+') created.'), jinfo('A service project bundles the request types, queues, SLAs and workflows that operationalise your ITIL practices.') ];
    }
    if(v==='list') return [ jout('KEY    NAME                        TYPE'), jout('ITSM   IT Service Management       service_desk'), jout('OPS    Operations                  service_desk'), jout('DEV    Product Development         software') ];
    if(v==='archive'){ var k=valOf(a,'--key')||a[1]; if(!k) return [ jerr('Error: required flag "key" not set'), jdiag('\u21b3 Specify which project: acli jira project archive --key ITSM.') ]; return [ jout('\u2714 Project '+k+' archived.'), jinfo('Archiving hides a project without deleting its history (safer than delete, which is irreversible).') ]; }
    if(v==='delete'){ var k2=valOf(a,'--key')||a[1]; if(!k2) return [ jerr('Error: required flag "key" not set'), jdiag('\u21b3 Deleting a project is permanent and cannot be restored \u2014 prefer "archive". If you are sure: acli jira project delete --key '+(k2||'KEY')+'.') ]; return [ jout('\u2714 Project '+k2+' deleted.'), jinfo('Deletion is irreversible \u2014 there is no undo for a deleted Jira project.') ]; }
    return [ jerr('Error: unknown command "'+(v||'')+'" for "acli jira project"'),
      jdiag('\u21b3 project commands: create, list, archive, delete. Example: "acli jira project list".') ];
  };

  JSMConsole.prototype.acliWorkitem = function(a){
    var v = a[0];
    var rest = a.slice(1);
    if(v==='create')     return this.wiCreate(rest);
    if(v==='search')     return this.wiSearch(rest);
    if(v==='view')       return this.wiView(rest);
    if(v==='edit')       return this.wiEdit(rest);
    if(v==='transition') return this.wiTransition(rest);
    if(v==='assign')     return this.wiAssign(rest);
    if(v==='comment')    return this.wiComment(rest);
    if(v==='delete'){ var k=valOf(rest,'--key')||rest[0]; if(!k) return [ jerr('Error: required flag "key" not set'), jdiag('\u21b3 Give the issue key: acli jira workitem delete --key ITSM-15.') ]; return [ jout('\u2714 Work item '+k+' deleted.') ]; }
    return [ jerr('Error: unknown command "'+(v||'')+'" for "acli jira workitem"'),
      jdiag('\u21b3 workitem commands: create, search, view, edit, transition, assign, comment, delete. e.g. "acli jira workitem view ITSM-14".') ];
  };

  JSMConsole.prototype.wiCreate = function(a){
    if(has(a,'--generate-json')) return [ jout('Wrote workitem.json template.'), jinfo('Fill it in and pass --from-json workitem.json to create reproducibly.') ];
    var proj = valOf(a,'--project') || valOf(a,'-p');
    var type = valOf(a,'--type') || valOf(a,'-t');
    var summ = valOf(a,'--summary') || valOf(a,'-s');
    var missing = [];
    if(!proj) missing.push('project'); if(!type) missing.push('type'); if(!summ) missing.push('summary');
    if(missing.length) return [ jerr('Error: required flag(s) "'+missing.join('", "')+'" not set'),
      jdiag('\u21b3 A work item needs at least a project, a type and a summary: acli jira workitem create --project ITSM --type Incident --summary "Payment API returning 500s".') ];
    var known = {'incident':1,'service request':1,'request':1,'change':1,'problem':1,'task':1,'bug':1,'story':1,'epic':1,'subtask':1};
    if(!known[String(type).toLowerCase()]) return [ jerr('Error: "'+type+'" is not a valid work item type for project '+proj),
      jdiag('\u21b3 Allowed types include Incident, Service Request, Change, Problem, Task. In an ITIL service project the type maps to the practice (Incident \u2192 Incident Management, Change \u2192 Change Enablement).') ];
    var key = proj+'-'+(this.seq++);
    var asg = valOf(a,'--assignee')||valOf(a,'-a')||'unassigned';
    if(asg==='@me') asg=this.user;
    this.issues[key] = {type:'[System] '+type, summary:summ, status:'Open', pri:'Medium', assignee:asg, sla:'Time to first response', slaState:'RUNNING'};
    var out=[ jout('\u2714 Created '+key), jout('  '+type+': '+summ), jout('  Project: '+proj+'   Assignee: '+asg) ];
    var lt=String(type).toLowerCase();
    if(lt==='incident') out.push(jinfo('Incident Management: the goal is to restore normal service as quickly as possible and minimise business impact.'));
    else if(lt==='change') out.push(jinfo('Change Enablement: assess, authorise and schedule changes to maximise successful changes while managing risk.'));
    else if(lt==='problem') out.push(jinfo('Problem Management: find the root cause of one or more incidents to reduce their likelihood and impact.'));
    else if(lt==='service request'||lt==='request') out.push(jinfo('Service Request Management: handle pre-defined, low-risk user requests through a repeatable, often self-service, flow.'));
    return out;
  };

  JSMConsole.prototype.wiSearch = function(a){
    var jqlv = valOf(a,'--jql');
    var rows = Object.keys(this.issues);
    if(jqlv){
      var m = /status\s*=\s*["']?([^"']+)["']?/i.exec(jqlv);
      if(m){ var want=m[1].toLowerCase(); rows = rows.filter(function(k){return this.issues[k].status.toLowerCase()===want;}.bind(this)); }
    }
    if(!rows.length) return [ jout('No work items matched.'), jinfo('Broaden the JQL, or check the status spelling against your workflow.') ];
    var out=[ jout('KEY       TYPE                      STATUS                 PRI     ASSIGNEE') ];
    rows.forEach(function(k){ var i=this.issues[k];
      out.push(jout(pad(k,10)+pad(i.type.replace('[System] ',''),26)+pad(i.status,23)+pad(i.pri,8)+i.assignee)); }.bind(this));
    out.push(jinfo(rows.length+' work item(s). Add --json for machine output, or --fields "key,summary,status" to trim columns.'));
    return out;
  };

  JSMConsole.prototype.wiView = function(a){
    var key = a.find(function(x){return /^[A-Z]+-\d+$/.test(x);}) || valOf(a,'--key');
    if(!key) return [ jerr('Error: a work item key is required'), jdiag('\u21b3 e.g. "acli jira workitem view ITSM-14". The key is PROJECT-NUMBER.') ];
    var i = this.issues[key];
    if(!i) return [ jerr("Error: work item '"+key+"' does not exist or you lack permission"),
      jdiag('\u21b3 Check the key. Known demo items: '+Object.keys(this.issues).join(', ')+'.') ];
    return [ jout('Key       : '+key),
      jout('Type      : '+i.type),
      jout('Summary   : '+i.summary),
      jout('Status    : '+i.status),
      jout('Priority  : '+i.pri),
      jout('Assignee  : '+i.assignee),
      jout('SLA       : '+i.sla+'  ['+i.slaState+']'),
      jinfo('Status reflects the workflow step; SLA state shows whether the service target clock is running, paused, met or breached.') ];
  };

  JSMConsole.prototype.wiEdit = function(a){
    var key = valOf(a,'--key')||a.find(function(x){return /^[A-Z]+-\d+$/.test(x);});
    if(!key) return [ jerr('Error: required flag "key" not set'), jdiag('\u21b3 Say which item to edit: acli jira workitem edit --key ITSM-14 --summary "...".') ];
    var i=this.issues[key];
    if(!i) return [ jerr("Error: work item '"+key+"' not found"), jdiag('\u21b3 Verify the key first with "acli jira workitem view '+key+'".') ];
    var s=valOf(a,'--summary'); if(s) i.summary=s;
    var p=valOf(a,'--priority'); if(p) i.pri=p;
    return [ jout('\u2714 Updated '+key) ];
  };

  JSMConsole.prototype.wiTransition = function(a){
    var key = valOf(a,'--key')||a.find(function(x){return /^[A-Z]+-\d+$/.test(x);});
    var status = valOf(a,'--status');
    if(!key) return [ jerr('Error: required flag "key" not set'), jdiag('\u21b3 e.g. "acli jira workitem transition --key ITSM-14 --status Resolved".') ];
    if(!status) return [ jerr('Error: required flag "status" not set'), jdiag('\u21b3 Provide the target status: --status "In Progress" | Resolved | Done. It must be a transition allowed by the workflow.') ];
    var i=this.issues[key];
    if(!i) return [ jerr("Error: work item '"+key+"' not found"), jdiag('\u21b3 Check the key with "acli jira workitem view '+key+'".') ];
    var allowed = {'open':1,'in progress':1,'waiting for support':1,'waiting for customer':1,'resolved':1,'done':1,'closed':1,'escalated':1,'awaiting cab':1,'under investigation':1};
    if(!allowed[status.toLowerCase()]) return [ jerr('Error: "'+status+'" is not a valid transition from "'+i.status+'"'),
      jdiag('\u21b3 A workflow only permits certain moves. Valid targets here: Open, In Progress, Waiting for customer, Resolved, Done, Closed, Escalated. The workflow is what enforces ITIL process discipline.') ];
    var old=i.status; i.status=status;
    var out=[ jout('\u2714 '+key+': "'+old+'" \u2192 "'+status+'"') ];
    if(/resolv|done|clos/i.test(status)) out.push(jinfo('Resolving stops the "Time to resolution" SLA clock. For an incident, confirm the user agrees service is restored before closing.'));
    return out;
  };

  JSMConsole.prototype.wiAssign = function(a){
    var key = valOf(a,'--key')||a.find(function(x){return /^[A-Z]+-\d+$/.test(x);});
    var who = valOf(a,'--assignee');
    if(!key||!who) return [ jerr('Error: required flag(s) "key", "assignee" not set'), jdiag('\u21b3 e.g. "acli jira workitem assign --key ITSM-14 --assignee @me" (or an email / account id).') ];
    var i=this.issues[key]; if(!i) return [ jerr("Error: work item '"+key+"' not found"), jdiag('\u21b3 Verify the key first.') ];
    if(who==='@me') who=this.user;
    i.assignee=who;
    return [ jout('\u2714 '+key+' assigned to '+who) ];
  };

  JSMConsole.prototype.wiComment = function(a){
    if(a[0]!=='create' && a[0]!=='add') return [ jerr('Error: unknown command "'+(a[0]||'')+'" for "acli jira workitem comment"'),
      jdiag('\u21b3 Use "comment create": acli jira workitem comment create --key ITSM-14 --body "Investigating now".') ];
    var key = valOf(a,'--key'); var body = valOf(a,'--body');
    if(!key||!body) return [ jerr('Error: required flag(s) "key", "body" not set'), jdiag('\u21b3 Provide both: --key ITSM-14 --body "your comment". Comments to the customer keep them informed (Service Desk practice).') ];
    return [ jout('\u2714 Comment added to '+key), jinfo('Keeping the requester updated is core to the Service Desk practice and improves the experience even before resolution.') ];
  };

  // ---------------- jira short alias ----------------
  JSMConsole.prototype.jira = function(a){
    if(!a.length) return [ jinfo('jira \u2014 lightweight alias over the service project '+this.project+'.'),
      jout('  jira create <Type> "<summary>"     jira list [status]'),
      jout('  jira transition <KEY> <Status>     jira comment <KEY> "<text>"   jira view <KEY>'),
      jdiag('\u21b3 For full flag control use the Atlassian CLI form, e.g. "acli jira workitem create --project ITSM --type Incident --summary \"...\"".') ];
    var v=a[0];
    if(v==='create'){
      var type=a[1]; var summ=a.slice(2).join(' ');
      if(!type||!summ) return [ jerr('usage: jira create <Type> "<summary>"'), jdiag('\u21b3 e.g. jira create Incident "Payment API returning 500s". Type maps to the ITIL practice.') ];
      return this.wiCreate(['--project',this.project,'--type',type,'--summary',summ]);
    }
    if(v==='list'){ var f=a[1]?['--jql','status = "'+a.slice(1).join(' ')+'"']:[]; return this.wiSearch(f); }
    if(v==='view') return this.wiView(a.slice(1));
    if(v==='transition') return this.wiTransition(['--key',a[1],'--status',a.slice(2).join(' ')]);
    if(v==='comment') return this.wiComment(['create','--key',a[1],'--body',a.slice(2).join(' ')]);
    if(v==='assign') return this.wiAssign(['--key',a[1],'--assignee',a[2]]);
    return [ jerr("jira: unknown subcommand '"+v+"'"), jdiag('\u21b3 Try create, list, view, transition, comment or assign.') ];
  };

  // ---------------- jsm service-desk admin ----------------
  JSMConsole.prototype.jsm = function(a){
    if(!a.length) return [ jinfo('jsm \u2014 Jira Service Management service-desk administration.'),
      jout('  jsm request create --type <name> --summary "<text>"     jsm queue list'),
      jout('  jsm sla show <KEY>      jsm approval approve|decline <KEY>     jsm workflow show'),
      jout('  jsm customer add <email>       jsm knowledge search "<terms>"'),
      jdiag('\u21b3 These map ITIL practices to JSM features: queues=Service Desk triage, SLA=Service Level Management, approval=Change Enablement, knowledge=knowledge management.') ];
    var v=a[0];
    if(v==='request'){
      if(a[1]!=='create') return [ jerr("jsm request: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Use "jsm request create --type \"Get IT help\" --summary \"...\"". Requests come in through the customer portal.') ];
      var type=valOf(a,'--type'); var summ=valOf(a,'--summary');
      if(!type||!summ) return [ jerr('Error: required flag(s) "type", "summary" not set'), jdiag('\u21b3 A customer request needs a request type and a summary. Request types are the portal-facing forms mapped to issue types.') ];
      return [ jout('\u2714 Request created as '+this.project+'-'+(this.seq++)+' via request type "'+type+'"'),
        jinfo('Request types are the customer-friendly forms on the portal; each maps to an issue type and workflow behind the scenes (Service Request Management).') ];
    }
    if(v==='queue'){
      if(a[1]==='list') return [ jout('QUEUE                        JQL                                                  COUNT'),
        jout('Unassigned incidents         type = Incident AND assignee is EMPTY                  3'),
        jout('SLA breaching soon           "Time to resolution" < remaining("2h")                2'),
        jout('Awaiting approval (changes)  type = Change AND status = "Awaiting CAB"              1'),
        jout('Waiting for customer         status = "Waiting for customer"                        4'),
        jinfo('Queues are saved JQL filters that route work to the right agents \u2014 the operational face of the Service Desk practice.') ];
      return [ jerr("jsm queue: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Try "jsm queue list".') ];
    }
    if(v==='sla'){
      if(a[1]==='show'){
        var key=a[2]; if(!key||!this.issues[key]) return [ jerr('Error: provide a valid issue key'), jdiag('\u21b3 e.g. "jsm sla show ITSM-14". SLAs are configured per service target.') ];
        var i=this.issues[key];
        return [ jout('SLA for '+key),
          jout('  Time to first response : MET (00:07 of 00:15 goal)'),
          jout('  Time to resolution     : '+(i.slaState==='PAUSED'?'PAUSED (clock stopped while Waiting for customer)':'RUNNING (02:41 of 08:00 goal)')),
          jinfo('Service Level Management defines, measures and reports these targets; pausing on "Waiting for customer" stops penalising the team for customer delay.') ];
      }
      return [ jerr("jsm sla: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Try "jsm sla show ITSM-14".') ];
    }
    if(v==='approval'){
      var act=a[1]; var key=a[2];
      if((act!=='approve'&&act!=='decline')||!key) return [ jerr('usage: jsm approval approve|decline <KEY>'), jdiag('\u21b3 e.g. "jsm approval approve ITSM-16". Approvals gate Change Enablement (the CAB decision).') ];
      var i=this.issues[key]; if(!i) return [ jerr("Error: '"+key+"' not found"), jdiag('\u21b3 Check the key.') ];
      i.status = act==='approve'?'Scheduled':'Rejected';
      return [ jout('\u2714 '+key+' '+(act==='approve'?'approved':'declined')+' \u2192 status "'+i.status+'"'),
        jinfo('Change Enablement: authorising a change (often via a change authority / CAB) balances the benefit of the change against its risk before deployment.') ];
    }
    if(v==='workflow'){
      if(a[1]==='show') return [ jout('Workflow: ITSM Incident'),
        jout('  Open \u2192 In Progress \u2192 Waiting for customer \u2192 Resolved \u2192 Closed'),
        jout('                 \u2514\u2192 Escalated \u2192 In Progress'),
        jinfo('Workflows encode the allowed status transitions; they operationalise ITIL practices and enforce that work moves in a controlled, auditable way.') ];
      return [ jerr("jsm workflow: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Try "jsm workflow show".') ];
    }
    if(v==='customer'){
      if(a[1]==='add'){ var e=a[2]; if(!e||e.indexOf('@')<0) return [ jerr('Error: a valid email is required'), jdiag('\u21b3 e.g. "jsm customer add jane@acme.com". Customers get portal access to raise and track requests.') ]; return [ jout('\u2714 Customer '+e+' added and invited to the portal.') ]; }
      return [ jerr("jsm customer: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Try "jsm customer add <email>".') ];
    }
    if(v==='knowledge'){
      if(a[1]==='search'){ var q=valOf(a,'--query')||a.slice(2).join(' ')||'vpn'; return [ jout('Knowledge base results for "'+q+'":'), jout('  KB-12  How to reset your VPN client   (helpful: 87%)'), jout('  KB-30  Known error: VPN drops on Wi-Fi roaming'), jinfo('Surfacing knowledge articles deflects tickets via self-service and speeds first-line resolution (knowledge management + Service Desk).') ]; }
      return [ jerr("jsm knowledge: unknown action '"+(a[1]||'')+"'"), jdiag('\u21b3 Try "jsm knowledge search \"vpn\"".') ];
    }
    return [ jerr("jsm: unknown area '"+v+"'"), jdiag('\u21b3 Areas: request, queue, sla, approval, workflow, customer, knowledge.') ];
  };

  // ---------------- JQL ----------------
  JSMConsole.prototype.jql = function(a, seg){
    var q = seg.replace(/^jql\s+/,'').replace(/^["']|["']$/g,'').trim();
    if(!q) return [ jerr('jql: a query is required'),
      jdiag('\u21b3 e.g. jql "project = ITSM AND type = Incident AND status != Done ORDER BY priority DESC". JQL is how queues, filters and reports are defined.') ];
    // very light validity check: must reference a field and an operator
    if(!/[=<>~!]|(\bIN\b)|(\bIS\b)/i.test(q)) return [ jerr('Error: expecting an operator but got: "'+q+'"'),
      jdiag('\u21b3 JQL clauses are field OPERATOR value, e.g. status = "In Progress". Combine with AND / OR and finish with ORDER BY.') ];
    var rows = Object.keys(this.issues).slice(0,3);
    var out=[ jout('Executed: '+q), jout('KEY       SUMMARY') ];
    rows.forEach(function(k){ out.push(jout(pad(k,10)+this.issues[k].summary)); }.bind(this));
    out.push(jinfo('JQL powers queues, dashboards and SLA scopes \u2014 mastering it is how ITIL reporting and Continual Improvement get their numbers.'));
    return out;
  };

  // ---------------- curl to the JSM REST API ----------------
  JSMConsole.prototype.curl = function(a, seg){
    if(!a.length) return [ jerr("curl: try 'curl --help' for more information"),
      jdiag('\u21b3 Call the JSM API, e.g. curl -s -u me@acme.com:$TOKEN https://acme.atlassian.net/rest/servicedeskapi/request') ];
    var url = a.find(function(x){return /^https?:\/\//.test(x);}) || '';
    if(!url) return [ jerr('curl: no URL specified'), jdiag('\u21b3 Provide a full https URL to the Atlassian Cloud REST API.') ];
    var m = /-X\s+(\w+)/.exec(seg) || (/--request\s+(\w+)/.exec(seg));
    var method = m ? m[1].toUpperCase() : (/-d\b|--data/.test(seg)?'POST':'GET');
    var authed = /-u\s+\S+|Authorization:/.test(seg);
    if(!authed) return [ jerr('{"errorMessages":["Client must be authenticated to access this resource."],"errors":{}}'),
      jdiag('\u21b3 The JSM API needs auth. Use basic auth with an API token: curl -u you@acme.com:$TOKEN ... (never your password), or a Bearer token.') ];
    if(/\/rest\/servicedeskapi\/request\b/.test(url)){
      if(method==='POST') return [ jout('{ "issueKey": "'+this.project+'-'+(this.seq++)+'", "requestTypeId": "25", "currentStatus": { "status": "Open" } }'),
        jinfo('POST /rest/servicedeskapi/request raises a customer request programmatically \u2014 useful for integrations and Service Request automation.') ];
      return [ jout('{ "values": [ { "issueKey": "ITSM-14", "requestTypeId": "10", "currentStatus": {"status":"In Progress"} } ], "size": 1 }'),
        jinfo('The Service Desk API returns customer-facing requests; the platform API (/rest/api/3) exposes the full issue model.') ];
    }
    if(/\/rest\/servicedeskapi\/.*sla/i.test(url) || /\/sla\b/i.test(url)) return [ jout('{ "values": [ { "name": "Time to resolution", "ongoingCycle": { "breached": false, "remainingTime": {"friendly":"2h 41m"} } } ] }'),
      jinfo('Query SLA cycles to build Service Level Management reports and breach alerts.') ];
    if(/\/rest\/api\/3\/(issue|search)/.test(url)){
      if(method==='POST') return [ jout('{ "id": "10921", "key": "'+this.project+'-'+(this.seq++)+'", "self": "https://'+this.site+'.atlassian.net/rest/api/3/issue/10921" }'),
        jinfo('POST /rest/api/3/issue creates an issue with a full ADF body \u2014 the platform equivalent of "acli jira workitem create".') ];
      return [ jout('{ "issues": [ { "key": "ITSM-14", "fields": { "status": {"name":"In Progress"} } } ], "total": 1 }'),
        jinfo('GET /rest/api/3/search runs JQL over the REST API for dashboards and integrations.') ];
    }
    return [ jout('{ "message": "OK" }  (HTTP 200)'),
      jinfo('Add -s to silence progress and | jq to parse. Base URLs: /rest/servicedeskapi (JSM) and /rest/api/3 (Jira platform).') ];
  };

  // ---------------- framework reference ----------------
  JSMConsole.prototype.itil = function(a){
    var topic = (a[0]||'').toLowerCase();
    if(topic==='principles'||topic==='principle') return [ jinfo('The 7 ITIL guiding principles:'),
      jout('  1. Focus on value            2. Start where you are'),
      jout('  3. Progress iteratively with feedback   4. Collaborate and promote visibility'),
      jout('  5. Think and work holistically   6. Keep it simple and practical'),
      jout('  7. Optimize and automate') ];
    if(topic==='dimensions'||topic==='dimension') return [ jinfo('The 4 dimensions of service management:'),
      jout('  1. Organizations & People    2. Information & Technology'),
      jout('  3. Partners & Suppliers      4. Value Streams & Processes') ];
    if(topic==='valuechain'||topic==='chain') return [ jinfo('Service value chain (ITIL 5 \u2014 eight activities):'),
      jout('  Plan \u00b7 Improve \u00b7 Engage \u00b7 Design & Transition \u00b7 Obtain/Build \u00b7 Deliver & Support (+ V5 additions)'),
      jinfo('Value streams are flexible combinations of these activities that turn demand into value.') ];
    if(topic==='practices'||topic==='practice') return [ jinfo('Key ITIL practices this console models:'),
      jout('  Incident Mgmt      restore normal service asap'),
      jout('  Problem Mgmt       remove root cause of incidents'),
      jout('  Change Enablement  authorise & schedule changes (CAB / approvals)'),
      jout('  Service Request    fulfil pre-approved user requests'),
      jout('  Service Desk       single point of contact + queues'),
      jout('  Service Level Mgmt define & report SLAs'),
      jout('  Continual Improve  the CI register + improvement model') ];
    if(topic==='journey') return [ jinfo('Service journey (7 steps, ITIL 5):'),
      jout('  Explore \u00b7 Engage \u00b7 Offer \u00b7 Agree \u00b7 Onboard \u00b7 Co-create \u00b7 Realize') ];
    return [ jinfo('itil <topic> quick reference. Topics: principles, dimensions, valuechain, practices, journey.'),
      jdiag('\u21b3 e.g. "itil principles". This is a study aid \u2014 the exam tests these concepts, and the JSM tooling above shows how they are operationalised.') ];
  };

  // right-pad helper for table columns
  function pad(s, n){ s=''+s; while(s.length<n) s+=' '; return s; }

  // expose
  window.JSMConsole = JSMConsole;
