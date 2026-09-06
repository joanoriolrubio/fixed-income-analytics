"""Interactive fixed-income research and risk workbench."""

from dataclasses import asdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fixed_income import Bond, BondQuote, bootstrap, curve_dv01, key_rate_dv01, yield_risk
from fixed_income.demo import sample_quotes

st.set_page_config(page_title="Fixed Income | Analytics", page_icon="◈", layout="wide")
st.caption("FIXED INCOME ANALYTICS  /  RESEARCH & RISK")
st.title("Understand the curve. Measure the risk.")
st.markdown(
    "A transparent bond valuation workbench with calibration, cash-flow analytics "
    "and full-revaluation stress testing."
)
st.caption("SYNTHETIC MARKET · All rates annualized · Settlement on coupon date · No live feeds")

with st.sidebar:
    st.header("Instrument")
    maturity = st.slider("Maturity (years)", 1, 10, 5)
    coupon = st.slider("Annual coupon (%)", 0.0, 10.0, 4.5, 0.1)
    frequency = st.selectbox("Coupons per year", [1, 2, 4], index=1)
    face = st.number_input("Face amount", min_value=100.0, value=1000000.0, step=10000.0)
    st.header("Curve scenario")
    shift = st.slider("Parallel shift (bp)", -200, 200, 0, 5)
    tilt = st.slider("Steepening tilt (bp)", -100, 100, 0, 5)
    st.caption(
        "Tilt moves the shortest node by −tilt and the longest by +tilt. "
        "Shocks apply to continuously compounded zero rates."
    )

with st.expander("Calibration inputs · edit synthetic par coupons"):
    market = st.data_editor(
        pd.DataFrame(
            [
                {"Maturity (years)": q.bond.maturity, "Par coupon (%)": q.bond.coupon_rate * 100}
                for q in sample_quotes()
            ]
        ),
        disabled=["Maturity (years)"],
        hide_index=True,
        column_config={
            "Par coupon (%)": st.column_config.NumberColumn(
                min_value=0.0, max_value=15.0, step=0.05
            )
        },
        key="quotes",
    )
    st.caption("Semiannual bullet bonds quoted at 100 per 100 face; inputs are illustrative.")

try:
    quotes = tuple(
        BondQuote(Bond(float(row["Maturity (years)"]), float(row["Par coupon (%)"]) / 100), 100)
        for _, row in market.iterrows()
    )
    curve = bootstrap(quotes)
    bond = Bond(float(maturity), coupon / 100, frequency, float(face))
    base_price = curve.price(bond)
    ytm = bond.yield_to_maturity(base_price)
    risk = yield_risk(bond, ytm)
    stressed = curve.shifted(float(shift), float(tilt))
    pnl = stressed.price(bond) - base_price
except (ValueError, OverflowError) as exc:
    st.error(f"Cannot value these inputs: {exc}")
    st.stop()

cols = st.columns(5)
for col, label, value in zip(
    cols,
    ["Price / 100", "Yield to maturity", "Modified duration", "Curve DV01", "Scenario P&L"],
    [
        f"{base_price / face * 100:.3f}",
        f"{ytm:.3%}",
        f"{risk.modified_duration:.3f} yrs",
        f"{curve_dv01(bond, curve):,.2f}",
        f"{pnl:+,.2f}",
    ],
    strict=True,
):
    col.metric(label, value)

curve_tab, risk_tab, cash_tab, method_tab = st.tabs(
    ["Yield curves", "Risk & scenarios", "Cash flows & calibration", "Methodology"]
)

with curve_tab:
    times = [i / 20 for i in range(1, 201)]
    fig = go.Figure()
    fig.add_scatter(
        x=times,
        y=[curve.zero_rate(t) * 100 for t in times],
        name="Base zero",
        line={"color": "#37D6C0", "width": 3},
    )
    fig.add_scatter(
        x=times,
        y=[stressed.zero_rate(t) * 100 for t in times],
        name="Scenario zero",
        line={"dash": "dash", "color": "#F7B955"},
    )
    fig.add_scatter(
        x=curve.times,
        y=[curve.zero_rate(t) * 100 for t in curve.times],
        name="Calibration nodes",
        mode="markers",
    )
    fig.update_layout(
        title="Zero curve · continuous compounding",
        xaxis_title="Years",
        yaxis_title="Rate (%)",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)
    left, right = st.columns(2)
    with left:
        fig = go.Figure(
            go.Scatter(
                x=times,
                y=[curve.discount(t) for t in times],
                fill="tozeroy",
                line={"color": "#37D6C0"},
            )
        )
        fig.update_layout(title="Discount factors", xaxis_title="Years", yaxis_title="D(t)")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        starts = [i / 2 for i in range(20)]
        fig = go.Figure(
            go.Bar(
                x=starts,
                y=[curve.forward_rate(t, t + 0.5) * 100 for t in starts],
                marker_color="#758BFD",
            )
        )
        fig.update_layout(
            title="6-month average forwards · continuous",
            xaxis_title="Start year",
            yaxis_title="Forward (%)",
        )
        st.plotly_chart(fig, use_container_width=True)
    st.metric("10Y − 2Y zero slope", f"{(curve.zero_rate(10) - curve.zero_rate(2)) * 10000:.1f} bp")

with risk_tab:
    left, right = st.columns(2)
    with left:
        shifts = list(range(-200, 201, 10))
        exact = [bond.price(ytm + s / 10000) - base_price for s in shifts]
        approx = [
            base_price
            * (-risk.modified_duration * s / 10000 + 0.5 * risk.convexity * (s / 10000) ** 2)
            for s in shifts
        ]
        fig = go.Figure()
        fig.add_scatter(x=shifts, y=exact, name="Exact yield repricing")
        fig.add_scatter(x=shifts, y=approx, name="Duration + convexity", line={"dash": "dash"})
        fig.update_layout(
            title="Yield-shock P&L approximation",
            xaxis_title="Nominal yield shift (bp)",
            yaxis_title="Currency P&L",
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = go.Figure(
            go.Bar(
                x=[f"{t:g}Y" for t in curve.times],
                y=key_rate_dv01(bond, curve),
                marker_color="#37D6C0",
            )
        )
        fig.update_layout(
            title="Key-rate DV01", xaxis_title="Zero node", yaxis_title="Currency / bp"
        )
        st.plotly_chart(fig, use_container_width=True)
    shocks = list(range(-150, 151, 15))
    tenors = list(range(1, 11))
    surface = [
        [
            (
                curve.shifted(s).price(Bond(t, coupon / 100, frequency))
                / curve.price(Bond(t, coupon / 100, frequency))
                - 1
            )
            * 100
            for s in shocks
        ]
        for t in tenors
    ]
    fig = go.Figure(
        go.Surface(
            x=shocks, y=tenors, z=surface, colorscale="Tealrose", colorbar={"title": "P&L %"}
        )
    )
    fig.update_layout(
        title="Interest-rate risk surface · constant coupon across tenors",
        height=540,
        scene={
            "xaxis_title": "Zero shift (bp)",
            "yaxis_title": "Maturity (years)",
            "zaxis_title": "Price change (%)",
        },
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(pd.DataFrame([asdict(risk)]), hide_index=True)
    st.caption(
        "Yield DV01 uses periodic nominal yield; curve and key-rate DV01 use continuous "
        "zero-rate bumps. Their values need not be equal."
    )

with cash_tab:
    flows = pd.DataFrame(
        [
            {
                "Time (years)": cf.time,
                "Cash flow": cf.amount,
                "Discount factor": curve.discount(cf.time),
                "Present value": cf.amount * curve.discount(cf.time),
            }
            for cf in bond.cashflows()
        ]
    )
    st.subheader("Cash-flow audit trail")
    st.dataframe(flows, hide_index=True, use_container_width=True)
    st.download_button(
        "Download cash flows (CSV)", flows.to_csv(index=False), "cashflows.csv", "text/csv"
    )
    calibration = pd.DataFrame(
        [
            {
                "Maturity": q.bond.maturity,
                "Quote": q.price,
                "Model": curve.price(q.bond),
                "Residual": curve.price(q.bond) - q.price,
            }
            for q in quotes
        ]
    )
    st.subheader("Calibration residuals · per 100 face")
    st.dataframe(calibration, hide_index=True, use_container_width=True)
    st.download_button(
        "Download calibration (CSV)", calibration.to_csv(index=False), "calibration.csv", "text/csv"
    )

with method_tab:
    st.markdown(r"""
### Model conventions
- Regular fixed-rate bullet bonds; maturity must lie on the coupon grid.
- Settlement at a coupon date: **accrued interest = 0**, clean price = dirty price.
- Yield is a nominal annual rate compounded at the coupon frequency.
- Spot/forward rates are continuously compounded. Rates in the engine are decimals.
- Log-linear discount interpolation implies piecewise-constant instantaneous forwards.
- Bootstrapping solves one terminal log discount per bond, including intermediate coupons.
- No extrapolation past 10 years in this demo. Negative curve rates are supported by the engine.

### Core equations
""")
    st.latex(r"P(y)=\sum_i CF_i(1+y/m)^{-mt_i},\quad P_{curve}=\sum_i CF_iD(t_i)")
    st.latex(r"z(t)=-\log D(t)/t,\quad f(a,b)=\log[D(a)/D(b)]/(b-a)")
    st.markdown(
        "This portfolio project does not model business-day calendars, settlement lags, "
        "stubs, ex-coupon periods, credit/default, optionality or multi-curve swaps. "
        "Synthetic quotes demonstrate the mechanics; they are not market observations."
    )
