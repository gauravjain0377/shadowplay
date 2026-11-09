# ShadowPlay — Attention-First AdOps AI Agent (Shadow Mode)

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain)
![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Build-Passing%20(9%2F9)-4ade80?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-e8c97a?style=for-the-badge)

<p align="center">
  <b>A shadow-mode agentic pipeline that transforms chaotic advertiser briefs into verified, attention-optimized media plans — without executing a single dollar until approved by a human.</b>
</p>

Crafted by **[Gaurav Jain](https://github.com/gauravjain0377)** · [Portfolio & Projects](https://github.com/gauravjain0377/portfolio)  
*Built as a prototype for the **iion AI Engineering Intern (Agentic Workflows)** role.*

</div>

---

> **One-Line Pitch**: **ShadowPlay is a shadow-mode agentic AI copilot for in-game AdOps that parses unstructured advertiser emails into structured campaign specs, plans media ranked by cognitive attention per dollar, deterministically self-heals inventory constraints, and enables conversational human approval.**

---

## The "Ghost Lap" Philosophy

In racing games, a **ghost car** replays the exact trajectory and lap time of a car without colliding with vehicles on the track. It allows drivers to test setups and benchmark performance in zero-risk isolation.

**ShadowPlay brings the ghost lap to Ad Operations:**
- Enterprise AdOps is high-stakes. A hallucinated CPM, over-allocated daily impression cap, or misplaced budget can waste thousands of dollars.
- ShadowPlay runs parallel to live campaign management. It listens to incoming brief emails, builds the plan, verifies every single number against inventory databases, and records the run.
- **It never executes bookings autonomously.** A human operator reviews the plan, inspects the verification checklist, optionally refines the parameters conversationally, and decides: **Approve** or **Reject**. The platform tracks the human agreement rate over time to calibrate agent trust.

---

## Built Specifically for iion: Attention-First Economics

Traditional programmatic advertising optimizes for outdated **MRC viewability** (50% pixels on screen for 2 seconds), which rewards passive scrolling and interstitial fatigue. **iion champions real human attention in gaming environments.**

ShadowPlay is designed around that vision:
1. **Attention-Seconds per $1,000 (Not CTR)**: Inventory is ranked and allocated by attention yield ($\text{attention duration} \div \text{CPM} \times 1000$).
2. **Predicted Attention Score (PAS™ Index)**: Generates a 0–100 cognitive attention index, demonstrating an average **+300% to +380% active attention lift** over standard web display ($1.4\text{s}$ baseline).
3. **Gaming Environment Taxonomy**:
   - 🎮 **In-Game Intrinsic**: Native billboards, trackside banners, and interactive playable units ($5.0\text{s}$–$18.5\text{s}$ attention).
   - 🎯 **Around-Game**: Overlays, UI frames, and leaderboard placements ($1.2\text{s}$–$2.5\text{s}$ attention).
   - 🏆 **Away-From-Game**: Rewarded video and opt-in value exchanges ($5.0\text{s}$–$12.0\text{s}$ attention).
4. **Attention Quality Gate**: The deterministic verifier flags and rejects any media plan lacking high-attention formats ($\ge 5.0\text{s}$).

---

## System Architecture

```
                       ┌──────────────────────────────────────────────┐
                       │     Incoming Brief (Messy Email / Forward)    │
                       └──────────────────────┬───────────────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │      Node: Extract      │  Structured Pydantic Spec
                                 │  (LLM + Regex Fallback) │  (Budget, Flight, Region, Genre)
                                 └────────────┬────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │     Node: Retrieve      │  Top 12 candidates ranked by
                                 │   (SQLite / Attention)  │  Attention-Seconds per $1k
                                 └────────────┬────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                        ┌───────►│       Node: Plan        │  Budget allocation across 2–4 slots
                        │        │    (LLM / Optimizer)    │  (Enforces CPM ≥ floor price)
                        │        └────────────┬────────────┘
                        │                     │
                        │                     ▼
             Conditional Retry   ┌─────────────────────────┐
            (Self-Healing Loop   │      Node: Verify       │  7 Deterministic Hard Checks
             max 2 attempts)     │ (Python - Zero LLM Trust)│  (IDs real? Supply fits? Over budget?)
                        │        └────────────┬────────────┘
                        │                     │
                        │               Pass or Exhausted
                        │                     │
                        └──────── Errors? ────┤
                                              ▼
                                 ┌─────────────────────────┐
                                 │        Node: Log        │  Save full trace + PAS™ telemetry +
                                 │      (Audit State)      │  Outbound Agency Clarification Email
                                 └────────────┬────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │ Human Verdict & Refine  │  A: Approve | R: Reject | HITL Refine
                                 └─────────────────────────┘
```

---

## 6 Production-Grade Agentic Features

### 1. Deterministic Guardrails (Zero LLM Trust)
No LLM is permitted to validate numbers. Seven pure Python verification checks enforce:
- **Real Inventory IDs**: Model cannot hallucinate non-existent inventory IDs.
- **No Duplicate Line Items**: Single allocation per inventory slot.
- **Supply Capacity Check**: $\text{Spend} \div \text{CPM} \times 1000 \le \text{daily\_impressions} \times \text{flight\_days}$.
- **Region Boundary Enforcement**: Prevents cross-region budget leakage.
- **Budget Ceiling**: Total spend $\le \text{budget} \times 1.001$.
- **Floor Price Guard**: Effective $\text{CPM} \ge \text{min\_bid}$ for every line item.
- **Attention Quality Threshold**: At least one line item with $\ge 5.0\text{s}$ active attention.

### 2. Autonomous Self-Healing Pacing
When an inventory candidate fails verification (e.g. required impressions exceed supply cap), the agent doesn't abort. It dynamically clamps the line item to the exact supply ceiling and reallocates residual spend into the next eligible attention-dense candidate, automatically proving the plan on Attempt 2.

### 3. Human-in-the-Loop (HITL) Plan Refinement (`POST /api/refine`)
Ops managers can negotiate and tune schedules via natural language:
> *"Increase budget by $5,000 and switch to US only"*  
> *"Prioritize playable formats and casual games"*

The agent parses feedback, adjusts the spec, re-retrieves candidates, and re-proves the plan in sub-second time.

### 4. Automated Agency Clarification Generator
When a brief arrives with missing information (e.g. no budget stated, ambiguous flight dates, or unknown regions), ShadowPlay flags incomplete fields and automatically drafts a professional outbound agency email with a 1-click clipboard copy.

### 5. Real-Time Server-Sent Events (SSE) Streaming (`/api/run/stream`)
Real-time step updates stream over SSE directly to the browser. The UI animates the ghost token along the 5-sector track, reflects live millisecond latencies, and rewinds on retries.

### 6. Audit Telemetry & Trust Governance (`/api/stats`, `/api/history`)
Tracks the human agreement rate over time, cumulative active attention hours generated, total spend modeled, and top rejection reasons with past-run replay.

---

## Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.13)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### 1. Clone & Set Up Environment

```bash
# Clone the repository
git clone https://github.com/gauravjain0377/shadowplay.git
cd shadowplay

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key (Optional)

```bash
# Copy example configuration
cp .env.example .env
```

Open `.env` in any text editor and add a free API key:
- **Groq** (Fastest, free tier): [console.groq.com](https://console.groq.com)
- **Google AI Studio** (Gemini free tier): [aistudio.google.com](https://aistudio.google.com)

> 💡 **No API key?** ShadowPlay runs in **Offline Demo Mode** using its built-in rule-based fallback. You can explore the full UI, run ghost laps, and test guardrails without any keys.

### 3. Start the Server

```bash
uvicorn app:app --reload --port 8000
```

Open your browser:
- 🏎️ **Landing Page**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- 🎛️ **AdOps Cockpit**: [http://127.0.0.1:8000/app.html](http://127.0.0.1:8000/app.html)
- 📖 **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Cockpit Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| <kbd>⇧</kbd> + <kbd>↵</kbd> (Shift + Enter) | Run Ghost Lap |
| <kbd>A</kbd> | Approve Current Plan |
| <kbd>R</kbd> | Reject Current Plan (opens optional reason box) |
| <kbd>Esc</kbd> | Dismiss modals (Audit drawer / Email modal) |

---

## Evaluation Benchmark Suite

Run the automated evaluation suite across 9 test briefs (including colloquial aliases, missing-budget briefs, and adversarial prompt injections):

```bash
python eval.py
```

### Benchmark Results

```
Brief                            spec guard flag att tries conf      ms  result
───────────────────────────────────────────────────────────────────────────────────────────────
PASS  Tulip Chews · Netherlands    ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Koala Bank · AU + US         ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Chai Rush · India            ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  SpeedSneakers · Messy fwd    ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Missing budget · AU + NL     ✓     ✓    ✓   —     0 0.50   ~20 ms
PASS  Benelux alias · NL           ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Oz alias · Australia         ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Word-number budget           ✓     ✓    ✓   ✓     1 1.00   ~45 ms
PASS  Adversarial brief            ✓     ✓    ✓   ✓     1 1.00   ~45 ms
───────────────────────────────────────────────────────────────────────────────────────────────
9/9 passed   (100% Guardrail Integrity)
```

> 🛡️ **Adversarial Security Test**: The adversarial brief injects fake inventory IDs (`INV-999, INV-1000, INV-FAKE`). The deterministic verifier catches all fabricated IDs and rejects them without exception.

---

## Project Structure

```
shadowplay/
├── agent.py               # LangGraph pipeline, deterministic verifier, HITL refine, SSE streamer
├── app.py                 # FastAPI endpoints (SSE streaming, REST API, static files)
├── db.py                  # SQLite storage, inventory catalog (80 slots), audit history & stats
├── eval.py                # 9-brief automated evaluation benchmark suite
├── samples.py             # Gold-standard test briefs & adversarial test cases
├── requirements.txt       # Dependencies (FastAPI, LangGraph, LangChain, Pydantic, etc.)
├── .env.example           # Example configuration template (Groq / Gemini)
├── .gitignore             # Strict ignore rules (keeps secrets & DB local)
├── skills/
│   └── brief_to_plan/
│       └── SKILL.md       # AdOps domain prompt instructions & attention ranking rules
└── static/
    ├── index.html         # Premium dark-mode landing page with animated hero demo
    └── app.html           # Full working cockpit with live lap track, HITL bar & audit drawer
```

---

## Production Roadmap for iion

If scaling this prototype into iion's live `immersiion` and `fusiion` platforms:

| Area | Current Prototype | Production Path |
|---|---|---|
| **Inventory Source** | SQLite (80 synthetic slots) | Direct iion SSP / OpenRTB inventory API integration |
| **Search / Matching** | Attention-per-dollar SQL sort | Vector search (pgvector) over game genre, context & player demographics |
| **Authentication** | Open sandbox session | OAuth2 / JWT with role-based access (Media Buyer vs Ops Lead) |
| **Execution** | Shadow mode (no execution) | Webhook to DSP/ad server upon human approval |
| **Alerting** | In-app notification | Slack / Microsoft Teams webhook pinging the on-duty AdOps team |

---

## Author & Attribution

Developed with passion by **[Gaurav Jain](https://github.com/gauravjain0377)**.  
- GitHub: [@gauravjain0377](https://github.com/gauravjain0377)  
- Portfolio: [gauravjain0377/portfolio](https://github.com/gauravjain0377/portfolio)  
- Contact: [jaingaurav906@gmail.com](mailto:jaingaurav906@gmail.com)

*All brand names, campaign briefs, and inventory records in this prototype are synthetic and used strictly for technical demonstration.*
