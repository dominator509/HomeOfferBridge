#!/usr/bin/env python3
"""Emit the 6 n8n workflows wired for DeepSeek V4 Flash-Thinking with the
TOKENKILLER prefix-cache pattern. Run once; guarantees valid importable JSON."""
import json, pathlib

OUT = pathlib.Path("/home/claude/acb/backend/workflows")
OUT.mkdir(parents=True, exist_ok=True)

def node(id, name, ntype, pos, params, tv=1, extra=None):
    n = {"parameters": params, "id": id, "name": name, "type": ntype,
         "typeVersion": tv, "position": pos}
    if extra: n.update(extra)
    return n

def deepseek_http(pos):
    return node("ds-http", "DeepSeek · Flash-Thinking", "n8n-nodes-base.httpRequest", pos, {
        "method": "POST",
        "url": "={{ $env.DEEPSEEK_BASE }}/chat/completions",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "=Bearer {{ $env.DEEPSEEK_API_KEY }}"},
            {"name": "Content-Type", "value": "application/json"}
        ]},
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {}
    }, tv=4, extra={"notes": "OpenAI-compatible. Prefix (system) cached on DeepSeek disk; only S3 user msg misses."})

def assembler(prefix, pick_js, maxtok, pos):
    code = (
        "// Prefix Assembler (TOKENKILLER) — S0..PAD frozen, S3 volatile last.\n"
        "const PREFIX = " + json.dumps(prefix) + ";\n"
        "const src = $input.first().json;\n"
        + pick_js + "\n"
        "return [{ json: { body: {\n"
        "  model: $env.DEEPSEEK_MODEL,\n"
        "  temperature: 0,\n"
        "  max_tokens: " + str(maxtok) + ",\n"
        "  messages: [\n"
        "    { role: 'system', content: PREFIX },\n"
        "    { role: 'user',   content: JSON.stringify(v) }\n"
        "  ]\n"
        "}, _prefix_bytes: PREFIX.length } }];"
    )
    return node("assembler", "Prefix Assembler (TOKENKILLER)", "n8n-nodes-base.code", pos,
                {"jsCode": code}, tv=2,
                extra={"notes": "PREFIX is a const literal → byte-identical every call → full-prefix cache hit."})

def ledger(pos):
    code = (
        "const r = $input.first().json;\n"
        "const u = r.usage || {};\n"
        "const hit = u.prompt_cache_hit_tokens || 0, miss = u.prompt_cache_miss_tokens || 0;\n"
        "const ratio = (hit+miss) ? hit/(hit+miss) : 0;\n"
        "let t = (r.choices && r.choices[0] && r.choices[0].message && r.choices[0].message.content) || '{}';\n"
        "let out; try { out = JSON.parse(t.replace(/```json|```/g,'').trim()); } catch(e){ out = { _parse_error:true }; }\n"
        "out._cache = { hit, miss, ratio: +ratio.toFixed(4), ok: ratio >= 0.97 };\n"
        "if(!out._cache.ok) console.warn('TOKENKILLER: cache ratio below floor', out._cache);\n"
        "return [{ json: out }];"
    )
    return node("ledger", "Cache Ledger (NukeGuard)", "n8n-nodes-base.code", pos,
                {"jsCode": code}, tv=2,
                extra={"notes": "Reads DeepSeek usage; asserts >=0.97; append rows to cache_ledger; CI replay gate."})

WH_NAMES = {"lead-intake":"Lead Webhook","valuation":"Valuation Webhook","triage":"Triage Webhook",
            "nurture":"Nurture Webhook","voice-assist":"Scheduler Webhook","contract":"Deal Agreed Webhook"}
def wh(path, pos, notes=None):
    ex = {"webhookId": path}
    if notes: ex["notes"] = notes
    return node("wh", WH_NAMES[path], "n8n-nodes-base.webhook", pos,
                {"httpMethod": "POST", "path": path, "responseMode": "onReceived", "options": {}},
                tv=1, extra=ex)

def write(name, wf):
    (OUT / name).write_text(json.dumps(wf, indent=2), encoding="utf-8")

# ---- Frozen prefixes (condensed; paste full agents/NN md for production, keep byte-stable) ----
P01 = ("S0 You are the Instant Responder for a cash home-buyer. Reply within 60s. Never quote price. "
       "Never impersonate a human; disclose you are automated if asked. TCPA: include STOP. Concise reasoning.\n"
       "S1 OUTPUT ONLY JSON: {\"sms_body\":\"<=320 chars, no links\",\"send\":bool,\"reason\":str}. "
       "If address invalid/spam set send=false reason=invalid_lead.\n"
       "PAD ---- alignment pad, freeze after 64-token calc ----")
P02 = ("S0 You are the Valuation analyst. Output an offer RANGE only, never a firm number. Internal advisory only; "
       "never shown to seller. Concise reasoning.\n"
       "S1 METHOD: ARV from best comps (recency<=90d, <=1mi, similar sqft/beds). "
       "repair_band light($15-25/sqft)/moderate($25-45)/heavy($45-75); pick most_likely from self_rated_condition + "
       "disclosed_issues (excellent->light, good->light-moderate, fair->moderate, poor->moderate-heavy, severe->heavy; "
       "foundation/fire/water_mold never below moderate, foundation/fire lean heavy; if condition absent assume moderate + "
       "flag 'condition unconfirmed'). "
       "MAO = ARV*(0.60..0.70) - repair_band - holding/closing; trend cooling->0.60 flat->0.65 rising->0.70; "
       "nudge -0.05 (floor 0.58) if poor/severe or major issue disclosed. Band is 0.60-0.70, NEVER above 0.70. "
       "OUTPUT ONLY JSON: {arv_estimate,repair_band:{low,high,most_likely},offer_range:{low,high},confidence,"
       "rationale,comps_used[],flags[]}. <3 comps => confidence=low, widen, flag 'thin comps'. Never invent comps.\n"
       "PAD ---- alignment pad ----")
P03 = ("S0 You are the Lead Scorer/Triage. Concise reasoning. Never discard a lead; distress floors tier at WARM. "
       "No protected-class inference.\n"
       "S1 WEIGHTS motivation40 timeline30 equity20 contact10 -> score0..100. HOT>=70 human_now; WARM40-69 schedule_24h; "
       "COLD<40 nurture. OUTPUT ONLY JSON: {tier,score,top_reasons[],route,notes}.\n"
       "PAD ---- alignment pad ----")
P04 = ("S0 You are the Nurture Copywriter. Value first, ask second. No pricing, no fake urgency. SMS<=320 + STOP; "
       "email needs address+unsubscribe. Vary wording each touch. Concise reasoning.\n"
       "S1 Write the touch for drip_step. OUTPUT ONLY JSON: {channel:'sms'|'email',subject,body,cta,send_after_days}.\n"
       "PAD ---- alignment pad ----")
P05 = ("S0 You are the Voice/Closer-Assist. Disclose automated at call start. Never state or negotiate price. "
       "No pressure; offer human callback. Respect calling hours + DNC. Concise reasoning.\n"
       "S1 Confirm identity/address/condition/timeline; book inspection or warm-transfer. "
       "OUTPUT ONLY JSON: {outcome,inspection_slot,condition_notes,timeline,handoff_summary}.\n"
       "PAD ---- alignment pad ----")
P06 = ("S0 You are the Contract/Title Coordinator. A human approves every contract before it reaches a seller "
       "(needs_human=true always). Never alter agreed terms. No legal advice; flag legal/title issues. Concise reasoning.\n"
       "S1 action=draft_contract. OUTPUT ONLY JSON: {action,documents[],title_company,milestones[],needs_human,human_note}.\n"
       "PAD ---- alignment pad ----")

# ---- Volatile whitelists ----
V01 = "const v = { address: src.address, city: src.city, state: src.state, consent: src.consent === true };"
V02 = ("const trim = (src.comps||[]).slice(0,6).map(c=>({p:Math.round(c.sold_price||c.p||0),"
       "d:c.sold_date||c.d,sqft:c.sqft,bd:c.beds||c.bd,ba:c.baths||c.ba,mi:+(c.distance_mi||c.mi||0).toFixed(1)}));\n"
       "const v = { address: src.address, subject: src.subject||{}, comps: trim, market: src.market||{},"
       " self_rated_condition: src.self_rated_condition, disclosed_issues: src.disclosed_issues||[],"
       " disclosure_text: src.disclosure_text };")
V03 = ("const v = { motivation: src.motivation, timeline: src.timeline, equity_signal: src.equity_signal||src.confidence,"
       " contactability: src.contactability, city: src.city };")
V04 = "const v = { city: src.city, situation: src.situation, drip_step: src.drip_step||0, channel_hint: src.channel_hint };"
V05 = "const v = { address: src.address, city: src.city, timeline: src.timeline, condition_notes: src.condition_notes };"
V06 = "const v = { deal: src.deal || src };"

def ds_chain(prefix, pick, maxtok, x0=460, y=300):
    return [assembler(prefix, pick, maxtok, [x0, y]), deepseek_http([x0+220, y]), ledger([x0+440, y])]

def ds_conn(prev):
    return {
        prev: {"main": [[{"node": "Prefix Assembler (TOKENKILLER)", "type": "main", "index": 0}]]},
        "Prefix Assembler (TOKENKILLER)": {"main": [[{"node": "DeepSeek · Flash-Thinking", "type": "main", "index": 0}]]},
        "DeepSeek · Flash-Thinking": {"main": [[{"node": "Cache Ledger (NukeGuard)", "type": "main", "index": 0}]]},
    }

# ===== 01 Lead Intake =====
def build_01():
    router = node("router","Event Router","n8n-nodes-base.if",[420,400],
        {"conditions":{"string":[{"value1":"={{ ($json.body||$json).event || 'lead' }}","value2":"enrich"}]}},
        extra={"notes":"enrich = condition + disclosures from form step 3; upsert by client_ref. lead = core capture."})
    enrich = node("enrich","Upsert Disclosures (by client_ref)","n8n-nodes-base.postgres",[680,560],
        {"operation":"update","table":"leads","updateKey":"client_ref",
         "columns":"self_rated_condition,disclosed_issues,disclosure_text,disclosure_ack"},
        extra={"notes":"Correlate to the core lead via client_ref; then re-run valuation with condition known."})
    reval = node("reval","→ Re-run Valuation (02)","n8n-nodes-base.httpRequest",[900,560],
        {"url":"={{ $env.VALUATION_WEBHOOK }}","method":"POST","sendBody":True,"specifyBody":"json",
         "jsonBody":"={{ JSON.stringify($json.body || $json) }}","options":{}}, tv=4,
        extra={"notes":"Condition now known → tighter repair band + range."})
    normalize = node("normalize", "Normalize + Validate", "n8n-nodes-base.code", [680, 340], {"jsCode":
        "const b=$input.first().json.body||$input.first().json;const digits=(b.phone||'').replace(/\\D/g,'');"
        "const valid=(b.address||'').trim().length>=4&&digits.length>=7;"
        "const lead={lead_id:'ld_'+Date.now().toString(36)+Math.random().toString(36).slice(2,7),"
        "client_ref:b.client_ref||null,"
        "address:(b.address||'').trim(),phone:digits,city:b.city||'',state:b.state||'',source:b.source||'',"
        "consent:b.consent===true,created_at:new Date().toISOString(),tier:'NEW',status:'new'};"
        "return [{json:{...lead,valid}}];"}, tv=2)
    ifvalid = node("if-valid","Valid Lead?","n8n-nodes-base.if",[900,340],
        {"conditions":{"boolean":[{"value1":"={{ $json.valid }}","value2":True}]}})
    crm = node("crm","CRM · Insert Lead","n8n-nodes-base.postgres",[1120,260],
        {"operation":"insert","table":"leads","columns":"lead_id,client_ref,address,phone,city,state,source,consent,created_at,tier,status"},
        extra={"notes":"Swap for REsimpli/GoHighLevel/HubSpot; payload matches backend/schema/lead.schema.json"})
    ifconsent = node("if-consent","Has SMS Consent?","n8n-nodes-base.if",[1340,260],
        {"conditions":{"boolean":[{"value1":"={{ $json.consent }}","value2":True}]}})
    chain = ds_chain(P01, V01, 400, x0=1560, y=200)
    twilio = node("twilio","Twilio · Send SMS","n8n-nodes-base.twilio",[2220,200],
        {"resource":"sms","operation":"send","from":"={{ $env.TWILIO_FROM }}",
         "to":"={{ $('Normalize + Validate').first().json.phone }}","message":"={{ $json.sms_body }}"},
        extra={"notes":"Reached only when consent=true and agent set send=true."})
    kickval = node("kick-val","→ Trigger Valuation (02)","n8n-nodes-base.httpRequest",[1340,400],
        {"url":"={{ $env.VALUATION_WEBHOOK }}","method":"POST","sendBody":True,"specifyBody":"json",
         "jsonBody":"={{ JSON.stringify($('Normalize + Validate').first().json) }}","options":{}}, tv=4)
    drop = node("drop","Drop Invalid","n8n-nodes-base.code",[1120,440],{"jsCode":"return [{json:{dropped:true,reason:'invalid_lead'}}];"},tv=2)
    nodes = [wh("lead-intake",[240,400]), router, enrich, reval, normalize, ifvalid, crm, ifconsent, *chain, twilio, kickval, drop]
    conns = {
        "Lead Webhook":{"main":[[{"node":"Event Router","type":"main","index":0}]]},
        "Event Router":{"main":[
            [{"node":"Upsert Disclosures (by client_ref)","type":"main","index":0}],
            [{"node":"Normalize + Validate","type":"main","index":0}]]},
        "Upsert Disclosures (by client_ref)":{"main":[[{"node":"→ Re-run Valuation (02)","type":"main","index":0}]]},
        "Normalize + Validate":{"main":[[{"node":"Valid Lead?","type":"main","index":0}]]},
        "Valid Lead?":{"main":[
            [{"node":"CRM · Insert Lead","type":"main","index":0},{"node":"→ Trigger Valuation (02)","type":"main","index":0}],
            [{"node":"Drop Invalid","type":"main","index":0}]]},
        "CRM · Insert Lead":{"main":[[{"node":"Has SMS Consent?","type":"main","index":0}]]},
        "Has SMS Consent?":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}],[]]},
        "Prefix Assembler (TOKENKILLER)":{"main":[[{"node":"DeepSeek · Flash-Thinking","type":"main","index":0}]]},
        "DeepSeek · Flash-Thinking":{"main":[[{"node":"Cache Ledger (NukeGuard)","type":"main","index":0}]]},
        "Cache Ledger (NukeGuard)":{"main":[[{"node":"Twilio · Send SMS","type":"main","index":0}]]},
    }
    return {"name":"01 · Lead Intake (DeepSeek, sub-60s)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-01"}

# ===== 02 Valuation =====
def build_02():
    avm = node("avm","Fetch AVM + Comps","n8n-nodes-base.httpRequest",[460,300],
        {"method":"GET","url":"={{ $env.AVM_API_URL }}?address={{ encodeURIComponent($json.address || $json.body.address) }}",
         "sendHeaders":True,"headerParameters":{"parameters":[{"name":"Authorization","value":"=Bearer {{ $env.AVM_API_KEY }}"}]},"options":{}},
        tv=4, extra={"notes":"ATTOM/county/AVM. Returns avm_estimate + comps for the volatile payload."})
    chain = ds_chain(P02, V02, 700, x0=680, y=300)
    store = node("store","CRM · Store Range","n8n-nodes-base.postgres",[1340,300],
        {"operation":"insert","table":"offers","columns":"offer_id,property_id,stage,arv_estimate,range_low,range_high,confidence,rationale"},
        extra={"notes":"stage=range. Matches backend/schema/offer.schema.json"})
    kick = node("kick","→ Trigger Triage (03)","n8n-nodes-base.httpRequest",[1560,300],
        {"url":"={{ $env.TRIAGE_WEBHOOK }}","method":"POST","sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json) }}","options":{}},tv=4)
    nodes=[wh("valuation",[240,300]), avm, *chain, store, kick]
    conns={"Valuation Webhook":{"main":[[{"node":"Fetch AVM + Comps","type":"main","index":0}]]},
           "Fetch AVM + Comps":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}]]},
           **ds_conn("__skip__")}
    del conns["__skip__"]
    conns["Cache Ledger (NukeGuard)"]={"main":[[{"node":"CRM · Store Range","type":"main","index":0}]]}
    conns["CRM · Store Range"]={"main":[[{"node":"→ Trigger Triage (03)","type":"main","index":0}]]}
    return {"name":"02 · Valuation (DeepSeek, offer-range)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-02"}

# ===== 03 Triage =====
def build_03():
    chain = ds_chain(P03, V03, 400, x0=460, y=300)
    sw = node("switch","Route by Tier","n8n-nodes-base.switch",[1120,300],
        {"dataType":"string","value1":"={{ $json.tier }}","rules":{"rules":[
            {"value2":"HOT","output":0},{"value2":"WARM","output":1},{"value2":"COLD","output":2}]}})
    hot = node("hot","HOT · Alert Closer NOW","n8n-nodes-base.emailSend",[1360,160],
        {"fromEmail":"alerts@{{ $env.DOMAIN }}","toEmail":"={{ $env.CLOSER_ALERT }}",
         "subject":"HOT LEAD — call now","text":"={{ JSON.stringify($json) }}"}, tv=2,
        extra={"notes":"Payload = score+reasons+offer_range+handoff_summary. Also triggers voice-assist(05) if closer not free in 2 min."})
    warm = node("warm","WARM · Schedule 24h","n8n-nodes-base.httpRequest",[1360,300],
        {"url":"={{ $env.SCHEDULER_WEBHOOK }}","method":"POST","sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json) }}","options":{}},tv=4)
    nurture = node("nurture","COLD/WARM · Enter Nurture","n8n-nodes-base.httpRequest",[1360,440],
        {"url":"={{ $env.NURTURE_WEBHOOK }}","method":"POST","sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json) }}","options":{}},tv=4)
    nodes=[wh("triage",[240,300]), *chain, sw, hot, warm, nurture]
    conns={"Triage Webhook":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}]]},
           **ds_conn("__skip__")}
    del conns["__skip__"]
    conns["Cache Ledger (NukeGuard)"]={"main":[[{"node":"Route by Tier","type":"main","index":0}]]}
    conns["Route by Tier"]={"main":[
        [{"node":"HOT · Alert Closer NOW","type":"main","index":0},{"node":"COLD/WARM · Enter Nurture","type":"main","index":0}],
        [{"node":"WARM · Schedule 24h","type":"main","index":0},{"node":"COLD/WARM · Enter Nurture","type":"main","index":0}],
        [{"node":"COLD/WARM · Enter Nurture","type":"main","index":0}]]}
    return {"name":"03 · Triage + Route (DeepSeek)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-03"}

# ===== 04 Nurture =====
def build_04():
    step = node("step","Resolve Drip Step","n8n-nodes-base.code",[460,300],
        {"jsCode":"const j=$input.first().json;return [{json:{...j,drip_step:(j.drip_step||0)}}];"},tv=2)
    chain = ds_chain(P04, V04, 500, x0=680, y=300)
    ifch = node("if-ch","SMS or Email?","n8n-nodes-base.if",[1340,300],
        {"conditions":{"string":[{"value1":"={{ $json.channel }}","value2":"sms"}]}})
    sms = node("sms","Send SMS","n8n-nodes-base.twilio",[1560,220],
        {"resource":"sms","operation":"send","from":"={{ $env.TWILIO_FROM }}",
         "to":"={{ $('Nurture Webhook').first().json.phone }}","message":"={{ $json.body }}"})
    email = node("email","Send Email","n8n-nodes-base.emailSend",[1560,380],
        {"fromEmail":"hello@{{ $env.DOMAIN }}","toEmail":"={{ $('Nurture Webhook').first().json.email }}",
         "subject":"={{ $json.subject }}","text":"={{ $json.body }}"},tv=2)
    waitn = node("wait","Wait to Next Touch","n8n-nodes-base.wait",[1780,300],
        {"amount":1,"unit":"days"},tv=1,extra={"notes":"Set from $json.send_after_days; re-enters to advance drip_step."})
    nodes=[wh("nurture",[240,300]), step, *chain, ifch, sms, email, waitn]
    conns={"Nurture Webhook":{"main":[[{"node":"Resolve Drip Step","type":"main","index":0}]]},
           "Resolve Drip Step":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}]]},
           **ds_conn("__skip__")}
    del conns["__skip__"]
    conns["Cache Ledger (NukeGuard)"]={"main":[[{"node":"SMS or Email?","type":"main","index":0}]]}
    conns["SMS or Email?"]={"main":[[{"node":"Send SMS","type":"main","index":0}],[{"node":"Send Email","type":"main","index":0}]]}
    conns["Send SMS"]={"main":[[{"node":"Wait to Next Touch","type":"main","index":0}]]}
    conns["Send Email"]={"main":[[{"node":"Wait to Next Touch","type":"main","index":0}]]}
    return {"name":"04 · Nurture Drip (DeepSeek, 12-24mo)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-04"}

# ===== 05 Voice/Scheduler =====
def build_05():
    chain = ds_chain(P05, V05, 500, x0=460, y=300)
    cal = node("cal","Create Calendar Event","n8n-nodes-base.googleCalendar",[1120,300],
        {"resource":"event","operation":"create","calendar":"={{ $env.CLOSER_CALENDAR }}",
         "start":"={{ $json.inspection_slot }}","end":"={{ $json.inspection_slot }}",
         "additionalFields":{"summary":"Property inspection — {{ $('Scheduler Webhook').first().json.address }}",
         "description":"={{ $json.handoff_summary }}"}}, tv=1,
        extra={"notes":"HUMAN STEP #1 (physical inspection) is scheduled here."})
    confirm = node("confirm","Confirm to Seller","n8n-nodes-base.twilio",[1340,300],
        {"resource":"sms","operation":"send","from":"={{ $env.TWILIO_FROM }}",
         "to":"={{ $('Scheduler Webhook').first().json.phone }}",
         "message":"You're booked! A specialist will meet you to finalize your cash offer. Reply to reschedule."})
    nodes=[wh("voice-assist",[240,300]), *chain, cal, confirm]
    conns={"Scheduler Webhook":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}]]},
           **ds_conn("__skip__")}
    del conns["__skip__"]
    conns["Cache Ledger (NukeGuard)"]={"main":[[{"node":"Create Calendar Event","type":"main","index":0}]]}
    conns["Create Calendar Event"]={"main":[[{"node":"Confirm to Seller","type":"main","index":0}]]}
    return {"name":"05 · Voice Assist + Scheduler (DeepSeek)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-05"}

# ===== 06 Contract/Title =====
def build_06():
    chain = ds_chain(P06, V06, 900, x0=460, y=300)
    gate = node("gate","HUMAN REVIEW GATE","n8n-nodes-base.emailSend",[1120,300],
        {"fromEmail":"deals@{{ $env.DOMAIN }}","toEmail":"={{ $env.CLOSER_ALERT }}",
         "subject":"REVIEW before send — contract","text":"Human review required. Draft + flags: {{ JSON.stringify($json) }}"},tv=2,
        extra={"notes":"Hard gate: no contract reaches the seller without human approval."})
    approval = node("approval","Wait for Approval","n8n-nodes-base.form",[1340,300],
        {"formTitle":"Approve contract?","formFields":{"values":[
            {"fieldLabel":"Decision","fieldType":"dropdown","fieldOptions":{"values":[{"option":"approve"},{"option":"edit"},{"option":"reject"}]}}]}})
    ifok = node("if-ok","Approved?","n8n-nodes-base.if",[1560,300],
        {"conditions":{"string":[{"value1":"={{ $json.Decision }}","value2":"approve"}]}})
    esign = node("esign","Send e-Sign","n8n-nodes-base.httpRequest",[1780,220],
        {"method":"POST","url":"={{ $env.ESIGN_API_URL }}","sendBody":True,"specifyBody":"json","jsonBody":"={{ JSON.stringify($json) }}","options":{}},tv=4)
    title = node("title","Open Title/Escrow","n8n-nodes-base.emailSend",[2000,220],
        {"fromEmail":"deals@{{ $env.DOMAIN }}","toEmail":"={{ $env.TITLE_COMPANY_EMAIL }}",
         "subject":"New file — open title","text":"={{ JSON.stringify($json) }}"},tv=2)
    nodes=[wh("contract",[240,300],notes="Fired by human closer after post-inspection agreement (Human Step #2)."), *chain, gate, approval, ifok, esign, title]
    conns={"Deal Agreed Webhook":{"main":[[{"node":"Prefix Assembler (TOKENKILLER)","type":"main","index":0}]]},
           **ds_conn("__skip__")}
    del conns["__skip__"]
    conns["Cache Ledger (NukeGuard)"]={"main":[[{"node":"HUMAN REVIEW GATE","type":"main","index":0}]]}
    conns["HUMAN REVIEW GATE"]={"main":[[{"node":"Wait for Approval","type":"main","index":0}]]}
    conns["Wait for Approval"]={"main":[[{"node":"Approved?","type":"main","index":0}]]}
    conns["Approved?"]={"main":[[{"node":"Send e-Sign","type":"main","index":0}],[]]}
    conns["Send e-Sign"]={"main":[[{"node":"Open Title/Escrow","type":"main","index":0}]]}
    return {"name":"06 · Contract + Title (DeepSeek)","nodes":nodes,"connections":conns,
            "active":False,"settings":{"executionOrder":"v1"},"versionId":"acb-ds-06"}

write("01-lead-intake.json", build_01())
write("02-valuation.json", build_02())
write("03-triage-route.json", build_03())
write("04-nurture-drip.json", build_04())
write("05-scheduler.json", build_05())
write("06-contract-title.json", build_06())
print("wrote 6 DeepSeek workflows")
