# Fixed Income Analytics

**A transparent Python workbench for bond valuation, yield-curve calibration and interest-rate risk.**

[🚀 Open the interactive demo](https://fixed-income-analytics-joan.streamlit.app)

Inspect each cash flow, reproduce the calibration, distinguish yield risk from curve risk and review the numerical choices. The core engine uses only Python's standard library. Streamlit and Plotly provide the interactive interface; SciPy is used only as a test benchmark.

## Run in three commands

Requires Python 3.11–3.13. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[app,dev]'
```

Launch the dashboard:

```bash
streamlit run app.py
```

Or run the reproducible JSON demo without the UI:

```bash
fixed-income-demo
```

For a core-only installation, `pip install .` has **zero runtime dependencies**.

## What you can demonstrate

| Capability | Implementation | Evidence |
|---|---|---|
| Bond valuation | Regular coupon cash flows, periodic discounting, YTM inversion | Par and zero-coupon identities; SciPy root comparison |
| Curve construction | Sequential terminal log-discount bootstrap from bond prices | Every calibration instrument reprices; known-curve recovery |
| Term structure | Log-linear discounts, continuous zero/forward rates | Discount-factor identities and sparse coupon interpolation |
| Yield risk | Macaulay/modified duration, convexity, analytical DV01 | Central finite differences across positive/negative yields |
| Curve risk | Parallel and tilted zero shocks, key-rate DV01 | Full repricing and sensitivity aggregation |
| Interactive analysis | Curve plots, risk decomposition, 3D maturity/shock surface | Streamlit app test with changed widgets |
| Engineering | Immutable models, type hints, strict typing, packaging, CI | pytest, coverage gate, Ruff, mypy, wheel build |

## Interactive workflow

1. Open **Yield curves** and explain why par coupons differ from spot rates.
2. Expand calibration inputs, change the 5Y par coupon, and inspect repricing residuals.
3. Apply a +100bp parallel curve shock; explain the negative P&L for a long bond.
4. Set a positive tilt to steepen the curve; inspect the key-rate risk profile.
5. Compare exact nominal-yield repricing with the duration/convexity approximation.
6. Rotate the 3D surface to show how maturity increases interest-rate sensitivity.
7. Open **Cash flows & calibration** and export the audit trail.

All market inputs are **synthetic**, deterministic and available offline after installation.

## Python API

```python
from fixed_income import Bond, bootstrap, yield_risk, curve_dv01
from fixed_income.demo import sample_quotes

curve = bootstrap(sample_quotes())
bond = Bond(maturity=5, coupon_rate=0.045, frequency=2, face=1_000_000)
price = curve.price(bond)
ytm = bond.yield_to_maturity(price)
risk = yield_risk(bond, ytm)
print(price, risk.modified_duration, risk.convexity, curve_dv01(bond, curve))
```

## Architecture

```text
app.py                      Streamlit presentation and Plotly visualizations
src/fixed_income/
    bonds.py                Immutable bond model and cash-flow generation
    curves.py               Discount interpolation and bond-quote calibration
    numerics.py             Validated, bracketed bisection solver
    risk.py                 Analytical yield risk and numerical curve sensitivities
    demo.py                 Synthetic fixtures and installed CLI
 tests/                     Financial, benchmark and dashboard tests
 docs/METHODOLOGY.md         Formulas, conventions and numerical tradeoffs
```

The dependency direction is UI → analytics → standard library. The engine has no Streamlit, pandas, Plotly or SciPy imports. Frozen dataclasses make model state explicit and deterministic.

## Financial conventions

- Engine rates are **decimals**, UI rates are percentages; 1bp = 0.0001.
- Prices and DV01 are in the bond's face currency. Dashboard headline price is per 100 face.
- Bond YTM is nominal annual yield compounded at coupon frequency.
- Curve spot and forward rates use continuous compounding.
- Settlement is exactly on a coupon date: accrued interest is zero, so clean = dirty.
- Regular schedules only: maturity × frequency must be a positive integer.
- Increasing discount factors are allowed because rates can be negative.
- No extrapolation beyond the final node; out-of-domain requests fail explicitly.
- Yield DV01 and zero-curve DV01 measure different shocks and need not match.

See [methodology](docs/METHODOLOGY.md) for equations and limitations.

## Validate

```bash
ruff check .
ruff format --check .
mypy
pytest
python -m build
```

Tests include analytic identities, negative yields, finite-difference derivatives, sparse bootstrapping, repricing, external SciPy solver comparisons, invalid inputs and UI interaction. Coverage must exceed 90% of the analytics package. SciPy validates numerical roots independently; analytical identities provide checks that do not reuse the pricing implementation. This is not a QuantLib or real-market validation claim.

## Model scope

The engine focuses on regular fixed-coupon bonds and deterministic yield curves. It omits actual-date schedules, holiday calendars, day-count conventions, settlement lags, accrued interest between coupon dates, stubs, ex-coupon treatment, default/recovery, callable bonds and multi-curve swap valuation. A natural extension is actual-date cash-flow scheduling with an independent QuantLib benchmark using aligned conventions.

## References

- [BIS — Zero-coupon yield curves: technical documentation](https://www.bis.org/publ/bppdf/bispap25.htm): institutional term-structure context.
- [ECB — Yield curve methodology](https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/euro_area_yield_curves/shared/pdf/technical_notes.pdf): zero and forward curve definitions; the ECB fitting approach is not the algorithm implemented here.
- [SciPy — brentq](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html): independent root-finding benchmark.
- [Streamlit — app testing](https://docs.streamlit.io/develop/api-reference/app-testing): executable dashboard checks.

MIT licensed. See [LICENSE](LICENSE).
