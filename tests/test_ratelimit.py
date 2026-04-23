"""Rate limiter unit tests."""

from __future__ import annotations

from api.ratelimit import RateLimiter


def test_allows_up_to_limit():
    rl = RateLimiter(limit=3, window_seconds=60)
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is False


def test_buckets_are_per_key():
    rl = RateLimiter(limit=1, window_seconds=60)
    assert rl.check("1.1.1.1") is True
    assert rl.check("1.1.1.1") is False
    assert rl.check("2.2.2.2") is True


def test_reset():
    rl = RateLimiter(limit=1, window_seconds=60)
    assert rl.check("x") is True
    rl.reset()
    assert rl.check("x") is True
