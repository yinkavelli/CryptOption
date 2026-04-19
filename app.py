import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# --- CONFIG ---
OPTIONS_TICKER_API_URL = "https://eapi.binance.com/eapi/v1/ticker"
OPTIONS_MARK_API_URL = "https://eapi.binance.com/eapi/v1/mark"
SPOT_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"

st.set_page_config(
    page_title="Crypto Options Lab",
    page_icon="📈",
    layout="centered",   # centered works better on mobile than wide
    initial_sidebar_state="collapsed",
)

# Mobile-friendly CSS
st.markdown("""
<style>
  /* Tighten padding on small screens */
  .block-container { padding: 1rem 0.75rem !important; }
  /* Make metric cards readable on phones */
  [data-testid="metric-container"] { background: #1a1d29; border-radius: 8px; padding: 0.5rem; }
  /* Horizontal scroll for dataframes on narrow screens */
  [data-testid="stDataFrame"] { overflow-x: auto; }
  /* Reduce h1 size on mobile */
  h1 { font-size: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_spot_prices():
    try:
        r = requests.get(SPOT_PRICE_URL, timeout=5)
        return {item["symbol"]: float(item["price"]) for item in r.json()}
    except Exception:
        return {}


@st.cache_data(ttl=60)
def fetch_data():
    try:
        t_res = requests.get(OPTIONS_TICKER_API_URL, timeout=10)
        if t_res.status_code != 200:
            st.error(f"Ticker API {t_res.status_code}: {t_res.text[:200]}")
            return pd.DataFrame()

        tickers = t_res.json()

        m_res = requests.get(OPTIONS_MARK_API_URL, timeout=10)
        marks = m_res.json() if m_res.status_code == 200 else []
        mark_map = {m["symbol"]: m for m in marks}

        data = []
        for t in tickers:
            sym = t["symbol"]
            try:
                parts = sym.split("-")
                if len(parts) != 4:
                    continue
                underlying, expiry_str, strike_s, call_put = parts
                strike = float(strike_s)
                side = "Call" if call_put == "C" else "Put"

                expiry_date = datetime.strptime(expiry_str, "%y%m%d")
                dte = (expiry_date - datetime.now()).days
                if dte < 0:
                    continue

                m = mark_map.get(sym, {})
                data.append({
                    "Symbol": sym,
                    "Underlying": underlying,
                    "Expiry": expiry_date.strftime("%Y-%m-%d"),
                    "DTE": dte,
                    "Strike": strike,
                    "Type": side,
                    "Price": float(t.get("lastPrice", 0)),
                    "Bid": float(t.get("bidPrice", 0)),
                    "Ask": float(t.get("askPrice", 0)),
                    "Vol": float(t.get("volume", 0)),
                    "IV": float(m.get("markIV", 0)),
                    "Delta": float(m.get("delta", 0)),
                    "Gamma": float(m.get("gamma", 0)),
                    "Theta": float(m.get("theta", 0)),
                    "Vega": float(m.get("vega", 0)),
                })
            except Exception:
                continue
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return pd.DataFrame()


# --- PAYOFF CALC ---
def calculate_payoff(strategy, spot_range_min, spot_range_max):
    x = np.linspace(spot_range_min, spot_range_max, 300)
    total_pnl = np.zeros_like(x)
    for leg in strategy["Legs"]:
        strike = leg["Option"]["Strike"]
        premium = leg["Price"]
        intrinsic = (
            np.maximum(x - strike, 0)
            if leg["Option"]["Type"] == "Call"
            else np.maximum(strike - x, 0)
        )
        total_pnl += (intrinsic - premium) if leg["Side"] == "Buy" else (premium - intrinsic)
    return x, total_pnl


# --- STRATEGY ENGINE ---
def generate_recommendations(df, spot_prices):
    recs = []
    df = df.copy()
    df["Liquid"] = (df["Vol"] > 1) & (df["Bid"] > 0)

    def find_leg(sub, type_filter, dmin, dmax):
        c = sub[
            (sub["Type"] == type_filter)
            & (sub["Delta"] >= dmin)
            & (sub["Delta"] <= dmax)
            & (sub["Liquid"])
        ]
        return c.sort_values("Vol", ascending=False).iloc[0] if not c.empty else None

    for (underlying, exp, dte), grp in df.groupby(["Underlying", "Expiry", "DTE"]):
        spot = spot_prices.get(f"{underlying}USDT", 0)
        if spot == 0:
            continue

        long_call = find_leg(grp, "Call", 0.45, 0.65)
        if long_call is not None and long_call["Ask"] > 0:
            p = long_call["Ask"]
            recs.append({
                "Type": "Long Call", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                "Symbol": f"{underlying} Call {long_call['Strike']}", "Spot": spot,
                "Legs": [{"Side": "Buy", "Option": long_call, "Price": p}],
                "Credit": -p, "MaxRisk": p,
                "NetDelta": long_call["Delta"], "NetTheta": long_call["Theta"],
                "NetGamma": long_call["Gamma"], "NetVega": long_call["Vega"],
                "BreakEven": long_call["Strike"] + p,
                "ProbProfit": (1 - long_call["Delta"]) * 100,
            })

        long_put = find_leg(grp, "Put", -0.65, -0.45)
        if long_put is not None and long_put["Ask"] > 0:
            p = long_put["Ask"]
            recs.append({
                "Type": "Long Put", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                "Symbol": f"{underlying} Put {long_put['Strike']}", "Spot": spot,
                "Legs": [{"Side": "Buy", "Option": long_put, "Price": p}],
                "Credit": -p, "MaxRisk": p,
                "NetDelta": long_put["Delta"], "NetTheta": long_put["Theta"],
                "NetGamma": long_put["Gamma"], "NetVega": long_put["Vega"],
                "BreakEven": long_put["Strike"] - p,
                "ProbProfit": (1 - abs(long_put["Delta"])) * 100,
            })

        atm_call = find_leg(grp, "Call", 0.45, 0.55)
        if atm_call is not None:
            atm_put_df = grp[(grp["Strike"] == atm_call["Strike"]) & (grp["Type"] == "Put") & (grp["Liquid"])]
            if not atm_put_df.empty:
                atm_put = atm_put_df.iloc[0]
                cost = atm_call["Ask"] + atm_put["Ask"]
                if cost > 0:
                    recs.append({
                        "Type": "Long Straddle", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                        "Symbol": f"{underlying} Straddle {atm_call['Strike']}", "Spot": spot,
                        "Legs": [
                            {"Side": "Buy", "Option": atm_call, "Price": atm_call["Ask"]},
                            {"Side": "Buy", "Option": atm_put, "Price": atm_put["Ask"]},
                        ],
                        "Credit": -cost, "MaxRisk": cost,
                        "NetDelta": atm_call["Delta"] + atm_put["Delta"],
                        "NetTheta": atm_call["Theta"] + atm_put["Theta"],
                        "NetGamma": atm_call["Gamma"] + atm_put["Gamma"],
                        "NetVega": atm_call["Vega"] + atm_put["Vega"],
                        "BreakEven": f"{atm_call['Strike'] - cost:.2f} / {atm_call['Strike'] + cost:.2f}",
                        "ProbProfit": 40,
                    })

    return pd.DataFrame(recs)


# --- MAIN UI ---
def main():
    st.title("📈 Crypto Options Lab")
    st.caption("Live defined-risk strategies • tap a row for details")

    with st.spinner("Scanning market…"):
        full_df = fetch_data()
        spot_prices = fetch_spot_prices()

    if full_df.empty:
        st.error("No data — check API or try again.")
        st.stop()

    opps = generate_recommendations(full_df, spot_prices)

    if opps.empty:
        st.info("No setups found right now. Pull to refresh.")
        st.stop()

    # --- Opportunity table (compact for mobile) ---
    st.subheader("Opportunities")

    display_cols = ["Underlying", "Type", "DTE", "Credit", "MaxRisk", "ProbProfit", "NetDelta"]
    col_cfg = {
        "Underlying": st.column_config.TextColumn("Asset", width="small"),
        "Type": st.column_config.TextColumn("Strategy", width="medium"),
        "DTE": st.column_config.NumberColumn("Days", format="%d"),
        "Credit": st.column_config.NumberColumn("Cost $", format="%.2f"),
        "MaxRisk": st.column_config.NumberColumn("Max Risk $", format="%.2f"),
        "ProbProfit": st.column_config.NumberColumn("Prob %", format="%.0f%%"),
        "NetDelta": st.column_config.NumberColumn("Delta", format="%.2f"),
    }

    event = st.dataframe(
        opps[display_cols],
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail view ---
    if not event.selection.rows:
        st.info("Tap a row above to see the payoff diagram.")
        return

    strat = opps.iloc[event.selection.rows[0]]
    st.divider()
    st.markdown(f"### {strat['Symbol']}")

    # Metrics row — stacks nicely on mobile
    c1, c2, c3 = st.columns(3)
    c1.metric("Cost", f"${-strat['Credit']:.2f}")
    c2.metric("Max Loss", f"${strat['MaxRisk']:.2f}")
    c3.metric("Prob %", f"{strat['ProbProfit']:.0f}%")

    d1, d2 = st.columns(2)
    d1.metric("Delta", f"{strat['NetDelta']:.3f}")
    d2.metric("Theta", f"{strat['NetTheta']:.2f}")

    be = strat["BreakEven"]
    if isinstance(be, (int, float)):
        st.metric("Break Even", f"${be:,.2f}")
    else:
        st.metric("Break Even", str(be))

    # Payoff chart
    spot = strat["Spot"]
    x_vals, y_vals = calculate_payoff(strat, spot * 0.75, spot * 1.25)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals, fill="tozeroy", mode="lines",
        line=dict(color="#00d4ff", width=2), name="P/L at Expiry",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=1)
    fig.add_vline(x=spot, line_dash="dash", line_color="yellow",
                  annotation_text="Spot", annotation_position="top right")
    if isinstance(be, (int, float)):
        fig.add_vline(x=be, line_dash="dot", line_color="orange",
                      annotation_text="BE", annotation_position="top left")

    fig.update_layout(
        template="plotly_dark",
        height=300,           # shorter chart fits mobile screen
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Price at Expiry",
        yaxis_title="P/L ($)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Legs table
    st.markdown("**Legs**")
    legs_data = [
        {
            "Action": leg["Side"],
            "Strike": leg["Option"]["Strike"],
            "Type": leg["Option"]["Type"],
            "Price $": f"{leg['Price']:.2f}",
            "Delta": f"{leg['Option']['Delta']:.2f}",
        }
        for leg in strat["Legs"]
    ]
    st.dataframe(pd.DataFrame(legs_data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
