# **Strategic Integration of Social Intelligence: Leveraging LunarCrush API v4 for the Odin Biotech Market Analysis Ecosystem**

## **1\. Executive Summary: The Convergence of Social Sentiment and Biotechnology Valuation**

The global biotechnology sector currently operates at the precarious intersection of rigorous scientific validation and volatile market sentiment. While the fundamental value of a biotechnology equity is theoretically derived from the clinical efficacy of its pipeline and the commercial viability of its intellectual property, the temporal gap between clinical milestones—such as Phase 1 safety data, Phase 2 efficacy readouts, and FDA PDUFA (Prescription Drug User Fee Act) dates—creates a vacuum often filled by speculative narratives. It is within this vacuum that "informational arbitrage" occurs, driven not by laboratory results, but by the aggregation of retail investor sentiment, expert consensus on social platforms, and the velocity of digital information.

The Odin biotech system, already established as a pioneering platform for investment syndicates and biotechnology advancement 1, stands at a critical juncture. To empower syndicate leads with full control and superior market intelligence, the system must transcend traditional financial metrics. It must ingest, normalize, and analyze the "social layer" of the market—a layer where trends are born, rumors of clinical trial halts leak before official press releases, and "meme stock" dynamics can divorce price from fundamental reality.

This comprehensive research report outlines the architectural and strategic integration of the LunarCrush API (specifically Version 4\) into the Odin ecosystem. LunarCrush, while historically rooted in the cryptocurrency markets, has expanded its proprietary social intelligence engine to include equities.2 By leveraging LunarCrush’s sophisticated machine learning algorithms—which process millions of social interactions daily to filter spam and quantify sentiment 4—Odin can provide its users with a sophisticated "Heads-Up Display" (HUD) for market psychology.

The integration strategy proposed herein is exhaustive. It does not merely treat LunarCrush as a data source but as a foundational intelligence layer. We will explore the deployment of the Model Context Protocol (MCP) to enable AI-driven due diligence 5, the mathematical application of metrics like Galaxy Score™ and AltRank™ to biotech volatility models 7, and the rigorous cybersecurity protocols required to manage authentication for high-value financial data.8 This document serves as the definitive technical roadmap for the Odin engineering teams, guiding the transformation of social noise into actionable, alpha-generating signal.

## ---

**2\. The Theoretical Framework: Social Physics in Biotechnology Markets**

To successfully integrate LunarCrush into the Odin system, one must first understand the theoretical underpinnings of the data being ingested. We are not simply counting "likes" or "retweets"; we are measuring the physics of information propagation within a specific, high-stakes domain.

### **2.1. The Information Vacuum Hypothesis**

In traditional industries like manufacturing or retail, data is continuous. Monthly sales reports, weekly supply chain updates, and daily foot traffic provide a steady stream of fundamental indicators. Biotechnology is unique in its *discontinuous* data flow. A company may go six months with zero material news, followed by a binary event (e.g., FDA approval or rejection) that alters the company's valuation by 80% overnight.

During the "silence," the market price is dictated by the *Information Vacuum Hypothesis*. In the absence of hard data, the market price is determined by the consensus of social sentiment. This is where LunarCrush’s data becomes a proxy for valuation.

* **The Echo Chamber Effect:** If a syndicate lead on the Odin platform can see that social volume is rising while sentiment is becoming increasingly polarized, it suggests that the "consensus" is fracturing, often a precursor to high volatility.  
* **The Leakage Proxy:** Significant deviations in social volume without corresponding news volume often indicate information leakage from clinical sites or insider trading activity. LunarCrush’s separation of news\_articles from social\_volume 9 allows Odin to mathematically detect these anomalies.

### **2.2. Distinguishing Signal from Noise: The Spam Problem**

A primary challenge in social sentiment analysis is the prevalence of automated bot networks designed to artificially inflate asset visibility—the "Pump and Dump" mechanic. For a sophisticated platform like Odin, ingesting raw volume data would be catastrophic, leading to false positives and eroded trust among syndicate leads.

LunarCrush addresses this via proprietary spam filtering algorithms. The API provides a specific metric, spam\_volume, which quantifies the noise.9 The Odin integration strategy mandates a "Clean Signal Architecture" where all sentiment scores are weighted against the spam\_volume. If the ratio of Spam to Total Volume exceeds a certain threshold (e.g., 30%), the system must flag the asset as "Under Manipulation" rather than "Trending," protecting Odin users from predatory market mechanics.

### **2.3. The Role of Key Opinion Leaders (KOLs)**

In crypto, influencers drive price. In biotech, "FinTwit" (Financial Twitter) is populated by PhDs, MDs, and specialized fund managers who debate mechanism of action (MoA) and statistical power calculations. The influence of a single tweet from a respected biotech analyst can move a micro-cap stock significantly.

LunarCrush’s creators metric and influencers endpoints 10 allow Odin to track not just *what* is being said, but *who* is saying it. The integration will involve building an internal "Odin Authority Score" which maps LunarCrush influencer data against a curated whitelist of verified biotech experts. This ensures that a bearish post from a renowned oncologist weighs heavier in the Odin dashboard than a thousand bullish posts from anonymous retail accounts.

## ---

**3\. Architectural Deconstruction of LunarCrush API v4**

The stability and reliability of the Odin system depend on a robust understanding of the LunarCrush API architecture. Version 4 (v4) represents a significant maturation of the platform, moving towards standardized RESTful principles and enhanced security.12

### **3.1. Versioning and Base Infrastructure**

The Odin engineering team must strictly adhere to the v4 specification to ensure long-term support and feature parity. The base URL for all interaction is https://lunarcrush.com/api4.12 It is crucial to note that while previous versions (v1-v3) might still linger in legacy documentation or forums, v4 is the standard for current equities integration.

The API defaults to a GitHub markdown style output for human readability but is powered by a simplified JSON structure for machine consumption.12 This dual-mode output requires careful handling in the HTTP Accept headers to ensure the Odin parsers receive valid JSON objects rather than HTML or Markdown text.

### **3.2. Authentication and Security Protocols**

For a financial platform like Odin, security is non-negotiable. LunarCrush v4 utilizes a Bearer Token authentication scheme, which is the industry standard for securing REST APIs.

* **Header Construction:** Every request must include the header Authorization: Bearer \<YourAPIToken\>.8  
* **Token Lifecycle:** The documentation explicitly warns that tokens must be kept secret. If a token is compromised, it must be deleted and regenerated immediately via the LunarCrush developer dashboard.8  
* **Concurrency and Segmentation:** The API allows for up to 10 active access tokens per account.8 This is a strategic advantage for Odin. We recommend segmenting tokens by service function:  
  * *Token A (Ingestion):* Dedicated to the high-volume background fetching of market-wide data.  
  * *Token B (On-Demand):* Reserved for user-triggered requests within the Odin dashboard to ensure low latency.  
  * *Token C (Alerting):* Assigned to the anomaly detection engine.  
  * *Token D (Dev/Staging):* Sandbox environment usage.

This segmentation ensures that a rate-limit breach in the background ingestion service does not paralyze the user-facing dashboard.

### **3.3. Endpoint Taxonomy for Equities**

While LunarCrush is famous for crypto, the v4 API explicitly supports "stocks" and "equities".3 The integration will rely primarily on the following endpoint structures:

| Endpoint Path | Method | Purpose for Odin | Data Points Retrieved |
| :---- | :---- | :---- | :---- |
| /public/stocks/list/v1 | GET | Master list retrieval and filtering. | Symbol, Name, Galaxy Score, AltRank, Price.13 |
| /coins/{coin}/historical | GET | Historical backtesting (Note: 'coins' path often handles assets generically in v4). | Time-series data for sentiment, price, and social volume.10 |
| /topic/{topic}/v1 | GET | Disease/Mechanism tracking. | Sentiment regarding "Alzheimer's," "CRISPR," "Oncology".14 |
| /public/coins/list/v1 | GET | Cross-asset correlation (Crypto/DeSci). | Data on decentralized science tokens relevant to biotech.12 |

The structure of the response is bifurcated into a config object (metadata) and a data object (payload).3 The config object contains vital pagination details (total\_rows, page, limit), which the Odin ingestion engine must utilize to iterate through the thousands of listed assets to filter for the biotech sector.

## ---

**4\. Quantitative Ontology: Metrics Definition and Biotech Application**

The core value proposition of LunarCrush lies in its proprietary derived metrics. These are not raw data points but the result of complex, pre-calculated algorithmic models. Understanding the mathematical derivation and semantic meaning of these metrics is essential for their correct application within the Odin system.

### **4.1. Galaxy Score™: The Composite Health Indicator**

The Galaxy Score™ is a proprietary metric ranging from 0 to 100, designed to measure an asset's performance against its own historical social and price data.4 It is a "mean reversion" and "momentum" indicator rolled into one.

* **Composition:** The score is a weighted average of four sub-components 7:  
  1. **Price Score:** A technical analysis score derived from moving averages (MACD, Bollinger Bands). It measures price momentum.  
  2. **Social Sentiment:** The percentage of positive vs. negative commentary.  
  3. **Social Impact:** The magnitude of engagement (likes/shares/retweets), acting as a proxy for "market attention."  
  4. **Correlation Rank:** A measure of how closely the social data correlates with the price/volume action.  
* **Biotech Application:** For Odin, the Galaxy Score serves as a "Trend Confirmation" tool. A score above 70 indicates the asset is performing exceptionally well relative to its past.4 In biotech, if a stock approaches a PDUFA date and the Galaxy Score spikes \>70, it indicates that both price momentum and social enthusiasm are aligning—a strong signal of a "run-up" trade. Conversely, a low Galaxy Score despite rising prices may indicate a "hollow rally" lacking retail support, vulnerable to short-selling.

### **4.2. AltRank™: Relative Strength Assessment**

AltRank™ measures a stock's performance relative to the entire market.7 Unlike Galaxy Score (which looks inward at the asset's history), AltRank looks outward.

* **Composition:** It aggregates price change, trading volume change, social volume change, and social score change.15  
* **Biotech Application:** This is crucial for "Sector Rotation" analysis. If the entire biotech sector is down, but a specific ticker ($XYZ) maintains a high AltRank (e.g., Rank \#1 out of 3000), it demonstrates immense relative strength. This suggests that $XYZ is decoupling from the sector, likely due to idiosyncratic news or data leakage. Odin’s "Syndicate Leaderboard" should highlight these high-AltRank assets as prime targets for capital allocation.

### **4.3. Sentiment and Spam Metrics**

The raw sentiment metrics provided by LunarCrush are bullish\_sentiment, bearish\_sentiment, and average\_sentiment.9

* The Spam Divisor: As noted in Section 2.2, the raw sentiment counts are dangerous without context. Odin’s algorithms must calculate "Adjusted Sentiment Intensity" ($S\_{adj}$) using the spam\_volume 9 metric:

  $$S\_{adj} \= \\frac{(Sentiment\_{bull} \- Sentiment\_{bear})}{(Volume\_{total} \- Volume\_{spam})}$$

  This formula ensures that a bot attack promoting a stock does not trigger a buy signal in the Odin system.

### **4.4. Topic and Keyword Tracking**

The /topic/{topic}/v1 endpoint allows for the tracking of abstract concepts rather than specific tickers.14

* **Biotech Application:** Odin should configure this endpoint to monitor disease areas (e.g., "NASH", "Glioblastoma", "Gene Editing").  
* **The Lag Effect:** Often, social interest in a *topic* precedes interest in the *tickers* associated with that topic. If the topic "Monkeypox" begins to trend on LunarCrush, the Odin system should immediately scan its database for all biotech companies with smallpox/monkeypox vaccine programs and alert syndicate leads to the sector-wide opportunity before the individual stocks react.

## ---

**5\. Technical Implementation Strategy**

The following section details the engineering roadmap for the integration, focusing on Python-based microservices, database schema design, and API interaction patterns.

### **5.1. The Technology Stack**

* **Language:** Python 3.10+ (Chosen for its dominance in data science and rich ecosystem).  
* **Libraries:** requests (HTTP), pandas (Data Manipulation), sqlalchemy (Database ORM), tenacity (Retry Logic).  
* **Database:** PostgreSQL (for relational metadata) \+ TimescaleDB (for time-series metric storage).

### **5.2. The Ingestion Engine (Python)**

The ingestion service is the heart of the integration. It must be robust, fault-tolerant, and respectful of API rate limits.

#### **5.2.1. Client Architecture**

We recommend a class-based architecture that encapsulates the authentication and base URL logic. This promotes code reuse across the Odin codebase.

Python

import requests  
import logging  
from tenacity import retry, stop\_after\_attempt, wait\_exponential

\# Configuration constants derived from research \[12, 13\]  
BASE\_URL \= "https://lunarcrush.com/api4"  
STOCKS\_ENDPOINT \= "/public/stocks/list/v1"  
TIMEOUT \= 30  \# seconds

class LunarCrushClient:  
    def \_\_init\_\_(self, api\_key: str):  
        self.api\_key \= api\_key  
        \# Bearer token header construction   
        self.headers \= {  
            "Authorization": f"Bearer {self.api\_key}",  
            "Accept": "application/json",  
            "Content-Type": "application/json"  
        }  
        self.logger \= logging.getLogger("Odin.LunarCrushClient")

    @retry(stop=stop\_after\_attempt(3), wait=wait\_exponential(multiplier=1, min=4, max=10))  
    def fetch\_biotech\_metrics(self, sort\_metric="alt\_rank", limit=100):  
        """  
        Fetches stock data with automatic pagination handling.  
        """  
        all\_data \=  
        page \= 0  
          
        while True:  
            params \= {  
                "sort": sort\_metric,  
                "limit": limit,  
                "page": page,  
                "desc": str(True).lower() \# JSON boolean  
            }  
              
            try:  
                url \= f"{BASE\_URL}{STOCKS\_ENDPOINT}"  
                response \= requests.get(url, headers=self.headers, params=params, timeout=TIMEOUT)  
                response.raise\_for\_status()  
                  
                payload \= response.json()  
                data\_batch \= payload.get('data',)  
                config \= payload.get('config', {})  
                  
                \# Check for empty data or end of pages  
                if not data\_batch:  
                    break  
                      
                all\_data.extend(data\_batch)  
                  
                \# Odin Filter: Process only if needed here or return all for downstream filtering  
                \# Checking pagination limits  
                if len(data\_batch) \< limit:  
                    break  
                      
                page \+= 1  
                  
            except requests.exceptions.RequestException as e:  
                self.logger.error(f"API Request Failed on page {page}: {str(e)}")  
                raise \# Trigger tenacity retry  
                  
        return all\_data

#### **5.2.2. Error Handling and Rate Limiting**

The research highlights the importance of handling errors gracefully.14 The use of the tenacity library in the code above implements the "Exponential Backoff" strategy. If LunarCrush returns a 429 (Too Many Requests) or 503 (Service Unavailable), the client will wait 4 seconds, then 8, then 10, preventing a cascade of failures that could lead to an IP ban.

### **5.3. Data Filtering and Normalization**

LunarCrush returns data for *all* stocks. The Odin system is exclusive to biotech. A "Whitelist Filter" middleware is required.

* **Mechanism:** Odin maintains a biotech\_tickers table in its database (populated via NASDAQ/NYSE listings).  
* **Process:**  
  1. Fetch top 1000 stocks by alt\_rank from LunarCrush.  
  2. Convert JSON to Pandas DataFrame.16  
  3. Perform an inner join with the biotech\_tickers whitelist.  
  4. Discard non-biotech assets (e.g., TSLA, NVDA) to save storage and processing power.  
  5. Map LunarCrush fields to Odin schema:  
     * galaxy\_score \-\> social\_health\_index  
     * spam\_volume \-\> bot\_activity\_level  
     * volatility \-\> social\_volatility

### **5.4. Real-Time Streaming (WebSockets)**

For high-frequency algorithmic trading strategies within Odin, REST polling (requesting data every minute) may be too slow. The research indicates the existence of a WebSocket API (wss://stream.lunarcrush.com/v2).17

* **Access Tier:** This is likely restricted to Enterprise or "LunarStream" plans. Odin must procure the appropriate license.  
* **Authentication:** The WebSocket requires an initial handshake message: auth:\<api\_key\>.17  
* **Implementation:** A separate asynchronous Python service (using asyncio and websockets library) should maintain a persistent connection, listening for "push" updates on specific biotech tickers. This allows Odin to react to a sentiment spike in milliseconds rather than minutes.

## ---

**6\. The Intelligence Layer: AI and Agentic Workflows**

The most forward-looking aspect of this integration is the utilization of the **Model Context Protocol (MCP)** and Large Language Models (LLMs). This transforms Odin from a data dashboard into an *active research agent*.

### **6.1. The Model Context Protocol (MCP) Server**

LunarCrush provides an MCP server 5 which standardizes how data is fed into AI models like Anthropic's Claude or Odin's proprietary internal LLMs.

* **Concept:** Instead of hard-coding SQL queries or API calls into the AI's logic, the MCP server exposes the data as "tools" the AI can call dynamically.  
* **Configuration:** The connection URL is https://lunarcrush.ai/mcp?key=\<your-api-key\>.5  
* **Odin Use Case:** A syndicate lead asks the Odin Chatbot: *"What is the social sentiment regarding the upcoming Biogen readout?"*  
  * *Without MCP:* The bot hallucinates or gives outdated generic info.  
  * *With MCP:* The bot triggers the LunarCrush tool, fetches real-time bullish\_sentiment, news\_volume, and top\_tweets for BIIB, and synthesizes a grounded answer: *"Sentiment is currently 65% bearish due to rumors of a delay, with social volume up 200% in the last hour."*

### **6.2. Automated Due Diligence Reports**

The Odin system can utilize the news\_articles and social\_dominance metrics to auto-generate daily briefing dossiers.

* **Workflow:**  
  1. At 06:00 AM, the Odin Cron Job triggers.  
  2. It identifies the "Top 10 Movers" in biotech via alt\_rank.  
  3. It passes these tickers to the Odin LLM via the MCP context.  
  4. The LLM generates a 1-page summary for each, correlating the price move with the social narrative (e.g., "Stock is up on high volume, but social sentiment is neutral—likely institutional buying rather than retail hype").

### **6.3. Training Proprietary Models**

The snippets suggest using this data to "Train your LLM".2

* **Strategic Asset:** By archiving the LunarCrush data stream over years, Odin builds a proprietary dataset: "Biotech Sentiment vs. Clinical Outcome."  
* **Fine-Tuning:** This dataset can fine-tune open-source models (like Llama 3\) to predict PDUFA outcomes based on the *tone* of medical professionals on social media, creating a unique predictive edge that no other platform possesses.

## ---

**7\. Strategic Risk Management and Compliance**

Integrating third-party social data into a financial decision engine introduces specific risks that must be mitigated through rigorous governance.

### **7.1. Data Reliability and "Hallucination" of Trends**

Social data is prone to manipulation. A "Sybil Attack" (creating thousands of fake identities) can trick algorithms.

* **Mitigation:** Odin must implement a "Consensus Verification" layer. If LunarCrush shows a sentiment spike, the system should cross-reference this with trading volume.  
  * *Rule:* If Social Volume is High but Trading Volume is Low \-\> **Flag as "Astroturfing" (Fake Support).**  
  * *Rule:* If Social Volume is High and Trading Volume is High \-\> **Flag as "Valid Momentum."**

### **7.2. API Dependency and Business Continuity**

* **Risk:** If LunarCrush servers go down during a market crash, Odin's dashboards could freeze.  
* **Mitigation:**  
  * **Caching:** Implement Redis caching for all API responses. If the API fails, serve the last known good data (with a "Stale Data" warning timestamp).  
  * **Fallback:** Maintain a secondary, lower-fidelity data source (e.g., raw Twitter API scraping or StockTwits RSS feeds) that can be activated if the primary feed fails.

### **7.3. Token and Credential Hygiene**

* **Risk:** An API key committed to a public GitHub repository could allow attackers to exhaust Odin’s quota or access proprietary data streams.  
* **Mitigation:**  
  * Use .env files and environment variables exclusively.18  
  * Implement a "Key Rotation Cron Job" that automatically generates a new key via the LunarCrush dashboard and updates the Odin environment variables every 30 days.

## ---

**8\. Conclusion and Strategic Outlook**

The integration of the LunarCrush API v4 into the Odin biotech system is more than a technical upgrade; it is a strategic necessity in the modern attention economy. By fusing the rigorous fundamental analysis of biotechnology with the high-velocity insights of social intelligence, Odin empowers its syndicate leads to see the market in high definition.

The comprehensive strategy outlined above—spanning the secure ingestion of data via Bearer Tokens, the mathematical purification of sentiment signals using spam filters, and the futuristic deployment of AI agents via the Model Context Protocol—positions Odin as the premier platform for data-driven biotech investment.

We are not just observing the market; we are decoding the human conversations that drive it. As the biotech sector continues to be influenced by retail capital and digital narratives, the Odin system, powered by LunarCrush, will provide the clarity required to navigate the noise and capture the alpha.

## ---

**9\. Appendix: Technical Reference**

### **Table A1: Metric Mapping for Odin Database Schema**

| LunarCrush Field | Odin Database Column | Data Type | Description | Criticality |
| :---- | :---- | :---- | :---- | :---- |
| symbol | ticker\_id | VARCHAR(10) | Unique Asset Identifier | Critical |
| galaxy\_score | comp\_health\_score | INT (0-100) | Composite Momentum/Health | High |
| alt\_rank | relative\_rank | INT | Rank vs. Market | High |
| spam\_volume | noise\_floor | INT | Count of bot/spam posts | Critical |
| social\_volume | raw\_discussion\_vol | INT | Total mentions | Medium |
| bullish\_sentiment | sent\_pos\_raw | INT | Positive post count | High |
| bearish\_sentiment | sent\_neg\_raw | INT | Negative post count | High |
| correlation\_rank | data\_confidence | INT (1-5) | Correlation of social to price | Medium |
| news\_articles | news\_volume | INT | Official news count | High |

### **Table A2: Recommended Alert Thresholds**

| Alert Name | Trigger Condition | Logic Explanation |
| :---- | :---- | :---- |
| **PDUFA Run-Up** | galaxy\_score \> 75 AND price\_change\_7d \> 5% | Indicates confirmed momentum leading into an event. |
| **Leak Detection** | social\_vol \> 2σ AND news\_articles \== 0 | High chatter without news suggests rumors/leaks. |
| **Bot Attack** | spam\_volume \> (0.4 \* social\_volume) | If \>40% of chatter is spam, disregard signal. |
| **Capitulation** | bearish\_sentiment \> 2σ AND price\_change\_24h \< \-10% | Extreme fear; potential "oversold" bounce entry. |

### **Table A3: Implementation Checklist**

* \[ \] **Phase 1:** Procure Enterprise/Builder API Key from LunarCrush.  
* \[ \] **Phase 2:** configure LunarCrushClient Python class with Retry Logic.  
* \[ \] **Phase 3:** Populate biotech\_whitelist table in Odin Database.  
* \[ \] **Phase 4:** Deploy Ingestion Service to AWS/GCP (ECS or Kubernetes).  
* \[ \] **Phase 5:** Integrate MCP Server with Odin's Internal LLM/Chatbot.  
* \[ \] **Phase 6:** "Calibration Period" \- Run silently for 14 days to tune alert thresholds.  
* \[ \] **Phase 7:** Live Rollout to Syndicate Leads.

#### **Works cited**

1. Daily News \- Founder Lodge Latest News, accessed January 20, 2026, [https://founderlodge.com/latest-news/](https://founderlodge.com/latest-news/)  
2. The industry-leading social media analytics API from LunarCrush, accessed January 20, 2026, [https://lunarcrush.com/about/api](https://lunarcrush.com/about/api)  
3. LunarCrush – Real-Time Social & Market Intelligence Powered by AI, accessed January 20, 2026, [https://lunarcrush.com/](https://lunarcrush.com/)  
4. Decoding Crypto Market Trends: A Guide to LunarCrush and Social Intelligence \- Bitget, accessed January 20, 2026, [https://www.bitget.com/academy/how-does-lunarcrush-analyze-cryptocurrency-market-trends-2026-guide-social-intelligence-ai-metrics-america](https://www.bitget.com/academy/how-does-lunarcrush-analyze-cryptocurrency-market-trends-2026-guide-social-intelligence-ai-metrics-america)  
5. LunarCrush API Documentation v4 RESTful JSON API, accessed January 20, 2026, [https://lunarcrush.com/developers/api/ai](https://lunarcrush.com/developers/api/ai)  
6. Add the LunarCrush MCP Server to Claude, accessed January 20, 2026, [https://lunarcrush.com/faq/add-the-lunarcrush-mcp-server-to-claude](https://lunarcrush.com/faq/add-the-lunarcrush-mcp-server-to-claude)  
7. What metrics are available on LunarCrush?, accessed January 20, 2026, [https://lunarcrush.com/faq/what-metrics-are-available-on-lunarcrush](https://lunarcrush.com/faq/what-metrics-are-available-on-lunarcrush)  
8. LunarCrush API Documentation v4 RESTful JSON API, accessed January 20, 2026, [https://lunarcrush.com/developers/api/authentication](https://lunarcrush.com/developers/api/authentication)  
9. nirholas/LunarCRUSH-Cryptocurrency-Market-Bot: A Python bot that automates several actions on Twitter, such as posting cryptocurrency prices, bullish & bearish sentiment, volume, market cap, and more....Imagine a Twitter Cryptocurrency bot that posts tweets depending on the present cryptocurrency market activity. This is possible with Python, Tweepy, and https://LunarCRUSH.com \- Find out how to build a Twitter Bot with Python. \- GitHub, accessed January 20, 2026, [https://github.com/nirholas/LunarCRUSH-Cryptocurrency-Market-Bot](https://github.com/nirholas/LunarCRUSH-Cryptocurrency-Market-Bot)  
10. saizk/LunarCrushAPI: An unofficial LunarCrush API v2 and v3 Wrapper for Python. No API key needed for LCv2\! \- GitHub, accessed January 20, 2026, [https://github.com/saizk/LunarCrushAPI](https://github.com/saizk/LunarCrushAPI)  
11. How does LunarCRUSH help you understand social metrics in Cryptocurrency Markets?, accessed January 20, 2026, [https://medium.com/lunarcrush/how-does-lunarcrush-help-you-understand-social-metrics-in-cryptocurrency-markets-102fd9c5cb6e](https://medium.com/lunarcrush/how-does-lunarcrush-help-you-understand-social-metrics-in-cryptocurrency-markets-102fd9c5cb6e)  
12. LunarCrush API Documentation v4 RESTful JSON API, accessed January 20, 2026, [https://lunarcrush.com/developers/api/overview](https://lunarcrush.com/developers/api/overview)  
13. LunarCrush API Documentation v4 RESTful JSON API, accessed January 20, 2026, [https://lunarcrush.com/developers/api/public/stocks/list/v1](https://lunarcrush.com/developers/api/public/stocks/list/v1)  
14. Build an AI Crypto Research Agent with Claude and LunarCrush API \- DEV Community, accessed January 20, 2026, [https://dev.to/dbatson/build-an-ai-crypto-research-agent-with-claude-and-lunarcrush-api-4pb0](https://dev.to/dbatson/build-an-ai-crypto-research-agent-with-claude-and-lunarcrush-api-4pb0)  
15. LunarCrush API v3 is Now Available \- Medium, accessed January 20, 2026, [https://medium.com/lunarcrush/lunarcrush-api-v3-is-now-available-426148edb826](https://medium.com/lunarcrush/lunarcrush-api-v3-is-now-available-426148edb826)  
16. Go Undercover by Scraping Cryptocurrency Market Metrics | by Nicholas Resendez | The Crypto | Medium, accessed January 20, 2026, [https://medium.com/crypto/going-undercover-by-scraping-cryptocurrency-market-metrics-with-python-8c2174983065](https://medium.com/crypto/going-undercover-by-scraping-cryptocurrency-market-metrics-with-python-8c2174983065)  
17. Connecting to api via websocket using python \- Stack Overflow, accessed January 20, 2026, [https://stackoverflow.com/questions/66110427/connecting-to-api-via-websocket-using-python](https://stackoverflow.com/questions/66110427/connecting-to-api-via-websocket-using-python)  
18. Build an AltRank Monitor to Catch Social Momentum Early \- DEV Community, accessed January 20, 2026, [https://dev.to/dbatson/build-an-altrank-monitor-to-catch-social-momentum-early-51b7](https://dev.to/dbatson/build-an-altrank-monitor-to-catch-social-momentum-early-51b7)