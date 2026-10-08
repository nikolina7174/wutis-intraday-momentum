"""
WUTIS Algorithmic Trading Division - Case Study
Intraday Momentum Strategy for SPY
Author: Applicant
Based on: Zarattini, Aziz, Barbon (2025)
"""
import numpy as np
import yfinance as yf
import pandas as pd
import yfinance as yf
import matploitlib.pyplot as plt

#Block1: Data Ingestion 
#We fetch 5-minute price bars for SPY and keep only regular traindg hours (9.30-16.00)

def load_spy_data():
    # Download 60 days of 5-minute intraday bars
    df = yf.download(tickers="SPY", period="60d", interval="5m", auto_adjust=False)
    
    # Keep only regular US trading hours (9:30 AM to 4:00 PM EST)
    df = df.between_time("09:30", "16:00").copy()
    df.dropna(inplace=True)
    return df


# BLOCK 2: INDICATOR CALCULATION (VWAP & 14-DAY NOISE AREA)
def calculate_indicators(data):
    df = data.copy()
    df['Date'] = df.index.date
    df['Time'] = df.index.time
    
    # 1. Calculate Intraday VWAP (resets every morning at 09:30)
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3.0
    df['PV'] = typical_price * df['Volume']
    df['Cum_PV'] = df.groupby('Date')['PV'].cumsum()
    df['Cum_Vol'] = df.groupby('Date')['Volume'].cumsum()
    df['VWAP'] = df['Cum_PV'] / df['Cum_Vol']
    
    # 2. Daily Reference Prices (09:30 Open and 16:00 Close of the day before)
    dates = sorted(df['Date'].unique())
    times = sorted(df['Time'].unique())
    daily_open = df[df['Time'] == times[0]].groupby('Date')['Open'].first()
    daily_close = df[df['Time'] == times[-1]].groupby('Date')['Close'].last()
    
    # 3. Compute the 14-day average move (sigma) for each time interval
    moves_by_time = {}
    for t in times:
        price_at_t = df[df['Time'] == t].set_index('Date')['Close']
        moves_by_time[t] = (price_at_t / daily_open - 1.0).abs()
        
    move_df = pd.DataFrame(moves_by_time)
    # Rolling 14-day mean, shifted by 1 so we only use past data (no lookahead bias)
    sigma_df = move_df.rolling(window=14).mean().shift(1)
    
    # 4. Construct Upper and Lower Noise Boundaries with Overnight Gap Adjustment
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
                'LB': min(o_930, c_prev) * (1.0 - sig) if pd.notna(sig) else np.nan})
            
    bounds_df = pd.DataFrame(records)
    merged = df.merge(bounds_df, on=['Date', 'Time'], how='inner')
    merged.dropna(subset=['UB', 'LB'], inplace=True)
    return merged

