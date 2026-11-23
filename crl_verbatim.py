# -*- coding: utf-8 -*-
"""The FDA's own words on /crl/letter pages (build_crl_letters.py), which the copy fixers and copy guards leave alone.

Only a page under /crl/letter/ may carry the verbatim block, and only once; anywhere else the block is house copy and
every fixer and guard reads it as such (tests/test_crl_letters.py fails a block found on any other page).
"""
import re

TAG = '<blockquote class="crl-text" data-verbatim="fda">'
VERBATIM_RE = re.compile(re.escape(TAG) + r".*?</blockquote>", re.S)


def is_letter_page(path):
    p = str(path or "").replace("\\", "/")
    return "/crl/letter/" in p and p.endswith("/index.html")


def strip_verbatim(doc, path, repl=" "):
    """doc with the FDA's verbatim block replaced by repl (or by repl(match) when callable), on a letter page only."""
    return VERBATIM_RE.sub(repl, doc) if is_letter_page(path) else doc
