# -*- coding: utf-8 -*-
"""quarantine_leads.py -- a watcher lead holds its OWN row, never the whole site (audit 2026-10-03, Tier 1.1/1.2).

WHY
From 2026-09-27 23:32 UTC to 2026-10-03, 17 consecutive scheduled runs (#222-#238) failed because
the four watchers (Drugs@FDA, drug pages, FDA "What's New: Drugs", sponsor news feeds) each exited 1
on an unreviewed lead. One real lead (JUVMO) and three false ones froze EVERY page: conference
statuses said "In progress" after the meeting ended, the home and /calendar stamps sat on 09-27, and
17 identical issues were opened that nobody read. The rule that a lead is never auto-published was
right. Freezing the whole site to enforce it was not.

NOW
  * each watcher still prints its leads, and also writes them (one JSON line each) to the file named by
    $WATCH_LEADS_JSONL; in CI the watcher steps no longer fail the job;
  * `quarantine_leads.py collect` reads that file after the watchers ran, keeps _held_state.json
    (held_since, consecutive held runs, the leads with first_seen), opens ONE issue per new lead (not
    one per run), and after the 2nd consecutive held run sends ONE email (Tier 1.2);
  * `quarantine_leads.py apply` runs after every page is built and before the guards: for each held
    row it restores, from the last commit, that row in the API dataset and the pages that render only
    that row (its event page, its ticker hub, its drug page). Everything else rebuilds and deploys.
    It also writes held_since and held_leads into /build-info.json.

A held row stays exactly as last published until someone verifies the lead and publishes (or acks).
Never publishes an outcome by itself. Facts only; not investment advice. Times are UTC (RULE 1).

    python quarantine_leads.py collect [--leads F] [--state F] [--now ISO] [--outbox F] [--no-issue]
    python quarantine_leads.py apply   [--state F] [--dry-run]
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import re
import smtplib
import subprocess
import sys
from email.message import EmailMessage

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "pdufa_site_src")
sys.path.insert(0, HERE)
import badge_decision_provenance  # noqa: E402
import inject_a11y  # noqa: E402
import inject_mobile_polish  # noqa: E402
STATE = os.path.join(HERE, "_held_state.json")
LEADS = os.environ.get("WATCH_LEADS_JSONL") or os.path.join(HERE, "_watch_leads.jsonl")
DATASET = os.path.join(SITE, "api", "v1", "dataset.mjs")
ESCALATE_AFTER = 2          # held runs before David is emailed
DEFAULT_TO = "rockyshoals@gmail.com"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def emit(source, row_id, key, text):
    """Called by a watcher for each unreviewed lead. Appends one JSON line to $WATCH_LEADS_JSONL."""
    path = os.environ.get("WATCH_LEADS_JSONL")
    if not path:
        return
    with io.open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"source": source, "row_id": row_id, "key": key, "text": str(text)[:400]},
                           ensure_ascii=False) + "\n")


def read_leads(path):
    out, seen = [], set()
    if not os.path.exists(path):
        return out
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        k = (o.get("source"), o.get("key"))
        if k not in seen:
            seen.add(k)
            out.append(o)
    return out


def load_state(path):
    if os.path.exists(path):
        try:
            return json.load(io.open(path, encoding="utf-8"))
        except ValueError:
            pass
    return {"held_since": None, "consecutive_held_runs": 0, "emailed_at": None, "leads": [],
            "issued_keys": [], "last_clear_run": None}


def step(state, leads, now):
    """One CI run. Returns (state, actions) where actions lists 'issue:<key>' and 'email'."""
    actions = []
    if not leads:
        if state.get("held_since"):
            state["last_clear_run"] = now
        state.update({"held_since": None, "consecutive_held_runs": 0, "emailed_at": None, "leads": []})
        return state, actions
    prev = {(l["source"], l["key"]): l for l in state.get("leads", [])}
    cur = []
    for l in leads:
        k = (l["source"], l["key"])
        first = prev.get(k, {}).get("first_seen") or now
        cur.append({**l, "first_seen": first})
    state["leads"] = cur
    state["held_since"] = state.get("held_since") or now
    state["consecutive_held_runs"] = int(state.get("consecutive_held_runs") or 0) + 1
    issued = set(state.get("issued_keys") or [])
    for l in cur:
        ik = f"{l['source']}|{l['key']}"
        if ik not in issued:
            actions.append("issue:" + ik)
            issued.add(ik)
    state["issued_keys"] = sorted(issued)[-200:]
    if state["consecutive_held_runs"] >= ESCALATE_AFTER and not state.get("emailed_at"):
        actions.append("email")
        state["emailed_at"] = now
    return state, actions


def email_body(state):
    lines = [f"pdufa.bio: {len(state['leads'])} watcher lead(s) have held their rows since "
             f"{state['held_since']} (UTC), {state['consecutive_held_runs']} consecutive runs.",
             "", "The rest of the site is still rebuilding and deploying; only these rows are frozen "
             "until each lead is verified and published, or acked with a reason.", ""]
    for l in state["leads"]:
        lines.append(f"- [{l['source']}] {l['row_id']}: {l['text']}")
        lines.append(f"  ack key: {l['key']}  (first seen {l['first_seen']})")
    lines += ["", "Actions: https://github.com/rockyshoals-lgtm/pdufa-bio/actions/workflows/pdufa-rebuild.yml",
              "Facts only; not investment advice."]
    return "\n".join(lines)


def send_email(state, outbox=None):
    subj = f"pdufa.bio: {len(state['leads'])} lead(s) holding rows since {state['held_since']}"
    body = email_body(state)
    if outbox:
        with io.open(outbox, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"subject": subj, "body": body}) + "\n")
        return "outbox"
    host, user, pw = os.environ.get("SMTP_HOST"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS")
    to = os.environ.get("ALERT_TO") or DEFAULT_TO
    if host and user and pw:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subj, os.environ.get("SMTP_FROM") or user, to
        msg.set_content(body)
        try:
            with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT") or 587), timeout=30) as s:
                s.starttls()
                s.login(user, pw)
                s.send_message(msg)
            return "sent"
        except Exception as e:  # noqa: BLE001
            print(f"::warning::escalation email failed: {e}")
    # Fallback: an issue that @-mentions the owner. GitHub emails a mentioned user by default.
    # 2026-10-15: ONE per held episode. emailed_at lives in _held_state.json, which is only committed when the
    # run passes; six failing runs on 10-15 each opened a new "ESCALATION" issue (#25 to #30) for the same
    # episode. GitHub is the record that survives a failed run, so ask it first.
    try:
        out = subprocess.run(["gh", "issue", "list", "--state", "open", "--search", f"in:title \"{subj}\"",
                              "--json", "title"], capture_output=True, text=True, timeout=60).stdout
        if any(i.get("title") == "ESCALATION: " + subj for i in json.loads(out or "[]")):
            print("   escalation issue for this held episode already open; not opening another")
            return "mention-issue (already open)"
    except Exception:  # noqa: BLE001
        pass
    try:
        try:  # audit 2026-11-09 §5 item 2: the live build's age belongs on every escalation
            from blocked_issue import since_last_deploy
            age = since_last_deploy()
        except Exception:  # noqa: BLE001
            age = "Days since last green deploy: unavailable."
        subprocess.run(["gh", "issue", "create", "--title", "ESCALATION: " + subj,
                        "--body", f"@rockyshoals-lgtm\n\n**{age}**\n\n" + body], check=True, timeout=60)
        print("::warning::SMTP_HOST/SMTP_USER/SMTP_PASS secrets not set: escalated by @-mention issue instead")
        return "mention-issue"
    except Exception as e:  # noqa: BLE001
        print(f"::warning::escalation could not be delivered ({e})")
        return "undelivered"


def raise_issue(lead):
    body = (f"**One row is held, the rest of the site deploys.** `{lead['source']}` reported a lead on "
            f"`{lead['row_id']}`:\n\n```\n{lead['text']}\n```\n\nVerify it against the primary source, then "
            f"publish the decision page or ack it with a reason. ack key: `{lead['key']}`\n\n"
            f"This issue is opened once per lead, not once per run.")
    title = f"HELD: {lead['row_id']} ({lead['source']}) lead to verify"
    # 2026-11-01: #55, #56 and #57 are one AZN lead opened three times. issued_keys lives in _held_state.json,
    # which is committed only when a run passes, so every FAILING run forgot it had already opened the issue
    # (the same shape as the 10-15 ESCALATION duplicates). GitHub is the record that survives a failed run.
    try:
        # 2026-11-26: --state all. The 15-minute news watch (news-watch.yml) reports a lead every run while its
        # release is in the window; an issue a reviewer closed must not reopen 15 minutes later.
        out = subprocess.run(["gh", "issue", "list", "--state", "all", "--search", f"in:title \"{title}\"",
                              "--json", "title,body"], capture_output=True, text=True, timeout=60).stdout
        if any(i.get("title") == title and lead["key"] in (i.get("body") or "") for i in json.loads(out or "[]")):
            print(f"   issue for this lead already opened; not opening another ({title})")
            return
    except Exception:  # noqa: BLE001
        pass
    try:
        subprocess.run(["gh", "issue", "create", "--title", title, "--body", body],
                       check=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"   (issue create skipped: {e})")


ACK_FILES = ("_drug_watch_ack.json", "_fda_drugs_feed_ack.json", "_newswire_ack.json", "_fda_watch_ack.json",
             "_edgar_8k_ack.json", "_fmp_press_ack.json")   # 2026-11-26: 8-K and press-release leads close too


def acked_keys(here=HERE):
    """Every ack key on file, in the form the HELD issue prints ("ack key: `...`"). drug_pages keys are
    "{slug}|{source}", fda_drugs_feed and sponsor_feed keys are the strings in "acked", drugs_at_fda keys are
    "{ticker}|{ap_date}". A key that is in none of these stays open: the safe direction."""
    keys = set()
    for f in ACK_FILES:
        p = os.path.join(here, f)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            continue
        for k in d.get("acked") or []:
            if isinstance(k, str):
                keys.add(k)
        for x in d.get("acks") or []:
            if not isinstance(x, dict):
                continue
            if x.get("slug") and x.get("source"):
                keys.add(f"{x['slug']}|{x['source']}")
            if x.get("ticker") and x.get("ap_date"):
                keys.add(f"{x['ticker']}|{x['ap_date']}")
    return keys


ACK_KEY = re.compile(r"ack key:\s*`?([^`\n]+?)`?\s*(?:\(first seen|$)", re.M)


def resolved_issues(issues, acked):
    """(number, why) for each open HELD / ESCALATION issue whose every ack key is now acked.

    2026-11-18 (David: "we are getting more blocked notices from github"): #93, #94, #97, #101 and #105 stayed open
    for a day after their leads were published and acked, because nothing closed them. Closing keys only on the ack
    files, never on "the lead did not appear this run": a watcher that failed to fetch also reports no leads, and
    closing on that would hide a real one (issued_keys would then stop it reopening)."""
    out = []
    for i in issues:
        t = str(i.get("title") or "")
        if not (t.startswith("HELD: ") or t.startswith("ESCALATION: pdufa.bio")):
            continue
        body = i.get("body") or ""
        keys = [k.strip() for k in ACK_KEY.findall(body)]
        # a key line the pattern cannot read (a backtick in a title-only newswire key) must keep the issue open,
        # never be skipped: closing on the keys we could read would close an issue that still has a live lead
        if len(keys) != len(re.findall(r"ack key:", body)):
            continue
        if keys and all(k in acked for k in keys):
            out.append((i["number"], f"every lead it names is acked on main ({len(keys)} key(s))"))
    return out


def close_resolved():
    try:
        out = subprocess.run(["gh", "issue", "list", "--state", "open", "--limit", "100", "--json",
                              "number,title,body"], capture_output=True, text=True, timeout=60).stdout
        issues = json.loads(out or "[]")
    except Exception as e:  # noqa: BLE001
        print(f"   (resolved-issue sweep skipped: {e})")
        return
    run = os.environ.get("GITHUB_RUN_ID", "local")
    for n, why in resolved_issues(issues, acked_keys()):
        try:
            subprocess.run(["gh", "issue", "close", str(n), "--comment",
                            f"Resolved: {why}. Closed by run {run}."], check=True, timeout=60)
            print(f"   closed #{n}: {why}")
        except Exception as e:  # noqa: BLE001
            print(f"   (could not close #{n}: {e})")


def cmd_collect(a):
    leads = read_leads(a.leads)
    state = load_state(a.state)
    state, actions = step(state, leads, a.now or utcnow())
    if leads:
        print(f"QUARANTINE: {len(leads)} lead(s) hold their rows (held since {state['held_since']} UTC, "
              f"{state['consecutive_held_runs']} consecutive run(s)); every other page rebuilds and deploys:")
        for l in leads:
            print(f"   [{l['source']}] {l['row_id']}  {l['text'][:160]}")
            print(f"      ack key: {l['key']}")
    else:
        print("quarantine: 0 leads this run; nothing held")
    for act in actions:
        if act.startswith("issue:") and not a.no_issue:
            ik = act[6:]
            raise_issue(next(l for l in state["leads"] if f"{l['source']}|{l['key']}" == ik))
        elif act == "email" and getattr(a, "no_escalate", False):
            print("   (escalation is the rebuild's; this run only opens issues)")
        elif act == "email":
            how = send_email(state, a.outbox)
            state["email_status"] = how
            print(f"ESCALATION: {state['consecutive_held_runs']} consecutive held runs -> email ({how})")
    io.open(a.state, "w", encoding="utf-8", newline="\n").write(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    if not a.no_issue:
        close_resolved()   # 2026-11-18: HELD/ESCALATION issues whose leads are all acked close themselves
    return 0


def _git_show(path):
    rel = os.path.relpath(path, HERE).replace("\\", "/")
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=HERE, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def _load_event_links():
    """(fn(doc, rel) -> doc with retarget_event_links.py applied, the set of redirected /pdufa/ URLs); (None, set())
    if the pass cannot load, so a hold is never blocked by it."""
    try:
        import retarget_event_links as RL
        tg = RL.targets()
        return (lambda doc, rel: RL.apply(doc, rel, tg)), set(tg)
    except Exception as ex:  # noqa: BLE001
        print(f"  note: event-link pass unavailable for restored pages ({ex.__class__.__name__})")
        return None, set()


def held_paths(row, slug_hint=None):
    """The pages that render ONLY this row (shared pages keep rebuilding)."""
    out = []
    u = str(row.get("url") or "")
    if u.startswith("/pdufa/"):
        out.append(os.path.join(SITE, u.strip("/"), "index.html"))
    t = str(row.get("t") or "")
    if t:
        out.append(os.path.join(SITE, "ticker", t, "index.html"))
    if slug_hint:
        out.append(os.path.join(SITE, "drug", slug_hint, "index.html"))
    return out


def restore_rows(dataset_text, head_text, row_ids):
    """Replace each held row in the working dataset by its last-committed version."""
    i, j = dataset_text.index("["), dataset_text.rindex("]") + 1
    rows = json.loads(dataset_text[i:j].replace("\x00", ""))
    hi, hj = head_text.index("["), head_text.rindex("]") + 1
    head = {r["id"]: r for r in json.loads(head_text[hi:hj].replace("\x00", ""))}
    n = 0
    for k, r in enumerate(rows):
        if r.get("id") in row_ids and r["id"] in head and head[r["id"]] != r:
            rows[k] = head[r["id"]]
            n += 1
    return dataset_text[:i] + json.dumps(rows, indent=1, ensure_ascii=False) + dataset_text[j:], n


def cmd_apply(a):
    state = load_state(a.state)
    leads = state.get("leads") or []
    held_ids = sorted({l["row_id"] for l in leads if l.get("row_id")})
    # build-info: held_since + held_leads, every run (null / [] when clear)
    hl = [{"row_id": l["row_id"], "source": l["source"], "first_seen": l["first_seen"]} for l in leads]
    for p in (os.path.join(SITE, "build-info.json"), os.path.join(SITE, "api", "_build-info.json")):
        if os.path.exists(p):
            bi = json.load(io.open(p, encoding="utf-8"))
            bi["held_since"] = state.get("held_since")
            bi["held_leads"] = hl
            if not a.dry_run:
                io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(bi, indent=1) + "\n")
    if not held_ids:
        print("quarantine apply: nothing held; build-info held_since=null")
        return 0
    src = io.open(DATASET, encoding="utf-8", errors="replace").read()
    head = _git_show(DATASET)
    rows = {r["id"]: r for r in json.loads(src[src.index("["):src.rindex("]") + 1].replace("\x00", ""))}
    restored = []
    if head:
        new, n = restore_rows(src, head, set(held_ids))
        if n and not a.dry_run:
            io.open(DATASET, "w", encoding="utf-8").write(new)
            # 2026-11-18 (design change 12): the homepage's "Data through" date reads calendar_updates from
            # build-info.json, which build_freshness_stamp.py wrote from the dataset before this step put the held
            # rows back; recompute it from the restored rows so the page and tests/test_accessibility.py agree.
            try:
                import build_freshness_stamp as _F
                cu = _F.calendar_updates()
                for p in (os.path.join(SITE, "build-info.json"), os.path.join(SITE, "api", "_build-info.json")):
                    if os.path.exists(p):
                        bi = json.load(io.open(p, encoding="utf-8"))
                        if "calendar_updates" in bi:
                            bi["calendar_updates"] = cu
                            io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(bi, indent=1) + "\n")
            except Exception as ex:  # noqa: BLE001
                print(f"  note: calendar_updates not refreshed after the restore ({ex.__class__.__name__}: {ex})")
        restored.append(f"dataset rows x{n}")
    _event_links = None
    for rid in held_ids:
        slug = rid[5:] if rid.startswith("drug:") else None
        row = rows.get(rid) or {}
        for p in held_paths(row, slug):
            old = _git_show(p)
            if old is None:
                continue
            # 2026-11-18 (design change 4): a bare /pdufa/{T} page this build retired into a redirect to the event's
            # own page stays retired (vercel.json sends it there); and a restored page's event links go straight to
            # the event's own page, as retarget_event_links.py makes every other page's.
            rel = os.path.relpath(p, SITE).replace("\\", "/")
            url = "/" + rel[:-len("/index.html")] if rel.endswith("/index.html") else None
            if _event_links is None:
                _event_links = _load_event_links()
            if url and not os.path.exists(p) and url in _event_links[1]:
                continue
            if _event_links[0]:
                old = _event_links[0](old, rel)
            # 2026-11-18 (change 5): the committed page may predate this build's provenance badges; give it the
            # badges the rest of the site carries, or tests/test_provenance_badges.py would block the deploy
            if p.endswith(".html"):
                old = badge_decision_provenance.apply(old)
            # 2026-11-18 (change 11 red team): a held page's committed copy can predate a site-wide chrome pass. The
            # fonts, type rules and logo mark (inject_site_type.py) are re-added, so tests/test_one_look.py does not
            # block every deploy while a row is held; build_sitemap strips them from the content hash, so the held
            # page's lastmod is unchanged.
            if p.endswith(".html"):
                import inject_site_type
                if inject_site_type.public(p, old):
                    old = inject_site_type.apply(old)[0]
            if p.endswith(".html") and url:
                # 2026-11-26: the committed copy can predate the Browse pdufa.bio footer's current layout (run 540
                # put the old dotted row back on two Vertex pages and tests/test_browse_footer.py blocked the
                # deploy). The block is marker-bounded and site-wide, not the held row's, so it is placed again;
                # build_sitemap strips it from the content hash, so the held page's lastmod is unchanged.
                import inject_site_links
                old = inject_site_links.refresh_browse(old, url)
            if p.endswith(".html"):  # after the badges and the site type, as in the build
                # a page committed before the accessibility pass gets it too (named charts first, then the phone
                # copies that carry their names), or the page it restores would fail tests/test_accessibility.py
                old = inject_mobile_polish.apply(inject_a11y.apply(old))[0]
            cur = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
            if cur != old:
                if not a.dry_run:
                    # 2026-10-17: the rebuild had removed /drug/phentolamine-ophthalmic (a separate bug) and this
                    # write raised FileNotFoundError, aborting the step. A held page is restored, directory and all.
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    io.open(p, "w", encoding="utf-8", newline="").write(old)
                restored.append(os.path.relpath(p, SITE).replace("\\", "/"))
    # 2026-10-15: a restored page must keep its committed content-change date too. Six scheduled runs on
    # 10-15 (14:35 to 23:38 UTC) failed test_datemodified_honest while the Anktiva lead was held: build_sitemap
    # had recorded the freshly built ticker/IBRX page as changed on 10-15, then this step put back the committed
    # page, whose schema says 10-14. A held row was meant to freeze one row and let the site deploy; it froze
    # every deploy. Restore the page's _sitemap_lastmod.json entry and its sitemap <lastmod> with it.
    # 2026-11-18 (design change 4): a restored /ticker/{T} hub or event page comes from the last commit, which may
    # predate the dossier's move to the event page (build_retail_pages.py decision 4); both would then disagree with
    # the profile, and tests/test_one_event_one_page.py would block the deploy over a page the hold only froze. The
    # dossier block is marker-bounded and comes from retail_profiles/, not from the held row, so it is placed again.
    moved = set()
    for rel in restored:
        m = re.match(r"^ticker/([A-Z][A-Z0-9.]{0,6})/index\.html$", rel)
        if m:
            moved.add(m.group(1))
        for pf in glob.glob(os.path.join(HERE, "retail_profiles", "*.json")):
            try:
                ev = str(json.load(io.open(pf, encoding="utf-8")).get("event_page") or "").strip("/")
            except Exception:  # noqa: BLE001
                continue
            if ev and rel == ev + "/index.html":
                moved.add(os.path.splitext(os.path.basename(pf))[0])
    for t in sorted(moved):
        if os.path.exists(os.path.join(HERE, "retail_profiles", f"{t}.json")) and not a.dry_run:
            r = subprocess.run([sys.executable, "build_retail_pages.py", "--ticker", t], cwd=HERE,
                               capture_output=True, text=True)
            print(f"  {t}: dossier placed again on the restored pages (build_retail_pages.py exit {r.returncode})")
    pages = [r for r in restored if r.endswith(".html")]
    if pages and not a.dry_run:
        stf = os.path.join(HERE, "_sitemap_lastmod.json")
        head_state = _git_show(stf)
        if head_state and os.path.exists(stf):
            st, hst = json.load(io.open(stf, encoding="utf-8")), json.loads(head_state)
            for rel in pages:
                k = "pdufa_site_src/" + rel
                if k in hst:
                    st[k] = hst[k]
                else:
                    st.pop(k, None)
            io.open(stf, "w", encoding="utf-8").write(json.dumps(st, indent=0, sort_keys=True))
        # 2026-11-20: the section sitemaps (sitemap-*.xml, listed in sitemap_index.xml) carry the same <lastmod>,
        # so restore it there too or they claim today's date for a held page. The committed sitemap.xml is the
        # reference for all of them (a section file may not be committed yet).
        head_sm = _git_show(os.path.join(SITE, "sitemap.xml"))
        for smf in [os.path.join(SITE, "sitemap.xml")] + sorted(glob.glob(os.path.join(SITE, "sitemap-*.xml"))):
            if not (head_sm and os.path.exists(smf)):
                continue
            sm = io.open(smf, encoding="utf-8").read()
            for rel in pages:
                url = "https://www.pdufa.bio/" + rel[:-len("index.html")].rstrip("/")
                pat = re.compile(r"(<loc>" + re.escape(url) + r"</loc>\s*<lastmod>)([^<]+)(</lastmod>)")
                hm = pat.search(head_sm)
                if hm:
                    sm = pat.sub(lambda m: m.group(1) + hm.group(2) + m.group(3), sm, count=1)
            io.open(smf, "w", encoding="utf-8").write(sm)
        print(f"   kept the committed content-change date for {len(pages)} restored page(s)")
    print(f"quarantine apply: holding {', '.join(held_ids)} at the last commit; restored {restored or 'nothing (unchanged)'}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--leads", default=LEADS)
    c.add_argument("--state", default=STATE)
    c.add_argument("--now")
    c.add_argument("--outbox")
    c.add_argument("--no-issue", action="store_true")
    c.add_argument("--no-escalate", action="store_true",
                   help="open HELD issues but never send the escalation email (news-watch.yml; the rebuild escalates)")
    p = sub.add_parser("apply")
    p.add_argument("--state", default=STATE)
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return cmd_collect(a) if a.cmd == "collect" else cmd_apply(a)


if __name__ == "__main__":
    sys.exit(main())
