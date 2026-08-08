# **Forensic Audit: ODIN Biotech FDA Prediction Model – Credibility Stress-Test & Quantitative Verification**

**DATE:** January 23, 2026

**AUDIT REFERENCE:** QA-2026-ODIN-BIO-AUDIT-FINAL

**SUBJECT:** Comprehensive Verification of Theoretical Basis, Operational Risks, and Predictive Accuracy

**CLASSIFICATION:** CONFIDENTIAL / INTERNAL RISK COMMITTEE

## ---

**1\. Executive Forensic Overview**

The biotechnology sector represents the frontier of high-risk, high-reward investing, characterized by binary outcomes, extreme information asymmetry, and volatility profiles that defy standard market beta. Traditional fundamental analysis—predicated on the review of publicly available clinical data, management guidance, and discounted cash flow (DCF) models—has become increasingly insufficient for generating alpha in a market dominated by algorithmic trading and rapid information diffusion. The ODIN Biotech FDA Prediction Model positions itself as a "quantamental" engine designed to bridge this gap, synthesizing insider trading signals, clinical trial probabilities, natural language processing (NLP) sentiment scores, and derivatives market flow into a cohesive predictive framework.

This report constitutes an exhaustive forensic audit of the ODIN model, executed to stress-test the credibility of its quantitative specifications, academic lineage, and operational logic. The objective is not merely to verify the existence of the cited parameters but to rigorously evaluate their application in a live trading environment. We have decomposed the model’s primary pillars—Insider Alpha, Clinical Priors, NLP Sentiment, Forensic Accounting, and Derivatives Flow—and cross-referenced every claim against foundational academic literature, forensic accounting standards, and real-world market microstructure.

Our analysis reveals a model architecture that is theoretically sound in its individual components but operationally fragile in its integration. While the quantitative inputs are largely accurate to their source materials, the audit has identified critical "fault lines"—specific logical or specification errors—that, if left unaddressed, could lead to catastrophic capital allocation failures.

### **1.1 Summary of Forensic Findings**

The audit's conclusions are categorized by the severity of the operational risk they pose to the model's predictive integrity.

#### **1.1.1 Critical Fault Lines (High Severity)**

The most significant risks identified stem from the misapplication of aggregate statistics to specific use cases and ambiguous signal definitions.

**The Hematology Artifact (Base Rate Fallacy)** The model currently utilizes a **93.1%** probability of success (PoS) prior for Hematology assets.1 Forensic verification confirms this figure is accurate only for the transition from New Drug Application (NDA) to Approval.1 However, applying this rate to early-stage assets (Phase I or II) constitutes a gross statistical error. The cumulative Likelihood of Approval (LOA) for Hematology assets from Phase I is only **23.9%**.1 Using the 93.1% prior for early-stage drugs would result in a massive overestimation of safety, exposing the fund to unpriced binary risk.

**Derivatives Signal Ambiguity (The PCR Paradox)** The model specifications define a Put-Call Ratio (PCR) threshold of **\> 1.2** as a signal.1 However, the logic fails to distinguish between the "Contrarian" interpretation (where high PCR indicates an oversold bottom, a Buy signal) and the "Informed Trading" interpretation (where high PCR indicates insider hedging ahead of bad news, a Sell signal). Academic literature confirms that in the context of binary biotech events, high put volume is predictive of negative returns.2 The model must explicitly reject the contrarian view to avoid buying into informed sell-offs.

**Manufacturing Blindness (The CMC Cliff)** The current model heavily weights clinical efficacy data (p-values) but lacks a dedicated module for Chemistry, Manufacturing, and Controls (CMC) risk. Audit data reveals that between 2020 and 2024, approximately **74%** of Complete Response Letters (CRLs) cited CMC deficiencies rather than clinical efficacy failures.3 A model focused solely on clinical data will inevitably produce "false positives" on assets that work biologically but fail operationally.

#### **1.1.2 Validated Quantitative Foundations**

Despite the risks noted above, several core components of the ODIN model have withstood forensic scrutiny:

**Insider Trading Coefficients** The model’s use of a **0.90** coefficient for "Opportunistic Buys" and a **\-0.78** coefficient for "Opportunistic Sells" is precise and verified against the Cohen, Malloy, and Pomorski (2012) literature.1

**Calibration Methodology** The selection of **Platt Scaling** over Isotonic Regression is methodologically correct for the biotech domain. Given that specific indications rarely offer datasets exceeding 1,000 samples, Platt Scaling minimizes overfitting and provides superior calibration, aligning with the findings of Guo et al. (2017).1

**Financial Forensics (Inventory Capitalization)** The inclusion of Inventory Capitalization (ASC 330\) as a bullish signal is a robust, "costly" signal that effectively filters management optimism from genuine conviction.3

The following sections detail the granular evidence for these findings, spanning the theoretical basis, operational implementation, and strategic remediation required for the ODIN model.

## ---

**2\. Clinical Probability Priors: The Foundation of Risk**

The cornerstone of any biotech predictive model is the accurate estimation of base rates. The ODIN model utilizes the "Clinical Prior" module to assign a base probability of success (PoS) to a drug candidate based on its therapeutic area and development phase. The audit identified specific claims requiring rigorous contextualization.

### **2.1 The BIO Industry Analysis (2011-2020)**

The quantitative foundation for these priors is the "Clinical Development Success Rates and Contributing Factors 2011–2020" report by BIO, QLS Advisors, and Informa.1 This dataset is the industry standard for benchmarking R\&D risk.

#### **2.1.1 The "93.1%" Hematology Statistic**

The forensic audit traces the "93.1%" figure directly to the **NDA/BLA to Approval** phase transition for Hematology. Verification confirms: "The NDA/BLA (New Drug Application/Biologic License Application) to approval success rate for Hematology therapies is 93.1%".1

**Critical Context:** This rate applies *only* to drugs that have already successfully completed Phase III trials and have been submitted to the FDA for review. The high success rate at the NDA stage reflects the fact that Hematology endpoints (e.g., blood cell counts, remission rates) are objective and quantifiable, leading to fewer regulatory surprises late in the process. However, if the ODIN model applies this 93.1% probability to a Hematology drug currently in Phase I or Phase II, it is committing a gross error.

#### **2.1.2 The "Valley of Death": Phase II to Phase III**

To stress-test the model's risk management parameters, we examined the success rates for earlier phases, specifically the transition from Phase II to Phase III.

* **Industry Average:** The transition success rate from Phase II to Phase III across all therapeutic areas is a "dismal" **28.9%**.5 This is the lowest success rate of any phase in drug development, representing the "proof-of-concept" hurdle where most hypotheses fail.  
* **Hematology Exception:** Hematology performs significantly better than the average at this stage, with a Phase II success rate of **48.1%** (![][image1]).1  
* **Implication:** While 48.1% is nearly double the industry average of 28.9%, it is still essentially a coin flip. The ODIN model must account for this steep drop-off. A Hematology asset in Phase II should have a prior probability of \~48% for the next phase, not 93.1%.

**Table 1: Verified Clinical Phase Transition Success Rates (BIO 2011-2020)**

| Therapeutic Area | Phase I → II | Phase II → III | Phase III → NDA | NDA → Approval | Cumulative LOA (Phase I) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Hematology** | 69.6% | 48.1% | 76.8% | **93.1%** | **23.9%** |
| Ophthalmology | 71.6% | \~51.2% | \~57.8% | \>90% | High (\>15%) |
| Oncology (All) | 55.0% | \~24.6% | \~47.7% | 92.0% | \~5.3% |
| Urology | Low (\<50%) | 15.0% | 69.2% | High | \~3.6% |
| **Industry Avg** | **52.0%** | **28.9%** | **57.8%** | **90.6%** | **7.9%** |

Source: BIO Industry Analysis 2011-2020 1

### **2.2 Synthetic Control Arms (SCAs) and Counterfactual Modeling**

Beyond standard randomized controlled trials (RCTs), the ODIN model integrates signals from Synthetic Control Arms (SCAs). SCAs utilize patient-level data from external sources—historical clinical trials, real-world data (RWD), and disease registries—to create a comparator arm for single-arm studies or to augment the control arm of randomized trials.7

#### **2.2.1 Mechanisms of Bias Reduction**

Single-arm trials, while cost-effective and faster to recruit, introduce significant bias due to the lack of randomization. SCAs aim to mitigate this by providing a "counterfactual" derived from observed historical data. Unlike purely synthetic data generated by generative adversarial networks (GANs), robust SCAs are built on high-quality historical clinical trial data (HCTD). HCTD possesses greater fidelity, standardization, and completeness compared to general real-world data (RWD) sourced from heterogeneous electronic health records (EHRs).7

For the institutional investor, the presence of a robust SCA in a Phase 2 trial design allows for a more accurate estimation of the drug's treatment effect size relative to the Standard of Care (SoC) prior to the pivotal Phase 3 readout. By modeling the SCA effectively, investors can identify "false positives" in early-stage open-label studies where perceived efficacy might be driven by patient selection bias rather than the drug's mechanism of action.

#### **2.2.2 The Risk of Unknown Confounding**

However, a legitimate and critical criticism of SCAs is "unknown confounding." This statistical phenomenon occurs when there is a material difference in baseline characteristics between the investigational arm and the synthetic control arm that is not measured or controlled for in the analysis. If the SCA population differs in prognostic factors—such as genetic biomarkers, prior lines of therapy, or performance status—the comparison becomes invalid.7

Investors must therefore perform independent covariate balance checks, verifying that the SCA matches the treatment arm across all known prognostic factors to validate the signal. The FDA has demonstrated a willingness to reject or delay applications where the external control is deemed non-comparable. Therefore, investors must prioritize SCAs derived from recent, regulatory-grade historical trials and assess whether the FDA has explicitly endorsed the external control strategy for the specific indication.8

## ---

**3\. The Alpha Engine: Decoding Insider Information**

The "Alpha Engine" of the ODIN model is predicated on the hypothesis that corporate insiders—CEOs, CFOs, and Directors—possess superior information regarding the probability of regulatory success. However, the raw data of insider trading is noisy; insiders trade for liquidity, diversification, and tax purposes. The ODIN model attempts to filter this noise using the taxonomy proposed by Cohen, Malloy, and Pomorski (2012), distinguishing between "Routine" and "Opportunistic" traders.

### **3.1 Theoretical Framework: The Cohen-Malloy-Pomorski Lineage**

The ODIN model’s reliance on *Decoding Inside Information* (2012) is scientifically robust. The fundamental premise of this research is that not all insider trades are created equal. By stripping away trades that follow a predictable calendar pattern, the remaining "opportunistic" trades reveal a potent predictive signal.

#### **3.1.1 The Identification Algorithm**

The audit verified the algorithm used by ODIN to classify traders, ensuring it matches the academic specification:

* **Routine Traders:** Defined as insiders who have placed a trade in the same calendar month for at least **three consecutive years**.1 This definition is rigid and backward-looking. The rationale is that trades occurring with such temporal regularity are likely driven by liquidity needs (e.g., paying for tuition, tax liabilities) or compensation structures (e.g., vesting schedules) rather than private information.  
* **Opportunistic Traders:** Defined as "everyone else"—insiders for whom no discernible temporal pattern can be detected in their past trading history.1

**Operational Consequence:** This classification introduces a significant operational constraint known as the **"Cold Start" problem**. To classify a trader as routine, the model requires at least three years of historical data. In the biotech sector, which is dominated by recent IPOs and spin-outs, many insiders will lack this history. The ODIN model must default these unclassified traders to "Opportunistic" or "Unclassified," but this dilutes the signal. The audit recommends a "Provisional Opportunistic" status for insiders at firms \<3 years old, heavily weighted by trade size rather than pattern.

### **3.2 Quantitative Verification of Regression Coefficients**

A primary focus of the audit was to verify the specific quantitative claims made in the ODIN specifications regarding regression coefficients. The model cites an opportunistic buy coefficient of **0.90** and an opportunistic sell t-statistic of **5.67**.

#### **3.2.1 The "Opportunistic Buy" Coefficient (0.90)**

The audit confirms the accuracy of this parameter. In the Fama-MacBeth regression analysis presented in Table III of the source text, the coefficient for the "Opportunistic Buy" variable is reported as **0.90** (with a t-statistic of 4.64).1

* **Interpretation:** This coefficient implies that the presence of an opportunistic buy signal is associated with an incremental increase in future monthly returns of **90 basis points**, after controlling for standard risk factors.  
* **Context:** This is a massive alpha signal. 90 basis points per month translates to over 10% annualized abnormal returns solely from the buy signal.  
* **Comparison to Routine:** In the same regression specifications, the coefficient for "Routine Buy" is significantly smaller (\~30 basis points) and often marginally significant. This validates the ODIN model's logic: following all insiders indiscriminately captures only a fraction of the available alpha.

#### **3.2.2 The "Opportunistic Sell" Signal (t-stat 5.67)**

The audit also verified the sell-side parameters.

* **Coefficient:** The literature reports that opportunistic sells are associated with a decrease in future returns of **\-78 basis points**.1  
* **Statistical Significance:** The t-statistic for this coefficient is **5.67**. A t-statistic of this magnitude (![][image2]) indicates an extremely high level of statistical confidence. It confirms that opportunistic selling is not merely a random fluctuation but a robust predictor of negative stock performance.  
* **Contrast with Routine Sells:** Routine sells, by comparison, have a coefficient of roughly **\+4 basis points** with a t-statistic of 0.24, effectively zero.1 This stark contrast validates the ODIN model's logic of filtering out routine sales; keeping them in the dataset would dilute the signal-to-noise ratio significantly.

**Table 2: Verified Coefficients from Cohen, Malloy, and Pomorski (2012)**

| Signal Type | Coefficient (Monthly Returns) | t-Statistic | Forensic Verdict |
| :---- | :---- | :---- | :---- |
| **Opportunistic Buy** | **0.90 (90 bps)** | **4.64** | **VERIFIED** 1 |
| **Opportunistic Sell** | **\-0.78 (-78 bps)** | **5.67** | **VERIFIED** 1 |
| Routine Buy | \~0.30 (30 bps) | Marginal | VERIFIED 1 |
| Routine Sell | \+0.04 (4 bps) | 0.24 | VERIFIED 1 |

### **3.3 The "Sudden Silence" Signal**

While verifying the "active" trading signals, the audit identified a potential area for model enhancement based on the research snippets. Research by Hong et al. suggests that **"Sudden Insider Silence"** can also be a powerful predictor.

* **Mechanism:** When insiders who typically trade routine patterns suddenly stop trading, it may indicate they are in possession of material non-public information (and are thus restricted from trading or afraid to trade).  
* **Predictive Value:** Snippets note that "Multiple Insider Silence" (MPPN) following routine purchases has a coefficient of **\-0.61%** for cumulative three-month returns.1  
* **Recommendation:** The current ODIN specifications focus heavily on active opportunistic trades. Integrating a "Silence" module—specifically tracking the cessation of established routine selling—could provide a valuable negative signal (indicating bad news is pending, preventing the insider from selling due to legal risk).

## ---

**4\. NLP Architecture and Sentiment Analysis**

The third pillar of the ODIN model is its Natural Language Processing (NLP) engine, designed to read regulatory filings, news releases, and earnings transcripts to gauge sentiment. The specifications point to **ProsusAI/FinBERT**.1 This section audits the architecture, the scoring mechanisms, and the crucial discrepancy regarding the score range.

### **4.1 Model Architecture and Provenance**

The choice of FinBERT (ProsusAI) is forensically sound and represents an industry-standard best practice for financial NLP.

* **Base Model:** BERT (Bidirectional Encoder Representations from Transformers).  
* **Domain Adaptation:** Standard BERT models often fail in financial contexts. For example, the word "liability" is negative in general English but neutral/descriptive in a financial balance sheet context. FinBERT addresses this by pre-training on a large financial corpus (**Reuters TRC2**) and fine-tuning on the **Financial PhraseBank**.11  
* **Training Specifics:** The model is trained using parameters such as a learning rate of 2e-5, 4.0 epochs, and a max sequence length of 64\.12

### **4.2 The Sentiment Score Specification Error**

A major "fault line" was detected in the ODIN specifications regarding the sentiment score range. The specifications examined imply a range of **\-0.5 to \+0.5**. The forensic audit reveals this is non-standard.

#### **4.2.1 Standard Scoring Calculation**

The standard output of the FinBERT model is a softmax probability distribution across three classes: **Positive, Negative, and Neutral**.11

* **Formula:** The sentiment score is typically calculated as:  
  ![][image3]  
* **Theoretical Range:** Since ![][image4] and ![][image5] are probabilities ranging from 0 to 1, the difference between them theoretically spans **\-1.0** (100% certainty of negative) to **\+1.0** (100% certainty of positive).  
* **Discrepancy:** The ODIN specification of "-0.5 to \+0.5" is inconsistent with this raw calculation.

#### **4.2.2 The "Neutrality" Hypothesis**

Investigation into the research snippets offers a plausible explanation for the non-standard range, suggesting it is a **Decision Boundary** rather than a raw output range.

* **Snippet Evidence:** Snippets explicitly state: "a sentiment score above 0.5 is considered positive and between \-0.5 and 0.5 the sentiment score is classified neutral".1  
* **Interpretation:** It appears the ODIN model employs a **"Noise Filter"** where any score with an absolute value less than 0.5 is discarded or treated as neutral. This is a robust design choice for a trading model, as it filters out low-conviction signals.  
* **Uncertainty Clustering:** Research highlights that for many inputs, FinBERT's predicted probabilities cluster around neutral, indicating high uncertainty.1 The model often struggles to confidently classify complex financial text, further validating the need for the "Neutral Zone" filter.

### **4.3 Simulation of Advisory Committee (AdCom) Debates**

Advanced frameworks go a step further by simulating the FDA Advisory Committee (AdCom) meeting itself. "Mock Panel" agents, primed with the specific scientific conservatism of the FDA (the "Reviewer" agent) and the optimism of the sponsor (the "Sponsor" agent), debate the briefing materials in a round-table format. The "Committee" agents then vote based on the simulated discussion. This approach helps identify weak points in the sponsor's data package—such as unproven surrogate endpoints, safety signals, or missing data—that are likely to trigger a negative vote or a split decision.7

## ---

**5\. Forensic Accounting and Financial Integrity**

For commercial-stage biotech companies, or those approaching commercialization, the analysis shifts to revenue verification, earnings quality, and the detection of aggressive accounting practices. The ODIN model incorporates several forensic tools to audit the "Financial Integrity" of a sponsor.

### **5.1 Inventory Capitalization (ASC 330\)**

A novel and highly effective signal identified in the audit is the use of **Inventory Capitalization** data under **ASC 330**.

* **Accounting Standard:** Under US GAAP (ASC 330), a company may capitalize pre-approval inventory only if the future economic benefit is **"probable"**.3  
* **The Signal:** Given the severe financial penalty of writing down inventory if approval is denied, management will only capitalize if they possess extremely high conviction—likely derived from private, positive communications with the FDA (e.g., successful mid-cycle review meetings).  
* **Predictive Weight:** This signal acts as a **Tier 1 Override**. If Inventory\_Cap\_Signal \== True, the model should effectively "veto" negative sentiment or weak clinical signals, raising the minimum PoS floor to **0.85**.3 It prioritizes audited financial commitments over public PR statements.

### **5.2 Detecting Channel Stuffing**

Biotech companies under pressure to meet revenue targets may engage in "channel stuffing"—shipping excess inventory to distributors to recognize revenue prematurely, borrowing from future quarters.

* **DSO and Inventory Divergence:** A classic quantitative signal of channel stuffing is a divergence where Days Sales Outstanding (DSO) and Inventory Turnover slow down while reported revenue grows. This indicates that distributors are holding unpaid, unsold stock.7  
* **Investment Signal:** This is particularly relevant for companies with a newly approved drug. If early sales numbers are high but DSO is ballooning, it suggests the demand is artificial, predicting a revenue "miss" in subsequent quarters as distributors work through the glut.

### **5.3 Benford’s Law Forensics**

Benford's Law posits that in naturally occurring datasets, the leading digit '1' appears about 30% of the time, with decreasing frequency for subsequent digits. Deviations from this distribution in financial statements or clinical trial data can indicate manual manipulation or fabrication.

* **Application:** Investors apply this test to revenue figures and trial enrollment counts to flag anomalies that require deeper investigation.7 A dataset that fails the Benford test is a high-risk flag for fraud.

## ---

**6\. Manufacturing Risk and The "CMC Cliff"**

Perhaps the most glaring deficiency identified in the current ODIN architecture is the inability to predict manufacturing-related failures. Analysis of Complete Response Letters (CRLs) reveals that this is the single largest source of "surprise" rejections.

### **6.1 The "Silent Killer": CMC Failures**

* **Statistic:** Between 2020 and 2024, approximately **74%** of CRLs cited **Chemistry, Manufacturing, and Controls (CMC)** deficiencies rather than clinical efficacy failures.3  
* **The Blind Spot:** A model focused solely on P-values and clinical trial endpoints will miss this risk entirely. A Phase 3 trial can meet all endpoints (![][image2]), yet the application can be rejected because the commercial manufacturing facility failed inspection.

### **6.2 Integrated Forensic Solutions**

To address this, the audit recommends the integration of a **"CMC Risk Module"** utilizing orthogonal data streams:

#### **6.2.1 Form 483 Prediction**

Models utilizing historical inspection data and facility-specific "risk scores" can predict the likelihood of a Form 483 issuance. Citations for "Data Integrity" are strong predictors of escalation to Warning Letters.7

#### **6.2.2 Hiring Lexicon Forensics**

Scanning job postings (Indeed/LinkedIn) for "remediation" keywords can reveal undisclosed problems. Terms like **"CAPA Lead," "FDA Response,"** or **"Remediation Consultant"** are forensic indicators of a failed inspection that has not yet been disclosed to the market. A spike in these terms is a Tier 1 predictor of a manufacturing-related CRL.3

#### **6.2.3 Satellite Surveillance**

Satellite monitoring of manufacturing plants can reveal operational disruptions. A cessation of activity in employee parking lots or loading docks at a key manufacturing site may indicate a shutdown, strike, or maintenance issue before it is reported to the market.7 This is particularly valuable for single-product companies where a manufacturing halt is an existential threat.

## ---

**7\. Operational & Legal Forensics: The Shadow Signals**

Beyond the clinical and financial data, a biotech company is an operating entity with a supply chain, a workforce, and a legal docket. Disruptions in these areas often precede clinical delays or regulatory enforcement actions.

### **7.1 Supply Chain Transparency and NHP Shortages**

The supply of Non-Human Primates (NHPs), specifically cynomolgus macaques, is a critical bottleneck for preclinical toxicology studies required for IND filings.

* **Bill of Lading Analysis:** By analyzing Bill of Lading (shipping manifest) data, investors can track the import volumes of NHPs. A disruption in NHP supply—often due to geopolitical tensions or wildlife trade restrictions (e.g., recent DOJ investigations into Cambodian imports) leads to significant delays in preclinical timelines.7  
* **Investment Signal:** Companies with secured, diversified NHP supply chains trade at a premium during shortages. Conversely, heavy reliance on flagged importers poses a significant operational risk that can delay entry into the clinic by 6-12 months.

### **7.2 Legal and Intellectual Property (IP) Alpha**

Biotech valuation is inextricably linked to intellectual property (IP) exclusivity.

* **Patent Litigation Prediction:** Models using NLP to analyze claim text can predict outcomes with accuracy rates exceeding 70%. Characteristics such as text complexity, scope, and semantic ambiguity are powerful predictors of invalidity decisions.7  
* **Qui Tam and Whistleblower Monitoring:** Under the False Claims Act (FCA), whistleblowers (relators) file Qui Tam lawsuits alleging fraud against the government. These cases remain under seal for 60 days—and often years—while the DOJ investigates. While the contents are sealed, the existence of a sealed case involving a specific entity can sometimes be inferred through metadata leaks in federal docketing systems (PACER). Monitoring dockets for "Sealed vs. Sealed" filings where the defendant's name might be momentarily visible or inferred allows investors to position themselves ahead of the public revelation of a massive liability.7

## ---

**8\. Derivatives and Market Sentiment: The Put-Call Ratio**

The final component of the ODIN model is the derivatives market signal, specifically the **Put-Call Ratio (PCR)**. The audit identified a significant ambiguity in the interpretation of this signal that requires immediate rectification in the model specifications.

### **8.1 The Interpretation Conflict: Informed vs. Contrarian**

The ODIN specifications cite a PCR threshold of **\> 1.2**. The forensic audit reveals two conflicting interpretations of this threshold in financial literature.

#### **8.1.1 The Contrarian View (Standard Technical Analysis)**

* **Logic:** When PCR is high (\>1.2), it means put volume significantly exceeds call volume. This indicates extreme market pessimism.  
* **Signal:** Contrarian theory suggests that when the "crowd" is extremely bearish, the market is oversold and due for a rebound. Thus, PCR \> 1.2 is often treated as a **Bullish** signal.15

#### **8.1.2 The Informed Trading View (Academic Finance)**

* **Logic:** In the context of "Informed Trading" (specifically around binary events like FDA approvals or earnings), high put volume often represents "smart money" hedging or betting on a negative outcome.  
* **Signal:** Research by **Pan and Poteshman (2006)** and others indicates that high put-call ratios predict **negative** future returns because informed traders prefer the options market for its leverage.1  
* **Snippet Evidence:** "Option traders are considered among the most informed investors... the put-call ratio that aggregates information content of option trades earned a 0.24% weekly alpha".1

#### **8.1.3 The ODIN Resolution**

Given that ODIN is an "Insider" and "Informed" trading model (based on the Cohen et al. lineage), it must interpret the PCR \> 1.2 signal through the lens of **Informed Trading**, not Contrarianism.

* **Audit Requirement:** The model specification must explicitly define PCR \> 1.2 as a **Negative/Bearish signal** in the days leading up to an FDA decision. Interpreting it as a contrarian "Buy" signal in a binary biotech event (where the stock can drop 80% on a failure) would be ruinous.

### **8.2 The 5-Day Informed Window**

The timing of the options signal is critical. The audit verifies the **5-day window** as the optimal lookback period for detecting informed flow.

* **Evidence:** Informed options trading is detectable in the 5-day window prior to significant corporate announcements (M\&A, FDA).1  
* **Mechanism:** Snippets explicitly link "Informed options trading prior to FDA announcements" to this window. Extending the window beyond 5-10 days introduces too much noise.

## ---

**9\. Chemical and Biological Forensics: PrOCTOR and CheMBL**

The audit verified the inclusion of the **CheMBL** Model Context Protocol (MCP) as a "Reality Check" for the physical viability of the drug candidate.

### **9.1 The PrOCTOR Score**

* **Methodology:** PrOCTOR (Predicting Odds of Clinical Trial Outcomes using Random-forest) integrates chemical structure properties with target-based features to predict toxicity.18  
* **Key Inputs:**  
  * **Lipophilicity (LogP):** High LogP (\>5) correlates with "promiscuity" (off-target binding) and drug-induced liver injury (DILI).  
  * **Target Network Degree:** Drugs targeting "hub" proteins (highly connected in the biological network) are more likely to cause pleiotropic side effects.18  
* **Predictive Power:** The audit confirms that PrOCTOR accurately differentiates between FDA-approved drugs and those that failed for toxicity, often identifying "false positives" in early clinical data where safety signals were subtle.20  
* **Implementation:** ODIN uses this as a **negative filter**. A "bad" PrOCTOR score lowers the PoS ceiling, effectively modeling the base rate of toxicity failure.

## ---

**10\. Scientific Validation: Bibliometrics**

The audit evaluated the use of **PubMed** and **bioRxiv** data to gauge "Scientific Velocity."

### **10.1 Citation Velocity and RCR**

* **Citation Velocity:** The rate at which a paper accrues citations. High velocity on a pre-print describing the drug's Mechanism of Action (MoA) serves as a proxy for **"Community Validation"**.18  
* **Relative Citation Ratio (RCR):** A metric that normalizes citations by field. An RCR \> 1.0 indicates influence above the NIH median.  
* **Correlation:** High RCR values correlate with "Scientific Consensus," reducing the risk of a "theoretical" rejection where the FDA questions the mechanism itself.3  
* **Pre-print Buzz:** A spike in bioRxiv downloads and Altmetric scores prior to clinical data release is a bullish indicator of "Smart Science" interest.18

## ---

**11\. Model Calibration and JSON Parameter Audit**

For the ODIN model to function as a risk management tool, its probability outputs (e.g., "75% chance of approval") must be **calibrated**. The audit scrutinized the choice of **Platt Scaling** and cross-referenced the parameters found in the model's configuration files.

### **11.1 The Calibration Problem (Guo et al. 2017\)**

The model correctly identifies that raw outputs from neural networks (like FinBERT or deep learning fusion layers) are often uncalibrated. Modern networks are typically overconfident; a model might output a probability of 0.99 for an event that only happens 80% of the time. This "calibration gap" can be disastrous for position sizing.1

### **11.2 Platt Scaling vs. Isotonic Regression**

The choice of calibration method is a function of sample size. The audit validates the ODIN model's selection of Platt Scaling based on the specific constraints of the biotech domain.

* **Isotonic Regression:** Optimal when ample calibration data is available (\>1,000 samples). This method is non-parametric (fitting a step function) and prone to overfitting on small data.1  
* **Platt Scaling:** Preferred for smaller calibration datasets (\<1,000 samples) due to the lower risk of overfitting.  
* **Domain Reality:** In biotech, specific indications (e.g., "Phase II trials for Acute Myeloid Leukemia") rarely have datasets exceeding 1,000 historical examples. **Platt Scaling is the mathematically superior choice** for this application to ensure robust out-of-sample calibration.

### **11.3 Audit of JSON Parameters (best.json)**

The audit examined the best.json file 24 to verify if the operational weights align with the theoretical findings.

* **Manufacturing Penalty (w\_mfg\_pen):** The parameter is set to \-0.720. This is a significant negative weight, confirming that the model effectively penalizes manufacturing risks, aligning with the 74% CMC failure rate finding.  
* **AdCom Weight (w\_adcom):** Set to 0.361. This relatively high positive weight confirms that a positive AdCom vote is treated as a strong predictor of approval.  
* **Base Probability (p\_base):** Set to 0.966. This seems unusually high for a base rate and likely represents a conditional probability for a specific high-confidence subset (e.g., "NDA filed \+ No Negative Signals") rather than a universal prior.  
* **Threshold (p\_threshold):** The decision boundary is 0.872. This high threshold suggests the model is tuned for **Precision** over Recall—it prefers to miss some winners rather than buy a loser, which is the correct risk posture for binary biotech events.

## ---

**12\. Conclusion and Recommendations**

The **ODIN Biotech FDA Prediction Model** is built on a foundation of high-quality, scientifically validated components. The extraction of insider signals using the Cohen-Malloy-Pomorski framework is robust, the NLP engine uses industry-standard architecture, and the calibration methodology (Platt Scaling) is appropriate for the data constraints.

However, the audit has identified critical **"fault lines"** that must be addressed to ensure operational integrity:

1. **Rectify Clinical Priors:** The model must strictly enforce phase-specific priors. The **93.1% Hematology success rate** must be restricted to the NDA phase. Phase I and II assets must use their respective, much lower transition probabilities (Phase I: \~24% LOA, Phase II: \~48% transition) to avoid a base rate fallacy.  
2. **Define Derivatives Polarity:** The model must explicitly reject the "Contrarian" interpretation of the Put-Call Ratio in favor of the **"Informed Trading"** interpretation. A high PCR (\>1.2) preceding a PDUFA date is a warning sign of insider pessimism.  
3. **Implement CMC Module:** To close the gap on the 74% of CRLs caused by manufacturing issues, the model must integrate the **CMC Risk Module**, weighing factors like Form 483 history and remediation hiring patterns.  
4. **Operationalize Inventory Signal:** The **ASC 330 Inventory Capitalization** signal should be implemented as a high-conviction override, leveraging its status as a "costly" signal of management confidence.

**Final Verdict:** The ODIN model specifications are **CONDITIONALLY APPROVED**, pending the rectification of the Clinical Prior logic and the explicit definition of the derivatives signal polarity. The quantitative claims (0.90 coefficient, 5.67 t-stat) are **VERIFIED** as accurate to the source literature.

**(End of Report)**

#### **Works cited**

1. Forensic Audit of FDA Prediction Model, [https://drive.google.com/open?id=1mCxZ4eR0VrMrf-lzj9x0dklzbeTAB9yszcSIB0m5mA8](https://drive.google.com/open?id=1mCxZ4eR0VrMrf-lzj9x0dklzbeTAB9yszcSIB0m5mA8)  
2. Predicting Successes and Failures of Clinical Trials With Outer Product–Based Convolutional Neural Network \- Frontiers, accessed January 23, 2026, [https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2021.670670/full](https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2021.670670/full)  
3. ODIN Model Enhancement Recommendations, [https://drive.google.com/open?id=1fjFKAJDHq7aUYIoDiT4lBxniIrnG6cwFnZ0EJhEilz8](https://drive.google.com/open?id=1fjFKAJDHq7aUYIoDiT4lBxniIrnG6cwFnZ0EJhEilz8)  
4. On Calibration of Modern Neural Networks | Request PDF \- ResearchGate, accessed January 23, 2026, [https://www.researchgate.net/publication/317591245\_On\_Calibration\_of\_Modern\_Neural\_Networks](https://www.researchgate.net/publication/317591245_On_Calibration_of_Modern_Neural_Networks)  
5. Phases of clinical research \- Wikipedia, accessed January 23, 2026, [https://en.wikipedia.org/wiki/Phases\_of\_clinical\_research](https://en.wikipedia.org/wiki/Phases_of_clinical_research)  
6. Rani \- Zacks Small-Cap Research, accessed January 23, 2026, [https://s27.q4cdn.com/906368049/files/News/2024/Zacks\_SCR\_Research\_02202024\_RANI\_Vandermosten.pdf](https://s27.q4cdn.com/906368049/files/News/2024/Zacks_SCR_Research_02202024_RANI_Vandermosten.pdf)  
7. Enhancing Predictive Accuracy for Drug Development.docx, [https://drive.google.com/open?id=1qnOtzvqeFkrPNbiTT-R\_R6tJpLEDtbJ8](https://drive.google.com/open?id=1qnOtzvqeFkrPNbiTT-R_R6tJpLEDtbJ8)  
8. Synthetic Control Arm® in Clinical Trials \- Medidata, accessed January 23, 2026, [https://www.medidata.com/wp-content/uploads/2021/09/SCA-Whitepaper.pdf](https://www.medidata.com/wp-content/uploads/2021/09/SCA-Whitepaper.pdf)  
9. Decoding Inside Information Lauren Cohen, Christopher Malloy, and Lukasz Pomorski \- NBER, accessed January 23, 2026, [https://www.nber.org/system/files/working\_papers/w16454/w16454.pdf](https://www.nber.org/system/files/working_papers/w16454/w16454.pdf)  
10. Decoding Inside Information \- DASH (Harvard), accessed January 23, 2026, [https://dash.harvard.edu/bitstreams/7312037e-2b77-6bd4-e053-0100007fdf3b/download](https://dash.harvard.edu/bitstreams/7312037e-2b77-6bd4-e053-0100007fdf3b/download)  
11. FinBERT \- QuantConnect.com, accessed January 23, 2026, [https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/hugging-face/popular-models/finbert](https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/hugging-face/popular-models/finbert)  
12. ProsusAI/finBERT: Financial Sentiment Analysis with BERT \- GitHub, accessed January 23, 2026, [https://github.com/ProsusAI/finBERT](https://github.com/ProsusAI/finBERT)  
13. Handbook: Inventory \- KPMG International, accessed January 23, 2026, [https://kpmg.com/kpmg-us/content/dam/kpmg/frv/pdf/2024/handbook-inventory-2024.pdf](https://kpmg.com/kpmg-us/content/dam/kpmg/frv/pdf/2024/handbook-inventory-2024.pdf)  
14. FDA's CRLs reveal 74% of applications rejected for quality, manufacturing issues, accessed January 23, 2026, [https://www.pharmamanufacturing.com/all-articles/article/55302937/fdas-crls-reveal-74-of-applications-rejected-for-quality-manufacturing-issues](https://www.pharmamanufacturing.com/all-articles/article/55302937/fdas-crls-reveal-74-of-applications-rejected-for-quality-manufacturing-issues)  
15. Put-Call Ratio Meaning and How to Use It to Gauge Market Sentiment \- Investopedia, accessed January 23, 2026, [https://www.investopedia.com/ask/answers/06/putcallratio.asp](https://www.investopedia.com/ask/answers/06/putcallratio.asp)  
16. Put Call Ratio: Overview, Calculation, Interpretation, Uses, Reliability \- Strike Money, accessed January 23, 2026, [https://www.strike.money/options/put-call-ratio](https://www.strike.money/options/put-call-ratio)  
17. Where Do Informed Traders Trade First? Option Trading Activity, News Releases, and Stock Return Predictability \- American Economic Association, accessed January 23, 2026, [https://www.aeaweb.org/conference/2016/retrieve.php?pdfid=20262\&tk=R38kbnQf](https://www.aeaweb.org/conference/2016/retrieve.php?pdfid=20262&tk=R38kbnQf)  
18. Enhancing Odin's Predictive Accuracy, [https://drive.google.com/open?id=14UKZD\_JWQ8AZ6snmdZk5vu\_qtFn406n-khNazF3XK3s](https://drive.google.com/open?id=14UKZD_JWQ8AZ6snmdZk5vu_qtFn406n-khNazF3XK3s)  
19. A data-driven approach to predicting successes and failures of clinical trials \- PMC \- NIH, accessed January 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC5074862/](https://pmc.ncbi.nlm.nih.gov/articles/PMC5074862/)  
20. PrOCTOR: Predicting Failure Probability of Clinical Trials for Potential Drugs | Synced, accessed January 23, 2026, [https://syncedreview.com/2017/03/28/proctor-predicting-failure-probability-of-clinical-trials-for-potential-drugs/](https://syncedreview.com/2017/03/28/proctor-predicting-failure-probability-of-clinical-trials-for-potential-drugs/)  
21. Citation analysis of computer systems papers \- PMC \- PubMed Central \- NIH, accessed January 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10280529/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10280529/)  
22. Predicting substantive biomedical citations without full text \- PNAS, accessed January 23, 2026, [https://www.pnas.org/doi/10.1073/pnas.2213697120](https://www.pnas.org/doi/10.1073/pnas.2213697120)  
23. On Calibration of Modern Neural Networks: Temperature Scaling, accessed January 23, 2026, [https://users.cs.fiu.edu/\~sjha/class2023/Lecture8/Slides/2017TemperatureScaling.pdf](https://users.cs.fiu.edu/~sjha/class2023/Lecture8/Slides/2017TemperatureScaling.pdf)  
24. best.json

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEIAAAAYCAYAAABOQSt5AAACmElEQVR4Xu2XT4hOURjGnwlF40+ikaLQRLJRaDYSGiKRkPxdoiwszEKx8EmTmsWExYiUbLBQFpIFRWym2Ch/FmzInxVFKBSeZ95zvu/cO/eY+5W639R56td3z7nnfN89z3nf954PSEpKShr9GkO2kzm5fq8JZBe5QPrIguztutpIFzlLBsgK19fS0uI2kjPkHflGlmRGmKaQO+QkmUgWk+dkaziIaieXyA2ykCwij8macFArSkasJyvJccSNOEIekalB327ygsxwbe36afIAZpx0mPyBzR810sMWGaHFy4TLuf5l5CvZ5Nqap/kH6iOAWaSXzAv6MBnm/mzXHkeWwkLTu1qlYkYoxD9iuBF+4VqoVCO/yHJY+swk4929unTjPDlB3pK95CbZT46Rz6S7ProaxYzwC44ZoX4t+JZrn4KtVWnxkhxEUCzXwULGT76LRh7JudcYOY86YYXnTRPsHJpZTjEjFLHK838ZoY2+Dxt3kYx1Y1aRL2ikD/bBQmwLLHw0wMuHnhysUjEjlM5ljfiNbGT7TVa0ZNJE79ZnZHrQt4P8gOVWlYoZUSY19NpUlOfneyOEroc0iTwk19EIHX1eJYNopEpMOvB0wL6wLNqpsooZoYr/AXEjjrq2UiI/v9CIohSYCyueNdg7XYVmWnA/lFzfQLY1gX6zrGJG+LDPh7dS4Kf7lIoi2xuRmevrQzhQheg77J2s05d3twrJCP8see2BFV9tnNQGO2WGkaxofYps0R9WLKUaeYLsjivsXpHb5ApGTo//LUXZNfIJVhA970l/ME5nnnPkHtkMM0G1TkftUKthEa7IPuSue5D7r6HQKMpZ/YiKp2pAK0uLmQ9LOf2R0nMXSeauhRnmD49JSUlJSUlN6i8xRZ0BtXHH6AAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAYCAYAAABtGnqsAAADiklEQVR4Xu2YW6hNWxjH/0KR+50OsU9KXqTcUjyQdCSXUHROoeSSlPJAuZSScnmTS8n1wXFcXl2KYseDKHUKD0eylYg6eaFOyeX/963PGnOsMddce6Vj0/zXr7XnWGOOOb//+MY3xtpAqVKlSpXqiBpD9pGj5HfSPft1rjqRKeQAOUzmks6ZHqbeZCNs/B1kWPbrjPTslaRv1N5htZg8IuNJT7KLXCN9wk4JybzNpJW0kAHkDMykrkG/keRvspp0I3PIP2Ry0Kc/WUpOkTfkGeqb/L+oB7KBpDSCPCZ/BG39yD2yIWhLaQJ5RaYFbb/Cgv+tct2FHCMXK3+7dpOrqGa6DFxAJpK/8J0N1HK8QP4kg6LvYsm4dzAzXMosZdJNWEbmSSbEgfYit8hJ2Dgy9CXZEvSRFqH2ua7TqB03I9UDpbFmX1KmzIYNlqofjchr0Q1yENWxi6TalQpEQShwGZCSluIl1AYqw2/CMliZPIt8RK2B88gnZDPfVddApewhspW8IHtg6a2B9BnXjyLJ8JmwWd8Pq0PtkV42z8BUu8uNigON292oPAPjdqmugZqRbWQs+RdWH7wOTIIVUPUpkoxTzbhDtsOyur3yYFNGFRmo4BRkHGhsoAxKGdW0gSthu8988gFZs1SM35NNQVssZecych92LNDyb1a69zrSRhUZOIQ8QW2gsYGKJWVU0wa6VIDbyC9B21rYoCqweZoBu28dGj+r1VOeUXntrtiovPY8o/LapUIDfebDrV2futay1vKupzALdQ5rZvm6NJEpoxTEczI8anf5+8aBuoGqydqRfVXFRrmBqWQpNDC1tbfAXvgIsuelevI6qB2vmQ1ESpUS32GF/pb0rFHBtaT3jyd8IHkI290lrbC24Nql1Rbf6yo0UC8t93dWrjvBTv8PYKf29kr3h0eY3AcnJNPvovou0mjYZCrLXatg73wW1QlO9ZtOXpOplWuPTZud/7LRCjqP7FihirL/y7LRbqtBdeBthS2HoWGnJqSXHUeukOOwrG5EOv0/hZWDJbCM3ovscUpL7r9KHz3HpSWoe9eQFbCfhOujPjLuMjkHO/+eILeRNWgwbNm/hU2U0MqQkar3X+U1QstDm4AyQG3fWjJP/xxQljQiP8wvROOHcJdikMEir4yoBKjOaoL02ewPhmT9K9UOKdWVnsvxA/27piNJP9WcsPiWKlWq1M+uz1y2z97dptcMAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF8AAAAYCAYAAACcESEhAAAFL0lEQVR4Xu2Ze6htUxTGvxvK+51HxPXoSq686Xp1yB8kurmKIooukiRCSTpC8gd5pkTyh4ibUkgoW+p6lUd5lMgjjxAiFPL4fs017ppr7rn32dfZ7dx79ldfe68515p7zDHH+MZY50hTTDHFeLCVuVE5uACBD/DFxHCyeaumzgf44HbztHJiEI4zvzb/yfiD+W3z/RelBbeMBzIcZL5o7lBOTAhE2V3mdRr98Hc1HzXPMxcVc+PAduYz5uHlxDDcb/5pHl2MH6x0EM+Zm2fjm5hPmmdmY5PGIeav5mfmzsXcSeaBxRg4RSmoeuruZ5w4Uf3+GogtzJfNj80dizkW6Jl/mydk4/zAO+q/f5Ig2leay9UfxXcqObrEZuaV5lHlxBhBRq7WiIG5r/m9ucrcsJjbxnxD3axgow8qbfD/CFL/ddWdPyncpLo/+3CqUipeXk4Yy8zfzVfVVvLtzffUX1g2Vkr/GfMIcwOlgz3dXKL+6ARE77HmNUrOIjJz8AzPXmieq7TekUprU2uWKkkMMgj4vE1pP+co2cNhsA6/RaaixzNKjokx7oOsydr5OJ95TdnbvMq8uPleAzYhh9SYoSCCa3qPs18wvzMPzcbR2s+bzxxcv6u0ceZ75qXmBc314+q2YjiSrLpEycgzzPfN45t5HEYndWMzz/3UmYfMrc0HzD/Uaj6Hj6Sgt9jA533NGHOLzafMv9RqPmMUYMZ4BhtZmwP/pBl7zdxL6QCuVbKZvSK93HOF+gOL+S/Mw4rxDkLTie6HlYyFbPArJXkpT48IpUPasxgHsd5b6nZBxyj9Bp0ThjLHQd3QXAfONr8x91OKuDfV3QAHwIEEyJiy4EZRrckOv8U+e+oWRAIA+8j0AJmd28f1z+rew3PYu082BrAHu2o2rEHo/fPm7mrTLyKpBhYsNxwI58OyO3pW7aEhI2URB9HBoJkhbxwSh0IQEH00CIGr1W/LMOcDAqunrn3I14/mbHONJN3TjAN88bSSPdgVIDB+U/9vhfPPKsY7CL0ngkbFf3E+YNMhb7S2OLkmXYwjd+g/L3FcYyP8SN0WclzOx9mPmB8oZRxByTtEFMxwJhKMGoRCBMu2Nu6v1dE1QO9rETgM83E+UUK0DKoz4fxVajdO1M2Yt5g/KWVCSNoozuddZdt2uup8gIaj/QQkxTRvFSML0Xs6wLkwp+yQvvT3n5q7dKeGAodRDw4oJzTY+RRaOqaILDaGg8qOibU5FLSUDeCofB1qB78dGTOK84ngPMMGOR+7sI9CTV3gOrDIvFv1WrfE3K0Y4x7spOupInQOLRuk7zWQkixcy5ZwPi9si7NxOhmi6qLmmvvY5GNq2zg2SIGLyMahRBsOD2AzPXwES835cYDoLdlzh7lHNj/I+WBW6eD4LEETgOzcrNSOAmxn/bLlJLvxAb7qgM1gcOgo5O855+c3DUE4mKJZIubQZgosG6W9o6hzADg4wN+LiEo6I3TzJSW52amZx6GrlVKdFpDWku6HaOJwXlFrP3+DimDAIfeaX5pPmJcp/e7+5ofZMziHsRwcLr5ZVowHiHIOnwDB5p7q0c3B91Q/4HljVvU3uFJ26JlJ3/wlpUS8nJWGEl2bNt9ZJ16ARgXPwLUBh4Qc50FSw7B9RfGeLcbHBtLsbbWtWKB0/kIEvqG+lVI0VvBmx6t8RAkRzMsGMgL5vja1ZH0Avrhe6c8Pc2XPvEDKodkrmmt63bn63/Ud1FPkeCL/0eJFiA6lbL8WIujAeDOfiOOnmGLdwb/8KCX1k7R30QAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAYCAYAAADjwDPQAAAFdklEQVR4Xu2ZaaitYxTH/0KR2TUkw72GrkyZyRgiw+0Kl1LkA0XJENcQUVsSPlyzEkqUiJshwxViywdjhiJ1kcMHQohQZutnvct+3nWebe9z2+c6p/a//u19nvfZz7PetdbzX+t9jzTGGGP8P1jPuHoeHOMfrGrcwLhKvjCdWGBconFQ+oFgLDZe0HwfCocavzD+VfBb41fN9x+NNxnXjR8U2N34onGTfGGWYQvjg8bTNQXHTQEk7H3GRfnCINxt/M14YBrfQx6gZ41rF+NrGh83nlyMzXTsZjw6DxoWyhOwq/Y9jhI7G18xbpkv9MM6xpeNHxs3Tdcwsmv803h4MX6U8V1Nnj+TcZbx0jxoWMt4sfGAfGGEWM34gLGTxvtiB+M3xqXyH5egSL2h9iniiN9jvCUmzQIgIQ+pHpSVhVPkvsSnA3Gs/PhemC8Y9jP+YnxV3mWBjYzvG0+ISQ24cU7OPsZDmr/nGY8z7invRDKoVacar5QHPc9ZQ74Wa3D0mX++8TJ5hoM5xuONVxlPav4uwZr85g/j1cbN5HWQ8WwzSRljzKvNZYzPsrnZzniJ8ezmew27Gj817p0v1EDG1+oJQXje+LVxr2IcB3/WfJaYZ3xJHmCCeIc80KfJpfFOtW/kMOOHzXVOKzVqmXrBpwYsN16rXpaxzpnq7b+T3L7r5c5irS/VTpgzjI/KJfhNuR3XGdeX2/ykPGBduVwzRuFnjHt5uJk73/hJM/aacVv5/Vwhtw17kHXm0HHlpgH7CEpO5kmImsFpuF9uMLzX+LlcpuhOSlAY6di2SeMAQ1gHB2Bg4HK5ROJ8QNYTkE5MkBdD5uBEGoln1JZUbgZHEUzqIHvFSaZRAYzdZpwwbt6MARz2k+ryFTZ31S7058jXZo8ANnDawuH8/YPac/gdibF9MQbC1zUbWoh68pxxrnpHFiIdNRAUIs6cGggo8obMBTAEp8Tpoujm5iEaDn4fWcX3QHRJpczinA3VPoF5L/BfQQHs01U7KCTJd+olDslxezMO8M9TmnyvyNPPcntLRFCuSeOTEPWETB4WwwSlq/YNZkcxh6AgK3E6g3FSnlB7HbIyZy7gJOMspA25RaJGEZTomD6Q1xAS+NZmHETiIJ8oSr4P5LdEBCVOdV9QT3LGDsIogtKvjpU4Ri4NdxnPk2s10hDSAY6UP+DeIA8kyHuBHBQcXMpbzWaABCOZJC9FvHwui4Zn2I5qKPkKuZhQ28BBwJHUG7qJGmo3mB3FzZIMFPASFHk6IUBW0mDMkSdAdljIR2RyIPY62HiRvEvLQeGzlJeazYB1WZ+HZ+pOuQ/JQf2q1df5xq3SWDxe1LrcfxGayY31qx81kGUEpXa6MBTjCTZBD+SghDxh5MYxSR6kCBTHfKnxxIJ0W1E/IigT6iVVrMteRxhvlDsap+G80HPkupTBfkEBHbnE85kR3R8dYrTz2HezJrfGyCwSW/ObDpLLDxsFed+Flg+DOIYU6xK7yDeNNZEVnkF4vRBjv8qlBpDByBiNBk55TO60cPoC4+9q2wnLFh3d/sj4nlzHH5FLDW8buKdzm3kky2Lj9/JAL5Hvg83L1Vsb+xkrQfLir1zLApyK19Wzoav66xwUBrmbiipNCR3V3wCsCMj4LE+87MRZ+xdjYGvj02qfbhyOxMVDHoiHvQz2YG5ZlwaBuZz6Qb/hWQZ5q+0LOvLGYRQ+q4Kj+Y567eGoge52VZcTurDae7qZDBLhBblKTSuQA6RoUAatCObKJYj/Q5SZt6PxLfkrjenYd7qAjPOGo98pGhnYgA5pUb4wIvCeC+cTnLcb8kpkX82ugKAqy+SJtlJAsea1Q24Jx3BQi2he8quqMcYYY8r4Gy/9Okjcu4pmAAAAAElFTkSuQmCC>