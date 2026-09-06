"""Fixed-rate bullet bonds on a regular year-fraction coupon grid."""

from dataclasses import dataclass
from math import isclose, pow

from .numerics import bisect_root, finite


@dataclass(frozen=True)
class CashFlow:
    """A payment in currency units at a time in years from settlement."""

    time: float
    amount: float


@dataclass(frozen=True)
class Bond:
    """Regular bullet bond; settlement is a coupon date, so accrued interest is zero."""

    maturity: float
    coupon_rate: float
    frequency: int = 2
    face: float = 100.0

    def __post_init__(self) -> None:
        for name in ("maturity", "coupon_rate", "face"):
            finite(getattr(self, name), name)
        if type(self.frequency) is not int or self.frequency not in (1, 2, 4, 12):
            raise ValueError("frequency must be 1, 2, 4 or 12")
        if self.maturity <= 0 or self.face <= 0 or self.coupon_rate < 0:
            raise ValueError("Positive maturity/face and nonnegative coupon required")
        periods = self.maturity * self.frequency
        if round(periods) < 1 or not isclose(periods, round(periods), abs_tol=1e-10):
            raise ValueError("maturity must lie on the coupon grid")

    def cashflows(self) -> tuple[CashFlow, ...]:
        """Return coupons and redemption, with final coupon combined with principal."""
        count = round(self.maturity * self.frequency)
        return tuple(
            CashFlow(
                i / self.frequency,
                self.face * self.coupon_rate / self.frequency + (self.face if i == count else 0),
            )
            for i in range(1, count + 1)
        )

    def price(self, yield_rate: float) -> float:
        """Dirty price using nominal annual yield compounded at coupon frequency."""
        finite(yield_rate, "yield")
        if yield_rate <= -self.frequency:
            raise ValueError("yield must exceed minus coupon frequency")
        return sum(
            cf.amount * pow(1 + yield_rate / self.frequency, -self.frequency * cf.time)
            for cf in self.cashflows()
        )

    def yield_to_maturity(self, price: float) -> float:
        """Invert price by bisection; bounded supported nominal yields are [-95%, 1000%]."""
        finite(price, "price")
        if price <= 0:
            raise ValueError("price must be positive")
        return bisect_root(lambda y: self.price(y) - price, -0.95, 10.0)
