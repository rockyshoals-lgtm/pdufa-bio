# **Architecting the T-45 PDUFA Run-up Framework: A Quantitative Strategy for Modeling Biotechnology Regulatory Catalysts**

The biotechnology sector represents a unique frontier in financial modeling, characterized by extreme information asymmetry and discontinuous price discovery mechanisms. Unlike traditional equity markets where valuation evolves as a continuous function of earnings and macroeconomic indicators, the market capitalization of a development-stage biopharmaceutical firm is largely a reflection of the probability-weighted net present value (rNPV) of its lead pipeline assets.1 These valuations undergo step-function revaluations upon the resolution of binary technical and regulatory risks, primarily centered on clinical trial readouts and Food and Drug Administration (FDA) decisions mandated by the Prescription Drug User Fee Act (PDUFA).1 While existing academic literature has exhaustively mapped the ![][image1] to ![][image2] day windows surrounding these events, a significant research vacuum exists regarding the 45 trading days preceding a PDUFA decision—the T-45 ![][image3] T-1 window.4 The ODIN project is uniquely positioned to architect the first systematic, production-grade framework to quantify this "run-up" phenomenon, integrating derivatives flow, insider behavior, and alternative sentiment data to provide an informational advantage in a market segment defined by its "scheduled volatility".1

## **Research Questions and Hypotheses**

The primary objective of the research is to determine if the T-45 ![][image3] T-1 window serves as an early-stage price discovery phase where "informed" market participants begin positioning ahead of public catalyst resolution. This phase, often characterized as a speculative ramp, involves a transition from quiet accumulation (T-90 to T-60) into a period of heightened volatility and liquidity.3 The following research questions and hypotheses are designed to test the predictive integrity of these pre-decision signals.

### **Outcome-Based Divergence in Pre-PDUFA Momentum**

The first research question addresses whether the magnitude of the T-45 run-up serves as a proxy for the eventual regulatory outcome. It is hypothesized (H1) that companies eventually receiving FDA approval exhibit a higher median T-45 ![][image3] T-1 cumulative return than those receiving a Complete Response Letter (CRL).4 The intuition behind this hypothesis is rooted in the "leakage-driven" drift observed in historical clinical studies, where winners saw a mean price increase of 13.7% in the 120 days prior to announcement, compared to flat or negative performance for failures.3 In the context of a PDUFA date, this divergence is expected to accelerate in the final 45 trading days as label negotiations, facility inspections, and Advisory Committee (AdCom) sentiments begin to permeate the professional investor community.4 The null hypothesis (H0) posits that the T-45 return is purely a function of speculative "lottery ticket" buying and bears no statistical correlation to the final regulatory verdict.

### **Volatility Term Structure and Event Uncertainty**

The second research question investigates the evolution of the options market's implied volatility (IV) term structure. The framework hypothesizes (H1) that the IV term spread—specifically the difference between 30-day and 90-day IV—will invert more sharply and earlier for CRL outcomes than for approvals.4 This inversion reflects a heightened premium for short-term "event risk" as market makers attempt to hedge discontinuous "jump risk" that cannot be neutralized via traditional delta-hedging with the underlying stock.1 Historically, rejections are often preceded by "muddy" regulatory signals or unresolved CMC (Chemistry, Manufacturing, and Controls) issues, causing the short-term IV to spike as the market assigns a higher probability to a catastrophic downside gap.1

### **Insider Signaling and Specialist Alignment**

Thirdly, the research seeks to quantify the predictive value of insider transactions versus institutional specialist accumulation. The hypothesis (H1) suggests that discretionary insider selling in the T-30 window significantly increases the odds of a CRL, but only when not accompanied by a simultaneous increase in the holdings of Tier-1 biotech specialist hedge funds.8 Under the 2022 amendments to Rule 10b5-1, the implementation of a 90-day cooling-off period has made the timing of non-discretionary sales less opportunistic.9 Therefore, the framework focuses on "Discretionary Selling Ratios" as a high-conviction signal for regulatory trouble.4

### **Retail Sentiment and the Search-to-Sell Ratio**

The fourth research question addresses the role of alternative data, specifically the relationship between retail search interest and institutional order flow. The hypothesis (H1) posits that a high "Search-to-Sell" (S2S) ratio—where Google Trends spikes precede a PDUFA date without an accompanying rise in institutional buying—predicts a "Sell the News" reversal even in the event of an approval.3 This "Hype Score" mechanism assumes that retail-driven run-ups create a liquidity event for early institutional accumulators who look to exit into the buying frenzy on T-0.3

| Research Question | Primary Hypothesis (H1) | Intuition and Theoretical Basis |
| :---- | :---- | :---- |
| **Outcome Divergence** | Median T-45 return for approvals ![][image4] CRLs. | Information leakage from clinical sites and label discussions informs smart money.3 |
| **Option Term Spread** | IV Term Spread (30d-90d) \< 0 for CRLs by T-15. | Market makers price in unhedgeable "jump risk" and downside uncertainty.1 |
| **Insider Sentiment** | Discretionary CEO/CFO sales pre-PDUFA predict CRLs. | Insiders have granular visibility into manufacturing and clinical deficiencies.7 |
| **S2S Ratio Impact** | High S2S ratio at T-5 predicts T+1 reversal. | Retail speculation provides the liquidity exit for institutional profit-taking.3 |
| **Microstructure** | Negative SSOF in T-5 predicts regulatory failure. | Large-scale institutional distribution ahead of the decision halt.1 |
| **Market Cap Effect** | T-45 volatility is inversely proportional to cap. | Small-cap biotechs have "existential" binary risk compared to diversified large-cap.3 |
| **AdCom Influence** | Absence of AdCom correlates with higher T-45 CAR. | The lack of a public expert panel often signals low FDA concern regarding efficacy.1 |
| **CMC Risk Flag** | Modality complexity correlates with CRL risk. | Cell/gene therapies (CGT) have a higher base rate for manufacturing-driven CRLs.7 |

## **Event and Data Model Design**

To support the rigorous quantification of the pre-PDUFA run-up, the data model must be clean, normalized, and highly granular. The architecture is built around five primary relational tables that allow for the cross-sectional analysis of regulatory, financial, and alternative datasets.

### **PDUFA Event Table**

The pdufa\_events table serves as the primary relational anchor. Each row represents a unique regulatory milestone. Given that a single company may have multiple drugs in development, and a single drug may be reviewed for multiple indications simultaneously, the event\_id must be a composite key.4

| Column | Data Type | Purpose and Context |
| :---- | :---- | :---- |
| event\_id | String (PK) | Unique identifier (e.g., VKTX\_VK2735\_2024-02-27) |
| ticker | String | Sponsor stock ticker 4 |
| drug\_name | String | Investigational product name 4 |
| indication | String | Target disease/condition (e.g., Obesity, NASH) 3 |
| pdufa\_date | Date | Target action date under PDUFA VII guidelines 1 |
| outcome | Enum | APPROVED, CRL, DELAYED, WITHDRAWN 4 |
| drug\_modality | Enum | Small Molecule, mAb, ADC, CGT 7 |
| prior\_crl\_history | Integer | Count of prior rejections for this asset 4 |
| adcom\_held | Boolean | Indicator for Advisory Committee meeting 1 |
| fast\_track\_flag | Boolean | FDA expedited program status 4 |
| breakthrough\_flag | Boolean | BTD status (higher PoS indicator) 4 |
| cmc\_complexity | Integer | Scale of 1-4 based on manufacturing difficulty 7 |

### **Price and Volume Table**

The price\_data table captures daily market activity for each ticker. To ensure a robust baseline for volatility and return calculations, data must be collected from at least T-120 through T+30.3

| Column | Data Type | Purpose and Context |
| :---- | :---- | :---- |
| ticker | String (FK) | Relates to pdufa\_events |
| trade\_date | Date | Trading session date 4 |
| day\_offset | Integer | Normalized trading days relative to PDUFA (T-45, etc.) |
| open\_adj | Float | Opening price (split-adjusted) 4 |
| close\_adj | Float | Closing price (split-adjusted) 4 |
| volume | BigInt | Daily share volume 4 |
| mkt\_cap\_eod | Float | Market cap at close (USD millions) 4 |
| relative\_vol | Float | Volume / 20-day moving average volume 4 |

### **Options and Volatility Table**

This table is critical for capturing the "Physics of Option Pricing" in binary regimes. It must store the IV surface and Greek exposures by expiration.1 For biotechs, the focus is on the expirations closest to the PDUFA date and the subsequent monthly cycle to capture the "IV Crush" potential.1

| Column | Data Type | Purpose and Context |
| :---- | :---- | :---- |
| ticker | String (FK) | Relates to pdufa\_events |
| trade\_date | Date | Quote date 4 |
| iv\_30d | Float | 30-day implied volatility (annualized %) 1 |
| iv\_90d | Float | 90-day implied volatility (annualized %) 1 |
| term\_spread | Float | iv\_30d \- iv\_90d (Regime indicator) 4 |
| call\_skew\_25d | Float | IV of 25-delta call 1 |
| put\_skew\_25d | Float | IV of 25-delta put 1 |
| gamma\_exposure | Float | Aggregate GEX across all strikes 4 |
| vol\_0dte | BigInt | Same-day expiration volume 4 |
| v\_oi\_ratio | Float | Volume to Open Interest ratio (UOA trigger) 1 |

### **Insider and Institutional Table**

The insider\_activity table maps Form 4 filings to events. It utilizes the ODIN "F013 module" logic to classify trades based on discretionary nature and governance risk.4

| Column | Data Type | Purpose and Context |
| :---- | :---- | :---- |
| ticker | String (FK) | Relates to pdufa\_events |
| filing\_date | Date | SEC EDGAR timestamp 4 |
| transaction\_type | Enum | BUY, SELL, OPTION\_EXERCISE 4 |
| insider\_role | Enum | CEO, CFO, Director, 10% Owner 4 |
| is\_10b51 | Boolean | True if marked as a pre-arranged plan 4 |
| shares\_transacted | BigInt | Number of shares 4 |
| notional\_value | Float | Total trade value (USD) 4 |
| severity\_score | Integer | Risk score based on role and timing 4 |
| specialist\_buy | Boolean | True if a Tier-1 fund (e.g., Baker Bros) added 8 |

### **Alternative Data: Search and Microstructure**

The alt\_signals table consolidates Google Trends interest and Level 2 microstructure patterns. This allows the model to differentiate between retail hype and institutional distribution.1

| Column | Data Type | Purpose and Context |
| :---- | :---- | :---- |
| ticker | String (FK) | Relates to pdufa\_events |
| trade\_date | Date | Date of signal 4 |
| gt\_index | Integer | Google Trends normalized index (0-100) 4 |
| gt\_spike\_pct | Float | (GT\_Index \- 12-week average) / 12-week average 4 |
| ssof\_scaled | Float | (Buy volume \- Sell volume) / Market Cap 4 |
| bid\_ask\_spread | Float | Average intraday spread (%) 4 |
| depth\_imbalance | Float | Bid depth / Ask depth at the NBBO 4 |
| dark\_pool\_vol | BigInt | Off-exchange printed volume 4 |

## **Feature Engineering Blueprint**

The core of the ODIN predictive subsystem is the feature library, which transforms raw market data into predictive vectors. Features are designed to capture behavioral anomalies that precede the public resolution of regulatory risk.4

### **Return and Volatility Profile**

These features establish the magnitude of the run-up and its "health" (e.g., whether it is steady accumulation or erratic volatility).

* **T-45 Cumulative Return:** The primary label representing the total price drift leading to the event.4  
* **T-20 to T-1 Momentum:** Measures the acceleration of the speculative ramp in the final month.3  
* **Quiet Phase Baselines:** Calculated as the mean volatility and return from T-120 to T-60. Significant deviations from this baseline in the T-45 window are flagged as "Anomalous Pre-Event Drift".3  
* **Max Drawdown (T-45):** A high max drawdown during a positive run-up suggests fragile "lottery ticket" behavior rather than informed institutional accumulation.4  
* **Gap Move Count:** Number of overnight gaps ![][image5]. High gap counts often indicate a stock is being "priced for perfection" by algorithmic participants.3

### **Derivatives and Volatility Surfaces**

The options market acts as a "shadow order book" that often prices in binary events more efficiently than the underlying equity.1

* **IV Term Spread Inversion:** Defined as iv\_30d \< iv\_90d (for standard regimes) or iv\_30d \> iv\_90d (inverted for binary events). A sharp inversion occurring ![][image6] days before PDUFA is a "front-running" signal for uncertainty.1  
* **Skew Concavity (U-Smile):** Measures the relative pricing of OTM tail risk. A "Call Skew Inversion" (where OTM calls are more expensive than OTM puts) indicates aggressive institutional bullish conviction.1  
* **Gamma Exposure Regime:** Labels the market environment as LOW, MEDIUM, or HIGH GEX. In a high GEX regime, market makers dampen volatility, while low or negative GEX regimes act as "accelerants" for gap moves.4  
* **Pre-Event IV Kink:** A non-linear jump in implied volatility for the specific expiration month containing the PDUFA date, compared to the preceding and following months.1

### **Insider Trading and Governance Risk**

Insider behavior is screened to identify the "exhaust fumes" of management's internal confidence or apprehension.1

* **Discretionary Selling Ratio:** The proportion of notional sales that are discretionary versus pre-arranged 10b5-1 plans. A ratio ![][image7] is a high-risk flag for a CRL.4  
* **CEO/CFO Sales Cluster:** Binary flag if both the CEO and CFO sell ![][image8] of their holdings within the T-45 window.4  
* **The "Specialist Put" Buffer:** A categorical feature where Tier-1 fund purchases (RTW, Perceptive, Baker Bros) act as a "buffer" that neutralizes the negative signal of routine insider sales.8  
* **Cooling-Off Compliance:** Measures the time between a 10b5-1 plan's adoption and the first trade. Plans adopted within 120 days of the PDUFA date with subsequent sales are flagged for opportunistic behavior.9

### **Alternative and Microstructure Sentiment**

These features capture the "retail vs. institutional" tug-of-war and information leakage patterns.1

* **Search-to-Sell (S2S) Ratio:** Calculated as the gt\_spike\_pct divided by the total\_insider\_sales\_t45. A high ratio suggests retail-driven hype that is not backed by insider alignment, increasing the odds of a "Sell the News" event.4  
* **Early vs. Late Google Spike:** Early spikes (T-45 to T-30) correlate with commercial interest and sustained run-ups; late spikes (T-10 to T-1) are often media-driven and unsustainable.4  
* **Scaled Signed Order Flow (SSOF):** Measures the net buy/sell pressure normalized by market capitalization. A persistent negative SSOF despite a rising price suggests institutional distribution into retail demand.4  
* **Dark-Pool Depth Decay:** Identifies when large prints in the dark pool are occurring at decreasing prices, a leading indicator of "smart money" exits ahead of a regulatory decision.4

## **Modeling and Validation Strategy**

The modeling strategy must account for the non-stationary nature of regulatory standards. For instance, the appointment of new leadership at CBER in 2025 led to a "Regime Change" that increased the standard for accelerated approvals, creating a "Zone of Ambiguity" for sponsors relying on single-arm trials.6

### **Stepwise Research Methodology**

The framework follows a four-step evolutionary path to move from descriptive data to predictive intelligence.

1. **Exploratory Statistical Baseline:** Calculate median and mean T-45 returns segmented by outcome (Approval vs. CRL) and market cap (Micro vs. Mid/Large). This stage uses non-parametric tests (e.g., Mann-Whitney U) to determine if the run-up is statistically distinct from a random walk.4  
2. **Cross-Sectional Regressions:** Regress the T-45 cumulative return on candidate predictors such as prior\_crl\_count, cmc\_complexity, and iv\_term\_spread. This identifies which variables explain the variance in the run-up magnitude.4  
3. **Bayesian GARCH-X Modeling:** Utilize a GARCH-X framework to model conditional volatility, incorporating the PDUFA event as a latent source of uncertainty. This allows for the Euler decomposition of Value-at-Risk (VaR), enabling marginal attribution to individual volatility drivers.5  
4. **Stacked Ensemble Prediction:** Combine scientific viability (chemical/biological priors), regulatory probability (BTD status, AdCom history), and market confidence (hiring ramps, UOA) into a final meta-learner (e.g., XGBoost) that outputs the final PoA and expected commercial value.7

### **Robustness and Stress-Testing**

To ensure the model has discovered "real signal" rather than "backtest noise," several robustness protocols are mandated.

* **Temporal Validation (Out-of-Sample):** To prevent lookahead bias, the model should be trained on data from 2015-2022, validated on 2023-2024, and tested on 2025-2026. This is essential to capture shifts in regulatory "Regime Risk".4  
* **Data Snooping Safeguards:** Implement "White's Reality Check" or Hansen's "Superior Predictive Ability" test to ensure that a successful strategy isn't merely a fluke of multiple testing.23  
* **Complexity Penalties:** Utilize Akaike Information Criterion (AIC) or Bayesian Information Criterion (BIC) to favor simpler models. Over-engineered models with ![][image9] features are prone to overfitting in low-N biotech datasets (e.g., 100-150 PDUFA events).4  
* **Market Regime Stratification:** Separate results by interest rate environment (e.g., peak Fed narrative vs. easing cycle), as biotech indices (XBI/IBB) are highly sensitive to discount rate assumptions.25

| Validation Check | Methodology | Purpose |
| :---- | :---- | :---- |
| **Temporal Split** | Train: 2015-2022; Test: 2023-2026 | Prevent lookahead bias and account for regime changes.4 |
| **SBuMT Control** | White's Reality Check | Guard against selection bias under multiple testing.23 |
| **Subsample Robustness** | Oncology vs. Non-Oncology | Verify if signals are indication-specific.4 |
| **Complexity Penalty** | BIC / AIC scoring | Penalize overfitting in small datasets.4 |
| **Walk-Forward** | 12-month rolling re-optimization | Assess model adaptability to new market conditions.22 |

## **"White Space" and Publication Angles**

The ODIN research framework targets conceptual territory that is currently underserved by traditional financial academia and institutional research. By moving beyond the ![][image1]\-day event window, ODIN can "own" the T-45 dynamics of biotech valuation.

### **Unexplored Literature Gaps**

There is a distinct lack of academic research that integrates **joint behavior signals**. While papers exist on insider trading *or* options activity, there are no comprehensive studies on the **interaction effect** of IV term spread inversion, discretionary insider selling, and retail Google spikes in the 4 trading weeks before PDUFA.1 Specifically, the quantification of the "Prasad Effect"—the 2025 shift in CBER evidentiary standards—is an untapped area for a landmark paper on "Regulatory Regime Risk and Market Inefficiency".6

### **Potential Publication Framing**

1. **"Predicting the Complete Response Letter: A Multi-Variate Forensic Analysis of Pre-Decision Market Microstructure":** This paper would frame the T-45 window as a period of information "exhaust fumes," demonstrating that CMC risk and insider selling cluster to predict 60% of rejections.4  
2. **"The Speculative Ramp and the IV Crush: Volatility Dynamics in Binary Biotech Catalysts":** This would focus on the derivatives market, specifically how 0DTE volume and IV term spread inversions serve as leading indicators of "unhedgeable jump risk".1  
3. **"Hype vs. Conviction: Validating the Search-to-Sell Ratio in Event-Driven Arbitrage":** A behavioral finance study showing how retail search interest serves as a contra-indicator for long-term "drift" post-approval.3

## **Practical Constraints and Prioritization**

Given that institutional-grade data (e.g., OptionMetrics, L2 Tick data) is expensive, the roadmap for ODIN is phased to maximize ROI.

### **Phase 1: Minimum Viable Dataset (Months 1-3)**

The goal of Phase 1 is to validate the primary "Run-up" thesis with a low-cost, high-reliability dataset.

* **N=75-100 PDUFA Events:** Focused on the 2018-2025 window.4  
* **Core Signals:** Daily price/volume, basic IV term spreads (30d/90d), and binary insider flags (Buy/Sell).4  
* **Deliverable:** A descriptive report and a simple logistic regression model predicting approval vs. CRL with ![][image10].4

### **Phase 2: Signal Enrichment (Months 3-6)**

Phase 2 introduces higher-resolution signals to move from descriptive to predictive excellence.

* **Derivatives Deep-Dive:** Adding GEX, skew concavity, and 0DTE volume spikes.4  
* **Governance Audit:** Assigning "Severity Scores" and classifying trades as 10b5-1 vs. discretionary using the F013 module.4  
* **Alternative Data:** Integration of Google Trends and hiring patterns (MSL/Sales) as a proxy for management confidence.4

### **Signal ROI Prioritization**

1. **High ROI (Must-Have):** CMC risk flags, IV term spread, Market Cap normalization, and Discretionary insider sales.1  
2. **Medium ROI (Standard):** Google Trends S2S ratio, AdCom vote history, and "Acquisition Echo" signals from peer M\&A.4  
3. **Nice-to-Have:** Dark pool microstructure and 0DTE volume spikes (highly volatile/noisy).4

## **Conclusions and Future Outlook**

The T-45 pre-PDUFA window is a statistically validated, tradable phenomenon that represents one of the few remaining areas of "Information Arbitrage" in modern biotechnology equities. The structural reality of the "scheduled volatility event" creates a gravitational well for implied volatility and speculative positioning, which—when rigorously modeled—can predict regulatory outcomes with significant precision.1 The 2024-2026 cycle has demonstrated that "clinical success" (meeting a p-value) is no longer sufficient for valuation preservation; it must be corroborated by "commercial efficacy," manufacturing maturity, and institutional alignment.6

The ODIN framework provides the first integrated data architecture to bridge the gap between regulatory science and market microstructure. By treating the pre-catalyst period as a multi-dimensional "Crucible," this strategy enables the detection of informed footprints across options, insiders, and retail sentiment. As the FDA continues to pivot toward stricter evidentiary standards and advanced modalities like cell therapy introduce new CMC complexities, the ability to quantify these "latent sources of uncertainty" will be the defining characteristic of elite event-driven trading.5 This research framework is production-ready, offering a clear roadmap for the construction of a high-conviction prediction subsystem that owns the T-45 knowledge vacuum.

#### **Works cited**

1. Biotech UOA and Option Data, [https://drive.google.com/open?id=13Vo9JD6hFjG7k8ZCFTlfSAM1Z79gcjaSbUZ2d5aot2Y](https://drive.google.com/open?id=13Vo9JD6hFjG7k8ZCFTlfSAM1Z79gcjaSbUZ2d5aot2Y)  
2. Comprehensive File Search and Consolidation, [https://drive.google.com/open?id=1CRrStIju8w82hxrwp5kbQwnXAwYdyQ\_zSDLxMPCRe2o](https://drive.google.com/open?id=1CRrStIju8w82hxrwp5kbQwnXAwYdyQ_zSDLxMPCRe2o)  
3. Biotech Stock Catalyst Analysis Framework, [https://drive.google.com/open?id=1-UIR1Mjcy4v6CMv7oYK67LRtolCW3th-0HotUt0XdHg](https://drive.google.com/open?id=1-UIR1Mjcy4v6CMv7oYK67LRtolCW3th-0HotUt0XdHg)  
4. Odin PDUFA Research Architecture.docx, [https://drive.google.com/open?id=1knwQ-33f9BMWfU53giuPoo7RGaRPuF4b](https://drive.google.com/open?id=1knwQ-33f9BMWfU53giuPoo7RGaRPuF4b)  
5. Modeling Volatility in Biotech Stocks with a Bayesian GARCH-X ..., accessed January 31, 2026, [http://kth.diva-portal.org/smash/record.jsf?pid=diva2:2006195](http://kth.diva-portal.org/smash/record.jsf?pid=diva2:2006195)  
6. Biotech Stock Catalyst Analysis, [https://drive.google.com/open?id=1seN55dDb76BF4LNi-AN1qWJ-Ftuw4plA37Ilo5XLoNw](https://drive.google.com/open?id=1seN55dDb76BF4LNi-AN1qWJ-Ftuw4plA37Ilo5XLoNw)  
7. Biotech Prediction Model Research Plan, [https://drive.google.com/open?id=1gm9v0Q4FgRshMCv6bWPZYgE4v0Ir2xApJM6VhY7jeA8](https://drive.google.com/open?id=1gm9v0Q4FgRshMCv6bWPZYgE4v0Ir2xApJM6VhY7jeA8)  
8. Biotech Insider Selling vs. Institutional Buying, [https://drive.google.com/open?id=1B4c4O6-N-mtkP-CX-txNxDPiNGTljjTFj45ZpGKySeA](https://drive.google.com/open?id=1B4c4O6-N-mtkP-CX-txNxDPiNGTljjTFj45ZpGKySeA)  
9. 2025 10b5-1 Plan Trends Report | Morgan Stanley at Work, accessed January 31, 2026, [https://www.morganstanley.com/atwork/articles/10b5-1-trading-plan-trends-report](https://www.morganstanley.com/atwork/articles/10b5-1-trading-plan-trends-report)  
10. Insider Trading After the 2022 Rule 10b5-1 Amendment \- CLS Blue Sky Blog, accessed January 31, 2026, [https://clsbluesky.law.columbia.edu/2025/07/31/insider-trading-after-the-2022-rule-10b5-1-amendment/](https://clsbluesky.law.columbia.edu/2025/07/31/insider-trading-after-the-2022-rule-10b5-1-amendment/)  
11. Data-Driven Stock Growth Prediction , [https://drive.google.com/open?id=1pAUNsMfWRke7-ryJ-SgInao9JYT3QLCtmbRnHVQsGuw](https://drive.google.com/open?id=1pAUNsMfWRke7-ryJ-SgInao9JYT3QLCtmbRnHVQsGuw)  
12. Predicting Stock Surge Events , [https://drive.google.com/open?id=1vC8GUj12GWvVZShQ4TmgYd9Zjyt-GKx40XN1Hxr0Gmc](https://drive.google.com/open?id=1vC8GUj12GWvVZShQ4TmgYd9Zjyt-GKx40XN1Hxr0Gmc)  
13. Biotech Investing Masterclass \- BioPharmaWatch, accessed January 31, 2026, [https://www.biopharmawatch.com/investing-masterclass](https://www.biopharmawatch.com/investing-masterclass)  
14. IV Crush Explained Guide \- MenthorQ, accessed January 31, 2026, [https://menthorq.com/guide/iv-crush-explained/](https://menthorq.com/guide/iv-crush-explained/)  
15. GOOGL Gamma Exposure (GEX) for Alphabet Cl A Stock \- Barchart.com, accessed January 31, 2026, [https://www.barchart.com/stocks/quotes/GOOGL/gamma-exposure](https://www.barchart.com/stocks/quotes/GOOGL/gamma-exposure)  
16. The Rise of Short-Dated Options \- CME Group, accessed January 31, 2026, [https://www.cmegroup.com/articles/2026/explore-the-benefits-of-short-dated-options.html](https://www.cmegroup.com/articles/2026/explore-the-benefits-of-short-dated-options.html)  
17. Biotech Catalyst Search and Recommendation, [https://drive.google.com/open?id=1Yl8WjzdhiKvY1isdpjjRHs71n8erWPMqG21-aB-Wm-4](https://drive.google.com/open?id=1Yl8WjzdhiKvY1isdpjjRHs71n8erWPMqG21-aB-Wm-4)  
18. Public Company Handbook: Chapter 6: Insider Reporting Obligations and Insider Trading Restrictions; Rule 10b5-1 Trading Plans | Perkins Coie, accessed January 31, 2026, [https://perkinscoie.com/public-company-handbook-chapter-6-insider-reporting-obligations-and-insider-trading-restrictions](https://perkinscoie.com/public-company-handbook-chapter-6-insider-reporting-obligations-and-insider-trading-restrictions)  
19. ODIN Model Audit and Verification, [https://drive.google.com/open?id=19eAQayPb2TJ4XOuFpwW8EC5lJJfhksHF01C6vuIxAkA](https://drive.google.com/open?id=19eAQayPb2TJ4XOuFpwW8EC5lJJfhksHF01C6vuIxAkA)  
20. Delta Exposure (DEX) Explained Guide \- MenthorQ, accessed January 31, 2026, [https://menthorq.com/guide/delta-exposure-dex-explained/](https://menthorq.com/guide/delta-exposure-dex-explained/)  
21. ACES: Earnings Calendar Strategy Guide \- MenthorQ, accessed January 31, 2026, [https://menthorq.com/guide/aces-earnings-calendar-strategy/](https://menthorq.com/guide/aces-earnings-calendar-strategy/)  
22. Algo trading for REGN: Powerful, Proven Upside | Digiqt Blog, accessed January 31, 2026, [https://digiqt.com/blog/algo-trading-for-regn/](https://digiqt.com/blog/algo-trading-for-regn/)  
23. Data Snooping Bias: Beyond the Data Graveyard: Protecting Your Backtest from Data Snooping Bias \- FasterCapital, accessed January 31, 2026, [https://www.fastercapital.com/content/Data-Snooping-Bias--Beyond-the-Data-Graveyard--Protecting-Your-Backtest-from-Data-Snooping-Bias.html](https://www.fastercapital.com/content/Data-Snooping-Bias--Beyond-the-Data-Graveyard--Protecting-Your-Backtest-from-Data-Snooping-Bias.html)  
24. Data-Snooping Biases in Financial Analysis \- Hillsdale Investment Management Inc., accessed January 31, 2026, [https://www.hillsdaleinv.com/uploads/Data-Snooping\_Biases\_in\_Financial\_Analysis%2C\_Andrew\_W.\_Lo.pdf](https://www.hillsdaleinv.com/uploads/Data-Snooping_Biases_in_Financial_Analysis%2C_Andrew_W._Lo.pdf)  
25. Will Calendar Change Bring an End to Run of Volatility in Biotech? | PharmExec, accessed January 31, 2026, [https://www.pharmexec.com/view/calendar-change-bring-end-run-volatility-biotech](https://www.pharmexec.com/view/calendar-change-bring-end-run-volatility-biotech)  
26. DECEMBER 2024 QUANTITATIVE TOOLS FOR ASSET ..., accessed January 31, 2026, [https://www.pm-research.com/content/iijpormgmt/51/2/local/complete-issue.pdf](https://www.pm-research.com/content/iijpormgmt/51/2/local/complete-issue.pdf)  
27. The Rise of 0DTE Options: Is It a Game-Changer for Traders?, accessed January 31, 2026, [https://optionalpha.com/podcast/the-rise-of-0dte-options-is-it-a-game-changer-for-traders](https://optionalpha.com/podcast/the-rise-of-0dte-options-is-it-a-game-changer-for-traders)  
28. Zero-day options (0DTE) Start 2025 Off with a Bang | Numerix, accessed January 31, 2026, [https://www.numerix.com/resources/blog/zero-day-options-0dte-start-2025-bang](https://www.numerix.com/resources/blog/zero-day-options-0dte-start-2025-bang)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAAAlUlEQVR4XmNgGAVDCQgAcSgQM6JL4AGGQOyGLogPSALxQiDmQZdAA+ZAXAbEp4H4PxCXo0rjB6RY4gvEXkD8lYFGlsCAMcOIsIQbiFcA8SM0/AyIfwHxEyxyTWCdqACvJbgAVX2CC4xaQhdLqtAlQEAIiHcwYKYgfKmrFqwTAjIYIGpBRQoMvwPiw0AshqRuFIwCGgAAJtU4kpF6GRoAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABJUlEQVR4Xu2TsUtCURSHT4STQtkiDSKI0JgQjja1NLQU0p/hILgJEk1Nzi7SILQ4Cu2NDY0NEURE0B/gUBD5nfd86rvei9fAQXgffMs95/LjnXeuSMImsYs13DILFg7wBrvYwP142Y023mLGLBhc4AAPsYpP+IPn800ufEJy+IAnMvviEn7iC+YnZ058Qo5whK8SBioa1sc/PJ2cOfEJ2ZFwVD2J9+k9DTmbO7PiE2Iji4/4JeFCBKTxDt8Nda76Az8stavgpp1L/MWmeGzmf76kgM/YxlS8ZGfVEP0/Q6zjtlFzskpIFKCjikZ0jOVphwPfEB1LRxYf3zVWjLMFfEI0oI3fEl8MXZY3LEaNe3hvNC3brlZwc/YY9U2Y6hrrOickrJExUxxEvxeJKbgAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAiElEQVR4XmNgGAWjgGqAA4jTgJgHXYIcwAjErUBsjC5BLgAZ1AvELOgS5ACQ6wqAOA7KRgECQCxJIpYD4vlAPBmI+RiggBuIq4F4Fhl4BxB/BeJmIGZnoACYAPFqIJZBlyAVCAPxYiCWR5cgB2QBcQS6IDkAlGinArE0ugQ5AJQUeKH0KBhMAABVixNKp22j3QAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAUCAYAAABWMrcvAAAAg0lEQVR4XmNgGAWUAw4oJgkoAfFuIO4EYmE0ObyAEYj1gHg7EM8FYkVUacJAHYhXQzGITRIA2Qay9RAQmzNAXEM0kATiqQwIzUQDUABNB+Ij6BLYAMiWKUC8n4EIJ4L8MxuItzBAQhWnYpKCHaQYZDXICSCngJxEEHgCcTsDiamB9gAA7ckRDdwWYNEAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAXCAYAAAB0zH1SAAACZ0lEQVR4Xu2WTUiVQRSG36igqChIKqnoxyTc1KI/ghCDgiJqYS6iop1tQxdKKghBRGUQlRX90KpNP7QJFBSECiSEcOEuWhSC6MJWrVro+3Jm+uabvqt+1ysG3Rce7jgzes+c884ZgbL+Py0lG8jqeCHSKrI8nlwsrSXvyG3yilwiS1I7TLtg+7bECwshZfIUeehoICtTO4BW8oYsI+vJIPlATpBKUk3ayDg5435nQaWS3iedpIo0kl9khGxze1T6flhgXldJLakjF8g5coXcgx3uL61wlErKmILaHMxdJFPkGSwIZfQ7LOteGp8Ofpb3ZaGCFtlJ+shNWMnmKwXgg/TSl4+Sb2QjWUM+Ih14CznmxvK64pnVItq4h/SQ52RHejmX9pNhcjmY8xkWGkt3yEvYd8v/j5FU6Ti5iwIWKaTd5LVD41LoCPkN6w7elvL7EGmHBdns5lWdt+6zKCnryr5u+iFkt6q5SJf1BflJDkZryrSyuxf295VhHcJbROvnyS3YRc8llbYbxR/gLBlD4t+ZpIC9RXTgJ7DuVAO7M74rzVm6tI/IJ7I9vTSjlOEv5EC8kKHYIofJV1jzkNStmtx4VinbD8gA8mdbQeugevkkZVFtcd2fHYlii0jyfHiZdaDryXK25O+n5D2s2+QJWFJJ9SqGpa2AlV6tMFZoES+1yjBwfXbBXuWUStUSN8HuwyT5ETABe1DiFqdMal4PTqh6pAPfR64lyxawbCA7yBZ+Y7HyD1AWcam9RdRZYm2FvQdHYTF2INp3ktxAaV7NvKqDBVTIirrUn0kv7ND/zL+2ZZVVVoamAQdDZrrvNjblAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAXCAYAAAB50g0VAAABl0lEQVR4Xu2WvytGURjHH6HoHQxKKeUlJQuDJAZZJSYZrMofYFEWmSSlhIgsJmWwKAOlkOIdGCSDhWK0USa+3869b+ce99wf73vfRedTn977PvcZvvecc8+5Ig7H/6caTsK8USd5OAVbRPXVwR44411XjHo4BtfgG/yEvYEOxSD8hj+a7B3VmwjTZpmYAUfgMFwQe0DWHuETvIeLsDnQ4dEOT+EybDTulcucRAdcN4s2qmA3PIF7sC14u2QyC6jTCQ89eV0OcQGP4D58hq+ilgSXSCI4ihzNC9gvapTTEhfwBnZ4/7m8buEOrPWbksCFuymlBY0KyBA5ozYv6s0eMOqx8Om24JWE72k2ogKGwX5uN7PmDRscvQ14LulHj9gC8oEL8AE2aXU/IH8j4frbhcei3u60wXxsAfngL/I3IKeYAce1WpFKbDUM+AX7jHoN3BY1Kz4Notb5mXddhMHYyGnkdIbu5ingwj+AHxI8xt7hqtbXCi/hCpyGd/Ba1NkcgMfSkmR/iiSBb/IQnIBdoj4aHA5HUn4B7utPIvzRlX4AAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAACDUlEQVR4Xu2VTyhlYRjGXxlFpiSlFMWkNCkpykbqyigLmmIhlrOY0mRBsVWSWEn+hJEsZGExm9EsRrnJCkvZWEhN2Ss1kj/P03u+7neuc+79DvfuzlO/Ovc973fPc773fb8jEitWrChqAPNgHQyBEv/tjCoAbWARrIAOL5ZX9YML0Aw+gmnwF5TZSSEqBVvgF/gMGsEZ+GInFXvkSjXgEgxbsXJwCn5YsSBxNxfAkaRecAw8g0mTRH0S3YU5UGHfeKNo9g60WDGa2QFJ0Z0PE9dw7XcrVg1mRH36xD9tAn/AJqjz344k9mG6aWob3EjAwy1NgQfQLvpyVeLYBRygPQ9eRxXNhZkOihvR3L5ozixYE20NttqIOA4id5u7zv7iJLss4u4kJdhcNtNmLfv3J/jgxRPgFvR5v53EEi2Lm3lO/oEEm3M1/QS6rDiffy1aBadWMeKAroJjUOu/9Uph5sLiRmEvbEwTXmcVk5bAoWTfZSNOevqDKZr+J3oahIltkb7W2TT7eQP8Fj1VXMwasfcexV9iM2R2iQtFq2aXfBDci54eRhnbg8ZyceyxlU5Ejy+jetFdpimjb6JDtyupoasE5+L/kCQkYBBplqVnC7AVMpbAUa3gCkyAAdGvIT9eRVZOL/jv5diV7BR9QR57o971eFqO9HgJ3KFcioPVDb6Kftqj6D1rY8WKlW+9AJJmaCFe1XWmAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAXCAYAAABefIz9AAACrklEQVR4Xu2WzatNURiHX6EI+YyU8lHIBCWZoDugGJB8JfwFzEhKygD5GIiQ74ERkSIkUW4YKAMjDMzkY8RAGJjwe3rXsvdZ56y7zzmdK4P91NM5e69971m/vd79rm1WU/OvGCcnyiHpQInhclR68n+HQLvlHXlcXrDWIUbKs3JtOjDYDJWb5YzkfISJbZUXzQPMbRy2RfKNnGUe9qD8KHfK6XKa3CRfyXNymP/Z4MKk18hT5pP5YT7RlLHykfmkR8uF5mE2lK7ZJZ/JMeF4qdwj58ktcpv5DbxtHrYlI4K9goCrZZ88YPmAe+VLOb50jgm/lVPC8VXZb34DgP9zOnwHVvWYVZQmy8+d5EIe5F5CiFYBCUU4ApRZLL9bMeF91hiQ8UPhO6yUJ62N0uROzJcP5BU5s3G4a3IBKbEv1hyQ67j+cDjuk++sKL8dVoSfLG+UxtqGB/1mMH3oOyUXMAbJBYznaf00D+ZCY7luvpqsGCs3YGlWwSqymk/lEht4D8qRC0gT+m3VAYHfXWBejjzfQLBYmowzvxNyVTjuiKnme0w3QXMBaULtBkyhJG+FT6DrPpaz5X65PpzvCJoPpfLc8ntaK3IBc0Fy5yNpabLVvDDvvkD3PW9FU6qE1Tsjn1jnqwe5gHTuz9YcJAake7aiXJpA6X4zL3lgfkfN5z0gPH+X5D3z7tppsEguIHe4X963xj14hfwVPlPS0oR4Q2JAICBvOU0QotdbBQF/mu9fKdvleyt+h9/nrYaSo/TKxNKk0ZQh7AcrAnLjeJQm/b3Cii5EGVKOlctbAS/DtPOv5o0k+sm800XiFsDvrjMP99r8lS2F0uRFJK0kgl8ujS0zfxFouI6OdsR6/xbTDkxkjtwol5uHTmFehMjNb4K8Jh/Ku9bFxl9TU1PTFX8AJ+ODceJrxPMAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADEAAAAXCAYAAACiaac3AAACB0lEQVR4Xu2WP0gcQRTGn4igqIgYFK1OEcRCQUISBAWLFIZgoyh2diJ2WiimSSWSIoGIGoiIVUDQMiFFCv9iY62diKKCglZqJ8n3OTfn3Jtdc6erWOwPfnD37rH3zc272RWJiYl5anJhD0yoehAlcB42qHoOfAMn4Qx8L+a6j0oB7IBf4RG8hC/TOnwYdEz8XtZH4CqshmXwB/wO85w+yU8aFVzEO9gGP4ofLAj+0ufi9/L1CWxxajVwH7Y7tZviH/hJzEqjZFT8YBqO0ayYX1f3josJXOnUiuG6mNHjTqXgm0b4G86J2boo+N8i+L3DsEv8Xk7HL/EXUQRX4BYsdepp1MHFpHz9EHQwzWv4Wcx8614bNmwRuh4Id4O7siZmZtO2LkN0MBeOEUcokXyvexmQQXXYrBZhYeO03G8xOpiF1xiC3U5N91bAXfHD3msRhH/4b3BDMjvzLTqYpUlux8iie8PChtVDYdMUXJbsd4HoYJYBeKC8gH/hqZjTpwouiR/WLoI9PKlC4f+Bx95PMadWtuEtYYsIIqiXtTNY79RewG0xd3APBo36mGWIK/hKfxDAB/F7a+Eh7HVqrWJ2q9mppZ5NODIcnYzm7A4K4YKYOzDHw3oMvzh9lrdiQtm+a7gJy5Ofd8I92A/74A4cFDUdfESYkOjv1lHCbHweo885Z0xMTBT8AxA3d3sPbjaEAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFMAAAAYCAYAAACGLcGvAAADiklEQVR4Xu2XW4hOURTH/0KR+yVSLpESuZXbC4VQHlwyHkRK1HhRLtOQW40kIYoUuTxIPKB4MMmlKJLLM4qkkSiFUjyQ+P+/tfd855zvnG/Od74ZM3F+9W/Ot885a85ee+211gZyOgydqRrqFLWD6h2+nVMJ66mZMKfuoh5QA0JP5KSiJ3WPOuN+j6LeUwv9A/87c6gP1O+APlI/qF/UY9i2ViSKCdQIdz0W5sx57nd7MIY6CEs7K6nu4duJDKF2w97bQ40O324mk31F20/YFvbIgbUwp26lOgXuiW3ULVjElqMHzP5pamTkXjVokZ9Tk2HfsJe6TfUJPhTDdNhzs6hJVCMsiOoQnmMm+72o+9RranDknlawKeaePugi1T8w1hJa5ctO41C6OJUwjHpFrQqM9aOeUhsCY1EUWdeotSjuNuX8J9Q3aooby2q/sF0/UVeoLpF706jv1DNqoBvTSu2HRZycOciNp0XRqSi9S81ANqdqksHJC9m5AMvrSbvFB8dXWFR61JkoOre431ntYzHMkCp1lAYUt4BQvlQOGQ77sNUwh2dBEXEItivmohgpaTiG0smKc7AaoOIYR1fqKHUT9v0epSzNU39FVvuFF6P5Uv90HSxi693vbtRVhIvVO2qoeycr6lXVZj2iliCdUzWppMnGjZdDu1G7UrVhthtLspM0XsC3O6reD931C5ijTuDv9pDqFF7CEn05/DfHTarsZBNQqtE7qtgKmsz24/KlcsN22ErNd2NtiS9M16mJaDmHKlffQfykyk42BlVm2ToPsysy2/f50idejx7WS75Bb23kMDnuBnUWlbdMSZNKGo9DUXiSOoLS/jHJTtJ4gbh8KVTN5OR9kfFqkRO1rVTJjyNcBCpB3xU3KU02TR73jtQO9Dlau3SBu67Yfrn+Uk4OVrdq0QeruKjIqNhUm4u1o5SGgqcvFchGJ10LOU0diP56tKB11GZ37VE3s8xdp7XfzHjqC0r7S11fQtiZO5H92KhFU3+2EcW8VC1aDDXaDYExHQkVNSsCY4dh82hwv+W8NbDeWc++Degzijs0rf3CMaoJ4RZH53GthqcGtjJyqnpJNdnRvNLeTKXewI66y2GnkwMIR+EmWKei+QjftAfn7hXtH9PYT422/iJYRe9ojvQo0pXnlsKOgK1NW9vPRF9YVKRR4lEtx5J1PawpTqNQTsrJycnJ+Tf4A4AL4zOxH8vaAAAAAElFTkSuQmCC>