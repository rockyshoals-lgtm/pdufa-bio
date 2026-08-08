#!/usr/bin/env python3
"""
ODIN Insider (HINT) Data Builder — FMP stable + FinBrain, T-1 compliant

Fixes:
- FMP moved to /stable endpoints; legacy /api/v4/insider-trading may 403.
- If FMP fails, continue with FinBrain (no hard crash unless --strict-fmp).
- Avoid printing full API keys in exception strings.

Outputs:
- insider_transactions_*.csv
- odin_insider_features_*.csv
- insider_filings_flags_*.csv
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
    """Returns (value, name_used) for first non-empty env var in names."""
    for n in names:
        v = os.environ.get(n, "")
        v = str(v).strip() if v is not None else ""
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
    """FinBrain often uses: "Mar 08 '24"."""
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
    # common coded formats: P-Purchase, S-Sale, M-Exempt
    if r.startswith("p-") or "purchase" in r or "buy" in r:
        return "BUY"
    if r.startswith("s-") or "sale" in r or "sell" in r:
        return "SELL"
    if r.startswith("m-") or "exercise" in r or "option" in r or "convert" in r:
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

def _safe_params_for_log(params: Optional[dict]) -> Optional[dict]:
    if params is None:
        return None
    sp = dict(params)
    for k in ["apikey", "token"]:
        if k in sp and sp[k]:
            sp[k] = "***"
    return sp

def get_with_retries(
    sess: requests.Session,
    url: str,
    params: Optional[dict] = None,
    http: Optional[HttpConfig] = None,
    headers: Optional[dict] = None,
) -> requests.Response:
    """
    Retries only transient errors (429/5xx). 4xx (except 429) fails fast.
    Raises PermissionError on 403 with sanitized context.
    """
    http = http or HttpConfig()
    last_err = None

    for attempt in range(http.max_retries):
        try:
            resp = sess.get(
                url,
                params=params,
                headers=headers,
                timeout=(http.timeout_connect, http.timeout_read),
            )

            if resp.status_code == 403:
                raise PermissionError(
                    f"403 Forbidden for {url} params={_safe_params_for_log(params)}"
                )

            # transient
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep((http.backoff_base ** attempt) + (0.25 * attempt))
                continue

            # fail-fast on other 4xx
            if 400 <= resp.status_code < 500:
                resp.raise_for_status()

            resp.raise_for_status()
            return resp

        except PermissionError as e:
            # no retry
            raise
        except Exception as e:
            last_err = e
            # retry only if not last attempt
            if attempt < http.max_retries - 1:
                time.sleep((http.backoff_base ** attempt) + (0.25 * attempt))
                continue
            break

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
    FinBrain:
      https://api.finbrain.tech/v1/insidertransactions/{market}/{ticker}?token=...&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD
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
# FMP (STABLE) — preferred
# -----------------------------

def _pick_first_key(d: dict, keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def fmp_fetch_transactions_stable_search(
    sess: requests.Session,
    ticker: str,
    api_key: str,
    max_records: int,
    max_pages: int,
    http: HttpConfig
) -> List[Dict[str, Any]]:
    """
    FMP stable search endpoint:
      https://financialmodelingprep.com/stable/insider-trading/search?symbol=AAPL&page=0&limit=100&apikey=...
    """
    base = "https://financialmodelingprep.com/stable/insider-trading/search"
    out_rows: List[Dict[str, Any]] = []

    # add header auth too (FMP supports it)
    fmp_headers = {"apikey": api_key}

    page = 0
    while page < max_pages and len(out_rows) < max_records:
        limit = min(100, max_records - len(out_rows))
        params = {"symbol": ticker, "page": page, "limit": limit, "apikey": api_key}

        data = get_with_retries(sess, base, params=params, headers=fmp_headers, http=http).json()
        if not isinstance(data, list) or len(data) == 0:
            break

        for t in data:
            filing_date = None
            if t.get("filingDate"):
                try:
                    filing_date = dtparser.parse(t["filingDate"]).date()
                except Exception:
                    filing_date = None

            tx_date = None
            if t.get("transactionDate"):
                try:
                    tx_date = dtparser.parse(t["transactionDate"]).date()
                except Exception:
                    tx_date = None

            shares = safe_int(_pick_first_key(t, ["securitiesTransacted", "shares", "securities", "transactionShares"]))
            price = safe_float(_pick_first_key(t, ["price", "transactionPrice"]))
            usd_value = safe_float(_pick_first_key(t, ["transactionValue", "value"]))
            if usd_value is None and shares is not None and price is not None:
                usd_value = float(shares) * float(price)

            # link field name varies; keep whatever exists
            link = _pick_first_key(t, ["link", "filingLink", "secLink", "url", "linkToFilingDetails", "linkToFiling"])

            out_rows.append({
                "source": "fmp_stable",
                "ticker": (t.get("symbol") or ticker).upper(),

                "company_name": None,
                "transaction_date": tx_date,
                "filing_datetime": None,
                "filing_date": filing_date,

                "insider_name": t.get("reportingName"),
                "insider_role": t.get("typeOfOwner"),

                "transaction_raw": t.get("transactionType"),
                "transaction_type": normalize_tx_type(t.get("transactionType", "")),

                "shares": shares,
                "price": price,
                "usd_value": usd_value,

                "sec_form4_link": link,
                "security_name": t.get("securityName"),
            })

        page += 1

    return out_rows


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

    w90 = window(90)
    prev90 = tx[(tx["filing_date"] > asof - timedelta(days=180)) & (tx["filing_date"] <= asof - timedelta(days=90))]
    last_disc = int(w90[w90["sell_is_discretionary"]]["insider_name"].nunique(dropna=True))
    prev_disc = int(prev90[prev90["sell_is_discretionary"]]["insider_name"].nunique(dropna=True))
    out["cessation_of_selling_90d_flag"] = 1 if (prev_disc > 0 and last_disc == 0) else 0

    # bounded heuristic score
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
    ap.add_argument("--strict-fmp", action="store_true", help="If set, any FMP failure aborts run.")
    ap.add_argument("--fmp-max-records", type=int, default=400)
    ap.add_argument("--fmp-max-pages", type=int, default=8)

    ap.add_argument("--parse-form4", action="store_true")
    ap.add_argument("--out-dir", type=str, default="insider_out")
    ap.add_argument("--sec-cache", type=str, default=".cache_sec")
    args = ap.parse_args()

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
        raise SystemExit("ERROR: FinBrain selected but FINBRAIN_API_KEY/FINBRAIN_TOKEN is not set (or blank).")
    if args.source in ("fmp", "both") and not fmp_key:
        raise SystemExit("ERROR: FMP selected but FMP_API_KEY is not set (or blank).")

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

        # ---- FinBrain
        if args.source in ("finbrain", "both"):
            try:
                rows.extend(finbrain_fetch_transactions(
                    sess=sess,
                    ticker=ticker,
                    market=args.market,
                    api_key=finbrain_key,
                    date_from=date_from,
                    date_to=date_to,
                    http=http
                ))
            except Exception as e:
                print(f"[WARN] FinBrain failed for {ticker}: {e}")

        # ---- FMP (stable)
        if args.source in ("fmp", "both"):
            try:
                rows.extend(fmp_fetch_transactions_stable_search(
                    sess=sess,
                    ticker=ticker,
                    api_key=fmp_key,
                    max_records=int(args.fmp_max_records),
                    max_pages=int(args.fmp_max_pages),
                    http=http
                ))
            except PermissionError as e:
                msg = (
                    f"[WARN] FMP returned 403 for {ticker}. "
                    f"This often happens if a legacy endpoint is blocked or your key lacks access. "
                    f"Continuing without FMP. ({e})"
                )
                print(msg)
                if args.strict_fmp:
                    raise SystemExit(msg)
            except Exception as e:
                msg = f"[WARN] FMP failed for {ticker}: {e}"
                print(msg)
                if args.strict_fmp:
                    raise SystemExit(msg)

        # Optional Form 4 XML flags
        if args.parse_form4:
            for r in rows:
                link = r.get("sec_form4_link")
                if not link:
                    continue
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
        raise SystemExit("No transactions returned. Check tickers/market and confirm API keys are valid.")

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
            "FMP uses stable endpoints under https://financialmodelingprep.com/stable/.",
            "FinBrain provides SECForm4Date/SECForm4Link directly.",
        ],
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
