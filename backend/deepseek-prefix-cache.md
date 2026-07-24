# DeepSeek V4 Flash-Thinking — Prefix-Cache Discipline (TOKENKILLER)

All six workflows call DeepSeek's OpenAI-compatible endpoint through one repeated three-node pattern:

```
… → Prefix Assembler (TOKENKILLER) → DeepSeek (HTTP) → Cache Ledger → …
```

DeepSeek Context Caching is automatic and disk-backed: it matches the **longest identical token prefix** of the request, counted in **64-token blocks**, and reports `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` in `usage`. There is no flag to set — the hit rate is entirely a function of how you order and stabilize the request. The target is **hit_tokens / (hit+miss) ≥ 0.97** on every steady-state call.

## Segment ordering (S0→S1→S2→S3)

The `messages` array is built so everything cacheable comes first, byte-identical, and only the volatile lead payload is appended last.

| seg | content | role | volatile? |
|-----|---------|------|-----------|
| **S0** | policy / identity / hard guardrails | system | no — frozen |
| **S1** | task spec + **output-contract JSON** | system | no — frozen |
| **S2** | exemplars (optional; see reasoner note) | system | no — frozen |
| **PAD** | alignment comment padding S0–S2 up to a 64-token boundary | system | no — frozen |
| **S3** | the lead/deal JSON, whitelisted + compact | user | **yes — the only miss** |

S0+S1+S2+PAD are concatenated into a single **constant string literal** inside the assembler node. Because it is a literal — never interpolated with per-lead data — its bytes are identical on every invocation, so DeepSeek matches the entire prefix and only S3 is billed as a miss.

## The five rules that hold the hit rate >97%

1. **Big frozen prefix, tiny volatile suffix.** Agent prompts are 500–1000 tokens; a whitelisted lead payload is 40–150. Ratio is naturally >0.9; the rules below push it past 0.97.
2. **Whitelist + compact S3.** Send only the fields the agent needs, `JSON.stringify` (no pretty-print), stable key order. Every token you don't send is a token that can't miss.
3. **64-token block alignment.** Pad the frozen prefix so its token count is a multiple of 64. Otherwise the final partial block mixes frozen + volatile bytes and won't cache. The `PAD` line exists for this — size it once with a tokenizer, then freeze it.
4. **Identical everything.** Same `model`, same `temperature`, same message roles/order on every call. Any drift in the prefix (a timestamp, a UUID, reordered keys) invalidates the match.
5. **Keep the cache warm.** Cache entries expire after inactivity. Fire a synthetic warm-up call per agent on deploy, and route same-agent leads in sequence so the prefix stays resident under real volume.

## Reasoner note (flash-thinking)

Flash-Thinking returns `reasoning_content` (CoT) **and** `content` (final). Parse `content` only. Reasoning tokens are *output*, so they don't affect the input prefix cache — but they cost output tokens, so keep `max_tokens` bounded and instruct concise reasoning in S0. Reasoner variants can degrade with heavy few-shot; default to **S2 empty** and lean on a crisp S1 contract. The contract still lives in the frozen prefix, so dropping exemplars costs nothing on cache and often helps quality.

## Canonical Prefix Assembler (embedded in every workflow)

```js
// Prefix Assembler (TOKENKILLER) — S0..PAD frozen, S3 volatile appended last.
const PREFIX = FROZEN_PREFIX; // const literal per agent — NEVER interpolate volatile in here
const src = $input.first().json;
const v = pickVolatile(src);                 // whitelist, compact, stable key order
return [{ json: { body: {
  model: $env.DEEPSEEK_MODEL,                 // e.g. deepseek-v4-flash-thinking
  temperature: 0,
  max_tokens: MAXTOK,
  messages: [
    { role: "system", content: PREFIX },      // S0+S1+S2+PAD — cached
    { role: "user",   content: JSON.stringify(v) } // S3 — the only miss
  ]
}, _prefix_bytes: PREFIX.length }}];
```

## Canonical Cache Ledger (append-only telemetry + NukeGuard)

```js
const r = $input.first().json;
const u = r.usage || {};
const hit = u.prompt_cache_hit_tokens || 0, miss = u.prompt_cache_miss_tokens || 0;
const ratio = (hit + miss) ? hit / (hit + miss) : 0;
let t = r.choices?.[0]?.message?.content || '{}';
let out; try { out = JSON.parse(t.replace(/```json|```/g,'').trim()); }
         catch(e){ out = { _parse_error: true }; }
out._cache = { hit, miss, ratio: +ratio.toFixed(4), ok: ratio >= 0.97 };
if (!out._cache.ok) console.warn('TOKENKILLER: cache ratio below floor', out._cache); // NukeGuard: alert, don't abort prod
return [{ json: out }];
```

Ship the ledger rows to a `cache_ledger` table and add a **CI replay gate**: replay a fixed lead corpus in staging, assert mean ratio ≥ 0.97, fail the build if a prompt edit broke alignment. Any change to a `FROZEN_PREFIX` must re-run the 64-token pad calc.

## Per-agent volatile whitelist (S3)

| workflow | agent | S3 fields | max_tokens | cache note |
|---|---|---|---|---|
| 01 | Instant Responder | address, city, state, consent | 400 | trivially >0.98 |
| 02 | Valuation | address, subject{}, comps[≤6 compact], market{} | 700 | **hardest** — comps are volatile; trim to top-6, round, drop unused keys |
| 03 | Lead Scorer | motivation, timeline, equity_signal, contactability, city | 400 | >0.98 |
| 04 | Nurture | city, situation, drip_step, channel_hint | 500 | >0.98 |
| 05 | Voice Assist | address, city, timeline, condition_notes | 500 | >0.98 |
| 06 | Contract/Title | deal{} (agreed price, dates, parties) | 900 | human-gated; volatile larger but off the hot path |

Agent 02 is the only one where the volatile payload is inherently large. Keep it >0.97 by (a) trimming to the 6 best comps, (b) compacting keys (`{p,d,sqft,bd,ba,mi}`), (c) rounding prices, and (d) keeping the full method/guardrails in the frozen prefix so the stable side stays heavy.
