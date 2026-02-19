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

        # --- A. BULL PUT SPREAD ---
        short_put = find_leg(group_df, 'Put', -0.35, -0.20)
        long_put = find_leg(group_df, 'Put', -0.15, -0.05)
        
        if short_put is not None and long_put is not None:
             if short_put['Strike'] > long_put['Strike']:
                credit = short_put['Bid'] - long_put['Ask']
                width = short_put['Strike'] - long_put['Strike']
                max_risk = width - credit
                
                if credit > 0 and max_risk > 0:
                    rr = max_risk / credit
                    if rr < 6:
                        recs.append({
                            "Type": "Bull Put Spread",
                            "Symbol": f"{underlying} Bull Put {short_put['Strike']}/{long_put['Strike']}",
                            "Underlying": underlying,
                            "Expiry": exp,
                            "DTE": dte,
                            "Spot": spot_price,
                            "Legs": [
                                {"Side": "Sell", "Option": short_put, "Price": short_put['Bid']},
                                {"Side": "Buy", "Option": long_put, "Price": long_put['Ask']}
                            ],
                            "Credit": credit, "MaxRisk": max_risk,
                            "NetDelta": short_put['Delta'] - long_put['Delta'], 
                            "NetTheta": short_put['Theta'] - long_put['Theta'],
                            "BreakEven": short_put['Strike'] - credit,
                            "ProbProfit": (1 - abs(short_put['Delta'])) * 100 # Approx
                        })

        # --- B. BEAR CALL SPREAD ---
        short_call = find_leg(group_df, 'Call', 0.20, 0.35)
        long_call = find_leg(group_df, 'Call', 0.05, 0.15)
        
        if short_call is not None and long_call is not None:
             if short_call['Strike'] < long_call['Strike']:
                credit = short_call['Bid'] - long_call['Ask']
                width = long_call['Strike'] - short_call['Strike']
                max_risk = width - credit
                
                if credit > 0 and max_risk > 0 and (max_risk/credit < 6):
                    recs.append({
                        "Type": "Bear Call Spread",
                        "Symbol": f"{underlying} Bear Call {short_call['Strike']}/{long_call['Strike']}",
                        "Underlying": underlying,
                        "Expiry": exp,
                        "DTE": dte,
                        "Spot": spot_price,
                        "Legs": [
                            {"Side": "Sell", "Option": short_call, "Price": short_call['Bid']},
                            {"Side": "Buy", "Option": long_call, "Price": long_call['Ask']}
                        ],
                        "Credit": credit, "MaxRisk": max_risk,
                        "NetDelta": -short_call['Delta'] + long_call['Delta'],
                        "NetTheta": -short_call['Theta'] + long_call['Theta'],
                        "BreakEven": short_call['Strike'] + credit,
                        "ProbProfit": (1 - short_call['Delta']) * 100 # Approx
                    })

        # --- C. IRON CONDOR (Symmetric wings) ---
        short_put_candidate = find_leg(group_df, 'Put', -0.25, -0.15)
        short_call_candidate = find_leg(group_df, 'Call', 0.15, 0.25)
        
        if short_put_candidate is not None and short_call_candidate is not None:
            sp_strike = short_put_candidate['Strike']
            sc_strike = short_call_candidate['Strike']
            
            available_strikes = set(group_df['Strike'])
            
            # Find best symmetric width
            candidates = []
            # Calculate step size based on underlying price roughly (e.g. BTC 1000, ETH 100)
            step = 1000 if spot_price > 10000 else 100 if spot_price > 1000 else 10
            widths = [step*i for i in range(1, 6)] # Check 5 width levels
            
            for width in widths:
                lp_strike = sp_strike - width
                lc_strike = sc_strike + width
                
                if lp_strike in available_strikes and lc_strike in available_strikes:
                    lp = group_df[(group_df['Strike']==lp_strike) & (group_df['Type']=='Put') & (group_df['Liquid'])].head(1)
                    lc = group_df[(group_df['Strike']==lc_strike) & (group_df['Type']=='Call') & (group_df['Liquid'])].head(1)
                    
                    if not lp.empty and not lc.empty:
                        candidates.append((width, lp.iloc[0], lc.iloc[0]))
            
            if candidates:
                # Pick first valid candidate (smallest width usually safest for defined risk)
                width, lp, lc = candidates[0]
                sp, sc = short_put_candidate, short_call_candidate
                
                total_credit = (sp['Bid'] - lp['Ask']) + (sc['Bid'] - lc['Ask'])
                max_risk = width - total_credit
                
                if total_credit > 0 and max_risk > 0:
                     recs.append({
                        "Type": "Iron Condor",
                        "Symbol": f"{underlying} Condor {lp['Strike']}/{sp['Strike']} | {sc['Strike']}/{lc['Strike']}",
                        "Underlying": underlying,
                        "Expiry": exp,
                        "DTE": dte,
                        "Spot": spot_price,
                        "Legs": [
                            {"Side": "Buy", "Option": lp, "Price": lp['Ask']},
                            {"Side": "Sell", "Option": sp, "Price": sp['Bid']},
                            {"Side": "Sell", "Option": sc, "Price": sc['Bid']},
                            {"Side": "Buy", "Option": lc, "Price": lc['Ask']}
                        ],
                        "Credit": total_credit, "MaxRisk": max_risk,
                        "NetDelta": (-sp['Delta'] + lp['Delta']) + (-sc['Delta'] + lc['Delta']), # Approx
                        "NetTheta": (-sp['Theta'] + lp['Theta']) + (-sc['Theta'] + lc['Theta']),
                        "BreakEven": "Multiple",
                        "ProbProfit": (1 - (abs(sp['Delta']) + sc['Delta'])) * 100 # Approx probability between short strikes
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
        
    if full_df.empty:
        st.error("Data unavailable. Check API connection."); st.stop()

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
        "DTE": st.column_config.NumberColumn("DTE", format="%d days"),
        "Credit": st.column_config.NumberColumn("Credit (Profit)", format="$%.2f"),
        "MaxRisk": st.column_config.NumberColumn("Max Risk", format="$%.2f"),
        "ProbProfit": st.column_config.ProgressColumn("Prob. Profit", format="%.0f%%", min_value=0, max_value=100),
    }

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
            if strategy['BreakEven'] != "Multiple":
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
            m1.metric("Max Profit (Credit)", f"${strategy['Credit']:.2f}", help="Net cash RECEIVED upfront.")
            m2.metric("Max Loss (Collateral)", f"${strategy['MaxRisk']:.2f}", delta_color="inverse", help="This amount is held as collateral.")
            
            st.metric("Probability of Profit (Est.)", f"{strategy['ProbProfit']:.1f}%", help="Estimated chance that the price stays in the profit zone.")
            st.metric("Risk / Reward Ratio", f"1 : {strategy['MaxRisk']/strategy['Credit']:.1f}")
            
            if strategy['BreakEven'] != "Multiple":
                st.metric("Break Even Price", f"${strategy['BreakEven']:,.2f}")
                
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
