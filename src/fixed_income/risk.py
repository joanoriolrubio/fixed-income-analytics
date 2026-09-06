"""Analytical yield risk and full-revaluation discount-curve risk."""

from dataclasses import dataclass

from .bonds import Bond
from .curves import DiscountCurve
from .numerics import finite


@dataclass(frozen=True)
class YieldRisk:
    """Duration in years, convexity in years squared, DV01 in currency per bp."""

    price: float
    macaulay_duration: float
    modified_duration: float
    convexity: float
    dv01: float


def yield_risk(bond: Bond, yield_rate: float) -> YieldRisk:
    """Compute exact first/second price derivatives for nominal periodic yield."""
    price = bond.price(yield_rate)
    base = 1 + yield_rate / bond.frequency
    weighted = [
        (cf.time, cf.amount * base ** (-bond.frequency * cf.time)) for cf in bond.cashflows()
    ]
    macaulay = sum(t * pv for t, pv in weighted) / price
    modified = macaulay / base
    convexity = sum(t * (t + 1 / bond.frequency) * pv for t, pv in weighted)
    convexity /= price * base * base
    return YieldRisk(price, macaulay, modified, convexity, price * modified * 0.0001)


def curve_dv01(bond: Bond, curve: DiscountCurve, bump_bp: float = 1.0) -> float:
    """Positive loss sensitivity to a parallel continuous-zero increase, per bp."""
    finite(bump_bp, "bump")
    if bump_bp <= 0:
        raise ValueError("bump must be positive")
    return (curve.shifted(-bump_bp).price(bond) - curve.shifted(bump_bp).price(bond)) / (
        2 * bump_bp
    )


def key_rate_dv01(bond: Bond, curve: DiscountCurve) -> tuple[float, ...]:
    """Central 1bp zero-node sensitivities; interpolation spreads each local bump."""
    from math import exp

    result = []
    for index in range(len(curve.times)):
        prices = []
        for sign in (-1, 1):
            bumped = tuple(
                d * exp(-sign * 0.0001 * t) if i == index else d
                for i, (t, d) in enumerate(zip(curve.times, curve.discounts, strict=True))
            )
            prices.append(DiscountCurve(curve.times, bumped).price(bond))
        result.append((prices[0] - prices[1]) / 2)
    return tuple(result)
