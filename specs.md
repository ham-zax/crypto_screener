# Specification: Project Omega
**Version:** 1.0
**Status:** FINAL

---

## 1. High-Level Objective & Problem Statement
*   For sophisticated crypto investors and analysts, the process of systematically identifying and tracking high-potential assets is manual and disorganized. Project Omega is a web-based application that implements "The Omega Protocol," enabling users to screen, track, and manage a watchlist of potential cryptocurrency investments in a structured, data-driven way. For v1, this watchlist is stored locally in the user's browser.

---

## 2. Scope & Exclusions
### 2.1. In Scope (v1)
*   User can manually add new cryptocurrency projects to their watchlist via a guided, multi-step wizard.
*   **All watchlist data is persisted in the user's web browser using `localStorage`.**
*   User can view the list of all projects they have added.
*   User can filter the project watchlist based on specific, user-entered criteria.
*   The application will automatically calculate a weighted "Omega Score" for each project based on manually entered data.
*   User can update the details of an existing project on their watchlist.
*   User can delete a project from their watchlist.

### 2.2. Exclusions (Out of Scope for v1)
*   **A server-side user account system is explicitly out of scope.** Data cannot be synchronized across different browsers or devices.
*   Automated charting capabilities are out of scope for v1.
*   Saving a project analysis as a draft mid-way through the wizard is explicitly out of scope for v1. The wizard must be completed in a single session.

### 2.3. Future Scope (v2+ Potential Features)
*   **User Accounts & Cloud Sync:** A server-side account system to enable data synchronization across devices.
*   **Automated Project Discovery:** Fetching and populating project data from third-party APIs.
*   **Alerting System:** Notifications for when a tracked project's on-chain data shows a significant change.

---

## 3. Key Personas & User Stories
### US-01: Add a New Project via Wizard
**As a** Crypto Analyst, **I want to** use a guided, step-by-step wizard to enter project data, **so that** the process mirrors the protocol's structured, pillar-by-pillar evaluation and ensures data entry is focused and consistent.

### US-02: Filter Watchlist for Relevant Projects
**As a** Crypto Analyst, **I want to** filter my watchlist based on specific Omega Protocol criteria (e.g., narrative sector, market cap range, Omega Score), **so that I can** quickly identify projects that meet my precise investment thesis without manually reviewing every entry.

### US-03: Calculate and Display the Omega Score
**As a** Crypto Analyst, **I want** the application to automatically calculate and display an "Omega Score" for each project, **so that I can** quickly compare the relative potential of assets on my watchlist according to the protocol's weighted standards.

---

## 4. Behavioral Rules & Non-Functional Requirements
| Rule ID | Description | Rationale |
| :--- | :--- | :--- |
| NFR-01 | The application must be web-based. | To ensure accessibility for users across different operating systems without requiring local installation. |
| BR-01 | The application must support manual data entry for all criteria defined in the Omega Protocol. | The initial version of the application depends on the user's own research and data gathering. |
| BR-02 | When multiple filters are applied, they must be combined with an 'AND' condition. | To ensure that the search results become progressively more specific, matching all selected criteria. |
| BR-03 | The Omega Score must be calculated using the formula: `(Narrative Score * 0.25) + (Tokenomics Score * 0.25) + (Data Score * 0.50)`. | This formula codifies the protocol's axiom that data-driven evidence is the most critical factor in asset evaluation. |
| BR-04 | The "Add Project" functionality must be implemented as a three-step wizard. Step 1 for Narrative, Step 2 for Tokenomics, and Step 3 for Data. | To mirror the protocol's methodical structure, reduce cognitive load, and improve the consistency and quality of data entry. |
| BR-05 | All user-generated watchlist data (projects and their scores) MUST be persisted in the browser's `localStorage`. | To enable data persistence within a single browser session without the need for a server-side database or user accounts in v1. |

---

## 5. Acceptance Criteria (Testable Scenarios)
### For US-01: Add a New Project via Wizard
**Scenario:** Analyst adds a project and it persists after refresh.
> **Given** I am viewing the application and my watchlist is empty
> **When** I complete the "Add Project" wizard for a new project named "Project X" AND I then refresh the browser page
> **Then** the main watchlist page should load and display "Project X" in the list.

**Scenario:** Analyst navigates between wizard steps.
> **Given** I am on Step 2 (Tokenomics) of the wizard and have already entered data in Step 1
> **When** I click the "Back" button
> **Then** I am taken to Step 1 (Narrative) AND my previously entered data for that step is still present.

**Scenario:** Analyst attempts to proceed with incomplete data.
> **Given** I am on Step 1 (Narrative) and have left the "Sector Strength" score blank
> **When** I click the "Next" button
> **Then** I remain on Step 1 AND an error message, "All fields are required before proceeding," is displayed.

**Scenario:** Analyst abandons the wizard mid-session.
> **Given** I have started the "Add Project" wizard and entered data into Step 1
> **When** I navigate away from the wizard without completing it (e.g., by refreshing the page or clicking a link in the main navigation)
> **Then** the entered data is discarded AND no new project is created in my watchlist.

### For US-02: Filter Watchlist for Relevant Projects
**Scenario:** User filters the list to find high-potential AI projects.
> **Given** my watchlist contains multiple projects with varying Omega Scores and sectors
> **When** I select 'AI' from the "Hot Sector" filter AND enter a minimum value of '8.0' in the "Omega Score" filter
> **Then** the project list should update to show only the AI project(s) with an Omega Score of 8.0 or higher.

### For US-03: Calculate and Display the Omega Score
**Scenario:** A project's Omega Score is correctly calculated and displayed.
> **Given** I have entered the following scores for a project: Sector Strength (9), Value Prop (7), Backing (8), Valuation (10), Utility (9), Supply Risk (7), Accumulation Signal (8)
> **When** I save the project details
> **Then** the application correctly calculates the Narrative Score as `Average(9,7,8) = 8.0`, the Tokenomics Score as `Average(10,9,7) = 8.67`, and the Data Score as `8.0`, resulting in a final Omega Score of `(8.0 * 0.25) + (8.67 * 0.25) + (8.0 * 0.50) = 8.17` which is displayed on the watchlist.

---

## 6. Risks, Assumptions, & Open Questions
*   **Risk:** Due to the `localStorage` model, all user data will be lost if the user clears their browser cache or switches to a different device/browser. This limitation should be made clear to the user within the application's UI.
*   **Risk:** The calculated Omega Score's accuracy is entirely dependent on the analyst's subjective and consistent rating of the input sub-components. (Mitigated by `BR-04`).
*   **Risk:** The application in v1 relies entirely on manually entered data. This data may be inaccurate, incomplete, or become outdated.
*   **Assumption:** Users are already familiar with the Omega Protocol methodology and its specific terminology.
*   **RESOLVED:** All major design and scope questions for v1 have been answered.

---

## 7. Dependencies
*   **Internal:** None defined yet.
*   **External:** For data gathering, the user is dependent on external sources such as Coinglass, Messari, Delphi Digital, project whitepapers, and crypto news outlets.

---

## 8. Glossary of Terms
| Term | Definition |
| :--- | :--- |
| **Omega Score** | A calculated, weighted score from 1-10 that provides a standardized measure of an asset's potential according to the Omega Protocol. |
| **Ticker** | A shorthand symbol used to uniquely identify a traded asset (e.g., BTC for Bitcoin, ETH for Ethereum). |
| **Market Cap** | The total market value of a cryptocurrency's circulating supply. It is calculated by multiplying the number of circulating coins by the current market price of a single coin. |
| **Fully Diluted Valuation (FDV)** | The theoretical market capitalization of a project if its entire future supply of tokens were in circulation. It is calculated by multiplying the token price by the maximum total supply. |
| **Accumulation Signal** | A rating (1-10) of the clarity and duration of a bullish divergence between an asset's price and its Spot CVD, indicating smart money accumulation. |
| **Backing & Team** | A rating (1-10) of the quality of a project's Venture Capital support and the perceived strength and experience of its team. |
| **Sector Strength** | A rating (1-10) of the perceived strength and capital-attracting power of a project's primary narrative (e.g., AI, DePIN, RWA). |
| **Supply Risk** | A rating (1-10) of the risk posed by future token unlocks based on the project's vesting schedule and distribution. |
| **Token Utility** | A rating (1-10) of the degree to which a token is integral to its protocol's function and value accrual mechanisms (e.g., staking, burning). |
| **Valuation Potential** | A rating (1-10) based on a project's current Fully Diluted Valuation (FDV), where lower valuations represent higher asymmetric upside potential. |
| **Value Proposition** | A rating (1-10) of the clarity, innovation, and compelling nature of a project's solution to a specific problem. |
| **DePIN** | Decentralized Physical Infrastructure Networks. The application of crypto-economic protocols for the deployment and operation of real-world physical infrastructure. |
| **RWA** | Real-World Asset. The tokenization of physical, tangible, or traditional financial assets on a blockchain. |
| **Spot CVD** | Spot Cumulative Volume Delta. A data indicator that measures the net difference between buying and selling pressure from spot market trading, reflecting the unfiltered flow of real money. |
| **Smart Money** | A colloquial term for market participants (e.g., VCs, large patient buyers) believed to be more informed. Their activity is identified through on-chain data patterns like Spot CVD accumulation. |
| **Hot Sector** | A cryptocurrency market category (e.g., AI, DePIN, RWA, GameFi) characterized by significant innovation, investor interest, and a narrative likely to dominate a market cycle. |