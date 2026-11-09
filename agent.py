import os, re, time, pathlib
from typing import TypedDict, Optional, List
from collections import Counter
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import db

BASE  = pathlib.Path(__file__).parent
SKILL = (BASE / "skills/brief_to_plan/SKILL.md").read_text()

REGIONS = ["AU", "NL", "IN", "US"]
FMTS    = ["rewarded_video", "playable", "banner", "native"]
GENRES  = ["puzzle", "word", "racing", "casual", "trivia"]
MIN_ATT = 5.0   # quality gate: at least one line item should have ≥ this many attention-seconds

# Colloquial region aliases & regex patterns → canonical codes
REGION_PATTERNS = [
    (r'\b(?:netherlands|dutch|holland|benelux|\bnl\b)', 'NL'),
    (r'\b(?:australia|oz|ozzie|\bau\b)', 'AU'),
    (r'\b(?:india)\b', 'IN'),
    (r'\b(?:the us|usa|united states|america|\bus\b)', 'US')
]

COUNTRY_NAME_TO_CODE = {
    "netherlands": "NL", "dutch": "NL", "holland": "NL", "benelux": "NL", "nl": "NL",
    "australia": "AU", "oz": "AU", "ozzie": "AU", "au": "AU",
    "india": "IN", "in": "IN",
    "the us": "US", "usa": "US", "united states": "US", "america": "US", "us": "US"
}

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class Spec(BaseModel):
    advertiser:   str                     = Field(default="unknown", description="brand name, or 'unknown'")
    objective:    str                     = Field(default="", description="one short line")
    regions:      Optional[List[str]]     = Field(default=None, description="codes from AU, NL, IN, US")
    budget_usd:   Optional[float]         = Field(default=None, description="numeric USD budget, null if not stated")
    flight_days:  Optional[int]           = Field(default=None, description="numeric days, null if not stated")
    formats_pref: Optional[List[str]]     = Field(default=None, description="from rewarded_video, playable, banner, native")
    genre_pref:   Optional[List[str]]     = Field(default=None, description="from puzzle, word, racing, casual, trivia")
    missing:      Optional[List[str]]     = Field(default=None, description="fields the brief did not state")

class Item(BaseModel):
    inv_id:     str   = Field(description="id copied exactly from the candidate list")
    budget_usd: float
    why:        str

class Plan(BaseModel):
    items:     List[Item]
    rationale: str

# ── Model factory ─────────────────────────────────────────────────────────────

def mode():
    return "live" if (os.getenv("GROQ_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "offline"

def chain(schema):
    """Build a structured-output chain with 3-tier fallback: Groq primary → Groq fallback → Gemini."""
    ms = []
    try:
        if os.getenv("GROQ_API_KEY"):
            from langchain_groq import ChatGroq
            # Primary Groq model
            ms.append(
                ChatGroq(
                    model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                    temperature=0,
                ).with_structured_output(schema)
            )
            # Secondary Groq model (in case primary is rate-limited or retired)
            fallback_model = os.getenv("GROQ_MODEL_FALLBACK", "openai/gpt-oss-20b")
            if fallback_model != os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"):
                ms.append(
                    ChatGroq(
                        model=fallback_model,
                        temperature=0,
                    ).with_structured_output(schema)
                )
        if os.getenv("GOOGLE_API_KEY"):
            from langchain_google_genai import ChatGoogleGenerativeAI
            ms.append(
                ChatGoogleGenerativeAI(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                    temperature=0,
                ).with_structured_output(schema)
            )
    except ImportError:
        pass
    if not ms:
        return None
    return ms[0].with_fallbacks(ms[1:]) if len(ms) > 1 else ms[0]

def _make_chain_raw(schema):
    """Same as chain() but with include_raw=True to detect when model ignores the tool call."""
    ms = []
    try:
        if os.getenv("GROQ_API_KEY"):
            from langchain_groq import ChatGroq
            primary = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            ms.append(ChatGroq(model=primary, temperature=0).with_structured_output(schema, include_raw=True))
            fb = os.getenv("GROQ_MODEL_FALLBACK", "openai/gpt-oss-20b")
            if fb != primary:
                ms.append(ChatGroq(model=fb, temperature=0).with_structured_output(schema, include_raw=True))
        if os.getenv("GOOGLE_API_KEY"):
            from langchain_google_genai import ChatGoogleGenerativeAI
            ms.append(ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), temperature=0
            ).with_structured_output(schema, include_raw=True))
    except ImportError:
        pass
    if not ms:
        return None
    return ms[0].with_fallbacks(ms[1:]) if len(ms) > 1 else ms[0]

def invoke_safe(schema, prompt, offline_fn, *offline_args):
    """
    Call the LLM with structured output.  If parsing fails (model returned prose
    instead of filling the tool call) fall back to the offline stand-in function.
    Returns a plain dict.
    """
    L = _make_chain_raw(schema)
    if L is None:                               # no API key → offline
        return offline_fn(*offline_args)
    try:
        raw = L.invoke(prompt)
        parsed = raw.get("parsed") if isinstance(raw, dict) else None
        if parsed is None or raw.get("parsing_error"):
            return offline_fn(*offline_args)   # model ignored tool call
        return parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
    except Exception:
        return offline_fn(*offline_args)       # any network/parse error → offline



def mock_extract(b):
    t = b.lower()

    # Budget: "$12,000", "$30k", "5000 usd", "five thousand dollars"
    word_nums = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
                 "seven":7,"eight":8,"nine":9,"ten":10,"fifteen":15,
                 "twenty":20,"thirty":30,"fifty":50,"hundred":100}
    bud = None
    m = re.search(r"\$\s?([\d,.]+)\s?(k)?|([,\d]+)\s?(k)?\s?(?:usd|dollars?)", t)
    if m:
        try:
            num = (m.group(1) or m.group(3)).replace(",", "").rstrip(".")
            bud = float(num) * (1000 if (m.group(2) or m.group(4)) else 1)
        except ValueError:
            bud = None
    if bud is None:
        for word, val in word_nums.items():
            wm = re.search(rf"\b{word}\s+(?:thousand|k)\b", t)
            if wm:
                bud = float(val * 1000)
                break

    # Flight duration: "14 days", "3 weeks", "7-day"
    d = re.search(r"(\d+)\s*[-]?\s*(day|week)", t)
    days = int(d.group(1)) * (7 if d.group(2) == "week" else 1) if d else None

    # Regions: canonical + aliases via boundary regex
    regs = []
    if "all regions" in t:
        regs = ["AU", "NL", "IN", "US"]
    else:
        for pat, code in REGION_PATTERNS:
            if re.search(pat, t) and code not in regs:
                regs.append(code)

    # Formats
    fm = {"playable": "playable", "rewarded": "rewarded_video", "banner": "banner", "native": "native"}
    fp = [v for k, v in fm.items() if k in t]

    # Genres
    gp = [g for g in GENRES if g in t]

    # Advertiser: grab the first capitalised proper noun before action verbs
    adv = "unknown"
    am = re.search(
        r"(?:hi[^,\n]*,\s*)?([A-Z][A-Za-z0-9 &']{1,30}?)(?:\s+(?:wants|is|was|will|has|are|needs|would|campaign|—|-))",
        b
    )
    if am:
        candidate = am.group(1).strip()
        # Reject generic openers
        if candidate.lower() not in ("hi team", "hi", "hello", "dear", "fwd", "re"):
            adv = candidate

    return {
        "advertiser": adv, "objective": "see brief",
        "regions": regs, "budget_usd": bud, "flight_days": days,
        "formats_pref": fp, "genre_pref": gp, "missing": [],
    }

def mock_plan(cands, budget, days, errors=None):
    # Ensure at least one line item has attention >= 5s (in-game format) to satisfy quality gate
    high_att = [c for c in cands if c.get("attention", 0) >= 5.0]
    other    = [c for c in cands if c not in high_att]
    selected = (high_att[:2] + other[:2])[:4]
    if not selected:
        selected = cands[:3]

    items = []
    remaining_budget = budget
    shares = [.45, .30, .15, .10] if len(selected) >= 4 else [.5, .3, .2] if len(selected) >= 3 else [.6, .4] if len(selected) == 2 else [1.0]
    
    for share, r in zip(shares, selected):
        if remaining_budget <= 0:
            break
        cap = r["daily_impr"] * (days or 1) * r["cpm"] / 1000
        spend_target = min(budget * share, cap, remaining_budget)
        min_spend = r.get("min_bid", 0) * (spend_target / r["cpm"] * 1000) / 1000 if r["cpm"] else 0
        allocated = round(max(spend_target, min_spend), 2)
        if allocated > remaining_budget:
            allocated = round(remaining_budget, 2)
        remaining_budget -= allocated
        att_per_dollar = round(r["attention"] / r["cpm"] * 1000, 1) if r["cpm"] else 0
        items.append({
            "inv_id": r["id"],
            "budget_usd": allocated,
            "why": f"{r['fmt'].replace('_',' ')} · {r['genre']} · {r['region']} · "
                   f"{r['attention']}s attention · {att_per_dollar} att-sec/$1k",
        })

    # Self-healing residual reallocation
    if remaining_budget > 1.0 and items:
        for item in items:
            r = next((c for c in selected if c["id"] == item["inv_id"]), None)
            if r:
                cap = r["daily_impr"] * (days or 1) * r["cpm"] / 1000
                spare = cap - item["budget_usd"]
                if spare > 1.0:
                    add = min(spare, remaining_budget)
                    item["budget_usd"] = round(item["budget_usd"] + add, 2)
                    remaining_budget -= add
                    if remaining_budget <= 1.0:
                        break

    return {"items": items, "rationale": "Plan: best attention per dollar, with rewarded/playable prioritized and supply-safe pacing."}

# ── Graph state ───────────────────────────────────────────────────────────────

class S(TypedDict, total=False):
    brief: str
    spec: dict
    cands: list
    plan: dict
    rows: list
    totals: dict
    checks: list
    errors: list
    attempts: int
    trace: list
    result: dict

def tr(s, name, t0, note):
    return s.get("trace", []) + [{"step": name, "ms": int((time.time() - t0) * 1000), "note": note}]

# ── Graph nodes ───────────────────────────────────────────────────────────────

def extract(s):
    t0     = time.time()
    prompt = (
        f"{SKILL}\n\nTASK: extract the campaign spec. "
        "Never guess missing values. "
        "Map region names strictly to codes: AU, NL, IN, US (e.g. Benelux/Netherlands→NL, Oz/Australia→AU, India→IN, USA/US→US). "
        "Extract total budget in USD as a number (e.g. $12,000 -> 12000). If no budget stated, return null. "
        "Extract flight length in days as an integer (e.g. 2 weeks -> 14). "
        "Detect game genre preferences from: puzzle, word, racing, casual, trivia.\n\n"
        f"BRIEF:\n{s['brief']}"
    )
    raw = invoke_safe(Spec, prompt, mock_extract, s["brief"])

    # Fallback/normalization guardrail: normalize country names if model returned names instead of codes
    normalized_regs = []
    for r in (raw.get("regions") or []):
        code = COUNTRY_NAME_TO_CODE.get(r.strip().lower(), r.strip().upper())
        if code in REGIONS and code not in normalized_regs:
            normalized_regs.append(code)
    
    # Deterministic fallback check: if LLM didn't extract fields, check mock_extract
    det = mock_extract(s["brief"])
    if not normalized_regs:
        normalized_regs = det["regions"]
    if raw.get("budget_usd") is None and det["budget_usd"] is not None:
        raw["budget_usd"] = det["budget_usd"]
    if raw.get("flight_days") is None and det["flight_days"] is not None:
        raw["flight_days"] = det["flight_days"]
    if not raw.get("formats_pref") and det["formats_pref"]:
        raw["formats_pref"] = det["formats_pref"]
    if not raw.get("genre_pref") and det["genre_pref"]:
        raw["genre_pref"] = det["genre_pref"]

    raw["regions"]      = [r for r in normalized_regs if r in REGIONS]
    raw["formats_pref"] = [f for f in (raw.get("formats_pref") or []) if f in FMTS]
    raw["genre_pref"]   = [g for g in (raw.get("genre_pref") or []) if g in GENRES]

    # Recompute missing in code — never trust the model's self-assessment
    raw["missing"] = [k for k in ("budget_usd", "flight_days", "regions") if not raw.get(k)]

    return {
        "spec": raw,
        "attempts": 0,
        "trace": tr(s, "Extract", t0, f"{len(raw['missing'])} field(s) missing"),
    }

def retrieve(s):
    t0 = time.time()
    sp = s["spec"]
    cands = db.search(
        sp["regions"] or REGIONS,
        sp.get("formats_pref") or None,
        sp.get("genre_pref") or None,
    )[:12]
    return {"cands": cands, "trace": tr(s, "Retrieve", t0, f"{len(cands)} candidates from inventory")}

def plan(s):
    t0 = time.time()
    sp = s["spec"]
    n  = s.get("attempts", 0) + 1

    if not sp.get("budget_usd") or not s.get("cands"):
        return {
            "plan": {"items": [], "rationale": "Not enough information to plan. A human should ask the advertiser."},
            "attempts": n,
            "trace": tr(s, "Plan", t0, "skipped — needs a human"),
        }

    table = "\n".join(
        f"{c['id']} | {c['genre']} | {c['region']} | {c['fmt']} | "
        f"placement:{c['placement']} | cpm:{c['cpm']} | attention:{c['attention']}s | "
        f"daily_impr:{c['daily_impr']} | min_bid:{c['min_bid']}"
        for c in s["cands"]
    )
    fb = ("\nYOUR LAST ATTEMPT HAD THESE PROBLEMS — FIX THEM: " + "; ".join(s["errors"])) \
         if s.get("errors") else ""
    prompt = (
        f"{SKILL}\n\n"
        f"TASK: split the budget across 2–4 candidates from the list below. "
        f"Budget: {sp['budget_usd']} USD total over {sp['flight_days']} days. "
        f"Use ONLY ids from this list. Never repeat an id. "
        f"Each item's effective CPM must be >= its min_bid. "
        f"Return the plan using the tool/function provided.\n\n"
        f"INVENTORY:\n{table}{fb}"
    )
    p = invoke_safe(Plan, prompt, mock_plan, s["cands"], sp["budget_usd"], sp["flight_days"])

    return {"plan": p, "attempts": n, "trace": tr(s, "Plan", t0, f"attempt {n}, {len(p['items'])} line items")}

def verify(s):
    t0  = time.time()
    sp  = s["spec"]
    errs = []
    rows = []
    spend = impr = att = 0.0

    # --- duplicate id check (must run before per-row loop) ---
    id_counts = Counter(it["inv_id"] for it in s["plan"]["items"])
    for inv_id, count in id_counts.items():
        if count > 1:
            errs.append(f"{inv_id} appears {count} times — combine into one line item")

    seen_ids = set()
    for it in s["plan"]["items"]:
        if it["inv_id"] in seen_ids:
            continue               # already counted above, skip to avoid double-penalising
        seen_ids.add(it["inv_id"])

        r = db.get(it["inv_id"])
        if not r:
            errs.append(f"{it['inv_id']} does not exist in inventory")
            continue

        n_impr = it["budget_usd"] / r["cpm"] * 1000
        cap    = r["daily_impr"] * (sp.get("flight_days") or 1)

        if n_impr > cap:
            errs.append(f"{r['id']} needs {int(n_impr):,} impressions but only {int(cap):,} available")
        if sp.get("regions") and r["region"] not in sp["regions"]:
            errs.append(f"{r['id']} is in {r['region']}, outside brief regions {sp['regions']}")
        # floor CPM guard: effective CPM must not fall below the inventory's min_bid
        effective_cpm = it["budget_usd"] / n_impr * 1000 if n_impr else 0
        if effective_cpm < r.get("min_bid", 0):
            errs.append(f"{r['id']} effective CPM ${effective_cpm:.2f} is below floor ${r['min_bid']:.2f}")

        spend += it["budget_usd"]
        impr  += n_impr
        att   += n_impr * r["attention"]

        att_per_dollar = round(r["attention"] / r["cpm"] * 1000, 1) if r["cpm"] else 0
        rows.append({
            **r,
            "spend": round(it["budget_usd"], 2),
            "impr":  int(n_impr),
            "why":   it["why"],
            "att_per_dollar": att_per_dollar,
        })

    if sp.get("budget_usd") and spend > sp["budget_usd"] * 1.001:
        errs.append(f"total spend ${spend:,.0f} is over budget ${sp['budget_usd']:,.0f}")

    # attention quality gate: at least one line item should have high attention
    if rows and all(r["attention"] < MIN_ATT for r in rows):
        errs.append(
            f"all line items have attention < {MIN_ATT}s — prefer rewarded_video or playable for quality"
        )

    bad = lambda k: any(k in e for e in errs)
    checks = [
        {"name": "Inventory ids are real",            "ok": not bad("does not exist")},
        {"name": "No duplicate ids in plan",          "ok": not bad("appears")},
        {"name": "Impressions fit available supply",  "ok": not bad("available")},
        {"name": "Regions match the brief",           "ok": not bad("outside brief")},
        {"name": "Spend within budget",               "ok": not bad("over budget")},
        {"name": "CPM above floor price",             "ok": not bad("below floor")},
        {"name": "Attention quality ≥ 5 s on ≥1 line","ok": not bad(f"attention < {MIN_ATT}s")},
        {"name": "Brief had everything needed",       "ok": not sp.get("missing")},
    ]
    # Attention economy telemetry & format breakdown
    in_game_spend     = sum(r["spend"] for r in rows if r.get("placement") == "in-game")
    around_game_spend = sum(r["spend"] for r in rows if r.get("placement") == "around-game")
    away_game_spend   = sum(r["spend"] for r in rows if r.get("placement") == "away-from-game")
    
    in_game_pct     = round(in_game_spend / spend * 100, 1) if spend else 0
    around_game_pct = round(around_game_spend / spend * 100, 1) if spend else 0
    away_game_pct   = round(away_game_spend / spend * 100, 1) if spend else 0

    # Predicted Attention Score (PAS Index 0 to 100 based on weighted avg attention seconds vs 12s benchmark)
    avg_attention = (att / impr) if impr else 0
    pas_score = min(100, round((avg_attention / 12.0) * 100, 0))
    # Comparison vs standard web display (standard display attention benchmark avg is ~1.4s)
    benchmark_lift = round(((avg_attention - 1.4) / 1.4) * 100, 0) if avg_attention > 1.4 else 0

    totals = {
        "spend":            round(spend, 2),
        "impr":             int(impr),
        "cpm":              round(spend / impr * 1000, 2) if impr else 0,
        "attention_hours":  round(att / 3600, 2),
        "attention_secs":   round(att, 0),
        "avg_attention_secs": round(avg_attention, 1),
        "pas_score":        int(pas_score),
        "benchmark_lift_pct": int(benchmark_lift),
        "environment_split": {
            "in_game": in_game_pct,
            "around_game": around_game_pct,
            "away_game": away_game_pct,
        },
    }
    return {
        "rows": rows, "totals": totals, "checks": checks, "errors": errs,
        "trace": tr(s, "Verify", t0, f"{len(errs)} problem(s) found"),
    }

def generate_clarification_email(spec: dict, brief: str) -> dict:
    """Generate a polished outbound agency email when brief parameters are missing or ambiguous."""
    missing = spec.get("missing") or []
    advertiser = spec.get("advertiser") if spec.get("advertiser") not in ("unknown", "", None) else "Valued Partner"
    regions = ", ".join(spec.get("regions")) if spec.get("regions") else "global / TBD"

    bullets = []
    if "budget_usd" in missing or not spec.get("budget_usd"):
        bullets.append("• Total Campaign Budget (USD): What is the intended investment cap? (We recommend min $5,000 for statistical attention significance).")
    if "flight_days" in missing or not spec.get("flight_days"):
        bullets.append("• Campaign Flight Window: Target start date and duration in days (we typically model 14–21 day flight windows for sustained in-game recall).")
    if "regions" in missing or not spec.get("regions"):
        bullets.append("• Geographic Regions: Confirm priority market allocation (supported: AU, NL, IN, US).")
    if not bullets:
        bullets.append("• Creative Readiness: Please confirm availability of Rewarded Video (15s/30s) or Playable HTML5 assets for immediate booking.")

    subject = f"Campaign Spec Confirmation: {advertiser} [{regions}] — In-Game Attention Media Plan"
    body = (
        f"Hi Team,\n\n"
        f"Thank you for sharing the campaign brief for {advertiser}. Our in-game AdOps pipeline has pre-parsed the brief and mapped initial attention-ranked inventory candidates across {regions}.\n\n"
        f"To finalize the deterministic media schedule and guarantee active attention thresholds, could you please clarify the following parameters:\n\n"
        + "\n".join(bullets)
        + "\n\n"
        f"Recommended In-Game Setup:\n"
        f"- Target Quality: Minimum 5.0s active gaze per line item (prioritizing Playable and Rewarded Video).\n"
        f"- Environment Allocation: 60% In-Game Intrinsic / Playable, 40% Rewarded Video.\n\n"
        f"Once confirmed, our agent will generate the finalized verified schedule for your approval.\n\n"
        f"Best regards,\n"
        f"iion Ad Operations & Agentic Planning Team"
    )

    return {
        "needed": len(missing) > 0 or (spec.get("confidence", 1.0) < 0.75),
        "subject": subject,
        "body": body,
        "missing_fields": missing,
    }

def log(s):
    t0   = time.time()
    sp   = s["spec"]
    n_missing = len(sp.get("missing", []))
    n_errors  = len(s.get("errors", []))
    rows      = s.get("rows", [])
    # Penalise if no high-attention format in the plan
    has_high_att = any(r.get("attention", 0) >= MIN_ATT for r in rows) if rows else True
    att_penalty  = 0.0 if has_high_att else 0.15
    conf = 1.0 - 0.25 * n_missing - 0.2 * n_errors - (0.1 if s.get("attempts", 0) > 1 else 0) - att_penalty
    t    = tr(s, "Log", t0, "saved to shadow log — nothing executed")
    clarification = generate_clarification_email(sp, s["brief"])
    res  = {
        "spec":       sp,
        "rows":       s["rows"],
        "totals":     s["totals"],
        "checks":     s["checks"],
        "errors":     s["errors"],
        "rationale":  s["plan"]["rationale"],
        "attempts":   s["attempts"],
        "confidence": round(max(.05, min(1.0, conf)), 2),
        "mode":       mode(),
        "trace":      t,
        "clarification_email": clarification,
    }
    res["run_id"] = db.save_run(s["brief"], res)
    return {"result": res, "trace": t}

# ── Build the graph ───────────────────────────────────────────────────────────

g = StateGraph(S)
for name, fn in [("extract", extract), ("retrieve", retrieve),
                 ("plan", plan), ("verify", verify), ("log", log)]:
    g.add_node(name, fn)
g.set_entry_point("extract")
g.add_edge("extract", "retrieve")
g.add_edge("retrieve", "plan")
g.add_edge("plan", "verify")
g.add_conditional_edges(
    "verify",
    lambda s: "plan" if (s["errors"] and s.get("attempts", 0) < 2) else "log",
    {"plan": "plan", "log": "log"},
)
g.add_edge("log", END)
APP = g.compile()

def run(brief):
    return APP.invoke({"brief": brief})["result"]

def refine(run_id: int, instruction: str) -> dict:
    """
    Human-in-the-Loop refinement of a previous run with natural language feedback.
    Allows ops managers to say 'Increase budget by $5,000 and focus on US' or
    'Only use playable and rewarded video'.
    """
    past_run = db.get_run(run_id)
    if not past_run:
        raise ValueError(f"Run {run_id} not found")

    spec = (past_run.get("spec") or {}).copy()
    text = instruction.lower()

    # Budget adjustments
    bud_add = re.search(r"(?:add|increase|more).*?(\d[\d,]*)", text)
    bud_set = re.search(r"(?:set|budget|spend|cap).*?(?:to|at|is)?\s*(\d[\d,]*)", text)
    if bud_add:
        amount = float(bud_add.group(1).replace(",", ""))
        spec["budget_usd"] = (spec.get("budget_usd") or 0) + amount
    elif bud_set:
        spec["budget_usd"] = float(bud_set.group(1).replace(",", ""))

    # Region updates
    for reg_pattern, code in REGION_PATTERNS:
        if re.search(reg_pattern, text):
            if "only" in text or "switch" in text:
                spec["regions"] = [code]
            else:
                if code not in (spec.get("regions") or []):
                    spec["regions"] = (spec.get("regions") or []) + [code]

    # Format adjustments
    if "rewarded" in text or "video" in text:
        if "rewarded_video" not in (spec.get("formats_pref") or []):
            spec["formats_pref"] = (spec.get("formats_pref") or []) + ["rewarded_video"]
    if "playable" in text:
        if "playable" not in (spec.get("formats_pref") or []):
            spec["formats_pref"] = (spec.get("formats_pref") or []) + ["playable"]
    if "banner" in text:
        if "banner" not in (spec.get("formats_pref") or []):
            spec["formats_pref"] = (spec.get("formats_pref") or []) + ["banner"]

    # Re-evaluate missing
    spec["missing"] = [k for k in ("budget_usd", "flight_days", "regions") if not spec.get(k)]

    s = {
        "brief": past_run.get("spec", {}).get("advertiser", "Brief") + f" [Refined: {instruction}]",
        "spec": spec,
        "attempts": 0,
        "trace": [{"step": "Refine", "ms": 5, "note": f"HITL: {instruction[:50]}"}],
    }
    
    # Run through retrieve -> plan -> verify -> log
    ret_out = retrieve(s)
    s.update(ret_out)
    plan_out = plan(s)
    s.update(plan_out)
    ver_out = verify(s)
    s.update(ver_out)
    if s.get("errors") and s.get("attempts", 0) < 2:
        plan_out2 = plan(s)
        s.update(plan_out2)
        ver_out2 = verify(s)
        s.update(ver_out2)
    log_out = log(s)
    return log_out["result"]

def stream_run(brief: str):
    """Yields real-time step events for SSE streaming."""
    s = {"brief": brief, "trace": [], "attempts": 0}

    # Step 1: Extract
    yield {"event": "step_start", "step": "Extract"}
    s.update(extract(s))
    ext_trace = s["trace"][-1]
    yield {"event": "step_done", "step": "Extract", "ms": ext_trace["ms"], "note": ext_trace["note"]}

    # Step 2: Retrieve
    yield {"event": "step_start", "step": "Retrieve"}
    s.update(retrieve(s))
    ret_trace = s["trace"][-1]
    yield {"event": "step_done", "step": "Retrieve", "ms": ret_trace["ms"], "note": ret_trace["note"]}

    # Step 3: Plan
    yield {"event": "step_start", "step": "Plan"}
    s.update(plan(s))
    plan_trace = s["trace"][-1]
    yield {"event": "step_done", "step": "Plan", "ms": plan_trace["ms"], "note": plan_trace["note"]}

    # Step 4: Verify
    yield {"event": "step_start", "step": "Verify"}
    s.update(verify(s))
    ver_trace = s["trace"][-1]
    yield {"event": "step_done", "step": "Verify", "ms": ver_trace["ms"], "note": ver_trace["note"]}

    # Retry conditional
    if s.get("errors") and s.get("attempts", 0) < 2:
        yield {"event": "retry", "step": "Plan", "errors": s["errors"]}
        yield {"event": "step_start", "step": "Plan", "status": "retry"}
        s.update(plan(s))
        plan_trace2 = s["trace"][-1]
        yield {"event": "step_done", "step": "Plan", "ms": plan_trace2["ms"], "note": plan_trace2["note"] + " (repaired)"}
        
        yield {"event": "step_start", "step": "Verify"}
        s.update(verify(s))
        ver_trace2 = s["trace"][-1]
        yield {"event": "step_done", "step": "Verify", "ms": ver_trace2["ms"], "note": ver_trace2["note"]}

    # Step 5: Log
    yield {"event": "step_start", "step": "Log"}
    res = log(s)["result"]
    log_trace = s["trace"][-1]
    yield {"event": "step_done", "step": "Log", "ms": log_trace["ms"], "note": log_trace["note"]}

    yield {"event": "complete", "result": res}
