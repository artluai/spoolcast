# Publishing Rules

How to make titles, descriptions, and thumbnails that actually match
what a video is about — not what the chunks/scenes/beat-descriptions
imply.

## The script-first rule (CRITICAL)

**Before generating any title, description, or thumbnail concept,
READ the full voiceover narration end-to-end.** Do NOT infer from:

- chunk titles / scene_title fields
- beat_description fields (those are visual scaffolding, not narrative)
- the project name or session id
- chapter timestamps alone

Read the actual sentences the narrator speaks. The script is in either:

1. `sessions/<id>/script/voiceover.md` (preferred location, may be empty)
2. Concatenated `narration` fields from `shot-list/shot-list.json`
   beats, in chunk order

The fastest way to get the script is the latter:

```bash
python3 -c "
import json
sl = json.load(open('sessions/<id>/shot-list/shot-list.json'))
for c in sl['chunks']:
    for b in c.get('beats', []):
        print(b.get('narration',''))
"
```

## The "actual hook" test

After reading the script, identify the **actual hook**: the surprising
claim, finding, or twist the video makes. This is rarely the setup or
premise. It's almost always the unexpected result.

Test the hook against these questions:

1. **Is this the question, or the answer?** Most videos are sold by
   the setup ("can AI predict X?") but the real value is the answer
   ("AI predicted A but the market said B"). Sell the answer.
2. **Is there a conflict/twist?** If the video has a "but" moment
   ("the model favored A, but the market favored B"), the title and
   thumbnail must surface that conflict. The conflict IS the click.
3. **Does the title imply something the script disproves?** If the
   script shows the AI didn't reliably pick winners but the title says
   "AI picks winning ads", you're misleading the viewer. They will
   bounce immediately and tank watch time. Be accurate.
4. **Could the title be true of a generic AI explainer?** If yes,
   too vague. Add the SPECIFIC claim from the script.

## Title structure

Aim for under 60 characters. Pattern that usually works:

- `<specific subject> <specific finding>` — e.g. "Meta's brain-AI
  picked the wrong winning ad"
- `<personal experience> <specific result>` — e.g. "I let an AI
  predict my ad winner. It got it wrong."
- `<question that the video actually answers>` — e.g. "Can AI predict
  which ad wins? Mine couldn't."

Avoid:
- Generic "AI does X" framings
- Vague capability claims ("scores ads")
- Titles that describe the SETUP not the FINDING

## Thumbnail concept

Thumbnail concept must reflect the actual hook, not the premise.

For a "model vs market" mismatch video, the concept should visualize
the **disagreement** — not just "AI thinks". Examples:

- Two side-by-side ads: AI brain pointing to one with checkmark,
  dollar sign pointing to the other with checkmark (split-screen
  conflict)
- A brain + an X over a dollar sign + a checkmark over a different
  dollar sign (the model lost, the market won)
- A character looking confused at two contradicting score sheets

For style, see `ASSET_RULES.md` re: prompt-only style overrides for
thumbnails (typically allow ONE accent color even when scenes are
locked to monochrome).

## Description structure

First 2-3 lines (above YouTube's "show more" cutoff) must contain:

1. The setup in one sentence
2. The actual finding/twist in one sentence

Then chapters (real timestamps from `preview-data.json`), then links,
then tags.

Do NOT bury the finding. Do NOT use the description to set up surprise
the viewer can already see in the title.

## Workflow

1. Read the script (full narration concatenation)
2. Identify the actual hook (the answer, not the question)
3. Draft title, description, thumbnail concept based on hook
4. Generate thumbnail via `generate_thumbnail.py` (uses session-aware
   helper from `ASSET_RULES.md`)
5. Pull real chapter timestamps from `preview-data.json`

## What this prevents

A previous session generated a title and thumbnail concept based on
chunk titles + the session name, without reading the script. The
result mis-sold the video — title implied "AI scores ads" when the
actual finding was "AI's score and market score disagreed". The user
caught it; the rule above is the systemic fix.
