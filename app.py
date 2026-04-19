import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import concurrent.futures

# --- CONFIG ---
DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
CURRENCIES = ["BTC", "ETH"]
TOP_N = 30  # top options per currency by volume (limits API calls)

st.set_page_config(
    page_title="Crypto Options Lab",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .block-container { padding: 1rem 0.75rem !important; }
  [data-testid="metric-container"] { background: #1a1d29; border-radius: 8px; padding: 0.5rem; }
  [data-testid="stDataFrame"] { overflow-x: auto; }
  h1 { font-size: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# --- API HELPERS ---
def _get(endpoint, params):
    try:
        r = requests.get(f"{DERIBIT_BASE}/{endpoint}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("result")
    except Exception:
        pass
    return None


def fetch_index_price(currency):
    result = _get("get_index_price", {"index_name": f"{currency.lower()}_usd"})
    return (result or {}).get("index_price", 0)


def fetch_book_summaries(currency):
    return _get("get_book_summary_by_currency", {"currency": currency, "kind": "option"}) or []


def fetch_ticker(instrument_name):
    return _get("ticker", {"instrument_name": instrument_name}) or {}


# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_data():
    rows = []

    for currency in CURRENCIES:
        spot = fetch_index_price(currency)
        if not spot:
            continue

        summaries = fetch_book_summaries(currency)

        # Keep liquid options; sort by volume descending; cap at TOP_N
        liquid = sorted(
            [s for s in summaries if (s.get("bid_price") or 0) > 0 and (s.get("volume") or 0) > 0],
            key=lambda x: x.get("volume", 0),
            reverse=True,
        )[:TOP_N]

        if not liquid:
            continue

        names = [s["instrument_name"] for s in liquid]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            tickers = list(ex.map(fetch_ticker, names))

        for ticker in tickers:
            if not ticker:
                continue
            name = ticker.get("instrument_name", "")
            parts = name.split("-")
            if len(parts) != 4:
                continue

            curr, expiry_str, strike_s, cp = parts
            try:
                strike = float(strike_s)
                expiry_date = datetime.strptime(expiry_str, "%d%b%y")
            except (ValueError, TypeError):
                continue

            dte = (expiry_date - datetime.now()).days
            if dte < 0:
                continue

            greeks = ticker.get("greeks") or {}
            ul_price = ticker.get("underlying_price") or spot

            # Deribit prices in BTC/ETH — convert to USD
            def usd(val):
                return (val or 0) * ul_price

            rows.append({
                "Symbol": name,
                "Underlying": curr,
                "Expiry": expiry_date.strftime("%Y-%m-%d"),
                "DTE": dte,
                "Strike": strike,
                "Type": "Call" if cp == "C" else "Put",
                "Price": usd(ticker.get("last_price")),
                "Bid": usd(ticker.get("best_bid_price")),
                "Ask": usd(ticker.get("best_ask_price")),
                "Vol": (ticker.get("stats") or {}).get("volume", 0),
                "IV": ticker.get("mark_iv") or 0,
                "Delta": greeks.get("delta") or 0,
                "Gamma": greeks.get("gamma") or 0,
                "Theta": usd(greeks.get("theta")),   # USD/day
                "Vega": usd(greeks.get("vega")),
                "Spot": ul_price,
            })

    return pd.DataFrame(rows)


# --- PAYOFF CALC ---
def calculate_payoff(strategy, x_min, x_max):
    x = np.linspace(x_min, x_max, 300)
    total = np.zeros_like(x)
    for leg in strategy["Legs"]:
        strike = leg["Option"]["Strike"]
        premium = leg["Price"]
        intrinsic = (
            np.maximum(x - strike, 0)
            if leg["Option"]["Type"] == "Call"
            else np.maximum(strike - x, 0)
        )
        total += (intrinsic - premium) if leg["Side"] == "Buy" else (premium - intrinsic)
    return x, total


# --- STRATEGY ENGINE ---
def generate_recommendations(df):
    recs = []
    df = df.copy()
    df["Liquid"] = (df["Vol"] > 0.1) & (df["Bid"] > 0)

    def best_leg(sub, type_filter, dmin, dmax):
        c = sub[
            (sub["Type"] == type_filter)
            & (sub["Delta"] >= dmin)
            & (sub["Delta"] <= dmax)
            & (sub["Liquid"])
        ]
        return c.sort_values("Vol", ascending=False).iloc[0] if not c.empty else None

    for (underlying, exp, dte), grp in df.groupby(["Underlying", "Expiry", "DTE"]):
        spot = grp["Spot"].iloc[0]

        long_call = best_leg(grp, "Call", 0.40, 0.65)
        if long_call is not None and long_call["Ask"] > 0:
            p = long_call["Ask"]
            recs.append({
                "Type": "Long Call", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                "Symbol": f"{underlying} Call {long_call['Strike']:.0f}", "Spot": spot,
                "Legs": [{"Side": "Buy", "Option": long_call, "Price": p}],
                "Credit": -p, "MaxRisk": p,
                "NetDelta": long_call["Delta"], "NetTheta": long_call["Theta"],
                "NetGamma": long_call["Gamma"], "NetVega": long_call["Vega"],
                "BreakEven": long_call["Strike"] + p,
                "ProbProfit": (1 - long_call["Delta"]) * 100,
            })

        long_put = best_leg(grp, "Put", -0.65, -0.40)
        if long_put is not None and long_put["Ask"] > 0:
            p = long_put["Ask"]
            recs.append({
                "Type": "Long Put", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                "Symbol": f"{underlying} Put {long_put['Strike']:.0f}", "Spot": spot,
                "Legs": [{"Side": "Buy", "Option": long_put, "Price": p}],
                "Credit": -p, "MaxRisk": p,
                "NetDelta": long_put["Delta"], "NetTheta": long_put["Theta"],
                "NetGamma": long_put["Gamma"], "NetVega": long_put["Vega"],
                "BreakEven": long_put["Strike"] - p,
                "ProbProfit": (1 - abs(long_put["Delta"])) * 100,
            })

        atm_call = best_leg(grp, "Call", 0.45, 0.55)
        if atm_call is not None:
            atm_put_df = grp[
                (grp["Strike"] == atm_call["Strike"]) & (grp["Type"] == "Put") & (grp["Liquid"])
            ]
            if not atm_put_df.empty:
                atm_put = atm_put_df.iloc[0]
                cost = atm_call["Ask"] + atm_put["Ask"]
                if cost > 0:
                    recs.append({
                        "Type": "Long Straddle", "Underlying": underlying, "Expiry": exp, "DTE": dte,
                        "Symbol": f"{underlying} Straddle {atm_call['Strike']:.0f}", "Spot": spot,
                        "Legs": [
                            {"Side": "Buy", "Option": atm_call, "Price": atm_call["Ask"]},
                            {"Side": "Buy", "Option": atm_put, "Price": atm_put["Ask"]},
                        ],
                        "Credit": -cost, "MaxRisk": cost,
                        "NetDelta": atm_call["Delta"] + atm_put["Delta"],
                        "NetTheta": atm_call["Theta"] + atm_put["Theta"],
                        "NetGamma": atm_call["Gamma"] + atm_put["Gamma"],
                        "NetVega": atm_call["Vega"] + atm_put["Vega"],
                        "BreakEven": f"{atm_call['Strike'] - cost:.0f} / {atm_call['Strike'] + cost:.0f}",
                        "ProbProfit": 40,
                    })

    return pd.DataFrame(recs)


# --- MAIN ---
def main():
    st.title("📈 Crypto Options Lab")
    st.caption("BTC & ETH • powered by Deribit • tap a row for details")

    with st.spinner("Scanning market…"):
        full_df = fetch_data()

    if full_df.empty:
        st.error("No data — Deribit may be temporarily unreachable. Pull to retry.")
        st.stop()

    opps = generate_recommendations(full_df)

    if opps.empty:
        st.info("No liquid setups found right now. Try refreshing.")
        st.stop()

    st.subheader("Opportunities")
    display_cols = ["Underlying", "Type", "DTE", "Credit", "MaxRisk", "ProbProfit", "NetDelta"]
    col_cfg = {
        "Underlying": st.column_config.TextColumn("Asset", width="small"),
        "Type": st.column_config.TextColumn("Strategy", width="medium"),
        "DTE": st.column_config.NumberColumn("Days", format="%d"),
        "Credit": st.column_config.NumberColumn("Cost $", format="%.2f"),
        "MaxRisk": st.column_config.NumberColumn("Risk $", format="%.2f"),
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

    if not event.selection.rows:
        st.info("Tap a row above to see the payoff diagram.")
        return

    strat = opps.iloc[event.selection.rows[0]]
    st.divider()
    st.markdown(f"### {strat['Symbol']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Cost", f"${-strat['Credit']:.2f}")
    c2.metric("Max Loss", f"${strat['MaxRisk']:.2f}")
    c3.metric("Prob %", f"{strat['ProbProfit']:.0f}%")

    d1, d2 = st.columns(2)
    d1.metric("Delta", f"{strat['NetDelta']:.3f}")
    d2.metric("Theta/day", f"${strat['NetTheta']:.2f}")

    be = strat["BreakEven"]
    st.metric("Break Even", f"${be:,.0f}" if isinstance(be, (int, float)) else str(be))

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
        template="plotly_dark", height=300,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Price at Expiry", yaxis_title="P/L ($)",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Legs**")
    legs_data = [{
        "Action": leg["Side"],
        "Strike": f"${leg['Option']['Strike']:,.0f}",
        "Type": leg["Option"]["Type"],
        "Ask $": f"{leg['Price']:.2f}",
        "Delta": f"{leg['Option']['Delta']:.2f}",
    } for leg in strat["Legs"]]
    st.dataframe(pd.DataFrame(legs_data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
