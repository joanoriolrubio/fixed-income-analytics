"""Deterministic synthetic market and executable analytics example."""

import json
from dataclasses import asdict

from .bonds import Bond
from .curves import BondQuote, bootstrap
from .risk import curve_dv01, yield_risk


def sample_quotes() -> tuple[BondQuote, ...]:
    """Synthetic par quotes, deliberately labelled as illustrative, not live data."""
    return tuple(
        BondQuote(Bond(t, c), 100.0)
        for t, c in [
            (0.5, 0.032),
            (1.0, 0.033),
            (2.0, 0.035),
            (3.0, 0.037),
            (5.0, 0.04),
            (7.0, 0.042),
            (10.0, 0.044),
        ]
    )


def main() -> None:
    """Print a reproducible pricing, yield-risk and calibration report as JSON."""
    quotes = sample_quotes()
    curve = bootstrap(quotes)
    bond = Bond(5, 0.045)
    price = curve.price(bond)
    ytm = bond.yield_to_maturity(price)
    print(
        json.dumps(
            {
                "market": "synthetic",
                "yield": ytm,
                "risk": asdict(yield_risk(bond, ytm)),
                "curve_dv01": curve_dv01(bond, curve),
                "max_calibration_error": max(abs(curve.price(q.bond) - q.price) for q in quotes),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
