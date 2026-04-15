"""Tests for the retry decorator in ogaden/retry.py."""

import time
from unittest.mock import MagicMock

import pytest
from ogaden.retry import with_retry


class TestWithRetry:
    def test_succeeds_on_first_attempt(self) -> None:
        mock = MagicMock(return_value=42)

        @with_retry(max_attempts=3, base_delay=0.0)
        def fn() -> int:
            return mock()  # type: ignore[no-any-return]

        assert fn() == 42
        assert mock.call_count == 1

    def test_retries_and_eventually_succeeds(self) -> None:
        calls = {"n": 0}

        @with_retry(max_attempts=3, base_delay=0.0)
        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("temporary")
            return "ok"

        assert flaky() == "ok"
        assert calls["n"] == 3

    def test_raises_after_max_attempts(self) -> None:
        @with_retry(max_attempts=3, base_delay=0.0)
        def always_fails() -> None:
            raise RuntimeError("always")

        with pytest.raises(RuntimeError, match="always"):
            always_fails()

    def test_non_retryable_exception_propagates_immediately(self) -> None:
        calls = {"n": 0}

        @with_retry(max_attempts=3, base_delay=0.0, exceptions=(ValueError,))
        def fn() -> None:
            calls["n"] += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError, match="not retryable"):
            fn()

        assert calls["n"] == 1  # no retries

    def test_exponential_backoff_timing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        @with_retry(max_attempts=3, base_delay=1.0, max_delay=10.0)
        def always_fails() -> None:
            raise Exception("fail")

        with pytest.raises(Exception):
            always_fails()

        assert sleep_calls == [1.0, 2.0]

    def test_max_delay_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        @with_retry(max_attempts=4, base_delay=10.0, max_delay=15.0)
        def always_fails() -> None:
            raise Exception("fail")

        with pytest.raises(Exception):
            always_fails()

        # delays: 10.0, 15.0 (capped), 15.0 (capped)
        assert sleep_calls[0] == 10.0
        assert all(d <= 15.0 for d in sleep_calls)

    def test_preserves_function_name(self) -> None:
        @with_retry()
        def my_function() -> None:
            pass

        assert my_function.__name__ == "my_function"

    def test_works_with_arguments(self) -> None:
        @with_retry(max_attempts=2, base_delay=0.0)
        def add(x: int, y: int) -> int:
            return x + y

        assert add(2, 3) == 5

    def test_single_attempt_raises_immediately(self) -> None:
        calls = {"n": 0}

        @with_retry(max_attempts=1, base_delay=0.0)
        def fn() -> None:
            calls["n"] += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fn()

        assert calls["n"] == 1
