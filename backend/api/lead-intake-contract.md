# Lead Intake — Webhook Contract

The landing pages POST here on form submit. This is the single entry point to the whole agentic pipeline. Point `lead_webhook` in `site/data/_brand.json` at this URL and rebuild.

## Endpoint
```
POST https://YOUR-N8N-HOST/webhook/lead-intake
Content-Type: application/json
```

The page fires **two** POSTs to the same endpoint, correlated by `client_ref`:

### Event 1 — `lead` (core capture, fires on the phone step)
```json
{
  "client_ref": "cr_lz3k9a...",
  "event": "lead",
  "address": "123 Main St, Phoenix, AZ",
  "phone": "6025551234",
  "city": "Phoenix",
  "state": "AZ",
  "source": "arizona/phoenix",
  "consent": true,
  "ts": "2026-01-15T18:22:04.000Z",
  "page": "https://homeofferbridge.com/arizona/phoenix/"
}
```

### Event 2 — `enrich` (condition + disclosures, fires on the final step)
```json
{
  "client_ref": "cr_lz3k9a...",
  "event": "enrich",
  "city": "Phoenix", "state": "AZ", "source": "arizona/phoenix",
  "self_rated_condition": "fair",
  "disclosed_issues": ["roof", "hvac"],
  "disclosure_text": "Roof ~20 yrs, leaks in back bedroom; AC intermittent.",
  "disclosure_ack": true,
  "ts": "2026-01-15T18:22:41.000Z"
}
```

| field | event | required | notes |
|---|---|---|---|
| client_ref | both | yes | correlation id; server upserts `enrich` onto the `lead` row |
| event | both | yes | `lead` or `enrich`; routed by the Event Router node |
| address | lead | yes | raw seller input; normalized server-side |
| phone | lead | yes | digits extracted server-side; <7 digits = invalid |
| city / state | both | yes | from the page that submitted |
| source | both | yes | `state-slug/city-slug` — per-metro attribution key |
| consent | lead | yes | TCPA. If false, no SMS is sent; email/manual only |
| self_rated_condition | enrich | yes* | one of excellent/good/fair/poor/severe (*required within step 3; core lead already saved) |
| disclosed_issues | enrich | no | multi-select of known issue types |
| disclosure_text | enrich | no | free-text repairs/damage |
| disclosure_ack | enrich | yes* | seller accuracy acknowledgement checkbox |
| ts / page | both | no | audit + attribution |

**Why two events:** the core lead is captured the instant the phone step submits (speed-to-lead is the whole thesis), so nothing is lost if the seller abandons the disclosure step. When `enrich` arrives, the server upserts it onto the lead by `client_ref` and **re-runs valuation** — now with condition known, the repair band and offer range tighten.

## Response
`200` immediately (`responseMode: onReceived`) — the page shows its success state without waiting on downstream agents. All processing is async.

## What happens next (async)
1. **Normalize + validate** → assign `lead_id`, extract phone digits.
2. **Valid?** invalid/spam → logged + dropped. Valid → two parallel branches:
   - CRM insert → consent check → **Agent 01** drafts SMS → Twilio sends (sub-60s).
   - Trigger **Valuation (02)** → **Triage (03)** → HOT/WARM/COLD routing.

## Pipeline map
```
lead-intake ─┬─ CRM insert ─ consent? ─ Agent01 SMS ─ Twilio
             └─ /valuation (02) ─ AVM+comps ─ Agent02 range ─ /triage (03)
                                                                  ├─ HOT  → alert closer NOW  ── Human Step #2
                                                                  ├─ WARM → /scheduler (05) ── Human Step #1 (inspection)
                                                                  └─ COLD → /nurture (04)
              (after agreement) → /contract (06) ─ Agent06 draft ─ HUMAN GATE ─ e-sign ─ title
```

## Anti-abuse
- Add a Cloudflare Turnstile token to the form and verify it in the Normalize node before insert.
- Rate-limit by IP at the Cloudflare layer.
- Honeypot field (hidden input) — if filled, drop as bot.
