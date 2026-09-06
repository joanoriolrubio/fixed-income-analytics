"""Small dependency-free numerical primitives with explicit failure modes."""

from collections.abc import Callable
from math import isfinite


def finite(value: float, name: str) -> None:
    """Reject NaN and infinity at public model boundaries."""
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")


def bisect_root(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    tolerance: float = 1e-12,
    max_iterations: int = 250,
) -> float:
    """Solve a bracketed continuous root; tolerance is in the root's units."""
    for value in (lower, upper, tolerance):
        finite(value, "solver input")
    if lower >= upper or tolerance <= 0 or max_iterations < 1:
        raise ValueError("Invalid solver bounds, tolerance or iteration limit")
    left, right = function(lower), function(upper)
    finite(left, "lower residual")
    finite(right, "upper residual")
    if left == 0:
        return lower
    if right == 0:
        return upper
    if (left > 0) == (right > 0):
        raise ValueError("Root is not bracketed")
    for _ in range(max_iterations):
        middle = (lower + upper) / 2
        residual = function(middle)
        finite(residual, "residual")
        if residual == 0 or upper - lower <= tolerance:
            return middle
        if (residual > 0) == (left > 0):
            lower, left = middle, residual
        else:
            upper = middle
    raise RuntimeError("Root solver did not converge")
