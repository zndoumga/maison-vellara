"""
Deterministic randomness helpers.

Every generation run is seeded from (date, source) so that re-running a given
day reproduces the same data — essential for idempotent backfills.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Sequence, TypeVar

T = TypeVar("T")


def seed_for(d: date, source: str, salt: str = "") -> int:
    """Stable integer seed derived from a date + source name."""
    key = f"{d.isoformat()}|{source}|{salt}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return int(digest[:16], 16)


def rng_for(d: date, source: str, salt: str = "") -> random.Random:
    """A fresh seeded Random for a given (date, source)."""
    return random.Random(seed_for(d, source, salt))


def weighted_choice(rng: random.Random, items: Sequence[T], weights: Sequence[float]) -> T:
    """Pick one item using the supplied weights."""
    return rng.choices(list(items), weights=list(weights), k=1)[0]


def weighted_pairs(rng: random.Random, pairs: Sequence[tuple[T, float]]) -> T:
    """Pick from a sequence of (value, weight) tuples."""
    values = [p[0] for p in pairs]
    weights = [p[1] for p in pairs]
    return weighted_choice(rng, values, weights)


def jitter(rng: random.Random, base: float, pct: float) -> float:
    """Multiply base by a random factor in [1-pct, 1+pct]."""
    return base * (1.0 + rng.uniform(-pct, pct))


def poisson(rng: random.Random, lam: float) -> int:
    """Knuth's Poisson sampler — count of events given an expected rate `lam`."""
    if lam <= 0:
        return 0
    import math

    l = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= l:
            return k - 1


def chance(rng: random.Random, p: float) -> bool:
    """True with probability p."""
    return rng.random() < p
