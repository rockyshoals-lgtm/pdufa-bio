#!/usr/bin/env python3
"""Quick ablation: which v32 feature groups help vs hurt?"""
import json, sys, os
import numpy as np
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DATA_DIR)

# Import from v32 train to reuse data loading
from gungnir_v32_train import *

def run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates, feature_names, drop_prefixes, label):
    """Run walk-forward with specific features dropped."""
    # Build keep mask
    keep = []
    for i, f in enumerate(feature_names):
        should_drop = any(f.startswith(p) or f == p for p in drop_prefixes)
        if not should_drop:
            keep.append(i)
    
    X_sub = X[:, keep]
    sub_names = [feature_names[i] for i in keep]
    
    date_arr = np.array(dates)
    splits = [
        ("2023H2", "2023-07-01", "2023-12-31"),
        ("2024H1", "2024-01-01", "2024-06-30"),
        ("2024H2", "2024-07-01", "2024-12-31"),
        ("2025+",  "2025-01-01", "2026-12-31"),
    ]
    
    aucs, briers, spreads = [], [], []
    for split_name, test_start, test_end in splits:
        train_mask = date_arr < test_start
        test_mask = (date_arr >= test_start) & (date_arr <= test_end)
        if train_mask.sum() < 100 or test_mask.sum() < 30:
            continue
        
        X_train, X_test = X_sub[train_mask], X_sub[test_mask]
        y_train, y_test = y_bin[train_mask], y_bin[test_mask]
        y_ret_test = y_ret[test_mask]
        
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_train)
        X_te = scaler.transform(X_test)
        
        m1 = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000)
        m1.fit(X_tr, y_train)
        p1 = m1.predict_proba(X_te)[:, 1]
        
        m4 = SGDClassifier(loss="log_loss", penalty="elasticnet", alpha=0.001,
                          l1_ratio=0.3, max_iter=2000, random_state=42)
        m4.fit(X_tr, y_train)
        d4 = m4.decision_function(X_te)
        p4 = 1.0 / (1.0 + np.exp(-np.clip(d4, -20, 20)))
        
        p_meta = 0.70 * p1 + 0.30 * p4
        p_meta = np.clip(p_meta, 0.02, 0.98)
        
        # Temperature scaling
        logits = np.log(p_meta / (1 - p_meta))
        p_cal = 1.0 / (1.0 + np.exp(-logits / 0.85))
        
        auc = roc_auc_score(y_test, p_meta) if len(set(y_test)) > 1 else 0.5
        brier = brier_score_loss(y_test, p_cal)
        
        # EV spread
        top = np.percentile(p_meta, 80)
        bot = np.percentile(p_meta, 20)
        ev_top = y_ret_test[p_meta >= top].mean() if (p_meta >= top).sum() > 0 else 0
        ev_bot = y_ret_test[p_meta <= bot].mean() if (p_meta <= bot).sum() > 0 else 0
        
        aucs.append(auc)
        briers.append(brier)
        spreads.append(ev_top - ev_bot)
    
    avg_auc = np.mean(aucs)
    avg_brier = np.mean(briers)
    avg_spread = np.mean(spreads)
    print(f"  {label:55s} | feats={len(sub_names):3d} | AUC={avg_auc:.4f} | Brier={avg_brier:.4f} | EV_Spread={avg_spread:+.2f}pp")
    return avg_auc, avg_brier, avg_spread

def main():
    import csv
    from collections import defaultdict
    
    print("=" * 120)
    print("GUNGNIR v32 FEATURE ABLATION")
    print("=" * 120)
    
    # Load data (reuse v32 pipeline)
    readout_events = []
    with open(READOUT_CSV) as f:
        for r in csv.DictReader(f):
            readout_events.append(r)
    
    orig_events = {}
    for fpath in [ENRICHED_CSV, HISTORICAL_CSV]:
        with open(fpath) as f:
            for r in csv.DictReader(f):
                key = f"{r.get('Ticker','')}|{r.get('date','')}"
                orig_events[key] = r
    
    merged = []
    for re_ev in readout_events:
        key = f"{re_ev.get('ticker','')}|{re_ev.get('date','')}"
        orig = orig_events.get(key, {})
        merged.append({
            "ticker": re_ev["ticker"], "date": re_ev["date"],
            "drug": re_ev.get("drug", orig.get("Drug", "")),
            "indication": re_ev.get("indication", orig.get("Indication", "")),
            "stage": re_ev.get("stage", orig.get("Stage", "")),
            "catalyst_text": orig.get("Catalyst", ""),
            "outcome": re_ev.get("outcome", ""),
            "pre_price": re_ev.get("pre_price", ""),
            "primary_ret_pct": float(re_ev.get("primary_ret_pct", 0)),
            "tier": re_ev.get("tier", "FLAT"), "nct_id": "",
        })
    
    # Load caches
    ctgov_lookup = {}
    for cp in [CTGOV_CACHE, CTGOV_CACHE_V2]:
        if os.path.exists(cp):
            with open(cp) as f:
                ctgov_lookup.update(json.load(f))
    
    journey_index = build_journey_index(merged)
    
    # Build sponsor + indication indexes
    sorted_merged = sorted(merged, key=lambda e: e.get("date", ""))
    sponsor_index = {}
    indication_counter = defaultdict(int)
    for ev in sorted_merged:
        ticker = ev["ticker"]
        indication = ev.get("indication", "").lower()[:40]
        if ticker not in sponsor_index:
            sponsor_index[ticker] = {"n_prior": 0, "n_pos": 0, "n_neg": 0,
                                     "pos_streak": 0, "neg_streak": 0, "success_rate": 0.5}
        ev["_sponsor"] = dict(sponsor_index[ticker])
        ev["_indication_count"] = indication_counter.get(indication, 0)
        outcome = ev.get("outcome", "")
        sponsor_index[ticker]["n_prior"] += 1
        if outcome == "positive":
            sponsor_index[ticker]["n_pos"] += 1
            sponsor_index[ticker]["pos_streak"] += 1
            sponsor_index[ticker]["neg_streak"] = 0
        elif outcome == "negative":
            sponsor_index[ticker]["n_neg"] += 1
            sponsor_index[ticker]["neg_streak"] += 1
            sponsor_index[ticker]["pos_streak"] = 0
        total = sponsor_index[ticker]["n_pos"] + sponsor_index[ticker]["n_neg"]
        if total > 0:
            sponsor_index[ticker]["success_rate"] = sponsor_index[ticker]["n_pos"] / total
        indication_counter[indication] += 1
    
    # Load enrichment
    v32_enrichment = {}
    if os.path.exists(V32_ENRICHMENT):
        with open(V32_ENRICHMENT) as f:
            v32_enrichment = json.load(f)
    
    def _norm(name):
        if not name: return ""
        name = name.split(" - ")[0].split(" (")[0].strip()
        return name.lower()[:40]
    
    for ev in sorted_merged:
        drug_key = _norm(ev.get("drug", ""))
        enrich = v32_enrichment.get(drug_key, {})
        if not enrich and " " in drug_key:
            enrich = v32_enrichment.get(drug_key.split()[0], {})
        ev["_enrichment"] = enrich
    
    merged = sorted_merged
    
    # Engineer ALL features
    feature_names = None
    X_rows, y_binary, y_good, y_crash, y_returns, dates_list = [], [], [], [], [], []
    for ev in merged:
        journey_data = ev.get("_journey", {})
        features = engineer_v31_features(ev, ctgov_lookup, None)
        for jk, jv in journey_data.items():
            features[f"journey_{jk}"] = jv
        if feature_names is None:
            feature_names = sorted(f for f in features.keys() if f != "year")
        X_rows.append([float(features.get(f, 0)) for f in feature_names])
        y_binary.append(1 if ev["outcome"] == "positive" else 0)
        y_good.append(1 if ev["tier"] in ["GOOD", "GREAT"] else 0)
        y_crash.append(1 if ev["tier"] == "CRASH" else 0)
        y_returns.append(ev["primary_ret_pct"])
        dates_list.append(ev["date"])
    
    X = np.array(X_rows, dtype=np.float64)
    y_bin = np.array(y_binary)
    y_gp = np.array(y_good)
    y_cr = np.array(y_crash)
    y_ret = np.array(y_returns)
    
    print(f"\nTotal features: {len(feature_names)}, Events: {X.shape[0]}")
    print(f"\n{'Ablation':55s} | {'feats':>5s} | {'AUC':>6s} | {'Brier':>6s} | {'EV_Spread':>10s}")
    print("-" * 120)
    
    # Define feature groups
    chembl_feats = ["is_antibody", "is_small_molecule", "is_adc", "chembl_first_in_class", 
                    "chembl_max_phase", "chembl_orphan", "chembl_has_data", "n_mechanisms",
                    "antibody_x_onc", "fic_x_small"]
    pubmed_feats = ["log_pubmed_broad", "log_pubmed_specific", "pubmed_high_evidence", 
                    "pubmed_low_evidence", "evidence_x_phase3"]
    sponsor_feats = ["sponsor_n_prior", "sponsor_success_rate", "sponsor_is_serial",
                     "sponsor_hot_streak", "sponsor_cold_streak", "sponsor_sr_x_phase3", "serial_x_small"]
    indication_feats = ["indication_density", "indication_crowded"]
    all_new = chembl_feats + pubmed_feats + sponsor_feats + indication_feats
    
    # Run ablations
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, all_new, "v31.1 BASELINE (drop ALL v32 features)")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, [], "v32.0 FULL (all 114 features)")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, chembl_feats, "DROP ChEMBL features only")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, pubmed_feats, "DROP PubMed features only")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, chembl_feats + pubmed_feats, "DROP ChEMBL + PubMed (keep sponsor/indication)")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, sponsor_feats, "DROP sponsor features only")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, indication_feats, "DROP indication features only")
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, sponsor_feats + indication_feats, "DROP sponsor + indication (keep ChEMBL/PubMed)")
    
    # Try JUST adding sponsor_success_rate + indication_density to v31
    lean_drop = [f for f in all_new if f not in ["sponsor_success_rate", "indication_density", "sponsor_sr_x_phase3"]]
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, lean_drop, "v31 + sponsor_sr + indic_density + sponsor_sr_x_p3 ONLY")
    
    # Try adding top sponsor + indication only
    lean_drop2 = [f for f in all_new if f not in ["sponsor_success_rate", "indication_density"]]
    run_ablation(X, y_bin, y_gp, y_cr, y_ret, dates_list, feature_names, lean_drop2, "v31 + sponsor_sr + indic_density ONLY (2 new)")
    
    print()

if __name__ == "__main__":
    main()
