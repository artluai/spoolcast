# Script Extraction Rules

## Why This Document Exists

The current spoolcast rules explain the system well once a session has already become a shot list.

They do **not** capture the most editorially important stage well enough:

- how a raw session package becomes a story
- how the story becomes a screenplay
- how the screenplay becomes a scene plan
- how the scene plan becomes a shot list

This document records the actual method used on a real session package so future agents do not flatten this stage into generic summarization.

The point is not to sound principled.
The point is to preserve the working editorial process that produced a screenplay, a scene plan, and then a shot board that were actually usable.

This is based on the real `tribe-session-001` pipeline:

- raw session package in `../spoolcast-content/sessions/tribe-session-001/source/`
- analysis in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-source-analysis.md`
- screenplay drafts in:
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v1.md`
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v2.md`
  - `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-screenplay-v3.md`
- scene plan in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-b-roll-plan.md`
- beat-level narration script in `../spoolcast-content/sessions/tribe-session-001/working/tribe-session-001-voiceover-script.md`
- shot list in `../spoolcast-content/sessions/tribe-session-001/working/tribe-shot-board.xlsx`

---

## The Actual Pipeline, In Order

This is the order that was actually followed.

It matters.

The main failure mode is skipping the middle and pretending a transcript can go straight into a shot list.
It cannot.

### 1. Start by stabilizing the raw session package

Before any writing, the package had to be treated like evidence, not inspiration.

The raw package for `tribe-session-001` contained:

- `manifest.json`
- `transcript.md`
- `notes.md`
- `logs.md`
- a few recovered image artifacts
- many missing screenshot references

The first job was not “start drafting.”
The first job was:

- confirm what the package actually contains
- confirm what is missing
- confirm what is trustworthy
- confirm what cannot be relied on visually

For this session, that changed the later script materially.

The package notes made clear:

- a lot of screenshots were gone
- the transcript had been rebuilt from session logs
- some visual artifacts were recreated as SVGs
- the source package was good enough to tell the story
- the source package was **not** good enough to support a screenshot-heavy reconstruction

That meant the screenplay could not depend on “then we show the exact screenshot from the session.”
That is not a visual preference note.
That is an editorial constraint.

### 2. Read the session transcript to understand what the session was really about

The next step was **not** summarizing the transcript.
It was identifying what kind of story was actually inside it.

The transcript was read looking for:

- the practical question that started the session
- the friction that made the session real
- the first moment where the session stopped being generic
- the result that actually changed the interpretation
- the final answer the session earned

The key distinction here:

- the transcript contains many events
- only some of them belong to the story spine

For `tribe-session-001`, the raw session started with a practical product question:

- can Meta’s TRIBE v2 analyze a video ad and help say whether the ad is good or bad?

That mattered more than the existence of TRIBE itself.

This is where the editorial method diverges from a generic “explain the technology” workflow.
The story was **not** “Meta released an interesting model.”
The story was:

- a practical workflow question met a strange research model
- the setup was painful
- the experiment worked enough to be interesting
- the result disagreed with the market

That is the spine.

### 3. Write a source analysis before drafting any screenplay

A separate source-analysis file was written first.
That was not optional.
That file forced the story to be extracted before tone or narration rhythm got involved.

The analysis step did four jobs.

#### Job A: reduce the transcript to hard facts

For `tribe-session-001`, the hard facts included:

- TRIBE predicts brain-response patterns from video, audio, and text
- it does not produce a direct good/bad ad score
- the model is under a non-commercial license
- local setup failed in multiple ways
- Colab on a Tesla T4 could run it
- each short clip still took about 3 hours 32 minutes to encode
- TRIBE-style signals favored Video A
- real ROAS favored Video B

This stripped out noise and gave the later drafts a factual floor.

#### Job B: identify the strongest story turn

This is the step where the editorial center gets chosen.

The strongest turn was not:

- “the model exists”
- “the model worked”
- “the setup was annoying”

It was:

- the model produced interpretable structure
- that structure disagreed with the market result

That mismatch became the turning point.

This was explicitly recorded in the source analysis because if it is not written down here, later drafts drift back toward generic tech explanation.

#### Job C: decide what kind of story this is

The source analysis turned the package into a specific narrative shape:

1. practical goal
2. setup friction
3. real experiment
4. interesting mismatch
5. interpretation
6. operational reality

That shape is not cosmetic.
It later determined the order of scenes.

#### Job D: decide what the video should **not** pretend

The analysis also wrote down the anti-claims:

- do not imply TRIBE directly reads real human brains
- do not imply the model proved it can pick winning ads
- do not rely on missing screenshots
- do not force a clean linear success story

Those constraints later saved the screenplay from hype.

### 4. Pick the story angle only after the source analysis is done

Only after the source analysis existed was the story angle chosen.

The recommended angle was:

- “Meta built a model to predict brain-response patterns from video. The surprising part was not that it worked. The surprising part was what happened when its answer disagreed with the market.”

This choice mattered because it prevented the piece from collapsing into one of the two bad default versions.

Bad default version 1:
- “here is what TRIBE is”

Bad default version 2:
- “I tried a new Meta model and here is the result”

The chosen angle did something better:

- it made the mismatch the center
- it kept the session practical
- it gave the piece a reveal
- it made the conclusion earned instead of generic

### 5. Draft screenplay v1 from the source-grounded spine

The first screenplay draft was not trying to be final.
It was trying to prove that the story spine could hold.

Version 1 did these things correctly:

- started with normal ad-analysis logic
- introduced the strange TRIBE premise quickly
- moved into setup friction
- ran the A/B experiment
- centered the model-vs-market mismatch
- treated runtime pain as part of the ending
- avoided overclaiming

That was enough for a valid first pass.

What version 1 was **not** trying to solve yet:

- exact comedic rhythm
- beat-level shot-board pacing
- cold-open punch
- chapterized structure
- line-by-line voiceover timing

Version 1 was essentially the “does this story work as prose?” pass.

### 6. Rewrite into screenplay v2 for voice, pressure, and better line-level contrast

Version 2 was not just a polish pass.
It changed how the story sounded.

This pass did three main things.

#### A. Increased deadpan pressure

Examples:

- v1: “Which sounds either very advanced or mildly unreasonable. Possibly both.”
- v2: “Which is either impressive, concerning, or a very efficient combination of both.”

That change made the voice feel drier and less like a generic explainer.

#### B. Made the session feel more deliberately absurd without becoming jokey

Examples:

- v1 moved directly from the question into TRIBE explanation
- v2 inserted: “Because apparently just watching the ad was no longer enough.”

That line does real editorial work.
It tells the viewer how to emotionally read the premise.

#### C. Sharpened the conclusion into tool-type language

Version 2 got clearer that the real conclusion was not “good model” or “bad model.”
It was:

- this looks more like a research or interpretation layer than a winner-picker

That was an editorial classification, not a summary.

### 7. Rewrite into screenplay v3 to match beatable video structure

Version 3 was the screenplay that matched the shot-board reality.

This pass did not just improve phrasing.
It restructured the screenplay into something that could be split into scenes and beats cleanly.

This is where the pipeline moved from “screenplay” to “screenplay that can become a shot list.”

The major changes in v3 were:

- stronger cold open
- chapter-worthy scene boundaries
- clearer “why this matters now” section
- explicit guardrail section about not literal mind-reading
- more bite-sized lines that can survive as independent voiceover units
- clearer pauses and reveal moments

Version 3 is where the script stopped being only readable and became buildable.

### 8. Build the scene plan after the screenplay, not before it

The scene plan was written after the screenplay stabilized.

That order matters.

If the scene plan comes first, it tends to become a gallery of asset ideas.
That is not what it is for.

The scene plan should answer:

- what each scene is trying to make the viewer understand
- what visual job each scene must do
- what visual sourcing priority belongs there
- where local proof assets must be used
- where stock or generated assets are acceptable

For `tribe-session-001`, the scene plan became `tribe-session-001-b-roll-plan.md`.

That plan was organized by scenes like:

- Scene 1: cold open
- Scene 2: what TRIBE is
- Scene 3: why this mattered
- Scene 4: the real question
- Scene 5: setup friction
- Scene 6: experiment design
- Scene 7: guardrail
- Scene 8: model answer
- Scene 9: market answer
- Scene 10: what the mismatch means
- Scene 11: runtime reality

That is not just a production convenience.
It is proof that the screenplay had already been broken into meaningful editorial modules.

### 9. Convert the screenplay into a beat-level voiceover script before building the shot list

Before the beat-level shot board was usable, the screenplay was rewritten into a voiceover script with one audio chunk per shot row.

This intermediate step mattered because screenplay paragraphs are still too large.

The voiceover script introduced:

- one row-sized line at a time
- named shot ids like `01A`, `01B`, `01C`
- pause planning (`none`, `short`, `medium`, `long`)
- scene-by-scene structure that could be timed

Example:

- screenplay v3 line cluster:
  - “What if a model looked at a video and tried to predict brain-response patterns from it?”
  - “Because apparently just watching the ad was no longer enough.”
  - “Brain-response patterns. You know. Casually.”

became separate beat units:

- `01G` “What if a model looked at a video”
- `01H` “and tried to predict brain-response patterns from it?”
- `01I` “Because apparently just watching the ad was no longer enough.”
- `01J` “Brain-response patterns. You know. Casually.”

That is the real bridge between screenplay and shot list.

### 10. Build the shot list from the voiceover script, not from the transcript

The shot list was not made by summarizing the transcript into rows.
It was made by converting the already-structured voiceover script into beat rows.

For each shot-list row, the process was:

1. take one voiceover unit
2. assign it a shot id
3. assign it a rough duration
4. write the beat description
5. choose the background visual job
6. write movement
7. write interaction
8. write camera
9. write tone job
10. mark asset-to-find if unresolved

This is where “editorial understanding” becomes production structure.

For example, `01A` was not just “first sentence in transcript.”
It became:

- script: “Ads are everywhere now.”
- beat: ad world is saturated
- movement: layers drift and stack
- interaction: the frame should feel crowded before any analysis starts
- camera: constant small pushes
- tone job: stock ad-collage montage

That row shows why the screenplay mattered.
The shot list is not a transcript index.
It is a statement of how the narration should behave on screen.

---

## Heuristics I Actually Used

These are not abstract principles.
These are the rules that were actually applied.

### 1. Find the practical question first

If the session starts from a practical goal, that goal should anchor the story.

For `tribe-session-001`, the real opening question was not:

- what is TRIBE?

It was:

- can TRIBE say something useful about ad quality in a real workflow?

That single choice made the video much better because it gave the viewer a job immediately.

Rule:
- start from the thing that someone was trying to figure out in practice
- use the technology explanation only after the viewer has a reason to care

### 2. Treat friction as part of the story if it changes the conclusion

Not all setup pain belongs in the final story.
Only include it if it changes what the session means.

In this case, setup friction stayed because it proved:

- the workflow was not lightweight
- the tool was not production-ready
- runtime pain was part of the answer, not just an annoyance

Rule:
- keep friction if it changes the viewer’s final judgment
- cut friction if it is only “we had some trouble along the way” filler

### 3. The turning point is where the interpretation changes, not where the data appears

This is one of the most important rules.

The turning point was not:

- when TRIBE produced output

The turning point was:

- when TRIBE favored Video A, but real ROAS favored Video B

That is the moment where the viewer has to reclassify the tool.

Rule:
- the turning point is the moment that changes what the result means
- not merely the first chart, first output, or first “success” moment

### 4. Make the ending answer the opening question in a stricter form

The opening question was:

- can this help judge whether a video ad is good or bad?

The ending answer became:

- it can produce structured signals worth studying, but not signals reliable enough to trust on their own or cheap enough to use as a normal scoring layer

That matters because the ending is not a vague recap.
It is the opening question answered under pressure.

Rule:
- the ending should not just summarize events
- it should answer the session’s real starting question with more precision than the opening had

### 5. Humor should come from contrast, not punchlines

This piece worked best when the humor came from:

- very serious subject matter
- very matter-of-fact delivery
- slightly absurd implications

Examples that worked:

- “Because apparently just watching the ad was no longer enough.”
- “Brain-response patterns. You know. Casually.”
- “It was not immediately persuaded.”
- “this was less quick scoring pass, and more excellent, the rest of the day has made other plans.”

What did **not** work:

- winky internet jokes
- meme phrasing
- trying to make every section funny
- sarcasm that made the experiment sound fake or unserious

Rule:
- humor lands best when the script stays calm
- the narration should sound like it is underreacting to something inherently strange

### 6. Guardrails belong where the viewer is most likely to overinterpret

The line “TRIBE is not reading a real person’s brain” did not exist just because it was accurate.
It existed because that is exactly where a viewer would overclaim what the model is doing.

That is why v3 carved out a separate guardrail scene.

Rule:
- put anti-misunderstanding language at the exact moment the misunderstanding becomes likely
- do not save it for a footnote at the end

### 7. A screenplay is ready for shot-list conversion when the lines can survive alone

If a screenplay paragraph only works as a paragraph, it is not ready.

The shot list needs lines that can survive as separate beats.

Example:

This works as separate beats:

- “And the output was not random noise.”
- “TRIBE-style signals favored Video A.”
- “Video A showed the stronger early hook.”
- “Several target regions also leaned higher for A.”
- “If the model had been allowed to cast a confident vote, it would have had opinions.”

That section can become a scene because each line has one job.

Rule:
- if a sentence is carrying two different ideas, split it before the shot-list stage

### 8. Use outside-world context only if it strengthens the session question

The Meta timing context was added in v3, but it was bounded.
It served one purpose:

- why did this feel worth looking at right then?

It was not allowed to turn into a generic state-of-the-AI-race paragraph.

Rule:
- outside context is allowed only if it increases the stakes of the session’s actual question
- if it pulls the piece away from the session, cut it

### 9. Every beat in the shot list should answer “why this visual now?”

This is the rule that separates real shot planning from transcription.

For every shot row, there should be a reason the visual changes **now**.

Example:

`01F`:
- script: “Then we wanted to ask a much stranger question.”
- visual change reason: the frame has to pivot from familiar metrics into something that feels stranger

If there is no reason for the visual change, the row is under-specified.

### 10. Do not let proof assets take over the piece

Official proof matters.
But proof is not the story.

The official TRIBE page/model card was useful as a scene element.
It was not strong enough to carry the main scene visually.

Rule:
- use proof inserts briefly to prove reality
- use stronger concept visuals to carry the scene emotionally and editorially

---

## Three Real Editorial Decisions Between Screenplay v1, v2, and v3

These are specific changes that mattered.

### Decision 1: Change the opening from “ordinary tool explanation” to “ad-saturated world”

In v1, the opening was:

- “Most ad analysis tools do something very normal.”

That is clear, but it is not very visual and it enters as explanation.

In v3, the opening became:

- “Ads are everywhere now.”
- “Which means everybody is trying to make theirs work better.”
- “And most ad-analysis tools do something very reasonable.”
- “They look at click-through rate, watch time, conversion rate, and ROAS.”

Why this change mattered:

- it made the opening visual before it became technical
- it created a normal-world baseline
- it gave the later TRIBE premise something to interrupt
- it split the introduction into lines that could actually become separate beats

Principle this proves:
- open on a world the viewer already understands
- then introduce the strange question as a disruption of that world

### Decision 2: Insert the explicit absurdity line before the formal explanation

Version 1 moved into the TRIBE explanation relatively cleanly.
Version 2 inserted:

- “Because apparently just watching the ad was no longer enough.”

Version 3 kept it and then followed with:

- “Brain-response patterns. You know. Casually.”

Why this change mattered:

- it told the viewer how to emotionally read the premise
- it created deadpan pressure before the exposition arrived
- it made the explanation feel like a real escalation, not just documentation

Principle this proves:
- when the premise is inherently weird, name the weirdness before explaining the mechanism
- otherwise the script becomes dry too early

### Decision 3: Add a dedicated guardrail scene about not literal mind-reading

In earlier drafts, the anti-overclaim was present as a note or implication.
In v3 it became a real scene:

- “Not in a mystical way.”
- “Not in a literal mind-reading way.”
- “TRIBE is not reading a real person’s brain.”
- “It is predicting response patterns from the content of the video.”

Why this change mattered:

- it protected the piece from fake-sci-fi drift
- it kept the conclusion honest
- it created a clean reset between experiment design and model answer
- it made the later mismatch easier to trust because the piece had already drawn its own boundaries

Principle this proves:
- if a viewer is likely to overread the system’s power, install a guardrail scene before the result scene

### Decision 4: Shift the final takeaway from “interesting experiment” to “category of tool”

Version 1 already implied that TRIBE was more useful as a research layer than a winner picker.
Versions 2 and 3 made that much more explicit and central.

This was not just wording.
It was a change in the kind of answer the piece offers.

Instead of ending on:
- the experiment was honest

it ended on:
- this tool belongs in a different category than the original question hoped for

Principle this proves:
- the best conclusion often classifies the tool, not merely reports the result

---

## Quality Tests: How I Knew The Screenplay Was Ready

The screenplay was ready when it passed all of these tests.

### 1. Source-grounded test

Could every important claim be traced back to the source package?

For this session, that meant:

- no invented setup details
- no fake screenshots treated as evidence
- no hype language about TRIBE reading brains
- no invented business metrics

If a line felt good but could not be defended from source, it had to go.

### 2. Story-shape test

Did the piece actually have this shape?

- practical question
- friction
- experiment
- turning point mismatch
- interpretation
- operational conclusion

If one of those stages was missing, the piece tended to flatten into either summary or explainer mode.

### 3. Turning-point clarity test

Was the mismatch clearly the center of gravity?

If the viewer could finish the piece and still think the main point was “Meta made a weird model,” the script was not ready.

The viewer should come away with:

- the useful part was the disagreement between model reward and market reward

### 4. Beatability test

Could the script be broken into separate lines without destroying the logic?

This is the bridge to the shot list.

If too many lines required the neighboring sentence to make sense, the piece was still in essay form and needed another pass.

### 5. Visualability test

Could each major section imply a clear visual job?

Examples:

- ad-saturated world
- ordinary metrics world
- TRIBE premise world
- setup friction / terminal / auth pain
- experiment-design explainer
- model answer
- market answer
- runtime reality

If a section had no obvious visual job, it was usually too abstract and needed rewriting.

### 6. Tone-control test

Was the piece dry without becoming smug?

The deadpan tone had to do three things at once:

- keep the subject serious
- let the absurdity land
- avoid sounding like the script was mocking the work

If the humor made the whole experiment feel unserious, that version had to be rejected.

### 7. Ending-answer test

Did the ending answer the opening question more precisely than the opening asked it?

If the ending was just:
- this was interesting

it failed.

If the ending said:
- useful signals, wrong category, too heavy operationally

it passed.

---

## What Would Have Made Me Reject The Screenplay

Any of these would have been rejection-level failures.

- The piece opens by explaining TRIBE before establishing the practical reason to care.
- The mismatch between TRIBE’s preference and market outcome is not the main reveal.
- The script implies literal mind-reading.
- The script sounds like a hype video for Meta research.
- The script becomes too dependent on screenshots that do not actually exist.
- The humor becomes internet-jokey instead of deadpan.
- The ending does not answer the opening question directly.
- The lines are too long and essay-like to survive conversion into beat-level narration.
- The piece contains scene paragraphs that cannot be assigned a clear visual job.

---

## Things I Tried, Or Nearly Tried, That Did Not Work

These false starts matter because future agents will naturally drift toward them again.

### 1. The generic “what is TRIBE?” explainer opening

This is the most tempting bad version.

It sounds reasonable because the tool is unfamiliar.
But it weakens the story because it starts from explanation instead of stakes.

Why it failed:
- it made the piece about the model instead of the workflow question
- it removed pressure from the first minute
- it delayed the viewer’s reason to care

### 2. Treating setup pain as just a comedy section

The setup friction was funny in places, but keeping it only for comic relief would have been wrong.

Why it failed:
- the friction actually changed the conclusion
- runtime pain and environment pain were part of the answer
- reducing them to “funny failure montage” would have weakened the operational takeaway

### 3. Letting outside Meta / AI-race context take over the piece

There was a real temptation to build a broader “where Meta sits in AI” section.

Some of that context was useful.
Too much of it pulled the piece away from the actual session.

Why it failed:
- the story stopped being about a real test and became industry commentary
- it delayed the experiment itself

### 4. Writing paragraphs that sound good but cannot be shot

Some screenplay prose can sound polished but collapses when converted into beats.

Why it failed:
- it created rows that had no clear visual change
- it forced too much information into single lines
- it made pacing control much harder later

### 5. Relying on missing screenshots

The package contained many missing screenshot references.

Why it failed:
- the visuals were not actually available
- building the story around them would have made the piece fragile and fake-specific
- the solution had to be concept visuals, official proof inserts, diagrams, and reconstructed explainer assets instead

### 6. Treating the result as a clean victory or a clean failure

Both of those were weaker than the actual truth.

Bad version A:
- the model worked, amazing

Bad version B:
- the model was wrong, useless

Why both failed:
- both destroy the real value of the mismatch
- both flatten the tool into a binary judgment the session did not earn

---

## Rules I Wish The Original Spec Had Said Explicitly

These are the taste decisions that were applied in practice and should now be treated as explicit rules.

### 1. The first draft after the transcript should be a source analysis, not a screenplay

Do not go raw package -> screenplay.

Always do:
- raw package -> source analysis -> screenplay

Without the source analysis step, the turning point is too easy to miss.

### 2. The story angle must be chosen before draft v1

A screenplay should not begin as open-ended paraphrase.
It needs a declared story angle.

For example:
- “the surprising part was not that it worked, but what happened when it disagreed with the market”

That angle should exist before prose drafting begins.

### 3. The turning point must be named explicitly in analysis docs

Do not assume it will remain obvious later.
Write it down.

If the source analysis does not name the strongest turn in a sentence, the screenplay will drift.

### 4. Humor must come from underreaction

The system should explicitly say:

- do not write jokes first
- write the sentence straight
- let the absurdity create the humor

### 5. The screenplay is not ready until it can be split into beat-sized lines

This should be a formal gate, not a vague preference.

If the screenplay still behaves like an essay, it is not ready for scene plan or shot list.

### 6. Every scene needs a visual job before shot-listing begins

Not a visual asset.
A visual job.

Examples:
- saturate the world with ads
- re-establish ordinary metrics logic
- introduce the weird TRIBE premise
- cancel the chatbot frame
- show the experiment variables clearly
- prove the mismatch

### 7. Guardrails should be treated as story beats, not cleanup notes

If the subject invites a predictable misunderstanding, put the correction into the main structure.
Do not hide it in notes or rely on the narrator’s tone to fix it.

### 8. The ending should classify the tool, not merely review the experiment

The strongest endings answer:
- what kind of thing is this actually?

That is better than simply repeating the results.

---

## The Short Version To Remember

The actual method was:

1. stabilize the package
2. read for the practical question, not for summary points
3. write source analysis first
4. identify the strongest turning point
5. choose the story angle
6. write screenplay v1 around the spine
7. rewrite for voice and pressure
8. rewrite again for beatability and scene structure
9. build the scene plan from the stabilized screenplay
10. build the voiceover script from the screenplay
11. build the shot list from the voiceover script

The main rule underneath all of it:

Do not confuse “what happened in the session” with “what the story is.”

The raw package tells you what happened.
The editorial work is deciding what the session **means**, and then writing only enough of the session to prove that meaning.
