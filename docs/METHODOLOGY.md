# Methodology and model boundaries

## Bonds and yield risk

For face F, annual coupon c, payments per year m and regular times tᵢ=i/m:

- Coupon = Fc/m; add F at maturity.
- P(y) = Σ CFᵢ (1+y/m)^(−mtᵢ).
- Macaulay duration = Σ tᵢ PVᵢ / P.
- Modified duration = Macaulay / (1+y/m).
- Convexity = Σ tᵢ(tᵢ+1/m) PVᵢ / [P(1+y/m)²].
- Yield DV01 = P × modified duration × 10⁻⁴ (positive loss sensitivity).
- Approximate ΔP/P = −Dmod Δy + ½ Convexity Δy².

YTM inversion is monotonic for positive fixed cash flows. The implementation uses bisection over nominal yields [-0.95, 10], with a 1e-12 absolute yield tolerance and a 250-iteration limit. A price outside this bounded domain raises a bracket error. Pricing itself permits finite y > −m. Extremely large magnitudes can exceed floating-point range; the tool is designed for ordinary bond-market scales.

## Curves and bootstrapping

D(0)=1. Between nodes a and b, log D(t) is linearly interpolated:

log D(t) = log D(a) + [(t−a)/(b−a)] [log D(b)−log D(a)].

z(t) = −log D(t)/t; f(a,b) = log[D(a)/D(b)]/(b−a).

The time-zero anchor and first node imply a constant short-end zero rate. Instantaneous forwards are constant within each interpolation segment and can jump at knots; the UI displays six-month average forwards. This interpolation is transparent and preserves positivity of discount factors, but does not impose smoothness or nonnegative forwards.

Calibration accepts dirty-price bond quotes, sorts by maturity and rejects duplicates. For each maturity, solve the terminal **log discount factor** so that Σ CFᵢD(tᵢ) equals the quote. Coupons between the last solved node and the new maturity are discounted using the same log-linear segment. This handles sparse tenor grids without incorrectly assuming every prior coupon date is a calibration node. Previous instruments have no cash flows beyond their own maturities, so later nodes preserve their prices.

The terminal log-discount bracket is [-50, 10] with absolute log-discount tolerance 1e-12. Inconsistent inputs may have no root and fail explicitly. A converged mathematical calibration alone does not establish economic plausibility; a market implementation would add quote quality controls and instrument-specific conventions.

## Curve sensitivity and scenarios

Parallel shocks add a decimal shift to continuous zero nodes: D′(t)=D(t)exp(−tΔz). Log interpolation makes this a parallel zero shift between nodes too. Tilt varies linearly from −tilt at the shortest node to +tilt at the longest node; between nodes the shifted curve follows the standard interpolation rule.

Curve DV01 = [P(curve−h bp)−P(curve+h bp)]/(2h).

Key-rate DV01 bumps one zero node by ±1bp and re-interpolates; other nodes remain fixed. The sum approximates parallel DV01, subject to finite-difference error. These are **zero-node sensitivities**, not sensitivities to input bond quotes: quote risk would require bumping quotes and recalibrating.

Scenario P&L is full curve repricing. The duration/convexity chart instead shocks periodic nominal YTM, so it compares like-for-like analytical and exact yield risk. The surface uses bonds with a constant coupon and varied maturities, normalized by each bond's own base price.

## Validation strategy

1. Closed-form zero-coupon and par-price identities check financial equations.
2. Numerical first and second derivatives check analytical duration and convexity.
3. Synthetic flat-curve recovery and calibration residuals check bootstrapping.
4. SciPy Brent roots check the independent solver against the same residual functions; this alone would not validate those residuals.
5. Negative rates, invalid shapes, duplicate maturities and domain failures test model boundaries.
6. Streamlit AppTest executes the interface and changes risk inputs.

Actual-date valuation, accrued interest, credit risk, liquidity and real-market calibration are outside the scope. No claim of production readiness or current market accuracy is made.
