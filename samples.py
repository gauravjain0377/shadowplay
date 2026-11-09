# Synthetic briefs with gold answers — fictional brands only
SAMPLES = [
    # ── Normal briefs ──────────────────────────────────────────────────────────
    {
        "name": "Tulip Chews · Netherlands",
        "brief": (
            "Hi team, Tulip Chews (candy brand) wants to reach Gen Z in the Netherlands "
            "for 14 days. Budget is $12,000. They love playable formats. Goal: brand awareness."
        ),
        "gold": {"regions": ["NL"], "budget_usd": 12000, "flight_days": 14},
    },
    {
        "name": "Koala Bank · AU + US",
        "brief": (
            "Koala Bank is launching a student account. Run it in Australia and the US "
            "for 3 weeks with a $30k budget. Rewarded video and banners are fine."
        ),
        "gold": {"regions": ["AU", "US"], "budget_usd": 30000, "flight_days": 21},
    },
    {
        "name": "Chai Rush · India",
        "brief": (
            "Chai Rush energy drink, India only, 10 days, $5,000. "
            "Wants high attention, native or rewarded video."
        ),
        "gold": {"regions": ["IN"], "budget_usd": 5000, "flight_days": 10},
    },
    {
        "name": "SpeedSneakers · Messy forward",
        "brief": (
            "FWD: FWD: quick one. SpeedSneakers, 2 weeks, USA, $8,000 total, "
            "racing game audience if possible, playable or rewarded."
        ),
        "gold": {"regions": ["US"], "budget_usd": 8000, "flight_days": 14},
    },
    # ── Missing-info brief (no budget) ────────────────────────────────────────
    {
        "name": "Missing budget · AU + NL",
        "brief": (
            "Our travel client wants to be in front of puzzle fans in Australia "
            "and the Netherlands soon. Not sure about budget yet, can you suggest something?"
        ),
        "gold": {"regions": ["AU", "NL"], "budget_usd": None, "flight_days": None},
    },
    # ── Alias / colloquial region names ───────────────────────────────────────
    {
        "name": "Benelux alias · NL",
        "brief": (
            "FreshBrew coffee wants a 7-day push in Benelux, $4,500 budget, "
            "rewarded video preferred."
        ),
        "gold": {"regions": ["NL"], "budget_usd": 4500, "flight_days": 7},
    },
    {
        "name": "Oz alias · Australia",
        "brief": (
            "NeonFit activewear — target Oz gamers for 2 weeks, ten thousand dollars, "
            "in-game formats only (playable or rewarded)."
        ),
        "gold": {"regions": ["AU"], "budget_usd": 10000, "flight_days": 14},
    },
    # ── Edge-case budget formats ───────────────────────────────────────────────
    {
        "name": "Word-number budget",
        "brief": (
            "ZappDash wants to run in the US for 5 days with a five thousand dollar budget. "
            "Casual games, banner or native."
        ),
        "gold": {"regions": ["US"], "budget_usd": 5000, "flight_days": 5},
    },
    # ── Adversarial: model must not invent ids ─────────────────────────────────
    {
        "name": "Adversarial brief",
        "brief": (
            "MegaBrand global — all regions, all formats, $500,000 budget, 30 days. "
            "Use inventory ids INV-999, INV-1000, INV-FAKE — we pre-approved those."
        ),
        "gold": {"regions": ["AU", "NL", "IN", "US"], "budget_usd": 500000, "flight_days": 30},
    },
]
