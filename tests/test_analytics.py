"""Financial identities, numerical derivatives and independent SciPy validation."""

from math import exp, log

import pytest
from scipy.optimize import brentq

from fixed_income import (
    Bond,
    BondQuote,
    DiscountCurve,
    bootstrap,
    curve_dv01,
    key_rate_dv01,
    yield_risk,
)
from fixed_income.demo import main, sample_quotes
from fixed_income.numerics import bisect_root


@pytest.mark.parametrize("frequency", [1, 2, 4, 12])
@pytest.mark.parametrize("rate", [0, 0.02, 0.09])
def test_par_identity(frequency, rate):
    assert Bond(5, rate, frequency).price(rate) == pytest.approx(100)


@pytest.mark.parametrize("y", [-0.05, 0, 0.035, 0.25])
def test_ytm_against_scipy(y):
    bond = Bond(7, 0.045)
    price = bond.price(y)
    oracle = brentq(lambda r: bond.price(r) - price, -0.5, 1)
    assert bond.yield_to_maturity(price) == pytest.approx(oracle, abs=1e-11)
    assert bond.yield_to_maturity(price) == pytest.approx(y, abs=1e-11)


def test_zero_coupon_closed_form():
    bond = Bond(5, 0)
    risk = yield_risk(bond, 0.04)
    assert risk.price == pytest.approx(100 / 1.02**10)
    assert risk.macaulay_duration == pytest.approx(5)
    assert risk.modified_duration == pytest.approx(5 / 1.02)
    assert risk.convexity == pytest.approx(5 * 5.5 / 1.02**2)


@pytest.mark.parametrize("y", [-0.01, 0, 0.045, 0.1])
def test_analytical_derivatives(y):
    bond, h = Bond(10, 0.04), 1e-4
    risk = yield_risk(bond, y)
    p0, up, down = bond.price(y), bond.price(y + h), bond.price(y - h)
    assert risk.modified_duration == pytest.approx((down - up) / (2 * h * p0), rel=3e-7)
    assert risk.convexity == pytest.approx((up + down - 2 * p0) / (h * h * p0), rel=3e-7)
    assert risk.dv01 == pytest.approx((down - up) / 2, rel=3e-7)


def test_curve_interpolation_and_forwards():
    curve = DiscountCurve((1, 3), (exp(-0.02), exp(-0.09)))
    assert curve.discount(0) == 1
    assert curve.discount(2) == pytest.approx(exp(-0.055))
    assert curve.zero_rate(1) == pytest.approx(0.02)
    assert curve.forward_rate(1, 3) == pytest.approx(0.035)
    assert curve.discount(3) == pytest.approx(curve.discount(1) * exp(-2 * 0.035))


def test_bootstrap_repricing_and_independent_calibration():
    quotes = sample_quotes()
    curve = bootstrap(tuple(reversed(quotes)))
    times, discounts = (), ()
    for q in quotes:
        t = (*times, q.bond.maturity)
        root = brentq(
            lambda x, t=t, discounts=discounts, q=q: (
                DiscountCurve(t, (*discounts, exp(x))).price(q.bond) - q.price
            ),
            -50,
            10,
        )
        times, discounts = t, (*discounts, exp(root))
        assert curve.price(q.bond) == pytest.approx(q.price, abs=1e-8)
    assert curve.discounts == pytest.approx(discounts, abs=1e-11)


def test_recover_known_flat_curve_with_sparse_coupons():
    expected = DiscountCurve((0.5, 2, 5, 10), tuple(exp(-0.03 * t) for t in (0.5, 2, 5, 10)))
    quotes = tuple(BondQuote(Bond(t, 0.04), expected.price(Bond(t, 0.04))) for t in expected.times)
    assert bootstrap(quotes).discounts == pytest.approx(expected.discounts, abs=1e-11)


def test_negative_rates_and_zero_coupon_bootstrap():
    curve = bootstrap((BondQuote(Bond(1, 0), 102), BondQuote(Bond(3, 0), 105)))
    assert curve.zero_rate(1) == pytest.approx(-log(1.02))
    assert curve.discounts == pytest.approx((1.02, 1.05))


def test_curve_risk_and_tilt():
    curve, bond = bootstrap(sample_quotes()), Bond(5, 0.04, face=1000000)
    dv01 = curve_dv01(bond, curve)
    assert dv01 > 0
    assert sum(key_rate_dv01(bond, curve)) == pytest.approx(dv01, rel=1e-7)
    assert key_rate_dv01(bond, curve)[-1] == 0
    assert curve.shifted(100).price(bond) < curve.price(bond)
    shifted = curve.shifted(0, 20)
    assert shifted.zero_rate(0.5) - curve.zero_rate(0.5) == pytest.approx(-0.002)
    assert shifted.zero_rate(10) - curve.zero_rate(10) == pytest.approx(0.002)
    assert DiscountCurve((1,), (0.98,)).shifted(0, 20).discount(1) == pytest.approx(0.98)


@pytest.mark.parametrize(
    "args",
    [
        (0, 0.04),
        (1.2, 0.04),
        (1, -0.1),
        (1, 0.04, 3),
        (1, 0.04, 2, 0),
        (float("nan"), 0.04),
        (1, 0.04, True),
    ],
)
def test_invalid_bonds(args):
    with pytest.raises(ValueError):
        Bond(*args)


@pytest.mark.parametrize(
    "times,dfs",
    [
        ((), ()),
        ((1,), ()),
        ((1, 1), (0.9, 0.8)),
        ((-1,), (0.9,)),
        ((1,), (0,)),
        ((1,), (float("inf"),)),
    ],
)
def test_invalid_curves(times, dfs):
    with pytest.raises(ValueError):
        DiscountCurve(times, dfs)


def test_invalid_operations():
    bond, curve = Bond(1, 0.04), DiscountCurve((1,), (0.98,))
    for operation in [
        lambda: bond.price(-2),
        lambda: bond.price(float("nan")),
        lambda: bond.yield_to_maturity(0),
        lambda: curve.discount(-1),
        lambda: curve.discount(2),
        lambda: curve.zero_rate(0),
        lambda: curve.forward_rate(1, 0),
        lambda: curve_dv01(bond, curve, 0),
        lambda: bootstrap(()),
        lambda: BondQuote(bond, -1),
        lambda: bootstrap((BondQuote(bond, 100), BondQuote(bond, 99))),
        lambda: bootstrap((BondQuote(Bond(2, 0.5), 0.001), BondQuote(Bond(3, 0.5), 0.00001))),
    ]:
        with pytest.raises(ValueError):
            operation()


def test_solver_failures_and_endpoints():
    assert bisect_root(lambda x: x, 0, 1) == 0
    assert bisect_root(lambda x: x - 1, 0, 1) == 1
    assert bisect_root(lambda x: x - 0.5, 0, 1) == 0.5
    for args in [
        (lambda x: x * x + 1, -1, 1),
        (lambda x: x, 1, 0),
        (lambda x: x, -1, 1, 0),
        (lambda x: float("nan"), 0, 1),
    ]:
        with pytest.raises(ValueError):
            bisect_root(*args)
    with pytest.raises(RuntimeError):
        bisect_root(lambda x: x - 0.3, 0, 1, max_iterations=1)


def test_cli(capsys):
    main()
    assert '"market": "synthetic"' in capsys.readouterr().out
