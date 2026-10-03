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
    try:
        subprocess.run(["gh", "issue", "create", "--title", "ESCALATION: " + subj,
                        "--body", "@rockyshoals-lgtm\n\n" + body], check=True, timeout=60)
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
    try:
        subprocess.run(["gh", "issue", "create", "--title",
                        f"HELD: {lead['row_id']} ({lead['source']}) lead to verify", "--body", body],
                       check=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"   (issue create skipped: {e})")


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
        elif act == "email":
            how = send_email(state, a.outbox)
            state["email_status"] = how
            print(f"ESCALATION: {state['consecutive_held_runs']} consecutive held runs -> email ({how})")
    io.open(a.state, "w", encoding="utf-8", newline="\n").write(json.dumps(state, indent=1, ensure_ascii=False) + "\n")
    return 0


def _git_show(path):
    rel = os.path.relpath(path, HERE).replace("\\", "/")
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=HERE, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


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
        restored.append(f"dataset rows x{n}")
    for rid in held_ids:
        slug = rid[5:] if rid.startswith("drug:") else None
        row = rows.get(rid) or {}
        for p in held_paths(row, slug):
            old = _git_show(p)
            if old is None:
                continue
            cur = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
            if cur != old:
                if not a.dry_run:
                    io.open(p, "w", encoding="utf-8", newline="").write(old)
                restored.append(os.path.relpath(p, SITE).replace("\\", "/"))
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
    p = sub.add_parser("apply")
    p.add_argument("--state", default=STATE)
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return cmd_collect(a) if a.cmd == "collect" else cmd_apply(a)


if __name__ == "__main__":
    sys.exit(main())
