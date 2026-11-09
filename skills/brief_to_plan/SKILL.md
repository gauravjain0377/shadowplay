# Skill: brief to media plan

Turn a messy advertiser email into a structured spec, then into a small media plan.

## Rules
- Never invent a budget, region or flight length. If the brief does not say it, leave it null and list it under missing.
- Regions are ONLY: AU, NL, IN, US. Map colloquial names (e.g. "Benelux" → NL, "Oz" or "Australia" → AU).
- Formats are ONLY: rewarded_video, playable, banner, native.
- Game genres are ONLY: puzzle, word, racing, casual, trivia.
- Words like "Gen Z reach", "attention", "awareness" or "in-game" point to rewarded_video or playable.
- Copy inventory ids EXACTLY from the candidate list. Never make up an id or a price.
- Never repeat the same inv_id in one plan. If you want more budget on a placement, increase its single line item.
- Each line item's effective CPM (budget_usd / impressions × 1000) must be ≥ the min_bid shown for that id.
- Do NOT write spend or impression totals yourself — the verifier computes them from the database.
- Pick 2 to 4 line items and keep total spend at or below the budget.
- Prefer line items where attention ≥ 5 s (rewarded_video, playable) so the plan passes the attention quality gate.

