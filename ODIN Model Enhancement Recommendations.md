# **ODIN v34 Forensic Architecture: Comprehensive Audit and Optimization Report for Biotech Catalyst Prediction**

## **1\. Executive Introduction: The Epistemological Shift to Forensic Intelligence**

The predictive modeling of biotechnology regulatory outcomes has historically operated under a "clinical-first" paradigm, where algorithms predominantly weigh public efficacy data—p-values, hazard ratios, and endpoint achievement—to forecast FDA decisions. However, a rigorous forensic audit of the ODIN project files, specifically the transition from v8.5 to the proposed v34 "Allfather" architecture, reveals a terminal epistemic crisis in this traditional approach. Public clinical data is increasingly commoditized, efficiently priced by the market, and insufficient for anticipating the "invisible" vectors of failure that now dominate the regulatory landscape. The analysis indicates that while legacy models like v8.6 achieved high precision (95.0%) on positive "Buy" signals, they suffered from catastrophic overconfidence, evidenced by a Brier score of \~0.176 against a target of ≤0.075, and a dismal recall rate of \~4% for Complete Response Letters (CRLs).

The next generation of the ODIN engine must transition from a deterministic calculator of clinical odds to a probabilistic inference engine grounded in "Forensic Intelligence." This report outlines a comprehensive strategy to integrate six orthogonal "shadow signals"—Financial Forensics (FinBrain), Operational Activity (Indeed), Scientific Velocity (PubMed/bioRxiv), Molecular Physics (ChEMBL), and Structural Trial Design (ClinicalTrials.gov)—to capture the latent risks of manufacturing, toxicity, and internal corporate pessimism that clinical data conceals. By synthesizing these inputs through a "Reference Class Forecasting" (RCF) framework and enforcing strict "Honest Backtest" protocols, the v34 architecture aims to achieve a Brier score of ≤0.075 and a CRL recall of ≥70%, aligning with the "ALLFATHER" performance gates.

## **2\. Architectural Audit and The Crisis of Calibration**

The fundamental challenge facing the ODIN system is not accuracy in the binary sense, but **calibration**—the alignment of predicted probabilities with observed frequencies. A model that predicts approval with 95% confidence for a drug that has only a 60% base rate of success is structurally flawed, even if the drug is eventually approved. The audit of the ODIN project files highlights a systemic failure in calibration that necessitates a complete re-engineering of the scoring logic.

### **2.1 The Brier Score Mandate**

The primary metric for validation in the v34 upgrade is the **Brier Score**, a proper scoring rule that measures the mean squared error of probability forecasts. It is defined mathematically as:

![][image1]  
Where ![][image2] is the forecasted probability (0 to 1\) and ![][image3] is the actual outcome (0 or 1).1 The current ODIN models (v9.0 "MAXMINING") yielded a score of 0.172, significantly higher than the random baseline of 0.25 but far exceeding the "ALLFATHER" target of 0.075. This discrepancy suggests that the model is extracting signal but failing to quantify uncertainty. To reduce the Brier score, the v34 architecture must decompose the error into **Reliability** (calibration) and **Resolution** (discrimination). The integration of new data feeds is primarily aimed at improving Resolution—distinguishing the "truly safe" 90% bets from the "risky" 60% bets that currently look identical in the clinical data.

### **2.2 The "Experienced Sponsor" Paradox**

A critical finding from the forensic audit of v8.5 was the **"Experienced Sponsor Paradox."** Legacy logic awarded a generic "+20 bonus" to experienced sponsors (e.g., Big Pharma), assuming their regulatory expertise reduced risk. However, the audit revealed that **90.4% of false positives** (predicted approvals that failed) were associated with these experienced sponsors. The data suggests that large sponsors leverage their capital to take greater clinical risks, particularly in high-volatility indications like Oncology, or to push forward assets with marginal efficacy.

**Strategic Implication:** The v34 model must invert this logic. Instead of a global bonus, the script must implement a **conditional penalty** (clinical\_crl\_risk) for experienced sponsors operating in high-risk therapeutic areas. This requires a nuanced "Sponsor Phenotype" metric derived from historical FDA outcomes, rather than simple market capitalization.

### **2.3 The "CMC Cliff" and Manufacturing Blind Spots**

Perhaps the most glaring deficiency in the current architecture is the inability to predict manufacturing-related CRLs. Analysis shows that between 2020 and 2024, approximately **74% of CRLs** cited Chemistry, Manufacturing, and Controls (CMC) deficiencies.2 These failures are often "silent" in clinical datasets. A Phase 3 trial can meet all endpoints (p \< 0.001), yet the application can be rejected because the commercial manufacturing facility failed inspection.

**Corrective Action:** The v34 model must integrate a dedicated **"CMC Risk Module"** that operates independently of the clinical score. This module will utilize data from ChEMBL (molecular complexity) and Indeed (remediation hiring) to assign a "Developability Penalty." If a drug is a complex biologic (e.g., gene therapy) and the sponsor has no recent manufacturing hires, the model must cap the Probability of Approval (POA) regardless of clinical efficacy.3

### **2.4 The "Honest Backtest" Protocol**

To ensure that new metrics do not introduce look-ahead bias, the v34 architecture mandates an **"Honest Backtest"** framework. This involves strict timestamp enforcement where data for a prediction at time ![][image4] must only include information available at ![][image5]. The Python infrastructure must effectively "time travel," reconstructing the state of the world (e.g., the number of job postings or citation counts) as it existed prior to the catalyst, ensuring that the model does not "leak" future knowledge into historical training sets.4

## ---

**3\. Financial Forensics: The FinBrain Integration**

Financial markets often aggregate dispersed information more efficiently than any single analyst. However, raw market data is noisy. The integration of FinBrain into ODIN v34 focuses on extracting **"Costly Signals"**—actions that entail significant financial risk for the actor and are therefore difficult to fake.

### **3.1 Inventory Capitalization (ASC 330\)**

The single most powerful predictor identified in the forensic audit is **Inventory Capitalization**. Under US GAAP (ASC 330), a pharmaceutical company may capitalize pre-approval inventory only if the future economic benefit is "probable." Given the severe financial penalty of writing down inventory if approval is denied, management will only capitalize if they possess extremely high conviction, likely derived from private, positive communications with the FDA.

**Metric Definition:** Inventory\_Cap\_Signal (Boolean).

* **Source:** SEC EDGAR (via FinBrain or direct scraping of 10-Q/10-K notes).  
* **Logic:** Scan financial footnotes for phrases like "capitalized pre-launch inventory" or "inventory anticipating regulatory approval."  
* **Weighting:** This signal acts as a **Tier 1 Override**. If Inventory\_Cap\_Signal \== True, the model should effectively "veto" negative sentiment or weak clinical signals, raising the minimum POA floor to 0.85. This aligns with the "Forensic Intelligence" doctrine of prioritizing audited financial commitments over public PR statements.

### **3.2 Insider Trading: The "Opportunistic" Filter**

Insider trading is a classic signal, but the v34 audit emphasizes the need to filter out noise. Routine sales (for tax purposes) and programmatic **Rule 10b5-1** trades carry zero predictive value. The ODIN script must isolate **"Opportunistic"** trades.

**Metric Definition:** Insider\_Confidence\_Score (Float).

* **Source:** FinBrain Insider Transactions API.  
* **Calculation:**  
  1. **Filter:** Exclude all transactions marked "Rule 10b5-1" or "Option Exercise."  
  2. **Cluster Detection:** Identify "Cluster Buys" (≥3 unique insiders buying within a 30-day window). This pattern suggests coordinated internal confidence and is a highly robust bullish signal.5  
  3. **Magnitude Weighting:** Apply a multiplier for "High Conviction" buys (\>$100,000) and for "Board Confidence" (buys by CEO/Directors).5  
  4. **Cluster Exit:** Conversely, flag "Cluster Sells" in the T-3 month window as a bearish indicator, suggesting insiders are de-risking before a binary event.  
* **Implementation:**  
  Python  
  def calculate\_insider\_score(ticker, lookback=180):  
      trades \= finbrain.get\_trades(ticker, lookback)  
      score \= 0  
      for t in trades:  
          if t.is\_10b5\_1: continue  
          if t.type \== 'BUY':  
              weight \= 1.5 if t.role in else 1.0  
              score \+= t.value \* weight  
          elif t.type \== 'SELL' and is\_cluster\_sell(t, trades):  
              score \-= t.value \* 0.5  
      return sigmoid(score)

  This script logic allows the model to ignore millions of dollars in routine selling while reacting aggressively to a $50,000 opportunistic buy by a Chief Medical Officer.

### **3.3 Sentiment Trend and Market Microstructure**

While point-in-time sentiment is noisy, the **trend** (first derivative) of sentiment often reveals information leakage.

* **Metric:** Sentiment\_Slope\_7D.  
* **Source:** FinBrain News Sentiment API.  
* **Logic:** Calculate the slope of the 7-day rolling average of sentiment scores. A sharp negative slope (![][image6]) in the T-14 window is a "Leak Signal," often preceding a CRL or delay announcement.  
* **Microstructure:** Integrate **Gamma Exposure (GEX)**. High positive GEX ("Gamma Pin") suggests market makers are suppressing volatility, anticipating a benign outcome. Conversely, high negative GEX indicates dealers are hedging against a crash, serving as a "Fragility Indicator".

## ---

**4\. Operational Intelligence: Indeed and "The Void"**

Operational data provides a window into a company's *actions* rather than its words. Companies preparing for a drug launch must hire commercial staff 3-6 months in advance. The absence of such hiring is a "smoking gun" for internal pessimism.

### **4.1 "The Void" Signal**

The forensic audit identified **"The Void"** as a massive negative predictor. It is defined as the total absence of job postings for commercial roles ("Sales Representative," "Key Account Manager," "Market Access") in the critical T-6 to T-3 month window before a PDUFA date.

**Metric Definition:** Commercial\_Hiring\_Void (Boolean).

* **Source:** Indeed / LinkedIn Job Scrapers.  
* **Logic:**  
  * Query active job listings for the ticker.  
  * Filter for keywords: "Sales," "Account Manager," "Reimbursement," "Launch."  
  * If Count \== 0 AND Days\_To\_PDUFA \< 180: Trigger "Void" Flag.  
* **Impact:** This signal caps the POA at **0.40**. The logic is that no rational management team would fail to hire a sales force for a drug they expect to approve, unless they have non-public knowledge of a delay or rejection (or a partnership deal, which must be checked as an exception).

### **4.2 The "Hiring Slope" and "Remediation" Lexicon**

Conversely, a surge in hiring acts as a confirmation of confidence.

* **Metric:** Hiring\_Slope.  
* **Calculation:** Perform a linear regression on the monthly count of open requisitions over the last 6 months.  
  ![][image7]  
  Where ![][image8] is the month index and ![][image9] is the job count. A slope ![][image10] (20% monthly growth) is a "Launch Ramp" signal.  
* **Forensic Lexicon:** Scan job descriptions for "Toxic" or "Remediation" keywords. Terms like **"CAPA Lead,"** **"FDA Response,"** or **"Remediation Consultant"** are forensic indicators of a failed inspection (Form 483\) that has not yet been disclosed. A spike in these terms is a Tier 1 predictor of a manufacturing-related CRL or delay.

## ---

**5\. Clinical Intelligence: Structural Forensics via ClinicalTrials.gov**

Clinical trial design is often more predictive of regulatory success than early-stage data. The ODIN v34 update must systematically penalize "fragile" trial designs that historically correlate with rejection.

### **5.1 The "Two-Trial Paradigm"**

The FDA standard for "substantial evidence" is typically two adequate and well-controlled Phase 3 trials. Submissions relying on a single trial ("p \< 0.05 in one study") are statistically fragile and prone to rejection unless specific regulatory flexibility (e.g., Orphan status) applies.

**Metric Definition:** Trial\_Count\_Risk (Float).

* **Source:** ClinicalTrials.gov API.  
* **Logic:**  
  1. Query for all Phase 3 trials linked to the asset/indication.  
  2. Count independent pivotal studies.  
  3. If Count \== 1 AND Orphan\_Status \== False: Apply a **0.9x Multiplier** (10% penalty) to the base POA.5  
  4. This aligns the model with the FDA's "Two-Trial" norm and penalizes the higher variance of single-trial submissions.

### **5.2 Geographic Risk and "Foreign Data" Trap**

The FDA has explicitly rejected applications based solely on foreign data (e.g., the sintilimab case) due to concerns over "generalizability" to the US population. ODIN must quantify this risk.

**Metric Definition:** US\_Site\_Ratio (Float).

* **Source:** ClinicalTrials.gov location\_countries field.  
* **Calculation:**  
  ![][image11]  
* **Thresholds:**  
  * If Ratio \< 0.20: Apply "Foreign Data Penalty" (-15 points).  
  * If Ratio \== 0 (No US sites): Apply "High Risk" cap (Max POA 0.50).  
  * This metric directly addresses the "Foreign Data Trap" identified in the audit.6

### **5.3 The "Delay Factor"**

Unplanned delays in trial completion often signal enrollment struggles, which in turn correlate with marginal treatment effects (patients/investigators are less eager to enroll).

**Metric Definition:** Trial\_Delay\_Months (Integer).

* **Calculation:** Actual\_Primary\_Completion\_Date \- Original\_Estimated\_Completion\_Date.  
* **Logic:** Delays \> 6 months without clear external justification (e.g., pandemic) serve as a proxy for "Marginal Efficacy Risk," triggering a small penalty to the clinical score.5

## ---

**6\. Scientific Validation: Bibliometric Forensics (PubMed & bioRxiv)**

Peer-reviewed literature provides an independent audit of a company's scientific claims. The ODIN v34 engine introduces bibliometric markers to measure "Scientific Velocity" and consensus.

### **6.1 Citation Velocity and Impact**

A high rate of citation indicates that the scientific community views the finding as foundational or disruptive.

* **Metric:** Citation\_Velocity (![][image12]).  
  ![][image13]  
* **Logic:** Using the PubMed/bioRxiv APIs, calculating ![][image12] for the asset's pivotal publications allows ODIN to rank the "heat" of the science. A ![][image12] in the top decile suggests strong validation, while a low ![][image12] for a late-stage asset suggests the mechanism is "stale" or ignored by peers.1

### **6.2 Relative Citation Ratio (RCR)**

To normalize for field differences (e.g., Oncology papers get more cites than Podiatry), we implement the NIH's **Relative Citation Ratio (RCR)**.

* **Metric:** RCR\_Score.  
* **Implementation:** Use Python libraries (e.g., metapub) to fetch co-citation networks. An RCR \> 1.0 indicates influence above the NIH median.  
* **Signal:** High RCR values correlate with "Scientific Consensus," reducing the risk of a "theoretical" rejection (where the FDA questions the mechanism itself).7

### **6.3 bioRxiv "Pre-Print" Signals**

For early-stage assets, peer-reviewed data may not exist. bioRxiv pre-prints offer a real-time view.

* **Metric:** Preprint\_Buzz.  
* **Logic:** Track Altmetric scores and download velocity of relevant pre-prints. A spike in attention *prior* to clinical data release is a bullish indicator of "Smart Money" or "Smart Science" interest.  
* **Negative Sentinel:** Scan abstracts for negative keywords ("failed to replicate," "toxicity," "off-target") to identify early warnings that haven't reached the mainstream press.1

## ---

**7\. Molecular & Manufacturing Forensics: ChEMBL & PrOCTOR**

The "Silent Killer" of biotech approvals is toxicity and CMC failure. The v34 update integrates physicochemical data to predict these risks *before* they manifest as clinical holds or CRLs.

### **7.1 The PrOCTOR Score**

We integrate the **PrOCTOR** (Predicting Odds of Clinical Trial Outcomes using Random-forest) method, which uses molecular properties to predict toxicity.1

**Metric Definition:** PrOCTOR\_Risk\_Score (Float).

* **Features:**  
  1. **Molecular Weight (MW):** High MW (\>500 Da) correlates with poor bioavailability and formulation challenges.  
  2. **Lipophilicity (LogP):** High LogP (\>5) is strongly correlated with off-target binding ("promiscuity") and liver toxicity (DILI).  
  3. **hERG Inhibition:** Using ChEMBL bioactivity data, check for hERG channel blockage (IC50 \< 10 µM), a proxy for QT prolongation and cardiac toxicity.5  
  4. **Target Network Degree:** Drugs targeting "hub" proteins with high connectivity are more likely to cause systemic side effects.  
* **Python Implementation:**  
  Python  
  from rdkit import Chem  
  from rdkit.Chem import Descriptors, Crippen

  def calculate\_molecular\_risk(smiles):  
      mol \= Chem.MolFromSmiles(smiles)  
      if not mol: return None  
      mw \= Descriptors.MolWt(mol)  
      logp \= Crippen.MolLogP(mol)

      risk \= 0  
      if mw \> 500: risk \+= 1 \# Rule of 5 violation  
      if logp \> 5: risk \+= 2 \# Toxicity/Bioavailability risk

      \# Check for Toxicophores (e.g., nitro-aromatics)  
      if has\_structural\_alerts(mol): risk \+= 3  
      return risk

* **Weighting:** This risk score feeds into the mfg slot in the ODIN kernel. A high PrOCTOR score lowers the POA ceiling, effectively modeling the "base rate" of toxicity failure.1

### **7.2 The "CMC Cliff" and Modality Penalties**

As noted in the audit, CMC issues drive 74% of CRLs. The risk is not uniform; it is concentrated in complex modalities like Cell & Gene Therapy (CGT).

* **Metric:** Modality\_Complexity\_Score.  
* **Logic:**  
  * Small Molecule: 1.0 (Baseline)  
  * Monoclonal Antibody: 1.5  
  * ADC / Bispecific: 2.0  
  * Cell / Gene Therapy: 3.0 (Highest Risk)  
* **Implementation:** This scalar acts as a multiplier for any detected manufacturing risk (e.g., a Form 483). A minor inspection finding at a small molecule plant might be ignored, but the same finding at a gene therapy plant triggers a massive penalty due to the "Process is the Product" reality.2

## ---

**8\. Technical Architecture: Script Additions and CUDA Optimization**

To operationalize these insights, the ODIN codebase requires specific additions to its Python ingestion layer and its CUDA scoring kernel.

### **8.1 Database Schema & Data Ingestion**

The ODIN\_PDUFA\_...csv input files must be expanded to include the new forensic columns.

* **New Columns:** insider\_conf\_score, hiring\_slope, commercial\_void\_flag, cmc\_risk\_score, citation\_velocity, us\_site\_ratio, inventory\_cap\_signal.  
* **Python Class Structure:**  
  A new ForensicDataFetcher class is required to modularize the scraping and calculation logic.  
  Python  
  class ForensicDataFetcher:  
      def \_\_init\_\_(self, tickers, nct\_ids):  
          self.tickers \= tickers  
          self.nct\_ids \= nct\_ids  
          self.chem\_client \= ChEMBLClient()  
          self.job\_client \= IndeedClient()

      def get\_hiring\_metrics(self, ticker):  
          \# Scrape jobs, calculate slope and void signal  
          jobs \= self.job\_client.get\_history(ticker)  
          slope \= calculate\_slope(jobs)  
          void \= check\_void\_signal(jobs)  
          return slope, void

      def get\_molecular\_metrics(self, smiles):  
          \# Calculate PrOCTOR score elements  
          return self.chem\_client.calculate\_risk(smiles)

### **8.2 CUDA Kernel Modifications (fused\_score\_kernel)**

The GPU kernel in ODIN\_GOD\_MODE\_V7\_WITH\_SOCIAL.py must be updated to process the new dense feature arrays.

* **Signature Update:**  
  C++  
  extern "C" \_\_global\_\_ void fused\_score\_kernel(  
      //... existing features...  
      const float\* \_\_restrict\_\_ insider\_score,  
      const float\* \_\_restrict\_\_ hiring\_slope,  
      const float\* \_\_restrict\_\_ proctor\_risk,  
      const int\* \_\_restrict\_\_ inventory\_cap,  
      //... weights...  
      const float\* \_\_restrict\_\_ w\_insider,  
      const float\* \_\_restrict\_\_ w\_hiring,  
      const float\* \_\_restrict\_\_ w\_proctor,  
      //...  
  )

* **Logic Injection:**  
  The scoring logic inside the kernel must be updated to apply the forensic overlays.  
  C++  
  // Accumulate Score  
  score \+= insider\_score\[i\] \* pw\_insider;  
  score \+= hiring\_slope\[i\] \* pw\_hiring;

  // Apply Penalties  
  if (proctor\_risk\[i\] \> 4.0) {  
      score \-= 0.15; // Toxicity Penalty  
  }

  // Apply Overrides (ASC 330\)  
  if (inventory\_cap\[i\] \== 1) {  
      score \= fmaxf(score, 0.85); // High Conviction Floor  
  }

  // Apply Void Cap  
  if (commercial\_void\_flag\[i\] \== 1) {  
      score \= fminf(score, 0.40); // Cap due to lack of prep  
  }

  This modification allows the highly parallelized GPU engine to perform the complex "Forensic Logic" across thousands of scenarios instantly.

## ---

**9\. Calibration Strategy: Platt Scaling and Validation**

The final step in the v34 upgrade is ensuring that the raw scores output by the CUDA kernel translate into accurate probabilities (minimizing the Brier Score).

### **9.1 Platt Scaling**

The audit recommends **Platt Scaling** (Logistic Calibration) over Isotonic Regression due to the limited sample size of biotech events (\<1,000 per indication). Isotonic regression tends to overfit in such sparse data regimes.

* **Method:** Fit a logistic regression to the raw model output ![][image14]:  
  ![][image15]  
  Where ![][image16] and ![][image17] are parameters learned on a holdout validation set (2020-2024 data). This transformation creates a smooth mapping from raw scores to calibrated probabilities.

### **9.2 The "Honest Backtest" Execution**

The validation of v34 must strictly follow the "Honest Backtest" protocol.

* **Timestamping:** Every data point (hiring count, citation, insider trade) must be timestamped. The backtest engine must assert Data\_Timestamp \< Catalyst\_Date.  
* **Blind Holdout:** The model parameters (![][image18] for Platt Scaling, feature weights) should be optimized on historical data up to 2024, and then tested "blind" on the 2025/2026 catalyst calendar to verify the Brier score reduction.

## ---

**10\. Strategic Recommendations & Conclusion**

The ODIN v34 architecture represents a paradigm shift from **analyzing what companies say** (clinical data) to **analyzing what they do** (forensic signals). By integrating the six Modular Content Providers—FinBrain, ClinicalTrials.gov, PubMed, ChEMBL, bioRxiv, and Indeed—the system moves beyond the commoditized analysis of p-values.

**Key Actionable Recommendations:**

1. **Deploy the "Void" Signal:** Immediately implement the Indeed scraper to detect the absence of commercial hiring. This single signal has the potential to catch \>50% of "surprise" CRLs.  
2. **Activate ASC 330 Override:** Use SEC scraping to identify Inventory Capitalization. Treat this as a definitive "Smart Money" signal that overrides weak retail sentiment.  
3. **Implement PrOCTOR Scoring:** Use RDKit and ChEMBL to assign a "Toxicity Base Rate" to every asset. Stop assuming all Phase 3 drugs have equal safety profiles.  
4. **Enforce Two-Trial Logic:** Hard-code the penalty for single-trial submissions in non-orphan indications to correct optimism bias.  
5. **Re-Calibrate with Platt Scaling:** Post-process all outputs to aggressively lower the Brier score, ensuring that a 70% probability actually means a 70% success rate.

By executing these specific script additions and metric fixes, ODIN v34 will evolve into a robust "Forensic Intelligence" engine, capable of identifying the invisible risks that define the modern biotech regulatory environment and achieving the "ALLFATHER" performance standards.

### ---

**Data Tables and Structural Summaries**

| Signal Cluster | Key Metric | Source | Predictive Function | Implementation |
| :---- | :---- | :---- | :---- | :---- |
| **Financial** | Inventory\_Cap\_Signal | SEC (ASC 330\) | **Tier 1 Override:** Signals probable economic benefit; vetoes negative sentiment. | Boolean Flag in DB; fmaxf logic in CUDA kernel. |
| **Financial** | Insider\_Confidence | FinBrain | **Alpha Generator:** Filters for opportunistic, clustered buying by insiders. | Float score; weighted sum in kernel. |
| **Operational** | Commercial\_Void | Indeed | **Failure Cap:** Absence of sales hiring \<6mo to PDUFA predicts CRL. | Boolean Flag; fminf cap at 0.40 POA. |
| **Operational** | Hiring\_Slope | Indeed | **Confirmation:** Rate of change in job reqs confirms launch readiness. | Linear Regression Slope (Float). |
| **Scientific** | Citation\_Velocity | PubMed/bioRxiv | **Validation:** High citation rate confirms scientific consensus/interest. | Normalized Float (citations/year). |
| **Clinical** | US\_Site\_Ratio | ClinicalTrials | **Risk Penalty:** Low US site count flags "foreign data" regulatory risk. | Ratio Float; penalty threshold \< 0.20. |
| **Clinical** | Delay\_Factor | ClinicalTrials | **Risk Penalty:** Unexplained delays proxy for enrollment/efficacy issues. | Integer (Months delayed). |
| **Molecular** | PrOCTOR\_Score | ChEMBL/RDKit | **Toxicity Base Rate:** Predicts safety/CMC failures based on structure. | Composite Float Score (MW, LogP, hERG). |
| **Manufacturing** | Modality\_Multiplier | FDA/Manual | **Risk Multiplier:** Amplifies CMC risk for complex modalities (CGT). | Scalar Multiplier (1.0 \- 3.0). |

*Table 1: comprehensive summary of new forensic signals for ODIN v34.*

#### **Works cited**

1. Enhancing Odin's Predictive Accuracy, [https://drive.google.com/open?id=14UKZD\_JWQ8AZ6snmdZk5vu\_qtFn406n-khNazF3XK3s](https://drive.google.com/open?id=14UKZD_JWQ8AZ6snmdZk5vu_qtFn406n-khNazF3XK3s)  
2. Biotech Research Mode: Catalyst & Signal Analysis, [https://drive.google.com/open?id=18qXWv6nEtcmXfud4ot6GzInGisbXmPCunqiLFgV9vAQ](https://drive.google.com/open?id=18qXWv6nEtcmXfud4ot6GzInGisbXmPCunqiLFgV9vAQ)  
3. Odin Biotech Catalyst Prediction Engine Audit.pdf, [https://drive.google.com/open?id=1NNkbLaC3OESD8uRN613i9ws6HoEPpSRw](https://drive.google.com/open?id=1NNkbLaC3OESD8uRN613i9ws6HoEPpSRw)  
4. ODIN\_COMPLETE\_SESSION\_2026-01-01.md.pdf, [https://drive.google.com/open?id=1PjMBAYWZI1IzAjIJTsXpFF6LnIHTGbPD](https://drive.google.com/open?id=1PjMBAYWZI1IzAjIJTsXpFF6LnIHTGbPD)  
5. Enhancing ODIN’s Predictive Accuracy with Six Data Feeds.pdf  
6. Biotech Prediction Model Research Plan, [https://drive.google.com/open?id=1gm9v0Q4FgRshMCv6bWPZYgE4v0Ir2xApJM6VhY7jeA8](https://drive.google.com/open?id=1gm9v0Q4FgRshMCv6bWPZYgE4v0Ir2xApJM6VhY7jeA8)  
7. openicite \- PyPI, accessed January 23, 2026, [https://pypi.org/project/openicite/](https://pypi.org/project/openicite/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA4CAYAAABAFaTtAAAFK0lEQVR4Xu3dW6jlUxwH8CWXmKG5uCXkmrvcxq1IuRQPvIyHkQcPEuEFIV6ckiIvrimX8DSSUDwwZA6KlJQymZRcEm+UUDxg/c5//2evvezd2XvOZf/N+Xzq29l7rX2m/9nz8mtdUwIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIDO2T/nq5w3eu+35GzPWbvjEwAATN3GnM05e+RclXPWYDcAANO0W866nDU5Mzm39doAAOiIA4rX23KuKd4DALBI9kk7v+ZsU/F6Jg0WcAAALND6nA05L+UcUvUBANAhLyYFGwBApynYAAA6TsEGANBx4xZsv+b8k/NXzvcjEv11TolfBgBg541bsMVZa++mpgiL1/OJ89guzvmy7ui4+1KzczZucAAA6IQo2A6rG0c4NjUF211p/ANy36sbsj3rhimqi88YSTwt54Gc1VUfALAC7JWaKcV2uvC33s9byw9lz+d8mnNvzuc57w92T9VTqXnmSUagygLtyZybivelT3K+yzm57lhCcR/qOXVj9kXdAACsHHHfZhQ8pd9z9u29jsNoDy76YiTrxuJ9F/ySmr/hjrpjHjHVWBenraNzbs85Lo0/erdYPkr9Q4CjuIxCOcT9qADAChRTbVGglaL4aYuDV3L2K/pC1y5UjxGyeOYo3CYRf8eJdWPPpTlX1I3LJP5P4nsPt+RcmXN8Wv7CEQDoiJ9yXk3NQv8Lcz5Lg2vIZlJ/N+bVqRmV6qIjUvOcT6fx16TFerlh4t/4JjVTwcdUfQv1cWq+x4dT88zDRCH5Q90IAKxcMbrWjpjFCM49OTf0u+dEAXReaoq2v6u+LonNB1G0/Vh3jDBbN/REwVoXTMOKwGiLQndYdi8+F2KKeTY1a9TK9/FzVa+tFb8fa+cAAOaKhW1p8JL0KN7iuIxQj6bFeq96vdtCxL81bsYRf88kn5+tG3rOzvmjeB/TwzEtWTs9NaNxw3Jk/2NzYoq1LHbjO59NzTO/VbQHBRsAsENsOCg3EMSI0cu99nB30RfuT8OLnPi9S1Iz1Tcs5/Y/uqTiOSaZEm3XidUey/m69/r6nNdSMz26ELGBoV0rGCOZj+ScmXNnag75PbzXF2LDw7ijhADALmrvnBdSMxL1c2oKhvj5Zs5Jvc8cmrMl59uc61Kz3uuiXl8XRRH0Yd04jyhMy9HFVhRrsfA/xOjaqMJuEvF8N6fme/wg9b/ndakZ0Stdm4YXxgAAA9anpmiL4i5GyTYMdnfOxjR6Ef8oR+VcUDemZrdpTGGGKOi2Fn0LVd/iELtU66Jxc2o2ewAAdEp7HtxM0RaL/08o3o8Sh/lGwTaOGOkqz5WLYqw9GPfUnNfT4Hlu0Tebc3nRtpguS/1z1kI83yQ3NwAALJtnc55IgxsGYmpwPu+kyYqbmP6txR2jXdFOxQIAdM4zOefn/Jn6u1Mf6ncP1W4yGEccpxFnn9XHdQAAMKZ2zVhcyRQjbbG2K+4JHaU9c23SLNXUJgDALm11ajY4hFhfFqNgMR0aR2GMEqNl9dln42Rt/DIAAJNpz31rxRlkb6f/7p4EAGAKDkxNcVaKtWzlgb4AAEzJQam/tuzxoj02HQw7Hw0AgP+hNal/ef0ocYNDfc0WAADLIG5hiOuzHk2Dd3EOo2ADAJiSuKg9xJ2fs1WikFvV61ewAQBMydbiddzTWSYOy21vQVCwAQBMSVxNdUbdWHkuZ3vOg3UHAABLLw7dBQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGDOv94g1+cU7qJVAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAABMUlEQVR4Xt2TMSiFURTHj1A8JKVX6tXblFIYTKwsUm9UBqNsL6PJoswUJSWDQdmMxGDDajGTyWKTxO90XN173veu9Cb+9Ru+87/3u/ee+78i/1I9MAvD0Oa8rKpwBZvwCDOpnde62OQN+ICFxM1oAG5gHwZhDNqTERmNwDOseiOnLhiCRXgX26p+98aDmmkK9uAWXuHo63syHvSTDsXOrGf/lfrEunwCHc7TppVcLVFLkyvwAGveEGvggS/GmoY3mPeG2L0v+2IsNV/EghE0LrbiE5zCUuQl2oI7sWTF0uBcFtS/pa/oXIqbpcHRe2/6ukKzis6lO2qo65/qcAY1scmjyQgLy4VY0iZgLhhluBdL1A7sSuOWu+FY7JnqY+kMhq68AtewDf3BcNKAaID+uj4BsfAvK1Wxhp8AAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAYCAYAAAAlBadpAAABDklEQVR4Xu3SP0uCURTH8RMVqBEUCOUgQriES0K9gcBApD1wcNTByXDvNTRGEA0iUdAQQVO+gNa2EBGipl5BQ34P917v8yflWcN+8Bk859z7PM/1ivxnUbOFYxxhLdKbmW3c4R4n6GKE/eDQbyngFRdYtbUl9PCEtK3FsoJLfKAY6V1jjJz9vYyMb4vs4kvMK+tGLik8Snixfs7VdELM4fygGSySHXyiL35TfcPQXFXMYt0kmBa+UcGemCfqZg9ouKE83tB2BVLCEKdiDk6jnzdA1g256NPfcWu94FD8Qk1dzOkHa9PoX6QXZCPasDmX+LkkyiaecYAyauH2/OglucEZOuIvUuLoBVmPFv9gJj0NJgMxBrpyAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAYCAYAAADKx8xXAAAAuUlEQVR4XmNgGDnACYjvAvEjIrELSBMjEE8B4pVArADlg8AcIP4HxB5QPjMQ2wPxAyA2BQmIA/EqIBaDKgABQSA+zQBRJI0kzgPEi4FYBsQBWVuIJAkC+kD8CYjXADELkjjIwElAzAvihAKxGpIkCEQD8X8gLkcTFwbiNAaEdzAAyH+/gdgGXQIfwOU/gsAYiL8yYPqPIMDlP7wA5On5DIPWf6A4PAfE7xggfoPhL0B8nQFi2CgY3AAAzMQr+zx1NKQAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAYCAYAAABqWKS5AAABMElEQVR4Xu2WMUsDQRBGRzSdFkEwiBZWtlFEbARBJIhgaZVebG0U/BeKlQgWVor/wlKwtRJCipQpJFaC+oa9w73lDgbC3QXcB6+42Sx8R74MEYlE/ie7+I59o3vuWqWsYyccTuE1PuBK8qzc4jfuJ8/TuIM93ExmZbOFZ/iCP3iePRZp4SMueLOmuAs9XPLms3iPy96sTDT8IR7gp+SE1wqcBrM2fuATznhzfakrnPNmVbAhBeGPcDWYdSX/a5rHY/mrVlUUhs9D+/6F2+FBTZjDF/W9Tszh0w+GfbfQELcAFg3qgtANZsEcvqjvFtbwxuiluNVswRRef4h3Mll9V0zhJ7Hviin8OH0vkzTXRXigO/4Vh+K6njrCN3EX6+IEB5LNpTmfJfuPIBKJRCL5/AJ4eE5BaitAMAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAXCAYAAABXlyyHAAAB0ElEQVR4Xu2WPyhFURzHf0KR//kXJZGSRckgxcAgkZTJZlCSxYSS1cImGZRMLKwYkUUpZWBQQklRbAYT32/nnZx737vd896772Y4n/oM73fu7d3vPef8zhVxOByO6MmDPXADbsFRmO+5IpwuOOQv/kcYdhGewxZYDffgNiw0rksFXxLvvYI/cMk7nBklEv7H2dAN32CfUWuFz3DYqKWCgcfgCPySLAO3wwO4D2t9Y1GyKipcg1ErgxdwV9QKCIMvLaPAei+dwk3Y5B2OnCJ4JMmBS+GZqKVaZdSDSDswG8SgqLe6LmofxYEOFhTYXw/COjCDjsNLuALLvcM5h2EYyh8s8sBsQpPwGs6LakzZUinq4WxkIFIPHyQ5WOSBB+ATnIXF3qGM4F5cEHWU2DitbgsMFlQPIjQwMWeZZ1ncy5kUwENJDqYDs6ewY4dhFVij9zE7YpwNS8OH/IAdRq0G3or68tJUwEZJfUylFVjjP5JsllIUtMEXUatN0w/fYW/iNyfhBn4bNRMdeNk/YAODd8ITuCPqcy/XTMBHOAOn4B2ck7/Z5BI/hvewOVEj7EGvoj4rtZ+itkKdcZ01DLsmahZyDWeRn4k07m3lcDgc/4NfkFpgYhUvlb0AAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAYCAYAAAAs7gcTAAAAyklEQVR4Xu3RsQtBURTH8SMpokRSVslgYDAbKMrfIKtZFgMjo1JmyYBRFrNdKYPJ5A+wKJOB73n3vZIno+n96jPczjm3+84T8fLv+FFEDWH4kEUVobc+iWKJDno4YowhplgjqI16wwAla0wkhQtWyOOKHSJajKMv9iQp4IYGAmgiZ9dc0aa7mPf/jD5phj1iHzUr+nETtJDAScyADmp0G1qzUscTI5TxQNeu6UVzZOyzpHHAAhu0cRazsi0qTqMT3URSzI/5dvbiygvC9RzA6VnpHQAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAYCAYAAADDLGwtAAAA9ElEQVR4XmNgGAXUBMxAbAzEdkDMiibHDxMDEROAuAqIDwFxL5IidSB+CcQRII4rENcAMR8QHwDilQwQG0AgGoi/AbEpiJMJxPpAbAkVBOuGgklAfBWIRZDEGBqA+AkQK0L5gkB8GoiXAjEjVIyBhwFi7RogZoGKgWz5BMTpUD4YSALxQyAuRxIDue83ENsgiTGIA/FdBoRCUJDsYcDiPpAbihkgbpzLAHHbfyCeD5WDAw4oBrkVZDooBEDuQw4BBhkgvs4AsYqbAeKZ6UB8BYjFkNSBfQcK/RyoonwgvgXEBsiKQAAUhSD3HYfiTgZILA0WAABa1ibOSzQ4bgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAAB/0lEQVR4Xu2VzSsFYRTGj1BEhJUi10fJRsrXP4CyIMVCLGVnZcGSkkRZECmyoGShrMiCcsOKNQuUklIWdmQjnsc7czt37jv3y7XRPPWrO+e8d95nzpx5j0igQIFSUT1YAOtgCORHp33FdVzP/y2DDpAdteKP1A9uQBMoBDPgGBTrRRYxvw9GQS2YAp/gyMlFlOeQKVWCOzCsYiXgCoypmE3Mb4Mi5zpLzAN/gUl3EVUjpgrzoEwn0hTNvoFmFePmOyAspvJ+2hJjcFzFWsE7OAEFKv5z00Yxr2ETVOtkimIfek1TNPQspkh+6gPXoFPFeB/eLyxxHpgf0J4Df6cqmvMzbYsnEt8cq7/oTdjEarPqZ6BdzNtIJFYiLHZz6Zjmx8f9b0GVJxdX5WBVkjPPnmPv2cylapr7TIB70ODJJSV+oGvgAoSiUzHyM+cX9xOPzXNJvF+MWOUVcCqJq+xqVuzmaPoJVHjiNtEwD4VS55ptx96OezSznzfAgZhTJRmzrnrFDAROMlfc7NDB3ZhTLqSuXbWJOR71MGF7LInFBwOZOPbYSpdgWsXqxFR5UMVGxJwKuyDHidEce/gFPCpexbzBiGiWr54twFZgS/xWLeBBzIc0IGYacnjlqjU94MNZ41aQLcQHsaEnrHSDOcnMNNTiSdIlZmBwtAcKFOi/6BtAKGR98OGIYgAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,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>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAYCAYAAAD3Va0xAAABP0lEQVR4Xu2TsSvEYRjHvzquRCmJZCBJjJIk2Qy3MJhlNdgMlE0y3M6m0NXdovwLV/4Di8lgMhkZbsD367mr9328d15G3ac+w+/5vvfe+3uf5wd0yWGE3tGPwAZdD9YUac2tOQjyiA3YgmsfNCnQKj2ifS6LWKSv9Ib2ukws0wrt94Fnmj7TOh2Mo68fX9EFV08yRh/pEx132TY9pj2unkSnqNMXOh/Up+gtHQ1qHdG96H7e6FKzphOU6WZrUS4XsM6pg2KNnuGHLqU4hG20T4dgszMTrchkC7bRKWyz3TjOR9P8Th9gM+PHQOjeSrD8ks7GsdEaSqkB9GgTfRqa7gFYN3Xyb2h+NEcnSM/MCr2nE7B8GG0aoeIq7N9SqBntPqFfodc4D57V2bngOZtJ2L3s0D3YsOr1/kTHu/mHfALn9jLHVDOs7gAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,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>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAYCAYAAACWTY9zAAACh0lEQVR4Xu2WTYhOYRiGb6FoSCLTRE0kJcpClMZYCGVBloqFkr9S/pKymtLUbGyYGf9JmkIKCyLKyA4bRUSKIisbZSGZcd/zvO/nPc93znGOvw1XXX3nnOc95zznef8+4D9/n7F0kr9YgQl0nL9YlRa6is6ho1xMKKETdLEPVKCdXg6/tdAN92kPfUdXZsMYQ/vodne9Dp30KmpWvAuWWDcdpuszUUt0EDUf6lAv9NIDPlDEZPqQnqZT6QI6OomPpzfpzuTaz7KEPqMzfSCPufQD3esDgYX0JazdrxKLsMEHUjRL2mCNvsK6T+eaQSnbYN080V2PaKYuC+pY1dbHLA3HHvXMAPIn2Agd9CR9RD/DGut8UdqInAvmoUlzhW6lR+g9eorup7fo4e9NG2iMlX1oA71U5VWZPareIGxSeDT2jtPZ4VxV+gSbSCvoED2L5sqsoW9gvVOIslb2WmO0JHhiYnkzSQntSc5XwyqvLtSaqCrOSOIRJfaezvKBFN34lh70gUBZYh5V9TWd7q57lNhH2OwvRF/3BdY4j6qJxXZFlU+p1JWacWXZ6yV6mWaSR9W+AFt845KTfsAW2Bbn0Srwirb6QIpm0lPYwlqE2lxH8yasdU+7xGa6KRzHymu2nqdTwnmKhk3e8xpogN7Bj8u/lj5Bc/IaBo9hy4xm3yHYR56h15C/IMceKB0aceCrO8vQ9vEclohHY0tViUuCP/foWdqStDVl0A276W26DpbY/EyLZnSPqqENuOiFVdlIL8J2iAzT6AvYgtpPj6G8GyOq7l06zwdqoEreQMH/OX3xDvqAHkW9vzF64CXUuyei93bRfeH4t7Oc7vIXK6BlQzvBH0nq3+MbjVlq7viHF5kAAAAASUVORK5CYII=>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAvCAYAAABexpbOAAAHLUlEQVR4Xu3da8hlUxzH8b9ccs01EjEjTeEF0ozcJ7dClLtClJhJXrgrl5pJQuQ6rtEMJZFCoVziTCQhvKBRyIxEUpR4weSyfrP2mv3f/7PPefY05zzPGfP91L9z9trn7L3PmRfze9baax0zAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgujg0AAACYDOemWpZqVWgHAADAhCGwAQAATDgCGwAAwIQjsAEAAEw4AhsAAMCEI7ABAABMuO9jAwAAmFnbp3osNk6z3WNDZdNUR6fa3LXp+Rluu41ec19ouybVVaENAABgRm2d6plU/1alXhM9fppqE/e6h1ItdNvjdk6qWaGtLbApdD2S6j1rhi8FL3/9g+ycap7b1vGedtsAAAATQyHtard9aqpXU22ZaqtUV7h946RzzU/1R6pDmrtaA9ttqb6xHLq2qdqWVNXV+6nOc9ubpVrktgEAAGbctpZDz27VtgLLs1aHmAWptqueFxqC1FCkqCdrR7dvFLoEtl0t3/i+1HJPWelR02fZs7yoomOdaPk1cywHw+Ik67+BXttzQxsAAMCM2S/VC5aDmpyZarXV94Q9VT0Wup/t2lSXVNvzU/26du9odAlsd6X6J9UbqS6zOrD1LIfQQter3sObLA+bqlfuRbdf54k30CuwTXUPHAAAwLR5INXZlgORKt771XPPFepusdz7dljVpqFT1Sh1CWzyY6p9QlsMmDdXjwemOt9yEN2/3r3muLGHrWc52I1KuUeQmuwCAGAiqSeqZ/1DiF4vNlgeMlXPlSg03ej2jUKXwKZg+a71D9fGwFYorMVjyqDA9kRoAwAAmBEa9puqZ0HDpZECVdHWy6VerONSnTWgDq1f2qpLYNNQrp8oUbxl9QQEeTDVLqm+sLr3UEOoha79B7ctH1n7sXXc+Fl86ZoAAABGZpnVQ0HLLYeaNqdZ/z4tpfFkqi9T3RD2rQ8Fol+svq573L4Y2BSoYlCUr6wZnD5J9XKqKy1f82tun6jnrRfaFO72CG0bg6nWr9P3qpnDg5SJHV6XoWX9UbB3bByztj9EAADYYM1OdWRo03/smqV5utX3so1bDGxaP64tPHxgOYQVek2Z0aprLs8LDe8uamkrkzDG4eDYMCGGrV+nf/PnrX8IulDguiPVCaHdh+5Bjkr1UmxcDzulet3q4F/WF9QfGOXz6ZxlWB8AgP+Fd1IdUD3XMhinWP6P+MO1rxi/EtgeTfWXDT637st7JTYOoP+8r68eiwus+asJo6Sh4JOtOaQ8jHoFp8uSqgZ5O9VP1t6rqWVdNIysnli/3IuONygARgr++uNgKnfHhiE0i/h4t631Bf09jius2zkBANhgHBsbppnWWlsXi1NtERsdDXnG4TptD5uAMQq6N69rYOsy3Lyv5dCpR9nBcrhVcFXvYpn9q3YFFn3u+dVzr239ukJhXcdT2Im9rTqHejT/tmYvqIKSjukpCJefEdP3EI+lXtOpAp7uSexCn7Ms/iyzrP8zamKJzgkAANAwysCm4KOeLR3zW8th53LLw38XpTqmev615d9I1XP1TCpg3W7NX7DoWXP9Ou/+6lHXE4PeEak+TvVnqsddu17bc9ui9e804WN5qussD1t6bbN+o66BTWHwTqsDq76f+F5do84JAADQMCywKYCVgKG6NWz7++/Uc6QepDIhZK7VYUr3ZmkIM/64vc7rQ6AWPC736vmhQk/HKr13CnptIVKhJ97Er+P5Y5ZjiMKdJpj42brSNuPY9xKqNHHEb7f1yOkz6Xr8xJGllofSPX1fOicAAEDDsMB2uOVeqlLqufLbs9a+MoeVVZaDSNl/kNv/s+VfgfBiYNP7y8+KDQpsC625uKwWWo50U39ciy8GNm9lbKj8ZnmBY0/LpfjvQBMH/LaGeiMFtZXWnJSicKbr99SmcwIAADQMC2xRW29WoZ4l3dTve6T2qh7VK6ahSgUa37MVA5t6ukoPVVy/TtRD52d96trbXtcWtHQ/oF5b6N4xHUtLg5RruLTevYb/TdtB4rBmGx1fEw48DQXHn1BTj2G8zw4AAGzkfG+V1pvTMiPDDAtshYLI55bvF1OQ0ppzOr6Cj2b06rkmBGifApuGShXk9J45VvPr111oefhQ7/2sanvO8nHU9nvVJjqu/y3aQuFOxyx0T5lu8FePoNa503X69fL0/i6fd6rA9qbV3/F3Vel62yZU6Lq7nBMAAGCgrmFCw4JdliIpPWwKinHWbVy/risFoQWx0XIvn47p6Zzq0dPkhnjv2WzrtqbfVIFtXaywbucEAACYFgp1q1Pda/2LB8u6rF8nCn2aofqw9feuFTpmXEi3jYJc/AWKcdM558VGAACADcHi2LCeNOw5bD080WzR2OM2bnGGKgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAZ8R8owpKdRszB1wAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAXCAYAAADUUxW8AAAA3ElEQVR4XmNgGNZAEoirgFgAXYIQYATiZiB+AsQyaHIEgTEQf4ViEJtowAnEi4H4ERD/BmIbVGn8IAiIu4G4Aoj/A7EvqjRuIAbEa4FYFojLGSCao1FU4AGlQBwDZYNsBGkGGUIQaDNA/MoD5cM0t8JV4ACsQDwFiG2RxEABBQqwhUhiGIAfiJcDsQqaOCiRPATiAwwI12CAIiBORxdkQGi+C8TiaHLgVARy2gUglkOTAwGQi44zQAwAGQQHIL+9Z4AECAg/B2ItJPk+IP6FJA9izwViNiQ1o2BwAwBqgCY8YTiPnwAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAABDElEQVR4XmNgGAXowAqIHwHxfyT8BYifQdl/gXgrEKvBNOACk4D4GxCboomrAvFdIL4OxDJocnDAA8QHgPgqEIugSoHBQgaIa3zRJWBACYifA/F8IGZEk4MZ/hOILVGlEMCPAWJDOroEEIQzQMJhChCzoMnBQSsDxAZPIJaEYnkgrgfil0AcCcTMcNVoAObE1wwQL8yC4rkMkDBpAWI+mGJsAJ//FRggMXAOiMVQpRAAn/9BABYDIO9hBbjiHwQ4gXgHEP8DYhc0OTAgFP+2DJDA3cUAUYsBNIH4LRAvZUD1PyjEQU5+D8RXGCAxggJAJj9kQKR9UDw/YYDkCRD9B4gfAHEuA8Qbo2D4AQDFDjxnJ33hQQAAAABJRU5ErkJggg==>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAYCAYAAAB5j+RNAAAB/0lEQVR4Xu2VO0gdQRSG/6AJCoKpTIIPEJQQLYRYWCQ2oqCFTQpB1FJS2EhAfLRiEQxWgYDBQixstBTBys5WQbCQ4ANRElAhYKOY+P+cO+7uuK67SYiB3A8+2Dvn7uyZmTMzQJ7/mGd0jD72A/fNAzpOD2iFF8tCNz2hP0Pq97fc8zn9TJ+6F9LQSM9y6vl3KKJLiB/oK9g3VmiJF4ulmM7RfXpBX0fDmSmnu7AElWgYJbSKDJPwhk7SEdjUd0bDmdHgNMhhP4Agcc1qdTR0kzK6SCthnSm5nsg/sqN+ftBWr111PQr7xqAXi2WI9uaeNWN6MW7EaSmkC/SIvoSdALKWTtNt2gJLNJF6WK25wnTJTVz/Iztu2XZgyThn6RYdgNV4Ig/pR9ocanO1oo5+laR6a4JtBJVRYoJt9BLR88gZt8vSclu9CbdTv9OGaCiglM7TGq9dtbEH6yDVGeSRdL6JJ7ClPaYvvNg17+hbvxFBcl9gHYXRlXbXtZZ0vgltPK3MJ9jGiaAdoppYp1VeTGhG12AJKlHHc/oVd59NWkotqe7nMKrvflgZLcO+E0GFf4qgrrTV60LxKdi95+J6nqGPYEu0Aftw3AHdh+DudO/qtpGHsKQ2aRctyL3zx9HoO/zGfwHVyAckL+u90U7fI8XJ/rfRrKlebhRynjy3cAWKf3DBXBUyGgAAAABJRU5ErkJggg==>