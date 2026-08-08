#!/usr/bin/env python3
"""
ODIN Insider (HINT) Data Builder — env-var friendly (FINBRAIN_API_KEY)

Changes vs earlier version:
- FinBrain key is read from FINBRAIN_API_KEY (preferred) OR FINBRAIN_TOKEN (fallback)
- FMP key is read from FMP_API_KEY (optional unless --source uses fmp)
- SEC user agent is read from SEC_USER_AGENT (optional; defaults if missing)
- Prints which env vars are detected (without leaking values)

Outputs:
- insider_transactions_*.csv      (transaction evidence; includes SEC Form 4 links when available)
- odin_insider_features_*.csv     (per ticker + asof_date features)
- insider_filings_flags_*.csv     (Form 4 XML flags: 10b5-1 / tax-withholding mentions)
- run_meta_*.json
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import pandas as pd
import requests
from dateutil import parser as dtparser


# -----------------------------
# Env helpers
# -----------------------------

def env_any(names: List[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (value, name_used) for first non-empty env var in names, else (None, None).
    """
    for n in names:
        v = os.environ.get(n, "")
        if v is not None:
            v = str(v).strip()
        if v:
            return v, n
    return None, None

def mask_key(k: str) -> str:
    if not k:
        return ""
    if len(k) <= 6:
        return "***"
    return k[:2] + "***" + k[-2:]


# -----------------------------
# Parsing helpers
# -----------------------------

def parse_yyyy_mm_dd(s: str) -> date:
    return dtparser.parse(s).date()

def safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() == "":
            return None
        return float(x)
    except Exception:
        return None

def safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        if isinstance(x, str) and x.strip() == "":
            return None
        return int(float(x))
    except Exception:
        return None

def parse_finbrain_tx_date(s: str) -> Optional[date]:
    """
    FinBrain often uses formats like: "Mar 08 '24"
    """
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^([A-Za-z]{3})\s+(\d{1,2})\s+'(\d{2})$", s)
    if m:
        mon, dd, yy = m.groups()
        yyyy = 2000 + int(yy)
        return datetime.strptime(f"{mon} {int(dd):02d} {yyyy}", "%b %d %Y").date()
    try:
        return dtparser.parse(s).date()
    except Exception:
        return None

def normalize_tx_type(raw: str) -> str:
    r = (raw or "").strip().lower()
    if "buy" in r or "purchase" in r or r.startswith("p-"):
        return "BUY"
    if "sale" in r or r.startswith("s-"):
        return "SELL"
    if "option" in r or "exercise" in r or r.startswith("m-"):
        return "OPTION_EXERCISE"
    if "gift" in r:
        return "GIFT"
    if "automatic" in r:
        return "AUTO"
    return "OTHER"

def is_c_suite_or_director(role: str) -> bool:
    r = (role or "").lower()
    return any(k in r for k in [
        "chief executive", "ceo", "chief financial", "cfo", "chief operating", "coo",
        "president", "chair", "director", "chief medical", "cmo", "chief technology", "cto",
        "general counsel", "principal", "officer", "vp", "svp", "evp"
    ])

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# -----------------------------
# HTTP helpers
# -----------------------------

@dataclass
class HttpConfig:
    timeout_connect: float = 7.0
    timeout_read: float = 30.0
    max_retries: int = 4
    backoff_base: float = 0.9
    user_agent: str = "ODIN Insider Parser (contact: you@example.com)"

def make_session(http: HttpConfig) -> requests.Session:
    sess = requests.Session()
    sess.headers.update({
        "Accept": "application/json,text/html,application/xml,text/plain,*/*",
        "User-Agent": http.user_agent,
    })
    return sess

def get_with_retries(sess: requests.Session, url: str, params: Optional[dict] = None,
                     http: Optional[HttpConfig] = None) -> requests.Response:
    http = http or HttpConfig()
    last_err = None
    for attempt in range(http.max_retries):
        try:
            resp = sess.get(url, params=params, timeout=(http.timeout_connect, http.timeout_read))
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep((http.backoff_base ** attempt) + (0.25 * attempt))
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            time.sleep((http.backoff_base ** attempt) + (0.25 * attempt))
    raise RuntimeError(f"GET failed after retries: {url} | last_err={last_err}")


# -----------------------------
# FinBrain
# -----------------------------

def finbrain_fetch_transactions(
    sess: requests.Session,
    ticker: str,
    market: str,
    api_key: str,
    date_from: Optional[date],
    date_to: Optional[date],
    http: HttpConfig
) -> List[Dict[str, Any]]:
    """
    FinBrain Insider Transactions API:
      GET /v1/insidertransactions/{market}/{ticker}?token=...&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD

    Uses SECForm4Date as the authoritative public-availability timestamp.
    """
    enc_market = quote(market, safe="")
    url = f"https://api.finbrain.tech/v1/insidertransactions/{enc_market}/{ticker}"
    params = {"token": api_key}
    if date_from:
        params["dateFrom"] = date_from.isoformat()
    if date_to:
        params["dateTo"] = date_to.isoformat()

    data = get_with_retries(sess, url, params=params, http=http).json()

    txs = data.get("insiderTransactions", []) or []
    out = []
    for t in txs:
        filing_dt = None
        if t.get("SECForm4Date"):
            try:
                filing_dt = dtparser.isoparse(t["SECForm4Date"])
            except Exception:
                filing_dt = None

        out.append({
            "source": "finbrain",
            "ticker": data.get("ticker", ticker),
            "company_name": data.get("name"),

            "transaction_date": parse_finbrain_tx_date(t.get("date")),
            "filing_datetime": filing_dt,
            "filing_date": filing_dt.date() if filing_dt else None,

            "insider_name": t.get("insiderTradings"),
            "insider_role": t.get("relationship"),

            "transaction_raw": t.get("transaction"),
            "transaction_type": normalize_tx_type(t.get("transaction")),

            "shares": safe_int(t.get("shares")),
            "price": safe_float(t.get("cost")),
            "usd_value": safe_float(t.get("USDValue")),
            "total_shares_after": safe_int(t.get("totalShares")),

            "sec_form4_link": t.get("SECForm4Link"),
            "sec_form4_date_raw": t.get("SECForm4Date"),
        })
    return out


# -----------------------------
# FMP v4 (optional)
# -----------------------------

def fmp_fetch_transactions_v4(
    sess: requests.Session,
    ticker: str,
    api_key: str,
    limit: int,
    http: HttpConfig
) -> List[Dict[str, Any]]:
    url = "https://financialmodelingprep.com/api/v4/insider-trading"
    params = {"symbol": ticker, "limit": int(limit), "apikey": api_key}
    data = get_with_retries(sess, url, params=params, http=http).json()
    if not isinstance(data, list):
        return []

    out = []
    for t in data:
        tx_date = None
        if t.get("transactionDate"):
            try:
                tx_date = dtparser.parse(t["transactionDate"]).date()
            except Exception:
                tx_date = None

        filing_date = None
        if t.get("filingDate"):
            try:
                filing_date = dtparser.parse(t["filingDate"]).date()
            except Exception:
                filing_date = None

        out.append({
            "source": "fmp",
            "ticker": (t.get("symbol") or ticker).upper(),

            "company_name": None,
            "transaction_date": tx_date,
            "filing_datetime": None,
            "filing_date": filing_date,

            "insider_name": t.get("reportingName"),
            "insider_role": None,

            "transaction_raw": t.get("transactionType"),
            "transaction_type": normalize_tx_type(t.get("transactionType", "")),

            "shares": safe_int(t.get("securitiesTransacted")),
            "price": safe_float(t.get("transactionPrice")) or safe_float(t.get("price")),
            "usd_value": safe_float(t.get("transactionValue")),

            "sec_form4_link": t.get("link"),  # SEC index page (often)
            "form_type": t.get("formType"),
        })
    return out


# -----------------------------
# SEC index filing-date resolver (only for FMP rows lacking filing_date)
# -----------------------------

SEC_FILING_DATE_RE = re.compile(r"Filing Date\s*</div>\s*<div[^>]*>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", re.IGNORECASE)

def resolve_sec_filing_date_from_index_html(
    sess: requests.Session,
    index_url: str,
    cache_dir: str,
    http: HttpConfig
) -> Optional[date]:
    if not index_url:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    fn = os.path.join(cache_dir, f"{sha1(index_url)}.html")
    if os.path.exists(fn):
        text = open(fn, "r", encoding="utf-8", errors="ignore").read()
    else:
        text = get_with_retries(sess, index_url, http=http).text
        try:
            open(fn, "w", encoding="utf-8").write(text)
        except Exception:
            pass
    m = SEC_FILING_DATE_RE.search(text)
    if m:
        try:
            return dtparser.parse(m.group(1)).date()
        except Exception:
            return None
    return None


# -----------------------------
# Optional Form 4 XML flags (primary disclosure heuristic)
# -----------------------------

def download_cached_text(sess: requests.Session, url: str, cache_dir: str, http: HttpConfig) -> Optional[str]:
    if not url:
        return None
    os.makedirs(cache_dir, exist_ok=True)
    fn = os.path.join(cache_dir, f"{sha1(url)}.txt")
    if os.path.exists(fn):
        return open(fn, "r", encoding="utf-8", errors="ignore").read()
    try:
        txt = get_with_retries(sess, url, http=http).text
        try:
            open(fn, "w", encoding="utf-8").write(txt)
        except Exception:
            pass
        return txt
    except Exception:
        return None

def parse_form4_flags(text: str) -> Dict[str, Any]:
    if not text:
        return {"likely_10b5_1": False, "likely_tax_withholding": False, "mentions": []}
    low = text.lower()
    mentions = []
    likely_10b5 = ("10b5-1" in low) or ("10b5 1" in low) or ("rule 10b5" in low)
    if likely_10b5:
        mentions.append("10b5-1")
    likely_tax = ("tax" in low) and (("withhold" in low) or ("withholding" in low) or ("cover" in low))
    if likely_tax:
        mentions.append("tax/withholding")
    return {
        "likely_10b5_1": bool(likely_10b5),
        "likely_tax_withholding": bool(likely_tax),
        "mentions": mentions,
    }


# -----------------------------
# Feature engineering (T-1 safe uses filing_date <= asof_date)
# -----------------------------

def compute_features_for_asof(tx: pd.DataFrame, asof: date) -> Dict[str, Any]:
    out: Dict[str, Any] = {"asof_date": asof.isoformat()}

    if tx.empty:
        out.update({
            "insider_alignment_score": 0.0,
            "insider_signal_bucket": "NO_DATA",
            "buyers_60d": 0,
            "sellers_60d": 0,
            "buy_usd_60d": 0.0,
            "sell_usd_60d": 0.0,
            "discretionary_sell_usd_60d": 0.0,
            "c_suite_buy_usd_60d": 0.0,
            "buy_cluster_14d_60d_flag": 0,
            "sell_cluster_14d_60d_flag": 0,
            "cessation_of_selling_90d_flag": 0,
        })
        return out

    tx = tx.copy()
    tx["filing_date"] = pd.to_datetime(tx["filing_date"], errors="coerce").dt.date
    tx = tx[tx["filing_date"].notna() & (tx["filing_date"] <= asof)].copy()

    if tx.empty:
        return compute_features_for_asof(pd.DataFrame(), asof)

    # default flags if missing
    if "likely_10b5_1" not in tx.columns:
        tx["likely_10b5_1"] = False
    if "likely_tax_withholding" not in tx.columns:
        tx["likely_tax_withholding"] = False

    tx["sell_is_plan_or_tax"] = (tx["transaction_type"] == "SELL") & (tx["likely_10b5_1"] | tx["likely_tax_withholding"])
    tx["sell_is_discretionary"] = (tx["transaction_type"] == "SELL") & (~tx["sell_is_plan_or_tax"])

    def window(days: int) -> pd.DataFrame:
        return tx[tx["filing_date"] >= (asof - timedelta(days=days))]

    def cluster_flag(df: pd.DataFrame, tx_type: str, window_days: int = 14, min_people: int = 2) -> int:
        dfx = df[df["transaction_type"] == tx_type]
        if dfx.empty:
            return 0
        dates = sorted(set(dfx["filing_date"].tolist()))
        for d0 in dates:
            d1 = d0 + timedelta(days=window_days)
            w = dfx[(dfx["filing_date"] >= d0) & (dfx["filing_date"] <= d1)]
            if w["insider_name"].nunique(dropna=True) >= min_people:
                return 1
        return 0

    w60 = window(60)
    buys = w60[w60["transaction_type"] == "BUY"]
    sells = w60[w60["transaction_type"] == "SELL"]
    disc_sells = w60[w60["sell_is_discretionary"]]

    # c-suite buying proxy
    buys_roles = buys.copy()
    buys_roles["is_c_suite"] = buys_roles["insider_role"].fillna("").apply(is_c_suite_or_director)
    cbuys = buys_roles[buys_roles["is_c_suite"]]

    out["buyers_60d"] = int(buys["insider_name"].nunique(dropna=True))
    out["sellers_60d"] = int(sells["insider_name"].nunique(dropna=True))
    out["buy_usd_60d"] = float(buys["usd_value"].fillna(0).sum())
    out["sell_usd_60d"] = float(sells["usd_value"].fillna(0).sum())
    out["discretionary_sell_usd_60d"] = float(disc_sells["usd_value"].fillna(0).sum())
    out["c_suite_buy_usd_60d"] = float(cbuys["usd_value"].fillna(0).sum())

    out["buy_cluster_14d_60d_flag"] = cluster_flag(w60, "BUY", 14, 2)
    out["sell_cluster_14d_60d_flag"] = cluster_flag(w60, "SELL", 14, 2)

    # cessation of selling: prior 90d had discretionary sells but last 90d has none
    w90 = window(90)
    prev90 = tx[(tx["filing_date"] > asof - timedelta(days=180)) & (tx["filing_date"] <= asof - timedelta(days=90))]
    last_disc = int(w90[w90["sell_is_discretionary"]]["insider_name"].nunique(dropna=True))
    prev_disc = int(prev90[prev90["sell_is_discretionary"]]["insider_name"].nunique(dropna=True))
    out["cessation_of_selling_90d_flag"] = 1 if (prev_disc > 0 and last_disc == 0) else 0

    # bounded alignment score (heuristic; ODIN can learn real weights later)
    score = 0.0
    score += 0.35 * out["buy_cluster_14d_60d_flag"]
    score += 0.25 * min(1.0, out["c_suite_buy_usd_60d"] / 250000.0)
    score += 0.15 * min(1.0, max(0.0, out["buy_usd_60d"] - out["sell_usd_60d"]) / 500000.0)
    score += 0.10 * out["cessation_of_selling_90d_flag"]

    score -= 0.35 * out["sell_cluster_14d_60d_flag"]
    score -= 0.35 * min(1.0, out["discretionary_sell_usd_60d"] / 500000.0)

    score = max(-1.0, min(1.0, score))
    out["insider_alignment_score"] = float(score)

    if score >= 0.45:
        out["insider_signal_bucket"] = "STRONG_BULL"
    elif score >= 0.15:
        out["insider_signal_bucket"] = "BULL"
    elif score <= -0.35:
        out["insider_signal_bucket"] = "BEAR"
    elif score <= -0.10:
        out["insider_signal_bucket"] = "WEAK_BEAR"
    else:
        out["insider_signal_bucket"] = "NEUTRAL"

    return out


# -----------------------------
# Load events/tickers
# -----------------------------

def load_events(events_csv: Optional[str], tickers: Optional[str], asof: Optional[str]) -> pd.DataFrame:
    if events_csv:
        df = pd.read_csv(events_csv)
        cols = {c.lower().strip(): c for c in df.columns}
        if "ticker" not in cols and "symbol" not in cols:
            raise ValueError("events CSV must contain 'ticker' or 'symbol' column.")

        tcol = cols.get("ticker") or cols.get("symbol")

        possible_asof = ["asof_date", "asof", "cutoff_date", "data_cutoff_date", "t1_date"]
        acol = None
        for p in possible_asof:
            if p in cols:
                acol = cols[p]
                break

        if acol is None:
            if not asof:
                raise ValueError("No asof/cutoff column found. Provide --asof YYYY-MM-DD.")
            df["_asof_date"] = asof
            acol = "_asof_date"

        out = pd.DataFrame({
            "ticker": df[tcol].astype(str).str.upper().str.strip(),
            "asof_date": pd.to_datetime(df[acol], errors="coerce").dt.date
        }).dropna(subset=["asof_date"])
        return out.reset_index(drop=True)

    if tickers:
        if not asof:
            raise ValueError("Using --tickers requires --asof YYYY-MM-DD")
        tlist = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        return pd.DataFrame({"ticker": tlist, "asof_date": [parse_yyyy_mm_dd(asof)] * len(tlist)})

    raise ValueError("Provide --events-csv or --tickers.")


# -----------------------------
# Main
# -----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-csv", type=str, default=None)
    ap.add_argument("--tickers", type=str, default=None)
    ap.add_argument("--asof", type=str, default=None)
    ap.add_argument("--market", type=str, default="NASDAQ")
    ap.add_argument("--lookback-days", type=int, default=365)
    ap.add_argument("--source", type=str, default="finbrain", choices=["finbrain", "fmp", "both"])
    ap.add_argument("--fmp-limit", type=int, default=250)
    ap.add_argument("--parse-form4", action="store_true")
    ap.add_argument("--out-dir", type=str, default="insider_out")
    ap.add_argument("--sec-cache", type=str, default=".cache_sec")
    args = ap.parse_args()

    # Keys: updated to FINBRAIN_API_KEY first
    finbrain_key, finbrain_env = env_any(["FINBRAIN_API_KEY", "FINBRAIN_TOKEN"])
    fmp_key, fmp_env = env_any(["FMP_API_KEY"])
    sec_ua, sec_ua_env = env_any(["SEC_USER_AGENT"])

    if not sec_ua:
        sec_ua = "ODIN Insider Parser (contact: your_email@domain.com)"
        sec_ua_env = "(default)"

    print("ENV CHECK:")
    print(f"  FinBrain key: {'FOUND' if finbrain_key else 'MISSING'} (env={finbrain_env})")
    print(f"  FMP key:      {'FOUND' if fmp_key else 'MISSING'} (env={fmp_env})")
    print(f"  SEC UA:       {'FOUND' if sec_ua_env != '(default)' else 'DEFAULT'} (env={sec_ua_env})")
    if finbrain_key:
        print(f"  FinBrain key sample: {mask_key(finbrain_key)}")
    if fmp_key:
        print(f"  FMP key sample: {mask_key(fmp_key)}")

    if args.source in ("finbrain", "both") and not finbrain_key:
        raise SystemExit("ERROR: FinBrain selected but FINBRAIN_API_KEY/FINBRAIN_TOKEN is not set (or is blank).")

    if args.source in ("fmp", "both") and not fmp_key:
        raise SystemExit("ERROR: FMP selected but FMP_API_KEY is not set (or is blank).")

    events = load_events(args.events_csv, args.tickers, args.asof)
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.sec_cache, exist_ok=True)

    http = HttpConfig(user_agent=sec_ua)
    sess = make_session(http)

    all_rows: List[Dict[str, Any]] = []
    filing_flags: Dict[str, Dict[str, Any]] = {}

    for _, ev in events.iterrows():
        ticker = str(ev["ticker"]).upper().strip()
        asof_date = ev["asof_date"]
        date_to = asof_date
        date_from = asof_date - timedelta(days=int(args.lookback_days))

        rows: List[Dict[str, Any]] = []

        if args.source in ("finbrain", "both"):
            rows.extend(finbrain_fetch_transactions(
                sess=sess,
                ticker=ticker,
                market=args.market,
                api_key=finbrain_key,
                date_from=date_from,
                date_to=date_to,
                http=http
            ))

        if args.source in ("fmp", "both"):
            fmp_rows = fmp_fetch_transactions_v4(
                sess=sess,
                ticker=ticker,
                api_key=fmp_key,
                limit=args.fmp_limit,
                http=http
            )
            # recover filing_date if missing (needed for T-1)
            for r in fmp_rows:
                if r.get("filing_date") is None and r.get("sec_form4_link"):
                    r["filing_date"] = resolve_sec_filing_date_from_index_html(
                        sess=sess,
                        index_url=r["sec_form4_link"],
                        cache_dir=os.path.join(args.sec_cache, "sec_index_html"),
                        http=http
                    )
            rows.extend(fmp_rows)

        # optional parsing of Form 4 XML
        if args.parse_form4:
            for r in rows:
                link = r.get("sec_form4_link")
                if not link:
                    continue
                # Only parse direct Archives URLs (often XML)
                if "sec.gov/Archives/" not in link:
                    continue
                if link not in filing_flags:
                    txt = download_cached_text(sess, link, os.path.join(args.sec_cache, "form4_xml"), http=http)
                    filing_flags[link] = parse_form4_flags(txt or "")
                r.update(filing_flags.get(link, {}))
        else:
            for r in rows:
                r.setdefault("likely_10b5_1", False)
                r.setdefault("likely_tax_withholding", False)

        for r in rows:
            r["event_asof_date"] = asof_date

        all_rows.extend(rows)

    tx_df = pd.DataFrame(all_rows)
    if tx_df.empty:
        raise SystemExit("No transactions returned. Check market string and tickers, and confirm keys are correct.")

    # Build features per (ticker, asof_date)
    feat_rows = []
    for (ticker, asof_date), g in tx_df.groupby(["ticker", "event_asof_date"], dropna=False):
        if pd.isna(asof_date):
            continue
        feats = compute_features_for_asof(g, asof_date)
        feats["ticker"] = ticker
        feat_rows.append(feats)

    feat_df = pd.DataFrame(feat_rows).sort_values(["asof_date", "ticker"])

    # Save outputs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tx_path = os.path.join(args.out_dir, f"insider_transactions_{ts}.csv")
    feat_path = os.path.join(args.out_dir, f"odin_insider_features_{ts}.csv")
    flags_path = os.path.join(args.out_dir, f"insider_filings_flags_{ts}.csv")
    meta_path = os.path.join(args.out_dir, f"run_meta_{ts}.json")

    tx_df.to_csv(tx_path, index=False)
    feat_df.to_csv(feat_path, index=False)

    if filing_flags:
        pd.DataFrame([{"sec_form4_link": k, **v} for k, v in filing_flags.items()]).to_csv(flags_path, index=False)
    else:
        pd.DataFrame(columns=["sec_form4_link", "likely_10b5_1", "likely_tax_withholding", "mentions"]).to_csv(flags_path, index=False)

    meta = {
        "timestamp": ts,
        "source": args.source,
        "market": args.market,
        "lookback_days": args.lookback_days,
        "parse_form4": bool(args.parse_form4),
        "n_events": int(len(events)),
        "n_transactions": int(len(tx_df)),
        "env_used": {
            "finbrain_env": finbrain_env,
            "fmp_env": fmp_env,
            "sec_user_agent_env": sec_ua_env,
        },
        "outputs": {
            "transactions_csv": tx_path,
            "features_csv": feat_path,
            "filings_flags_csv": flags_path,
        },
        "notes": [
            "T-1 compliance uses filing_date <= asof_date.",
            "FinBrain provides SECForm4Date and SECForm4Link per transaction.",
            "FMP rows without filing_date attempt SEC index HTML parsing to recover filing date.",
        ]
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("\nSaved:")
    print(f"  {tx_path}")
    print(f"  {feat_path}")
    print(f"  {flags_path}")
    print(f"  {meta_path}")
    print("Done.")


if __name__ == "__main__":
    main()
