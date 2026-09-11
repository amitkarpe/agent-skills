#!/usr/bin/env python3
"""Generate one self-contained multi-host Nessus CIS/HCR HTML report."""
from __future__ import annotations
import argparse,csv,html,json,re,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

REQUIRED={"Plugin","Plugin Name","Severity","IP Address","DNS Name","Plugin Output"}
CIS=re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$")
RESULT=re.compile(r"Result:\s*([A-Z]+)",re.I)
NS={"a":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RNS="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PNS={"p":"http://schemas.openxmlformats.org/package/2006/relationships"}

def status(output):
    vals=list(dict.fromkeys(x.upper() for x in RESULT.findall(output or "")))
    if len(vals)>1:return "CONFLICT"
    if not vals:return "UNKNOWN"
    return vals[0] if vals[0] in {"PASSED","FAILED","WARNING","ERROR","UNKNOWN"} else "UNKNOWN"

def part(output,name,stops):
    m=re.search(rf"{re.escape(name)}:\s*(.*?)(?=\n(?:{'|'.join(map(re.escape,stops))}):|\Z)",output or "",re.I|re.S)
    return " ".join(m.group(1).split()) if m else ""

def parse_output(output):
    return {"information":part(output,"Information",["Actual Value","Policy Value","Solution","Remediation","Result"]),
            "actual_value":part(output,"Actual Value",["Policy Value","Solution","Remediation","Result"]),
            "policy_value":part(output,"Policy Value",["Solution","Remediation","Result"]),
            "remediation":part(output,"Remediation",["Result"]) or part(output,"Solution",["Remediation","Result"])}

def area(name):
    x=name.lower()
    for needles,label in [(("audit",),"Audit"),(("log","journald","rsyslog"),"Logging"),(("selinux","unconfined"),"SELinux"),(("banner","message of the day"),"Banner"),(("password","authselect","sudo"),"Authentication"),(("partition","filesystem","world writable","suid","sgid"),"Filesystem"),(("chrony","time"),"Time"),(("ip forwarding","ipv6","firewall","listening","ssh access"),"Network"),(("gpg","repo","package","update"),"Package Trust")]:
        if any(n in x for n in needles):return label
    return "Other"

def xlsx(path):
    with zipfile.ZipFile(path) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            root=ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared=["".join(t.text or "" for t in si.iterfind(".//a:t",NS)) for si in root.findall("a:si",NS)]
        wb=ET.fromstring(z.read("xl/workbook.xml")); rel=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets={x.attrib["Id"]:x.attrib["Target"] for x in rel.findall("p:Relationship",PNS)}; out={}
        for s in wb.find("a:sheets",NS):
            target=targets[s.attrib[RNS]].lstrip("/"); target=target if target.startswith("xl/") else "xl/"+target
            root=ET.fromstring(z.read(target)); rows=[]
            for rr in root.findall(".//a:sheetData/a:row",NS):
                vals={}
                for c in rr.findall("a:c",NS):
                    col=0
                    for ch in re.match(r"[A-Z]+",c.attrib.get("r","A1")).group(0):col=col*26+ord(ch)-64
                    typ=c.attrib.get("t"); v=c.find("a:v",NS); ins=c.find("a:is",NS); val=""
                    if typ=="s" and v is not None and v.text is not None:val=shared[int(v.text)]
                    elif typ=="inlineStr" and ins is not None:val="".join(t.text or "" for t in ins.iterfind(".//a:t",NS))
                    elif v is not None and v.text is not None:val=v.text
                    vals[col]=val
                if vals:rows.append([vals.get(i,"") for i in range(1,max(vals)+1)])
            out[s.attrib["name"]]=rows
        return out

def header(rows,need):
    for i,row in enumerate(rows[:30]):
        m={}
        for j,v in enumerate(row):
            if str(v).strip():m.setdefault(str(v).strip(),j)
        if need<=set(m):return i,m

def risk_register(path):
    if not path:return {}
    for _,rows in xlsx(path).items():
        h=header(rows,{"Control ID","Risk Group"})
        if not h:continue
        hi,c=h
        def g(row,k):return str(row[c[k]]).strip() if k in c and c[k]<len(row) else ""
        out={}
        for row in rows[hi+1:]:
            cid=g(row,"Control ID")
            if not cid:continue
            decision=g(row,"Security Decision") or "Pending security review"; d=decision.lower()
            acceptance="Rejected" if "reject" in d else "Accepted" if "accept" in d and "pending" not in d else "Not Accepted" if "remediate" in d else "Pending TISO"
            out[cid]={"risk_group":g(row,"Risk Group"),"description":g(row,"Control Description"),"position":g(row,"Position"),"why_not_fixed":g(row,"Why Not Fixed Now"),"scope":g(row,"Workload Scope"),"compensating":g(row,"Compensating Controls"),"removal":g(row,"Removal Condition"),"acceptance_id":g(row,"Acceptance ID"),"approver":g(row,"Security Approver"),"risk_rating":g(row,"Risk Rating"),"expiry":g(row,"Expiry / Next Review"),"decision":decision,"acceptance":acceptance}
        return out
    raise SystemExit("Risk register XLSX: Control ID / Risk Group headers not found")

def tiso_risks(path):
    if not path:return {"sheet":"","risks":{},"findings":[]}
    for sheet,rows in xlsx(path).items():
        h=header(rows,{"Risk ID","Risk Statement"})
        if not h:continue
        hi,c=h
        def g(row,k):return str(row[c[k]]).strip() if k in c and c[k]<len(row) else ""
        risks={}; findings=[]
        for row in rows[hi+1:]:
            rid=g(row,"Risk ID")
            if not re.fullmatch(r"CS-\d+",rid):continue
            stmt=g(row,"Risk Statement"); title=stmt.split("Risk Statement:",1)[0].strip().splitlines()[0] if stmt else rid
            risks[rid]={"title":title,"initial_risk":str(row[12]) if len(row)>12 else "","residual_risk":str(row[15]) if len(row)>15 else ""}
            findings += [{"risk_group":rid,"control_id":cid,"description":desc.strip()} for cid,desc in re.findall(r"(?m)^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$",stmt)]
        return {"sheet":sheet,"risks":risks,"findings":findings}
    raise SystemExit("TISO XLSX: Risk ID / Risk Statement headers not found")

def norm(s):return " ".join(re.sub(r"[^a-z0-9/]+"," ",re.sub(r"\bensure\b","",(s or "").lower())).split())

def load_csv(path):
    with path.open(newline="",encoding="utf-8-sig",errors="replace") as f:rows=list(csv.DictReader(f))
    if not rows:raise SystemExit("CSV is empty")
    missing=REQUIRED-set(rows[0]);
    if missing:raise SystemExit(f"Missing required columns: {sorted(missing)}")
    out=[]; ignored=0
    for x in rows:
        m=CIS.match(x.get("Plugin Name",""))
        if not m:ignored+=1;continue
        cid,rule=m.groups(); po=x.get("Plugin Output","")
        out.append({"plugin":x.get("Plugin",""),"control_id":cid,"rule":rule,"status":status(po),"severity":x.get("Severity","") or "Unknown","ip":x.get("IP Address",""),"dns":x.get("DNS Name",""),"first_discovered":x.get("First Discovered",""),"last_observed":x.get("Last Observed",""),"area":area(rule),"evidence":" ".join(po.split())[:1200],**parse_output(po)})
    return out,ignored

def enrich(rows,register,tiso):
    byid={x["control_id"]:x for x in tiso["findings"]}; bytitle=defaultdict(list)
    for x in tiso["findings"]:bytitle[norm(x["description"])].append(x)
    for r in rows:
        cid=r["control_id"]
        if cid in register:
            x=register[cid];r.update(x);r.update(mapping_confidence="HIGH",mapping_source="Risk Acceptance register (curated current control)",tiso_control_id="",treatment="Risk Acceptance" if x["acceptance"] in {"Pending TISO","Accepted"} else "Remediate")
        elif cid in byid:
            x=byid[cid];r.update(risk_group=x["risk_group"],mapping_confidence="HIGH",mapping_source="TISO exact CIS ID",tiso_control_id=x["control_id"],acceptance="—",decision="—",treatment="Remediate" if r["status"]=="FAILED" else "Review Required")
        else:
            ms=bytitle.get(norm(r["rule"]),[])
            if len(ms)==1:
                x=ms[0];r.update(risk_group=x["risk_group"],mapping_confidence="REVIEW",mapping_source="TISO exact title match; benchmark/control ID differs",tiso_control_id=x["control_id"],acceptance="—",decision="—",treatment="Remediate" if r["status"]=="FAILED" else "Review Required")
            else:r.update(risk_group="—",mapping_confidence="UNMAPPED",mapping_source="No trustworthy deterministic match",tiso_control_id="",acceptance="—",decision="—",treatment="Remediate" if r["status"]=="FAILED" else "Review Required")
    return rows

def data(csv_path,reg_path,tiso_path):
    rows,ignored=load_csv(csv_path); register=risk_register(reg_path); tiso=tiso_risks(tiso_path); rows=enrich(rows,register,tiso)
    hosts=[]
    for ip in sorted({r["ip"] for r in rows if r["ip"]}):
        rs=[r for r in rows if r["ip"]==ip];c=Counter(r["status"] for r in rs);hosts.append({"ip":ip,"dns":next((r["dns"] for r in rs if r["dns"]),""),"total":len(rs),"failed":c["FAILED"],"review":c["WARNING"]+c["ERROR"]+c["UNKNOWN"]+c["CONFLICT"],"passed":c["PASSED"]})
    open_rows=[r for r in rows if r["status"]!="PASSED"]; current={r["control_id"] for r in open_rows}; unique=set(current); mapped={r["control_id"] for r in open_rows if r["mapping_confidence"]!="UNMAPPED"}
    meta={"source_name":csv_path.name,"input_rows":len(rows)+ignored,"cis_rows":len(rows),"ignored_rows":ignored,"hosts":len(hosts),"open_occurrences":len(open_rows),"failed_occurrences":sum(r["status"]=="FAILED" for r in open_rows),"review_occurrences":sum(r["status"] in {"WARNING","ERROR","UNKNOWN","CONFLICT"} for r in open_rows),"unique_open_controls":len(unique),"acceptance_candidates":len(register),"acceptance_currently_open":sum(cid in current for cid in register),"acceptance_not_open":sum(cid not in current for cid in register),"mapped_unique_controls":len(mapped),"unmapped_unique_controls":len(unique-mapped)}
    return {"meta":meta,"hosts":hosts,"rows":open_rows,"register":register,"tiso":tiso}

def render(d):
    J=json.dumps(d,ensure_ascii=False,separators=(",",":")).replace("</","<\\/"); source=html.escape(d["meta"]["source_name"])
    return f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HCR Advanced</title><style>body{{margin:0;background:#f4f7fb;color:#122033;font:14px system-ui}}*{{box-sizing:border-box}}header{{background:#0b2942;color:#fff;padding:22px}}nav{{position:sticky;top:0;background:#fff;padding:7px;display:flex;gap:5px;overflow:auto}}button,select,input{{padding:7px;border:1px solid #c7d2df;border-radius:6px;background:#fff}}main{{max-width:1580px;margin:auto;padding:16px}}.panel{{display:none}}.active{{display:block}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}.card,.box{{background:#fff;border:1px solid #d9e1ea;border-radius:9px;padding:13px;margin-bottom:12px}}.n{{font-size:24px;font-weight:800}}.toolbar{{display:flex;gap:6px;flex-wrap:wrap;background:#fff;padding:9px;margin-bottom:9px}}.toolbar input{{min-width:220px;flex:1}}.table{{overflow:auto;background:#fff}}table{{width:100%;border-collapse:collapse;min-width:950px}}th,td{{padding:8px;border-bottom:1px solid #e6ebf0;text-align:left;vertical-align:top}}th{{background:#eef4f8;position:sticky;top:0}}.pill{{padding:3px 7px;border-radius:99px;font-size:11px;font-weight:800}}.FAILED,.Rejected,.Remediate{{background:#fee4e2;color:#b42318}}.WARNING,.ERROR,.UNKNOWN,.CONFLICT,.PendingTISO,.ReviewRequired,.REVIEW{{background:#fff1cf;color:#9a5b00}}.Accepted,.HIGH{{background:#dcfae6;color:#067647}}.RiskAcceptance{{background:#eee5ff;color:#6938a8}}.UNMAPPED{{background:#eef2f6}}.muted{{color:#667085}}.dense td{{padding:4px;font-size:12px}}@media print{{nav,.toolbar{{display:none}}.panel{{display:block!important}}}}</style><header><h1>HCR Advanced — CIS Compliance & Risk Acceptance</h1><div>One multi-host report · scanner truth + TISO risk context + governance state</div></header><nav>{''.join(f'<button class="tab" data-id="{x}">{y}</button>' for x,y in [('dash','Dashboard'),('actions','Action Explorer'),('acceptance','Risk Acceptance'),('risk','TISO Risk Groups'),('unique','Unique Controls'),('evidence','Evidence & Mapping')])}</nav><main><section id="dash" class="panel active"><div id="kpis" class="grid"></div><div class="box"><h2>Host summary</h2><div id="hosts"></div></div><div class="box"><b>Risk Acceptance never changes scanner truth.</b> A FAILED control remains FAILED even if TISO later accepts the risk.</div></section><section id="actions" class="panel"><div class="toolbar"><select id="host"></select><select id="status"><option value="ALL">All status</option><option>FAILED</option><option>WARNING</option><option>ERROR</option><option>UNKNOWN</option><option>CONFLICT</option></select><select id="treatment"><option value="ALL">All treatment</option><option>Remediate</option><option>Risk Acceptance</option><option>Review Required</option></select><select id="acceptanceFilter"><option value="ALL">All acceptance</option><option>Pending TISO</option><option>Accepted</option><option>Rejected</option><option value="—">Not registered</option></select><select id="riskFilter"></select><select id="confidence"><option value="ALL">All mapping</option><option>HIGH</option><option>REVIEW</option><option>UNMAPPED</option></select><input id="q" placeholder="Search..."><button onclick="dense()">Dense</button><button onclick="exportCSV()">Export CSV</button><span id="count"></span></div><div class="table"><table id="actionsTable"></table></div></section><section id="acceptance" class="panel"><div class="box"><h2>Risk Acceptance candidates</h2><p>Candidate ≠ accepted. Pending stays Pending TISO until explicit approval evidence exists.</p></div><div class="table"><table id="acceptTable"></table></div></section><section id="risk" class="panel"><div class="box"><h2>TISO Risk Groups</h2><p>HIGH = curated/current or exact ID. REVIEW = exact title but benchmark ID differs. UNMAPPED = no deterministic match.</p></div><div id="riskCards"></div></section><section id="unique" class="panel"><div class="table"><table id="uniqueTable"></table></div></section><section id="evidence" class="panel"><div class="box"><h2>Source & mapping</h2><p><b>Nessus:</b> {source}</p><ol><li>Risk Acceptance register current-control mapping → HIGH.</li><li>TISO exact CIS ID → HIGH.</li><li>Exact title, different benchmark ID → REVIEW.</li><li>No trustworthy match → UNMAPPED; never guess.</li></ol></div></section></main><script>const D={J},S={{host:'ALL',status:'ALL',treatment:'ALL',acceptance:'ALL',risk:'ALL',confidence:'ALL',q:'',dense:false}};const e=x=>String(x??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])),cl=x=>String(x).replace(/[^A-Za-z0-9]/g,''),p=(x,c)=>`<span class="pill ${{c||cl(x)}}">${{e(x)}}</span>`,tr=x=>p(x,x==='Risk Acceptance'?'RiskAcceptance':x==='Review Required'?'ReviewRequired':'Remediate'),ac=x=>x==='—'?'—':p(x,cl(x));function tab(id){{document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===id))}}document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>tab(b.dataset.id));function filt(){{let z=D.rows.filter(r=>(S.host==='ALL'||r.ip===S.host)&&(S.status==='ALL'||r.status===S.status)&&(S.treatment==='ALL'||r.treatment===S.treatment)&&(S.acceptance==='ALL'||r.acceptance===S.acceptance)&&(S.risk==='ALL'||r.risk_group===S.risk)&&(S.confidence==='ALL'||r.mapping_confidence===S.confidence));let x=S.q.toLowerCase();return x?z.filter(r=>JSON.stringify(r).toLowerCase().includes(x)):z}}function draw(){{let z=filt();count.textContent=`${{z.length}} / ${{D.rows.length}}`;actionsTable.className=S.dense?'dense':'';actionsTable.innerHTML=`<tr><th>Host</th><th>Status</th><th>Control</th><th>Rule</th><th>Treatment</th><th>Risk Acceptance</th><th>Risk</th><th>Mapping</th><th>Evidence</th></tr>${{z.map(r=>`<tr><td>${{e(r.ip)}}</td><td>${{p(r.status,r.status)}}</td><td><b>${{e(r.control_id)}}</b></td><td>${{e(r.rule)}}</td><td>${{tr(r.treatment)}}</td><td>${{ac(r.acceptance)}}</td><td>${{e(r.risk_group)}}</td><td>${{p(r.mapping_confidence,r.mapping_confidence)}}</td><td><details><summary>Open</summary><b>Actual:</b> ${{e(r.actual_value||'—')}}<br><b>Policy:</b> ${{e(r.policy_value||'—')}}<br><b>Remediation:</b> ${{e(r.remediation||'—')}}<br><b>Mapping:</b> ${{e(r.mapping_source)}} ${{e(r.tiso_control_id||'')}}</details></td></tr>`).join('')}}`}}function init(){{host.add(new Option('All hosts','ALL'));D.hosts.forEach(x=>host.add(new Option(x.ip,x.ip)));riskFilter.add(new Option('All risk groups','ALL'));Object.keys(D.tiso.risks).sort().forEach(x=>riskFilter.add(new Option(x,x)));for(const [id,k] of [['host','host'],['status','status'],['treatment','treatment'],['acceptanceFilter','acceptance'],['riskFilter','risk'],['confidence','confidence']]){{let n=document.getElementById(id);n.onchange=()=>{{S[k]=n.value;draw()}}}}q.oninput=()=>{{S.q=q.value;draw()}};let m=D.meta;kpis.innerHTML=[['Hosts',m.hosts],['Open',m.open_occurrences],['FAILED',m.failed_occurrences],['Review',m.review_occurrences],['Acceptance candidates',m.acceptance_candidates],['Open candidates',m.acceptance_currently_open],['Mapped unique',m.mapped_unique_controls],['Unmapped unique',m.unmapped_unique_controls]].map(x=>`<div class="card"><div class="n">${{x[1]}}</div><div>${{x[0]}}</div></div>`).join('');hosts.innerHTML=`<table><tr><th>Host</th><th>Total CIS</th><th>FAILED</th><th>Review</th><th>PASSED</th><th>Compliance</th></tr>${{D.hosts.map(h=>`<tr><td>${{e(h.ip)}}</td><td>${{h.total}}</td><td>${{h.failed}}</td><td>${{h.review}}</td><td>${{h.passed}}</td><td>${{h.total?(100*h.passed/h.total).toFixed(1):0}}%</td></tr>`).join('')}}</table>`;acceptTable.innerHTML=`<tr><th>Control</th><th>Description</th><th>Risk</th><th>Acceptance</th><th>Why not fixed now</th></tr>${{Object.entries(D.register).sort().map(([c,r])=>`<tr><td>${{e(c)}}</td><td>${{e(r.description)}}</td><td>${{e(r.risk_group)}}</td><td>${{ac(r.acceptance)}}<br>${{e(r.decision)}}</td><td>${{e(r.why_not_fixed)}}</td></tr>`).join('')}}`;let u={{}};D.rows.forEach(r=>u[r.control_id]??={{...r,hosts:new Set()}});D.rows.forEach(r=>u[r.control_id].hosts.add(r.ip));uniqueTable.innerHTML=`<tr><th>Control</th><th>Rule</th><th>Hosts</th><th>Treatment</th><th>Acceptance</th><th>Risk</th><th>Mapping</th></tr>${{Object.values(u).sort((a,b)=>a.control_id.localeCompare(b.control_id,undefined,{{numeric:true}})).map(r=>`<tr><td>${{e(r.control_id)}}</td><td>${{e(r.rule)}}</td><td>${{r.hosts.size}}</td><td>${{tr(r.treatment)}}</td><td>${{ac(r.acceptance)}}</td><td>${{e(r.risk_group)}}</td><td>${{p(r.mapping_confidence,r.mapping_confidence)}}</td></tr>`).join('')}}`;riskCards.innerHTML=Object.entries(D.tiso.risks).sort().map(([g,r])=>`<div class="box"><h3>${{e(g)}} — ${{e(r.title)}}</h3><div>${{e(r.initial_risk)}} → ${{e(r.residual_risk)}}</div></div>`).join('');draw()}}function dense(){{S.dense=!S.dense;draw()}}function cv(x){{x=String(x??'');return /[",\n]/.test(x)?'"'+x.replace(/"/g,'""')+'"':x}}function exportCSV(){{let c=[['ip','IP'],['status','Status'],['control_id','Control ID'],['rule','Rule'],['treatment','Treatment'],['acceptance','Risk Acceptance'],['risk_group','Risk Group'],['mapping_confidence','Mapping']];let s=c.map(x=>x[1]).join(',')+'\n'+filt().map(r=>c.map(x=>cv(r[x[0]])).join(',')).join('\n');let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{{type:'text/csv'}}));a.download='HCR_filtered_actions.csv';a.click()}}window.addEventListener('DOMContentLoaded',init)</script>'''

def main():
    p=argparse.ArgumentParser();p.add_argument("csv_path",type=Path);p.add_argument("--html-out",type=Path);p.add_argument("--json-out",type=Path);p.add_argument("--risk-register",type=Path);p.add_argument("--tiso-risk",type=Path);a=p.parse_args();d=data(a.csv_path,a.risk_register,a.tiso_risk)
    if a.json_out:a.json_out.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    out=a.html_out or a.csv_path.with_name(a.csv_path.stem+"_HCR_Advanced.html");out.write_text(render(d),encoding="utf-8");print(json.dumps({"html":str(out),**d["meta"]},indent=2))
if __name__=="__main__":main()
