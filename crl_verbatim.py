# -*- coding: utf-8 -*-
"""Text the copy fixers and copy guards leave alone, because it is quoted as recorded, not written as house copy.

  * The FDA's own words on /crl/letter pages (build_crl_letters.py). Only a page under /crl/letter/ may carry the
    verbatim block, and only once; anywhere else the block is house copy and every fixer and guard reads it as such
    (tests/test_crl_letters.py fails a block found on any other page).
  * The record table on /changes (build_row_history.py): each Was and Now cell is a dataset value exactly as a public
    commit held it, so a fixer that rewrote one would misstate the commit. Only /changes/index.html is exempt;
    tests/test_row_history.py checks every cell of that table against the ledger and the page's own words outside it.
"""
import re

TAG = '<blockquote class="crl-text" data-verbatim="fda">'
VERBATIM_RE = re.compile(re.escape(TAG) + r".*?</blockquote>", re.S)


def is_letter_page(path):
    p = str(path or "").replace("\\", "/")
    return "/crl/letter/" in p and p.endswith("/index.html")


RECORD_TAG = '<table data-changes="recent" data-verbatim="record">'
RECORD_RE = re.compile(re.escape(RECORD_TAG) + r".*?</table>", re.S)


def is_record_page(path):
    p = "/" + str(path or "").replace("\\", "/").lstrip("/")
    return p.endswith("/changes/index.html") and not p.endswith("-changes/index.html")


def strip_verbatim(doc, path, repl=" "):
    """doc with the quoted block replaced by repl (or by repl(match) when callable): the FDA's verbatim block on a
    letter page, the record table on /changes; any other page is returned as it is."""
    if is_letter_page(path):
        return VERBATIM_RE.sub(repl, doc)
    if is_record_page(path):
        return RECORD_RE.sub(repl, doc)
    return doc
