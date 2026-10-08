# Intraday Momentum Strategy for SPY
**Author:** Candidate (WU Vienna - Business & Economics)  
**Target:** WUTIS Algorithmic Trading Department  
**Reference Paper:** *Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)* (Zarattini, Aziz, Barbon, 2025)

---

## 1. Project Overview
This repository implements and evaluates an intraday time-series momentum strategy on the SPDR S&P 500 ETF Trust (SPY). The model seeks to capture intraday price trends driven by abnormal supply/demand imbalances, under-reaction to institutional news flows, and dealer delta-hedging feedback loops.

---

## 2. Core Strategy Logic
- **Signal Construction (The Noise Area):** 
  - An intraday equilibrium band is computed based on the 14-day rolling average absolute move from the 09:30 Open to time `HH:MM` ($\sigma_{t,\text{HH:MM}}$).
  - Boundaries are adjusted for overnight gaps using the maximum/minimum of the 09:30 Open and the previous day's 16:00 Close.
  - A break above the Upper Band triggers a **Long** position; a break below the Lower Band triggers a **Short** position.
- **Execution Cadence:** 
  - To minimize whipsaws from high-frequency noise, entry signals are sampled on semi-hourly intervals (`:00` and `:30`).
- **Risk Control (Dynamic Trailing Stop):** 
  - Long exits are governed by $\max(\text{Upper Band}, \text{VWAP})$.
  - Short exits are governed by $\min(\text{Lower Band}, \text{VWAP})$.
  - All positions are closed by 16:00 EST to eliminate overnight risk.

---

## 3. Backtest Methodology
- **Train / Test Split:** Historical data is divided into a 70% In-Sample (Train) window and a 30% Out-of-Sample (Test) window to ensure strategy robustness and guard against overfitting.
- **Realistic Friction:**
  - Broker Commission: $0.0035 per share (Interactive Brokers baseline).
  - Slippage: $0.0010 per share.
  - Total round-trip execution cost: $0.0090 per share.
- **Performance Evaluation Metrics:**
  - Annualized Return
  - Annualized Volatility
  - Annualized Sharpe Ratio

---

## 4. Code Structure
The implementation is contained in a single modular script (`backtest.py`):
1. `load_spy_data()`: Pulls 5-minute intraday bars and filters for regular market hours (09:30 - 16:00 EST).
2. `calculate_indicators()`: Generates rolling intraday VWAP and the 14-day time-of-day dynamic Noise Area bands.
3. `run_backtest()`: Executes the event simulation across train and test sets, incorporating stops and slippage.
4. `evaluate()`: Computes annualized return, volatility, and Sharpe ratio across both subsets.
5. **Visualization:** Generates and saves a cumulative equity curve chart comparing Train vs. Test performance.

---

## 5. How to Run
```bash
# Clone the repository
git clone [https://github.com/](https://github.com/)<your-username>/wutis-intraday-momentum.git
cd wutis-intraday-momentum

# Install dependencies
pip install -r requirements.txt

# Run the backtest
python backtest.py
