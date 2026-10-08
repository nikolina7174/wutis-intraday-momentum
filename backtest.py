"""
WUTIS Algorithmic Trading Case Study
Strategy: Intraday Momentum on SPY (Zarattini, Aziz, Barbon, 2025)
Tasks 2 & 3: Base Model vs. VWAP Stop vs. Task 3 Morning Volatility Filter
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

def load_spy_data():
    df = yf.download(tickers="SPY", period="60d", interval="5m", auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df = df.between_time("09:30", "16:00").copy()
    df.dropna(inplace=True)
    return df

def calculate_indicators(data):
    df = data.copy()
    df['Date'] = df.index.date
    df['Time'] = df.index.time
    
    # 1. VWAP (resets daily at 09:30)
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    df['PV'] = typical_price * df['Volume']
    df['Cum_PV'] = df.groupby('Date')['PV'].cumsum()
    df['Cum_Vol'] = df.groupby('Date')['Volume'].cumsum()
    df['VWAP'] = df['Cum_PV'] / df['Cum_Vol']
    
    # 2. Daily Reference Prices
    dates = sorted(df['Date'].unique())
    times = sorted(df['Time'].unique())
    daily_open = df[df['Time'] == times[0]].groupby('Date')['Open'].first()
    daily_close = df[df['Time'] == times[-1]].groupby('Date')['Close'].last()
    
    # 3. 14-Day Average Move (sigma)
    moves_by_time = {}
    for t in times:
        price_at_t = df[df['Time'] == t].set_index('Date')['Close']
        moves_by_time[t] = (price_at_t / daily_open - 1.0).abs()
        
    move_df = pd.DataFrame(moves_by_time)
    sigma_df = move_df.rolling(window=14).mean().shift(1)
    
    # 4. Noise Boundaries with Overnight Gap Adjustment
    records = []
    for d in dates:
        if d not in sigma_df.index or pd.isna(sigma_df.loc[d].iloc[-1]):
            continue
        idx_prev = dates.index(d) - 1
        if idx_prev < 0:
            continue
        prev_date = dates[idx_prev]
        
        o_930 = daily_open.get(d, np.nan)
        c_prev = daily_close.get(prev_date, o_930)
        
        for t in times:
            sig = sigma_df.loc[d, t] if t in sigma_df.columns else np.nan
            records.append({
                'Date': d,
                'Time': t,
                'UB': max(o_930, c_prev) * (1.0 + sig) if pd.notna(sig) else np.nan,
                'LB': min(o_930, c_prev) * (1.0 - sig) if pd.notna(sig) else np.nan
            })
            
    bounds_df = pd.DataFrame(records)
    merged = df.merge(bounds_df, on=['Date', 'Time'], how='inner')
    merged.dropna(subset=['UB', 'LB'], inplace=True)
    return merged

def run_simulation(df, use_vwap_stop=True, use_vol_filter=False):
    COST_PER_SHARE = 0.0035 + 0.0010  # IBKR commission ($0.0035) + slippage ($0.0010)
    valid_dates = sorted(df['Date'].unique())
    split_idx = int(len(valid_dates) * 0.70)
    train_dates = set(valid_dates[:split_idx])
    daily_results = []
    
    for d in valid_dates:
        day_df = df[df['Date'] == d].copy()
        if len(day_df) < 5:
            continue
            
        # TASK 3 EXTENSION: Filter out dead, low-volatility mornings
        if use_vol_filter:
            morn = day_df[day_df['Time'] <= pd.to_datetime("10:00").time()]
            if len(morn) > 0:
                morn_range = (morn['High'].max() - morn['Low'].min()) / morn['Open'].iloc[0]
                if morn_range < 0.0020:  # If morning range < 0.20%, stay in cash all day
                    daily_results.append({'Date': d, 'PnL': 0.0, 'Trades': 0, 'Split': 'Train' if d in train_dates else 'Test'})
                    continue
        
        pos = 0
        entry_price = 0.0
        daily_pnl = 0.0
        trades_count = 0
        times = sorted(day_df['Time'].unique())
        
        for i, row in day_df.iterrows():
            price = row['Close']
            ub = row['UB']
            lb = row['LB']
            vwap = row['VWAP']
            is_decision_time = (row['Time'].minute in [0, 30])
            is_market_close = (row['Time'] == times[-1])
            
            # Exit Logic
            if pos == 1:
                stop_thresh = max(ub, vwap) if use_vwap_stop else lb
                if (price < stop_thresh) or is_market_close:
                    daily_pnl += ((price - entry_price) / entry_price) - ((COST_PER_SHARE * 2) / entry_price)
                    pos = 0
                    trades_count += 1
            elif pos == -1:
                stop_thresh = min(lb, vwap) if use_vwap_stop else ub
                if (price > stop_thresh) or is_market_close:
                    daily_pnl += ((entry_price - price) / entry_price) - ((COST_PER_SHARE * 2) / entry_price)
                    pos = 0
                    trades_count += 1
            
            # Entry Logic
            if pos == 0 and is_decision_time and not is_market_close:
                if price > ub:
                    pos = 1
                    entry_price = price
                elif price < lb:
                    pos = -1
                    entry_price = price
                    
        daily_results.append({'Date': d, 'PnL': daily_pnl, 'Trades': trades_count, 'Split': 'Train' if d in train_dates else 'Test'})
        
    return pd.DataFrame(daily_results)

def get_metrics(df_sub):
    r = df_sub['PnL']
    ann_ret = r.mean() * 252.0
    ann_vol = r.std() * np.sqrt(252.0)
    sharpe = (ann_ret / ann_vol) if ann_vol > 0 else 0.0
    return round(ann_ret * 100, 2), round(ann_vol * 100, 2), round(sharpe, 2)

if __name__ == "__main__":
    print("Loading SPY data...")
    raw = load_spy_data()
    data = calculate_indicators(raw)
    
    print("Running simulations...")
    res_base = run_simulation(data, use_vwap_stop=False, use_vol_filter=False)
    res_paper = run_simulation(data, use_vwap_stop=True, use_vol_filter=False)
    res_ext = run_simulation(data, use_vwap_stop=True, use_vol_filter=True)
    
    summary = pd.DataFrame({
        'Model': [
            'Base (Opposite Stop) [Train]', 'Base (Opposite Stop) [Test]',
            'Paper (VWAP Stop) [Train]', 'Paper (VWAP Stop) [Test]',
            'Task 3 Extension (Vol Filter) [Train]', 'Task 3 Extension (Vol Filter) [Test]'
        ],
        'Ann. Return (%)': [
            get_metrics(res_base[res_base['Split']=='Train'])[0], get_metrics(res_base[res_base['Split']=='Test'])[0],
            get_metrics(res_paper[res_paper['Split']=='Train'])[0], get_metrics(res_paper[res_paper['Split']=='Test'])[0],
            get_metrics(res_ext[res_ext['Split']=='Train'])[0], get_metrics(res_ext[res_ext['Split']=='Test'])[0],
        ],
        'Ann. Volatility (%)': [
            get_metrics(res_base[res_base['Split']=='Train'])[1], get_metrics(res_base[res_base['Split']=='Test'])[1],
            get_metrics(res_paper[res_paper['Split']=='Train'])[1], get_metrics(res_paper[res_paper['Split']=='Test'])[1],
            get_metrics(res_ext[res_ext['Split']=='Train'])[1], get_metrics(res_ext[res_ext['Split']=='Test'])[1],
        ],
        'Sharpe Ratio': [
            get_metrics(res_base[res_base['Split']=='Train'])[2], get_metrics(res_base[res_base['Split']=='Test'])[2],
            get_metrics(res_paper[res_paper['Split']=='Train'])[2], get_metrics(res_paper[res_paper['Split']=='Test'])[2],
            get_metrics(res_ext[res_ext['Split']=='Train'])[2], get_metrics(res_ext[res_ext['Split']=='Test'])[2],
        ]
    })
    
    print("\n" + "="*70)
    print("BACKTEST COMPARISON: BASE vs. PAPER vs. TASK 3 EXTENSION")
    print("="*70)
    print(summary.to_string(index=False))
