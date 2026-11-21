# -*- coding: utf-8 -*-
"""text_hygiene.py -- one place for "the same words twice in a row" in names we compose.

2026-11-20 (live check): /ticker/TARS read "TP-04 Kore Phase 2 Phase 2 topline". The readout mine's row names
were built as program + trial + readout ("TP-04" + "Kore Phase 2" + "Phase 2 topline"), and the only check was
"is the readout already inside the name", which a shared phrase at the seam passes. 60 guided-readout names on
the API dataset carried the stutter ("Phase 3 Phase 3", "Part A Part A", "VK2735 VK2735", ...), and every page
built from the dataset (ticker pages, condition hubs, the screener, /readouts, the calendar feed, search) showed it.

    join_phrases(["TP-04", "Kore Phase 2", "Phase 2 topline"])  -> "TP-04 Kore Phase 2 topline"
    collapse_repeats("lanifibranor NATiV3 Phase 3 Phase 3 topline") -> "lanifibranor NATiV3 Phase 3 topline"
    find_repeat(text) -> the first repeated phrase, or None (used by tests/test_no_repeated_phrases.py)

A "phrase" is 1-6 whitespace-separated words, compared case-insensitively with trailing punctuation ignored, and it
must contain a letter: "1 1" or "2026 2026" are numbers, not a stutter, and are left alone.
"""
import re

MAX_WORDS = 6
_TRAIL = ",;:.!?\u2026"


def _key(tok):
    return tok.rstrip(_TRAIL).lower()


def _has_letter(toks):
    return any(re.search(r"[A-Za-z]", t) for t in toks)


def _repeat_at(toks, i):
    """Length n of a phrase starting at toks[i] that is immediately repeated, longest first; 0 if none."""
    for n in range(min(MAX_WORDS, (len(toks) - i) // 2), 0, -1):
        a, b = toks[i:i + n], toks[i + n:i + 2 * n]
        # Only the last word of the first copy may carry punctuation that the second copy lacks; a comma
        # inside the first copy ("Part 2, Part 2") is a list, not a stutter.
        if any(t.endswith(tuple(_TRAIL)) for t in a[:-1]):
            continue
        if a[-1].endswith(tuple(_TRAIL)):
            continue
        if [_key(t) for t in a] == [_key(t) for t in b] and _has_letter(a):
            return n
    return 0


def find_repeat(text):
    """The first adjacent repeated phrase in text (as written, both copies), or None."""
    toks = str(text or "").split()
    for i in range(len(toks)):
        n = _repeat_at(toks, i)
        if n:
            return " ".join(toks[i:i + 2 * n])
    return None


def collapse_repeats(text):
    """Drop the second copy of any adjacent repeated phrase. Keeps the first copy's spelling and the second
    copy's trailing punctuation. Whitespace is normalised to single spaces."""
    toks = str(text or "").split()
    out = []
    i = 0
    while i < len(toks):
        n = _repeat_at(toks, i)
        if n:
            first = toks[i:i + n]
            tail = toks[i + 2 * n - 1]
            punct = tail[len(tail.rstrip(_TRAIL)):]
            first[-1] = first[-1] + punct
            toks = toks[:i] + first + toks[i + 2 * n:]
            continue  # the same position may repeat again ("Phase 2 Phase 2 Phase 2")
        out.append(toks[i])
        i += 1
    return " ".join(out)


def join_phrases(parts):
    """Join name parts with spaces, merging any overlap at each seam: when the next part starts with the words
    the name so far ends with, those words are written once. Then collapse any remaining stutter."""
    name = []
    for p in parts:
        toks = str(p or "").split()
        if not toks:
            continue
        k = min(len(name), len(toks))
        while k and [_key(t) for t in name[-k:]] != [_key(t) for t in toks[:k]]:
            k -= 1
        name += toks[k:]
    return collapse_repeats(" ".join(name))


if __name__ == "__main__":
    for s in ["TP-04 Kore Phase 2 Phase 2 topline", "VK2735 VK2735 maintenance dosing study, Part 2 Part 2 results",
              "paxalisib Paxalisib Stage IV TNBC study", "Phase 2, Phase 2", "Q1 2026 2026", "a Phase 2 Phase 2 Phase 2 b"]:
        print(f"{s!r} -> {collapse_repeats(s)!r}  (repeat: {find_repeat(s)!r})")
    print(join_phrases(["TP-04", "Kore Phase 2", "Phase 2 topline"]))
