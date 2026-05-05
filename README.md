# IBKR Pairs Trading Bot (Statistical Arbitrage)

Welcome to the bot that's statistically more likely to make money than you are. This is a production-grade, end-to-end Pairs Trading (StatArb) pipeline designed to interface with Interactive Brokers (IBKR).

## Project Overview

This system is split into two halves:
1. **The Research Pipeline (Offline)**: Scans the market, runs PCA/Clustering to find groups, and then uses rigorous statistics (Cointegration, ADF, Hurst, OU) to find "soulmate" pairs.
2. **The Execution Engine (Live)**: Monitors the live spread of vetted pairs, calculates real-time Z-scores, and submits Combo Orders to IBKR when the spread diverges.

---

## Architecture: The "Why" and "How"

### 1. Research Pipeline (`research/`)
*   **PCA & DBSCAN**: Instead of guessing which stocks move together, we use Principal Component Analysis to extract latent factors and DBSCAN to group stocks that are structurally similar.
*   **Cointegration (ADF Test)**: We check if the spread between two stocks is stationary. If it doesn't revert to the mean, it's just a random walk, and we don't touch it.
*   **Hurst Exponent & Half-Life**: We ensure the pair reverts fast enough (H < 0.5) to be tradable within a human lifetime.

### 2. Execution Engine (`execution/`)
*   **Z-Score Signal**: We maintain a rolling window of the spread. If the Z-score hits +2.0, we short the spread. If it hits -2.0, we go long.
*   **IBKR Combo Orders**: We submit both legs simultaneously as a "Bag" order. This prevents "legging risk" where you get filled on one side but not the other while the market runs away from you.
*   **Risk Management**: Includes a circuit breaker that stops trading if the Z-score blows past 4.0 (indicating the relationship has fundamentally broken).

---

## Setup & Installation

### 1. Requirements
Install the dependencies (you'll need Python 3.8+):
```bash
pip install -r requirements.txt
```

### 2. IBKR Configuration (TWS or Gateway)
To actually trade, you need to tell IBKR it's okay to let a script touch your money:
1. Open **Trader Workstation (TWS)** or **IB Gateway**.
2. Go to **File > Global Configuration**.
3. Navigate to **API > Settings**.
4. Check **"Enable ActiveX and Socket Clients"**.
5. Note the **"Socket Port"** (Default is 7497 for paper trading, 7496 for live).
6. Update `config/settings.yaml` with your port and host.

---

## How to Run

### Step 1: Find the Money (Research)
Run the research pipeline to scan your universe and find cointegrated pairs. This will save the valid pairs to `pairs_trading.db`.
```bash
python -m research.pipeline
```

### Step 2: Print the Money (Execution)
Once the database is populated, start the live bot:
```bash
python main.py
```

---

## Component Breakdown

*   `research/universe_selection.py`: The math that groups stocks.
*   `research/cointegration.py`: The math that proves they move together.
*   `execution/ib_client.py`: The plumbing that talks to IBKR.
*   `execution/alpha.py`: The brain that decides when to enter/exit.
*   `execution/order_manager.py`: The hands that pull the trigger.
*   `execution/risk_management.py`: The parent that stops you from going broke.
*   `models/database.py`: Where the pairs live.
*   `config/settings.py`: Where you change things before you break them.

---

## Disclaimer
*This bot is for educational purposes. If you lose your life savings because you ran a script from the internet, don't come crying to me. Use paper trading first.*
