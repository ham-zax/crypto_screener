
# Specification: Project Omega
**Version:** 2.7
**Status:** FINAL

---

## 1. High-Level Objective & Problem Statement
*   For a sophisticated crypto analyst, manually discovering and evaluating new crypto assets is time-consuming and inefficient. Project Omega v2 is a semi-automated discovery engine that ingests market data to score assets on their Narrative and Tokenomics, then allows the analyst to provide premium data via a simple paste action to calculate the final, decisive Data Score.

---

## 2. Scope & Exclusions
### 2.1. In Scope (v2)
*   System will automatically fetch a list of cryptocurrency projects from the CoinGecko API.
*   System will automatically calculate the Narrative and Tokenomics scores for ingested projects.
*   The application will allow a user to paste data to generate a Data Score for a specific project.
*   The application will display a filterable, searchable list of all assets.

### 2.2. Exclusions (Out of Scope for v2)
*   Trading or portfolio management capabilities.
*   Real-time, streaming data updates (data will be fetched on a scheduled basis, e.g., daily).

---

## 3. Key Personas & User Stories
### US-04: Automated Project Ingestion
**As the** System, **I want to** connect to the CoinGecko API on a recurring schedule, **so that I can** maintain an up-to-date universe of assets to be screened.

### US-06: Generate Data Score from Pasted Data
**As a** Crypto Analyst, **I want to** paste my exported TradingView chart data into a text box for a specific project, **so that** the system can instantly parse the data and calculate the final Data Score.

### 3.3. Future Concepts (v3+)
### US-05: AI-Powered Qualitative Analysis
**As the** System, **I want to** pass a project's name and ticker to an external AI Agent (Gemini API), **so that I can** programmatically score qualitative metrics like "Backing & Team" and "Value Proposition".

---

## 4. Behavioral Rules & Non-Functional Requirements
| Rule ID | Description | Rationale |
| :--- | :--- | :--- |
| BR-06 | The system MUST use the CoinGecko API as the primary source for the asset universe. | To automate the discovery process. |
| BR-07 | API failures MUST be handled gracefully. | To ensure system resilience. |
| BR-08 | The system MAY use the DefiLlama API to enrich project data with DeFi-specific metrics like TVL. | To provide deeper analytical capabilities for a specific sector. |
| BR-09 | The UI for pasting data (`US-06`) MUST display clear instructional text detailing the data requirements: **1. Required Columns:** `time`, `close`, `Volume Delta (Close)`. **2. Minimum Data:** At least 90 periods (e.g., 90 days of daily data). | To minimize user error and ensure the provided data is valid for analysis. |

### 4.1. Automated & Semi-Automated Scoring Logic (v2)
| Rule ID | Description | Rationale |
| :--- | :--- | :--- |
| AS-01 | **Narrative Score:** The Narrative Score shall be calculated as the average of its three sub-components. | To maintain structural consistency with the Omega Protocol's definition. |
| AS-01a | **Sector Strength Score:** Score is determined by mapping the CoinGecko `category`: Score 9 for (`AI`, `DePIN`, `RWA`); Score 7 for (`L1`, `L2`, `GameFi`, `Infrastructure`); Score 4 for all others. | To objectively quantify the "Hot Sector" principle. |
| AS-01b| **Backing & Team Score:** This score MUST be set to a default, neutral value of 5. | The selected APIs do not provide reliable data for this metric. A neutral score prevents flawed proxies from corrupting the analysis. |
| AS-01c| **Value Proposition Score:** This score MUST be set to a default, neutral value of 5. | This is a qualitative metric that cannot be reliably automated. A neutral score allows quantitative data to drive the final Omega Score. |
| AS-02 | **Tokenomics Score:** The Tokenomics Score shall be calculated as the average of its three sub-components. | To maintain structural consistency with the Omega Protocol's definition. |
| AS-02a | **Valuation Potential Score:** Score is determined by `market_cap`: Score 10 (`< $20M`), 9 (`<$50M`), 8 (`<$100M`), 7 (`<$200M`), 5 (`<$500M`), 3 (`<$1B`), 1 (`>= $1B`). | To programmatically reward assets with higher asymmetric upside potential. |
| AS-02b | **Token Utility Score:** This score MUST be set to a default, neutral value of 5. | This is a qualitative metric. A neutral score is the most prudent choice as the APIs do not provide structured data on value accrual. |
| AS-02c | **Supply Risk Score:** Score is based on Circulation Ratio (`circulating_supply / total_supply`): Score 10 (`>=90%`), 9 (`>=75%`), 7 (`>=50%`), 5 (`>=25%`), 2 (`>=10%`), 1 (`<10%` or data unavailable). | To quantitatively measure the risk of future sell pressure. |
| AS-03 | **Data Score:** The Data Score MUST be calculated based on user-pasted CSV data. By default, a project has no Data Score. | To implement the "user-in-the-loop" model, leveraging premium user data. |
| AS-03a | **CSV Parsing:** The system must parse CSV-formatted text pasted into an input box, expecting headers including `time`, `close`, `Volume Delta (Close)`. | To ensure the system can correctly interpret the data provided by the user. |
| AS-03b | **Accumulation Signal Calculation:** Score is calculated by analyzing at least the last 90 periods in the pasted data: <br>1. Calculate the price trend using **Linear Regression slope** of `close` prices. <br>2. Calculate the "Cumulative Volume Delta" trend using **Linear Regression slope** of the cumulative sum of `Volume Delta (Close)`. <br>3. Score is assigned based on the divergence (e.g., positive CVD slope + flat/negative price slope = high score). | To create a deterministic algorithm that programmatically identifies the "Macro Accumulation Divergence". |
| AS-05 | **Omega Score State:** The final Omega Score for a project MUST NOT be calculated or displayed until the Data Score has been successfully generated. The UI should indicate this unevaluated state (e.g., 'N/A' or 'Awaiting Data'). | To prevent displaying partial or misleading scores and ensure the final score is only shown when complete and accurate. |

---

## 5. Acceptance Criteria (Testable Scenarios)
### For US-06: Generate Data Score from Pasted Data
**Scenario:** Analyst successfully generates a Data Score.
> **Given** I am viewing a project that has an Omega Score status of 'Awaiting Data'
> **When** I paste valid CSV text (containing the required headers and >90 periods) into the data input box and click "Analyze"
> **Then** the system calculates the Data Score based on the logic in `AS-03b`, the score is displayed for the project, and the overall Omega Score is calculated and updated from 'Awaiting Data'.

**Scenario:** Analyst pastes invalid or incomplete data.
> **Given** I am viewing a project
> **When** I paste text that does not contain the required headers (e.g., `Volume Delta (Close)`) OR contains fewer than 90 periods of data
> **Then** an error message is displayed stating "Invalid or incomplete data. Please check requirements." AND no score is calculated.

---

## 6. Risks, Assumptions, & Open Questions
*   **Risk:** **Data Integrity (Manual Paste):** The accuracy of the Data Score is entirely dependent on the user pasting the correct, uncorrupted data for the correct project.
*   **Risk:** **API Dependency:** The system is dependent on CoinGecko and DefiLlama.
*   **RESOLVED:** All major design and scope questions for v2 core functionality have been answered.

---

## 7. Dependencies
*   **External (API):** CoinGecko, DefiLlama.
*   **External (Data Format):** The system is dependent on the CSV text format exported by TradingView, specifically the header names `time`, `close`, and `Volume Delta (Close)`.

---

## 8. Glossary of Terms
| Term | Definition |
| :--- | :--- |
| **Linear Regression** | A statistical method used to model the relationship between a dependent variable and independent variables by fitting a linear equation to observed data. Used to find the "line of best fit" and its slope to determine a trend. |
| **Cumulative Volume Delta (CVD)** | A running total of the Volume Delta. An upward-trending CVD indicates that buying pressure is consistently outpacing selling pressure over time. |
| **Omega Score** | A calculated, weighted score from 1-10 that provides a standardized measure of an asset's potential according to the Omega Protocol. |
| **Ticker** | A shorthand symbol used to uniquely identify a traded asset (e.g., BTC for Bitcoin, ETH for Ethereum). |
| **Market Cap** | The total market value of a cryptocurrency's circulating supply. It is calculated by multiplying the number of circulating coins by the current market price of a single coin. |
| **Fully Diluted Valuation (FDV)** | The theoretical market capitalization of a project if its entire future supply of tokens were in circulation. It is calculated by multiplying the token price by the maximum total supply. |
| **DePIN** | Decentralized Physical Infrastructure Networks. |
| **RWA** | Real-World Asset. |
| **Spot CVD** | Spot Cumulative Volume Delta. A data indicator that measures the net difference between buying and selling pressure from spot market trading. |