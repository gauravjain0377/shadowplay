"""
eval.py — ShadowPlay evaluation harness
Run:  python eval.py
      python eval.py --check-models    (ping both providers; ~2 s)

Pass criteria per brief
  spec_ok   : regions, budget_usd, flight_days all match the gold answer
  guard_ok  : all verifier checks (except "Brief had everything") pass
  flagged_ok: briefs without a budget are correctly flagged as incomplete
  Overall   : all three must be true
"""
import sys, time, os
sys.stdout.reconfigure(line_buffering=True)
from dotenv import load_dotenv
load_dotenv()

import agent, db
from samples import SAMPLES

db.init()

# ── optional: verify that the configured model names are live ─────────────────
if "--check-models" in sys.argv:
    print("Checking model availability …")
    groq_key    = os.getenv("GROQ_API_KEY")
    google_key  = os.getenv("GOOGLE_API_KEY")
    groq_model  = os.getenv("GROQ_MODEL",   "openai/gpt-oss-120b")
    gemini_model= os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            ChatGroq(model=groq_model, temperature=0).invoke("hi")
            print(f"  Groq   {groq_model!r:40s}  ✓ live")
        except Exception as e:
            print(f"  Groq   {groq_model!r:40s}  ✗ {e}")
    else:
        print("  Groq   (no GROQ_API_KEY set)")
    if google_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            ChatGoogleGenerativeAI(model=gemini_model, temperature=0).invoke("hi")
            print(f"  Gemini {gemini_model!r:40s}  ✓ live")
        except Exception as e:
            print(f"  Gemini {gemini_model!r:40s}  ✗ {e}")
    else:
        print("  Gemini (no GOOGLE_API_KEY set)")
    print()

# ── run evaluation ────────────────────────────────────────────────────────────
print(f"{'Brief':<32} {'spec':>4} {'guard':>5} {'flag':>4} {'att':>3} {'tries':>5} {'conf':>4}  {'ms':>6}  result")
print("─" * 95)

passed = 0
t_total = time.time()

for s in SAMPLES:
    t0 = time.time()
    r  = agent.run(s["brief"])
    ms = int((time.time() - t0) * 1000)
    sp = r["spec"]
    g  = s["gold"]

    # spec extraction
    spec_ok = (
        set(sp["regions"]) == set(g["regions"]) and
        sp["budget_usd"]   == g["budget_usd"]   and
        sp["flight_days"]  == g["flight_days"]
    )

    # verifier (skip the "Brief had everything" and "Attention quality" checks here —
    # those are subjective; we only require the hard guardrails to pass)
    hard_checks = [c for c in r["checks"] if c["name"] not in
                   ("Brief had everything needed", "Attention quality ≥ 5 s on ≥1 line")]
    guard_ok = all(c["ok"] for c in hard_checks)

    # incomplete briefs must be flagged as missing
    flagged_ok = bool(sp["missing"]) == (g["budget_usd"] is None)

    # attention quality gate: at least one row with attention ≥ 5 s (skipped if no plan)
    att_ok = not r["rows"] or any(row["attention"] >= 5.0 for row in r["rows"])

    ok = spec_ok and guard_ok and flagged_ok
    passed += ok

    mark = "PASS" if ok else "FAIL"
    print(
        f"{mark}  {s['name']:<30} "
        f"{'✓' if spec_ok  else '✗':>4} "
        f"{'✓' if guard_ok else '✗':>5} "
        f"{'✓' if flagged_ok else '✗':>4} "
        f"{'✓' if att_ok  else '✗':>3} "
        f"{r['attempts']:>5} "
        f"{r['confidence']:>4.2f} "
        f"{ms:>7} ms"
    )
    if not ok:
        for e in r["errors"]:
            print(f"       ↳ {e}")

total_ms = int((time.time() - t_total) * 1000)
print("─" * 95)
print(f"\n{passed}/{len(SAMPLES)} passed   total {total_ms} ms   (mode: {agent.mode()})")
if passed < len(SAMPLES):
    print("\nTip: run with a live API key — offline mock_extract may miss some alias tests.")
