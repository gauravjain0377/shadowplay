import sqlite3, random, json, time, os
import pathlib

# On Vercel serverless, root directory is read-only; use /tmp for SQLite
if os.getenv("VERCEL"):
    DB = pathlib.Path("/tmp/shadowplay.db")
else:
    DB = pathlib.Path(__file__).parent / "shadowplay.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS inventory(
        id TEXT PRIMARY KEY,
        genre TEXT,
        region TEXT,
        fmt TEXT,
        placement TEXT,
        cpm REAL,
        attention REAL,
        daily_impr INTEGER,
        min_bid REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL,
        brief TEXT,
        result TEXT,
        decision TEXT,
        reason TEXT
    );""")
    # migrate: add min_bid if upgrading from an older db
    try:
        c.execute("ALTER TABLE inventory ADD COLUMN min_bid REAL DEFAULT 0")
        c.commit()
    except Exception:
        pass  # already exists
    if not c.execute("SELECT 1 FROM inventory").fetchone():
        rnd = random.Random(7)
        # fmt -> (placement, base_cpm, base_attention_secs)
        fmts = {
            "rewarded_video": ("in-game",        9.0,  5.0),
            "playable":       ("in-game",        11.0, 7.5),
            "banner":         ("around-game",    2.2,  1.2),
            "native":         ("away-from-game", 4.0,  2.0),
        }
        # regional CPM multiplier (synthetic)
        mult = {"AU": 1.3, "NL": 1.15, "US": 1.4, "IN": 0.35}
        n = 0
        for g in ["puzzle", "word", "racing", "casual", "trivia"]:
            for r in mult:
                for f, (pl, cpm, att) in fmts.items():
                    n += 1
                    base_cpm = round(cpm * mult[r] * rnd.uniform(.9, 1.1), 2)
                    min_bid  = round(base_cpm * 0.60, 2)   # floor = 60% of listed CPM
                    c.execute("INSERT INTO inventory VALUES(?,?,?,?,?,?,?,?,?)",
                              (f"INV-{n:03d}", g, r, f, pl, base_cpm,
                               round(att * rnd.uniform(.85, 1.15), 1),
                               rnd.randint(40, 400) * 1000, min_bid))
    c.commit()
    c.close()

def search(regions, fmts=None, genres=None):
    """Return inventory rows ordered by attention/CPM (best quality per dollar first)."""
    c = conn()
    q = "SELECT * FROM inventory WHERE region IN (%s)" % ",".join("?" * len(regions))
    a = list(regions)
    if fmts:
        q += " AND fmt IN (%s)" % ",".join("?" * len(fmts))
        a += fmts
    if genres:
        q += " AND genre IN (%s)" % ",".join("?" * len(genres))
        a += genres
    rows = [dict(r) for r in c.execute(q + " ORDER BY attention / cpm DESC", a)]
    c.close()
    return rows

def get(inv_id):
    c = conn()
    r = c.execute("SELECT * FROM inventory WHERE id=?", (inv_id,)).fetchone()
    c.close()
    return dict(r) if r else None

def save_run(brief, result):
    c = conn()
    cur = c.execute("INSERT INTO runs(ts, brief, result) VALUES(?,?,?)",
                    (time.time(), brief, json.dumps(result)))
    c.commit()
    i = cur.lastrowid
    c.close()
    return i

def decide(run_id, decision, reason):
    c = conn()
    c.execute("UPDATE runs SET decision=?, reason=? WHERE id=?", (decision, reason, run_id))
    c.commit()
    c.close()

def stats():
    c = conn()
    r = c.execute(
        "SELECT COUNT(*) n, SUM(decision='approve') a, SUM(decision='reject') j FROM runs"
    ).fetchone()
    
    # Reason breakdown for rejections
    reasons = [
        {"reason": row["reason"], "count": row["cnt"]}
        for row in c.execute(
            "SELECT reason, COUNT(*) cnt FROM runs WHERE decision='reject' AND reason != '' GROUP BY reason ORDER BY cnt DESC LIMIT 5"
        ).fetchall()
    ]
    
    # Cumulative stats
    all_runs = c.execute("SELECT result FROM runs").fetchall()
    total_spend = 0.0
    total_att_hours = 0.0
    for row in all_runs:
        try:
            res = json.loads(row["result"])
            tot = res.get("totals", {})
            total_spend += float(tot.get("spend", 0))
            total_att_hours += float(tot.get("attention_hours", 0))
        except Exception:
            pass

    c.close()
    a, j = r["a"] or 0, r["j"] or 0
    return {
        "runs": r["n"],
        "approved": a,
        "rejected": j,
        "agreement": round(a / (a + j), 2) if (a + j) else None,
        "top_rejection_reasons": reasons,
        "cumulative_spend": round(total_spend, 2),
        "cumulative_attention_hours": round(total_att_hours, 1),
    }

def history(limit=30):
    """Last N shadow runs for the audit tab."""
    c = conn()
    rows = c.execute(
        "SELECT id, ts, brief, decision, reason,"
        " json_extract(result,'$.confidence') conf,"
        " json_extract(result,'$.mode') mode,"
        " json_extract(result,'$.totals.spend') spend,"
        " json_extract(result,'$.spec.advertiser') advertiser"
        " FROM runs ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_run(run_id):
    """Fetch a full saved run result by id (used by the replay endpoint)."""
    c = conn()
    row = c.execute("SELECT result FROM runs WHERE id=?", (run_id,)).fetchone()
    c.close()
    return json.loads(row["result"]) if row else None

def inventory_meta():
    """Return summary stats and filter options for the inventory explorer."""
    c = conn()
    total = c.execute("SELECT COUNT(*) n FROM inventory").fetchone()["n"]
    regions = [r[0] for r in c.execute("SELECT DISTINCT region FROM inventory ORDER BY region")]
    fmts    = [r[0] for r in c.execute("SELECT DISTINCT fmt    FROM inventory ORDER BY fmt")]
    genres  = [r[0] for r in c.execute("SELECT DISTINCT genre  FROM inventory ORDER BY genre")]
    agg = c.execute(
        "SELECT AVG(cpm) avg_cpm, AVG(attention) avg_att, SUM(daily_impr) total_impr FROM inventory"
    ).fetchone()
    c.close()
    return {
        "total": total,
        "regions": regions,
        "formats": fmts,
        "genres":  genres,
        "avg_cpm":    round(agg["avg_cpm"], 2),
        "avg_att":    round(agg["avg_att"], 2),
        "total_daily_impr": agg["total_impr"],
    }
