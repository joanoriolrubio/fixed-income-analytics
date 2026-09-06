"""Discount curves: log-linear discount interpolation and continuous zero rates."""

from bisect import bisect_left
from dataclasses import dataclass
from math import exp, log

from .bonds import Bond
from .numerics import bisect_root, finite


@dataclass(frozen=True)
class DiscountCurve:
    """Positive discount nodes; D(0)=1, no extrapolation beyond the final node."""

    times: tuple[float, ...]
    discounts: tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "times", tuple(self.times))
        object.__setattr__(self, "discounts", tuple(self.discounts))
        if not self.times or len(self.times) != len(self.discounts):
            raise ValueError("Nonempty equal-length nodes required")
        previous = 0.0
        for time, discount in zip(self.times, self.discounts, strict=True):
            finite(time, "time")
            finite(discount, "discount")
            if time <= previous or discount <= 0:
                raise ValueError("Times must increase from zero; discounts must be positive")
            previous = time

    def discount(self, time: float) -> float:
        """Interpolate log D; increasing discounts are allowed for negative rates."""
        finite(time, "time")
        if time < 0 or time > self.times[-1]:
            raise ValueError("time outside calibrated curve")
        if time == 0:
            return 1.0
        index = bisect_left(self.times, time)
        t0 = self.times[index - 1] if index else 0.0
        d0 = self.discounts[index - 1] if index else 1.0
        weight = (time - t0) / (self.times[index] - t0)
        return exp(log(d0) + weight * (log(self.discounts[index]) - log(d0)))

    def zero_rate(self, time: float) -> float:
        """Continuously compounded annual spot rate, defined for positive time."""
        if time <= 0:
            raise ValueError("zero rate requires positive time")
        return -log(self.discount(time)) / time

    def forward_rate(self, start: float, end: float) -> float:
        """Continuously compounded average forward rate over [start, end]."""
        if end <= start:
            raise ValueError("end must exceed start")
        return log(self.discount(start) / self.discount(end)) / (end - start)

    def price(self, bond: Bond) -> float:
        """Present value of every coupon and principal cash flow."""
        return sum(cf.amount * self.discount(cf.time) for cf in bond.cashflows())

    def shifted(self, basis_points: float, tilt_basis_points: float = 0) -> "DiscountCurve":
        """Shift continuous zero nodes; tilt ranges from -tilt to +tilt across nodes."""
        finite(basis_points, "shift")
        finite(tilt_basis_points, "tilt")
        span = self.times[-1] - self.times[0]
        return DiscountCurve(
            self.times,
            tuple(
                d
                * exp(
                    -t
                    * (
                        basis_points
                        + tilt_basis_points * (2 * (t - self.times[0]) / span - 1 if span else 0)
                    )
                    / 10000
                )
                for t, d in zip(self.times, self.discounts, strict=True)
            ),
        )


@dataclass(frozen=True)
class BondQuote:
    """A bond and its full currency dirty price, not a percentage of face."""

    bond: Bond
    price: float

    def __post_init__(self) -> None:
        finite(self.price, "quote price")
        if self.price <= 0:
            raise ValueError("quote price must be positive")


def bootstrap(quotes: tuple[BondQuote, ...]) -> DiscountCurve:
    """Sequentially solve terminal log discounts, interpolating intermediate coupons.

    Unique maturities are required. Each new node reprices its instrument while
    preserving all prior nodes. The terminal discount search is exp([-50, 10]).
    """
    if not quotes:
        raise ValueError("At least one quote required")
    ordered = sorted(quotes, key=lambda q: q.bond.maturity)
    times: tuple[float, ...] = ()
    discounts: tuple[float, ...] = ()
    for quote in ordered:
        maturity = quote.bond.maturity
        if times and maturity <= times[-1]:
            raise ValueError("Quote maturities must be unique")
        next_times = (*times, maturity)

        def residual(
            log_discount: float,
            next_times: tuple[float, ...] = next_times,
            discounts: tuple[float, ...] = discounts,
            quote: BondQuote = quote,
        ) -> float:
            curve = DiscountCurve(next_times, (*discounts, exp(log_discount)))
            return curve.price(quote.bond) - quote.price

        solved = bisect_root(residual, -50.0, 10.0)
        times, discounts = next_times, (*discounts, exp(solved))
    return DiscountCurve(times, discounts)
