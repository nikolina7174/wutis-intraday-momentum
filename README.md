# Intraday Momentum Strategy for SPY
**Author:** Candidate (WU Vienna - Business & Economics)  
**Target:** WUTIS Algorithmic Trading Department  
**Reference Paper:** *Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)* (Zarattini, Aziz, Barbon, 2025)

---

## 1. Executive Summary & Hypotheses (Task 1)
This project evaluates an intraday time-series momentum strategy on SPY (SPDR S&P 500 ETF Trust).
- **Core Hypothesis:** Abnormal supply/demand imbalances drive intraday momentum due to institutional order slicing (slow-moving capital) and dealer delta-hedging (negative gamma feedback).
- **Why It Works:** Captures multi-hour trends on high-activity days while cutting reversals quickly with dynamic stops, creating an asymmetric risk/reward profile.
- **Failure Modes:** Low-volatility range-bound days (whipsaws) and mean-reverting environments (positive gamma regimes).

---

## 2. Methodology & Implementation (Task 2)
- **Signal Construction (The Noise Area):** 
  - Dynamic bands computed from the 14-day rolling average move from 09:30 Open to time `HH:MM` ($\sigma_{t,\text{HH:MM}}$).
  - Overnight gap adjustments applied using $\max(\text{Open}_{9:30}, \text{Close}_{t-1, 16:00})$ and $\min(\text{Open}_{9:30}, \text{Close}_{t-1, 16:00})$.
- **Execution & Stops:** 
  - Trades evaluated on semi-hourly intervals (`:00` and `:30`).
  - Dynamic trailing stops: $\max(\text{Upper Band}, \text{VWAP})$ for Longs; $\min(\text{Lower Band}, \text{VWAP})$ for Shorts.
  - Strict exit at 16:00 (zero overnight risk).
- **Backtesting Rigor:** 
  - 70% In-Sample (Train) / 30% Out-of-Sample (Test) split.
  - Realistic friction modeling: $0.0035/share commission + $0.0010/share slippage ($0.0090 round-trip).

---

## 3. Original Strategy Extension (Task 3): Morning Volatility Regime Filter
- **Design Choice:** Section 4.1 of the paper shows that the strategy generates alpha during volatile regimes and suffers false breakouts on quiet days.
- **Mechanism:** The strategy checks SPY's range in the first 30 minutes (09:30–10:00). If $(\text{High} - \text{Low}) / \text{Open} < 0.20\%$, the session is classified as **Range-Bound** and the strategy stays 100% in cash for the entire day.
- **Expected Edge:** Avoids low-probability whipsaws, cuts unnecessary commission costs, and protects the out-of-sample Sharpe Ratio.

---

## 4. Code Structure
The single script (`backtest.py`) contains:
1. `load_spy_data()`: Pulls 5-minute intraday bars and filters for regular trading hours (09:30 - 16:00 EST).
2. `calculate_indicators()`: Generates rolling intraday VWAP and the 14-day time-of-day dynamic Noise Area bands.
3. `run_simulation()`: Configurable simulation engine supporting:
   - Base Model (Opposite band stop)
   - Paper Model (VWAP dynamic trailing stop)
   - Task 3 Extension (VWAP dynamic stop + Morning Volatility Filter)
4. `get_metrics()`: Computes Annualized Return, Annualized Volatility, and Sharpe Ratio across Train and Test splits.

---

## 5. How to Run
```bash
# Clone the repository
git clone [https://github.com/](https://github.com/)<your-username>/wutis-intraday-momentum.git
cd wutis-intraday-momentum

# Install dependencies
pip install -r requirements.txt

# Run backtest
python backtest.py
