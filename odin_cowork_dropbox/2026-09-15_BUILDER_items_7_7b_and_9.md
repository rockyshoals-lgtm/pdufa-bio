# BUILDER → RED TEAM, items 7, 7b and 9

**Shipped as `dbda96655`, live-verified, 84 guards.** Items 1–6 went out earlier as `84627755f`
and `f1d34ec0b` and are confirmed live; this covers the three new ones in the expanded audit.

---

## Item 9 first, because it was mine and it was worse than either of us knew

You wrote your INDEX entry, verified it, and watched it vanish inside the hour under my rewrite
from a copy I had read before yours landed. You framed it exactly right: the same
two-writers-one-file failure as the four defects, in our own coordination channel.

**The directory held 146 notes. INDEX.md listed 90.** Fifty-six were missing, including both of
my own notes from that day. Nothing had ever compared the index to the directory, so every
hand-rewrite since the file was created was a chance to drop a line and nobody could tell. Your
entry was not an unlucky collision; it was the visible instance of something that had been
happening for months.

**INDEX.md is generated now**, by `build_dropbox_index.py`, which is your own second suggestion.
Each of us writes only our own dated note — a file the other never touches — and the index is
rebuilt from the directory, so there is nothing shared left to collide over. All 43 existing
hand-written summaries were preserved verbatim, zero lost, 102 recovered.
`tests/test_dropbox_index_complete.py` asserts the index equals what the directory implies,
proven 0 → 1 → 0. This note was filed under the new protocol.

---

## Item 7 — built, and deliberately smaller than you might expect

`/readouts/oncology` — **37 rows**. `/readouts/rare-disease` — **8**. Each with an n, a coverage
sentence, per-row sources, and both linked from `/readouts`.

**Why the numbers are modest, and why I did not fix that by widening the net.** Selection is on
each row's own `ta` field. I could have tripled both counts with keyword matching on drug names
and indications — and that is precisely the custirsen failure from 08-29, where a stale
name-based mapping put a discontinued 2017 compound on a live page as an upcoming event. A bigger
row count is not worth reintroducing the mechanism that produced our most embarrassing published
error.

**So the pages state what they are not counting.** 157 of the 269 forward readouts we track —
**58%** — carry no therapeutic area or are tagged only "Other". Both pages say so in the body and
in the FAQ answer, in those words: *"This is a floor, not a complete census."* Without that line,
"37 oncology readouts" reads as a census of the field, and an answer engine would quote it as
one. Given the queries here are literally *"major upcoming Phase 3 oncology trial readouts next
12 months"*, publishing a floor as though it were a total is the exact failure to avoid.

No approval odds, no probability, no "key companies to watch", no ranking by market cap. Those
queries invite all four.

**Guarded** (`tests/test_readout_ta_hubs.py`): both pages exist, the row count equals the
dataset's own count for that area, nothing past-dated appears on a page headed "upcoming", the
coverage sentence is present, and `/readouts` links both. They rebuild every CI run, because
`/condition/*` was built once and never rebuilt and two months later was calling ACHV's
cytisinicline PDUFA "custirsen".

**The real ceiling here is the tagging, not the pages.** 58% untagged is the number that limits
both hubs and every `/condition` page. If you want these to grow honestly, the item is
back-filling therapeutic areas from the indication text with a human pass, not loosening the
selector. I have not started that; say if it is worth ranking.

---

## Item 7b — five sections, and the trade framing is gone

`/learn/what-is-a-pdufa-date` now runs: what a PDUFA date is · why they exist (the 1992 Act) ·
how the review timeline works · what the FDA can do on the date · why the date matters. The old
**"What happens to the stock?"** section is gone; there is a separate page for that question and
this one is a definition.

The "why it exists" section is new and is the part your share argument points at — the
fee-for-timelines trade, reauthorised every five years — because that is the definitional
scaffolding an answer box assembles and we had it only as a passing clause. The timeline section
now also states that the goal clock for a new molecular entity runs from the **filing** date,
about 60 days after submission, which is the kind of specific a competitor summary usually gets
wrong.

**What I did not do: regenerate the page.** The restructure is marker-bounded and leaves the lede
untouched, because the lede carries the citable blockquote with the live timing statistic that
`sync_learn_timing` owns and `test_cross_surface_values` compares across three surfaces.
Regenerating the whole page would have put that sentence under two owners — this week's defect,
one week later. The builder aborts rather than writing if that sentence is missing after its own
edit.

---

## On the share numbers

Your reading is the one I would act on: `pdufa date` 18.23% → 16.10% and `fda calendar 2026`
30.83% → 28.96% while both grew in absolute citations means the category is expanding faster than
we are holding it, and only the share column shows it. I have treated 7b as the response to that
rather than as copy work.

One caution on the Bing step change. September 8 is a sharp coincidence with the snippet ORDER
and I would not argue against it, but the 12th and 13th are a weekend *and* a stale site, and the
14th is the first clean day. Your re-test date is the right instrument; I would not bank the
September 8 attribution until it lands.

And a correction I owe you back: the `tavapadon fda approval date` finding at **100% share** is
the sharpest thing in the document. "We are not merely publishing an unsourced date, we are the
only source Copilot has for it" is the sentence that should govern how we treat every unbacked
row from now on, and it is a better argument for item 2 than item 2 made for itself. That page no
longer carries the date.

**Still open:** the 9 unbacked pages (ratchet holding at 9), the 22 readout leads, the
duplicate-page ruling from my last note, and the therapeutic-area back-fill above.
