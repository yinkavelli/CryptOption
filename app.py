import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- 1. CONFIG & API ENDPOINTS ---
OPTIONS_TICKER_API_URL = "https://eapi.binance.com/eapi/v1/ticker"
OPTIONS_MARK_API_URL = "https://eapi.binance.com/eapi/v1/mark"
SPOT_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"

st.set_page_config(page_title="Crypto Options Strat Lab", layout="wide")

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_spot_prices():
    try:
        url = SPOT_PRICE_URL
        response = requests.get(url, timeout=5)
        data = response.json()
        return {item['symbol']: float(item['price']) for item in data}
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_data():
    try:
        t_res = requests.get(OPTIONS_TICKER_API_URL, timeout=10)
        if t_res.status_code != 200:
            st.error(f"Ticker API Error: {t_res.status_code} - {t_res.text[:200]}")
            return pd.DataFrame()
            
        tickers = t_res.json()
        
        m_res = requests.get(OPTIONS_MARK_API_URL, timeout=10)
        if m_res.status_code != 200:
            st.error(f"Mark API Error: {m_res.status_code} - {m_res.text[:200]}")
            marks = []
        else:
            marks = m_res.json()
            
        mark_map = {m['symbol']: m for m in marks}
        
        data = []
        for t in tickers:
            sym = t['symbol']
            try:
                parts = sym.split('-')
                if len(parts) != 4: continue
                underlying = parts[0]
                expiry_str = parts[1]
                strike = float(parts[2])
                side = "Call" if parts[3] == "C" else "Put"
                
                # Expiry Filter
                expiry_date = datetime.strptime(expiry_str, "%y%m%d")
                curr_date = datetime.now()
                dte = (expiry_date - curr_date).days
                if dte < 0: continue 

                m = mark_map.get(sym, {})
                iv = float(m.get('markIV', 0))
                delta = float(m.get('delta', 0))
                gamma = float(m.get('gamma', 0))
                theta = float(m.get('theta', 0))
                vega = float(m.get('vega', 0))
                
                price = float(t.get('lastPrice', 0))
                bid = float(t.get('bidPrice', 0))
                ask = float(t.get('askPrice', 0))
                vol = float(t.get('volume', 0))
                
                data.append({
                    "Symbol": sym, "Underlying": underlying, "Expiry": expiry_date.strftime("%Y-%m-%d"),
                    "DTE": dte, "Strike": strike, "Type": side, "Price": price, "Bid": bid, "Ask": ask,
                    "Vol": vol, "IV": iv, "Delta": delta, "Gamma": gamma, "Theta": theta, "Vega": vega
                })
            except: continue
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

# --- 3. PAYOFF DIAGRAM CALCULATION ---
def calculate_payoff(strategy, spot_range_min, spot_range_max):
    x = np.linspace(spot_range_min, spot_range_max, 300)
    total_pnl = np.zeros_like(x)
    
    for leg in strategy['Legs']:
        strike = leg['Option']['Strike']
        premium = leg['Price']
        side = leg['Side']
        otype = leg['Option']['Type']
        
        if otype == 'Call':
            intrinsic = np.maximum(x - strike, 0)
        else:
            intrinsic = np.maximum(strike - x, 0)
            
        if side == 'Buy':
            # Long: Pay Premium, Gain Intrinsic
            leg_pnl = intrinsic - premium
        else:
            # Short: Gain Premium, Lose Intrinsic
            leg_pnl = premium - intrinsic
            
        total_pnl += leg_pnl
        
    return x, total_pnl

# --- 4. STRATEGY ALGORITHMS ---
def generate_recommendations(df, spot_prices):
    recs = []
    df = df.copy()
    
    # Filter for liquidity
    df['Liquid'] = (df['Vol'] > 1) & (df['Bid'] > 0)
    
    def find_leg(subset_df, type_filter, min_delta, max_delta):
        candidates = subset_df[
            (subset_df['Type'] == type_filter) & 
            (subset_df['Delta'] >= min_delta) & 
            (subset_df['Delta'] <= max_delta) & 
            (subset_df['Liquid'])
        ]
        return candidates.sort_values('Vol', ascending=False).iloc[0] if not candidates.empty else None

    # Group by Underlying AND Expiry
    grouped = df.groupby(['Underlying', 'Expiry', 'DTE'])
    
    for (underlying, exp, dte), group_df in grouped:
        spot_price = spot_prices.get(f"{underlying}USDT", 0)
        if spot_price == 0: continue

        # --- A. LONG CALL (Directional Bullish) ---
        long_call = find_leg(group_df, 'Call', 0.45, 0.65) # ATM/ITM Call
        
        if long_call is not None:
            premium = long_call['Ask']
            if premium > 0:
                recs.append({
                    "Type": "Long Call",
                    "Symbol": f"{underlying} Long Call {long_call['Strike']}",
                    "Underlying": underlying,
                    "Expiry": exp,
                    "DTE": dte,
                    "Spot": spot_price,
                    "Legs": [
                        {"Side": "Buy", "Option": long_call, "Price": premium}
                    ],
                    "Credit": -premium, # Debit logic handled inverted for display or standardized? Let's use negative credit for debit
                    "MaxRisk": premium,
                    "NetDelta": long_call['Delta'], 
                    "NetTheta": long_call['Theta'],
                    "NetGamma": long_call['Gamma'],
                    "NetVega": long_call['Vega'],
                    "BreakEven": long_call['Strike'] + premium,
                    "ProbProfit": (1 - long_call['Delta']) * 100 # Rough approx
                })

        # --- B. LONG PUT (Directional Bearish) ---
        long_put = find_leg(group_df, 'Put', -0.65, -0.45) # ATM/ITM Put
        
        if long_put is not None:
            premium = long_put['Ask']
            if premium > 0:
                recs.append({
                    "Type": "Long Put",
                    "Symbol": f"{underlying} Long Put {long_put['Strike']}",
                    "Underlying": underlying,
                    "Expiry": exp,
                    "DTE": dte,
                    "Spot": spot_price,
                    "Legs": [
                        {"Side": "Buy", "Option": long_put, "Price": premium}
                    ],
                    "Credit": -premium,
                    "MaxRisk": premium,
                    "NetGamma": long_put['Gamma'],
                    "NetVega": long_put['Vega'],
                    "NetDelta": long_put['Delta'], 
                    "NetTheta": long_put['Theta'],
                    "BreakEven": long_put['Strike'] - premium,
                    "ProbProfit": (1 - abs(long_put['Delta'])) * 100 
                })

        # --- C. LONG STRADDLE (Volatility Play) ---
        # Buy ATM Call + Buy ATM Put
        atm_call = find_leg(group_df, 'Call', 0.45, 0.55)
        # Find put with matching strike
        if atm_call is not None:
             atm_put = group_df[(group_df['Strike'] == atm_call['Strike']) & (group_df['Type'] == 'Put') & (group_df['Liquid'])]
             
             if not atm_put.empty:
                atm_put = atm_put.iloc[0]
                cost = atm_call['Ask'] + atm_put['Ask']
                
                if cost > 0:
                     recs.append({
                        "Type": "Long Straddle",
                        "Symbol": f"{underlying} Straddle {atm_call['Strike']}",
                        "Underlying": underlying,
                        "Expiry": exp,
                        "DTE": dte,
                        "Spot": spot_price,
                        "Legs": [
                            {"Side": "Buy", "Option": atm_call, "Price": atm_call['Ask']},
                            {"Side": "Buy", "Option": atm_put, "Price": atm_put['Ask']}
                        ],
                        "Credit": -cost, 
                        "MaxRisk": cost,
                        "NetGamma": atm_call['Gamma'] + atm_put['Gamma'],
                        "NetVega": atm_call['Vega'] + atm_put['Vega'],
                        "NetDelta": atm_call['Delta'] + atm_put['Delta'], 
                        "NetTheta": atm_call['Theta'] + atm_put['Theta'],
                        "BreakEven": f"{atm_call['Strike'] - cost:.2f} / {atm_call['Strike'] + cost:.2f}",
                        "ProbProfit": 40 # Varies heavily, hard to calc simply
                    })

    return pd.DataFrame(recs)

# --- 5. MAIN UI ---
def main():
    st.title("🧠 AI Crypto Options Strategist")
    st.caption("Auto-generated Defined Risk Strategies with Payoff Diagrams")

    # 1. Fetch
    with st.spinner("Scanning Entire Market (BTC, ETH, BNB, etc.)..."):
        full_df = fetch_data()
        spot_prices = fetch_spot_prices()
        
    # Force redeploy: Update 2
    if full_df.empty:
        st.error("Data unavailable. This could be due to API limits or empty response. See detailed error above if any."); st.stop()

    # 2. Generate Recommendations for ALL assets
    opportunities_df = generate_recommendations(full_df, spot_prices)
    
    if opportunities_df.empty:
        st.info("No high-probability defined risk setups found currently.")
        st.stop()
        
    # 3. Master Table
    st.subheader("Opportunities")
    
    # Styling column config
    column_config = {
        "Symbol": st.column_config.TextColumn("Strategy Name", width="large"),
        "Type": st.column_config.TextColumn("Type", width="medium"),
        "Underlying": st.column_config.TextColumn("Asset", width="small"),
        "Expiry": st.column_config.TextColumn("Expiry", width="medium"),
        "NetDelta": st.column_config.NumberColumn("Delta", format="%.2f"),
        "NetGamma": st.column_config.NumberColumn("Gamma", format="%.4f"),
        "NetTheta": st.column_config.NumberColumn("Theta", format="%.2f"),
        "NetVega": st.column_config.NumberColumn("Vega", format="%.2f"),
    }

    # Use selection API for the table
    event = st.dataframe(
        opportunities_df[['Underlying', 'Type', 'Expiry', 'DTE', 'Symbol', 'Credit', 'MaxRisk', 'ProbProfit', 'NetDelta', 'NetGamma', 'NetTheta', 'NetVega']],

    # Use selection API for the table
    event = st.dataframe(
        opportunities_df[['Underlying', 'Type', 'Expiry', 'DTE', 'Symbol', 'Credit', 'MaxRisk', 'ProbProfit']],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    # 4. Detail View (Conditionally Rendered)
    if len(event.selection.rows) > 0:
        selected_row_index = event.selection.rows[0]
        strategy = opportunities_df.iloc[selected_row_index]
        
        st.divider()
        st.markdown(f"### Analysis: {strategy['Symbol']}")
        
        # --- DASHBOARD LAYOUT ---
        dash_col1, dash_col2 = st.columns([2, 1])
        
        with dash_col1:
            # Plot Payoff
            spot = strategy['Spot']
            # Determine range for plot
            x_min = spot * 0.75
            x_max = spot * 1.25
            x_vals, y_vals = calculate_payoff(strategy, x_min, x_max)
            
            fig = go.Figure()
            
            # Green/Red Areas
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                fill='tozeroy',
                mode='lines',
                line=dict(color='cyan', width=3),
                name='P/L at Expiry'
            ))
            
            # Zero Line
            fig.add_hline(y=0, line_dash="dash", line_color="white")
            
            # Current Price Marker
            fig.add_vline(x=spot, line_dash="dash", line_color="yellow", annotation_text="Current Price")
            
            # Break Even Marker (Vertical Line)
            if isinstance(strategy['BreakEven'], (int, float)):
                 fig.add_vline(x=strategy['BreakEven'], line_dash="dot", line_color="orange", annotation_text="Break Even")
            
            fig.update_layout(
                title=f"Payoff Diagram ({strategy['Type']})",
                xaxis_title="Price at Expiry",
                yaxis_title="Profit / Loss ($)",
                template="plotly_dark",
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with dash_col2:
            st.subheader("Risk Mechanics")
            
            m1, m2 = st.columns(2)
            m1.metric("Est. Cost (Debit)", f"${-strategy['Credit']:.2f}", help="Cash PAID upfront.")
            m2.metric("Max Loss", f"${strategy['MaxRisk']:.2f}", delta_color="inverse", help="Total premium paid.")
            
            st.metric("Probability of Profit (Est.)", f"{strategy['ProbProfit']:.1f}%", help="Estimated chance that the price stays in the profit zone.")
            
            if isinstance(strategy['BreakEven'], (int, float)):
                st.metric("Break Even Price", f"${strategy['BreakEven']:,.2f}")
            else:
                 st.metric("Break Even Prices", str(strategy['BreakEven']))
                
            st.markdown("---")
            g1, g2 = st.columns(2)
            g1.metric("Net Delta", f"{strategy['NetDelta']:.3f}", help="Directional risk.")
            g2.metric("Net Theta", f"{strategy['NetTheta']:.2f}", help="Daily time decay earnings.")

        # 5. EXECUTION DETAILS
        st.subheader("Strategy Composition (Legs)")
        legs_data = []
        for leg in strategy['Legs']:
            opt = leg['Option']
            legs_data.append({
                "Action": leg['Side'],
                "Expiry": opt['Expiry'],
                "Strike": opt['Strike'],
                "Type": opt['Type'],
                "Limit Price": f"${leg['Price']:.2f}",
                "Delta": f"{opt['Delta']:.2f}",
                "Gamma": f"{opt['Gamma']:.4f}",
                "Theta": f"{opt['Theta']:.2f}"
            })
            
        st.dataframe(pd.DataFrame(legs_data), use_container_width=True)
    else:
        st.info("👆 Select an opportunity from the table above to view the analysis and payoff diagram.")

if __name__ == "__main__":
    main()
