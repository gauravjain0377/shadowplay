from dotenv import load_dotenv
load_dotenv()

import pathlib, json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import db, agent
from samples import SAMPLES

db.init()
app = FastAPI(title="ShadowPlay")

# ── Request models ────────────────────────────────────────────────────────────

class BriefBody(BaseModel):
    brief: str = Field(min_length=10, max_length=4000)

class DecisionBody(BaseModel):
    run_id:   int
    decision: str
    reason:   str = Field("", max_length=500)

class ReplayBody(BaseModel):
    run_id: int

class RefineBody(BaseModel):
    run_id: int
    instruction: str = Field(min_length=3, max_length=500)

# ── API endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/samples")
@app.get("/samples")
def samples():
    return [{"name": s["name"], "brief": s["brief"]} for s in SAMPLES]

@app.get("/api/stats")
@app.get("/stats")
def stats():
    return {**db.stats(), "mode": agent.mode()}

@app.post("/api/run")
@app.post("/run")
def run_brief(b: BriefBody):
    return agent.run(b.brief)

@app.get("/api/run/stream")
@app.get("/run/stream")
def stream_brief(brief: str):
    """Server-Sent Events endpoint to stream real-time pipeline steps."""
    def event_generator():
        for event in agent.stream_run(brief):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/refine")
@app.post("/refine")
def refine_plan(b: RefineBody):
    """Human-in-the-Loop refinement of a previous media plan."""
    try:
        return agent.refine(b.run_id, b.instruction)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Refinement error: {str(e)}")

@app.post("/api/decide")
@app.post("/decide")
def decide(d: DecisionBody):
    if d.decision not in ("approve", "reject"):
        raise HTTPException(400, "decision must be approve or reject")
    db.decide(d.run_id, d.decision, d.reason)
    return {"ok": True}

@app.get("/api/history")
@app.get("/history")
def history(limit: int = 30):
    """Return the last N shadow runs for the audit tab."""
    return db.history(limit)

@app.post("/api/replay")
@app.post("/replay")
def replay(body: ReplayBody):
    """Return a saved run result so the UI can replay the lap without re-running the agent."""
    result = db.get_run(body.run_id)
    if not result:
        raise HTTPException(404, "run not found")
    return result

@app.get("/api/inventory")
@app.get("/inventory")
def inventory(region: str = None, fmt: str = None, genre: str = None):
    """Return inventory rows, optionally filtered."""
    regions = [region] if region else ["AU", "NL", "IN", "US"]
    fmts    = [fmt]    if fmt    else None
    genres  = [genre]  if genre  else None
    rows = db.search(regions, fmts, genres)
    return rows

@app.get("/api/inventory/meta")
@app.get("/inventory/meta")
def inventory_meta():
    """Return filter options and summary stats for the inventory explorer."""
    return db.inventory_meta()

# ── Serve the UI ──────────────────────────────────────────────────────────────

app.mount("/", StaticFiles(
    directory=pathlib.Path(__file__).parent / "static", html=True
), name="ui")
