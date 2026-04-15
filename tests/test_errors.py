"""Tests for core.errors."""

import pytest
from ogaden.errors import ConfigError, FetchError, OgadenError, OrderError


class TestOgadenError:
    def test_is_exception(self) -> None:
        assert issubclass(OgadenError, Exception)

    @pytest.mark.parametrize(
        "error_class,expected_base",
        [
            (FetchError, OgadenError),
            (OrderError, OgadenError),
            (ConfigError, OgadenError),
        ],
    )
    def test_hierarchy(self, error_class: type, expected_base: type) -> None:
        assert issubclass(error_class, expected_base)

    @pytest.mark.parametrize(
        "error_class,message",
        [
            (FetchError, "failed to fetch BTCUSDT"),
            (OrderError, "order rejected: insufficient balance"),
            (ConfigError, "API_KEY is not set"),
        ],
    )
    def test_message_preserved(self, error_class: type, message: str) -> None:
        with pytest.raises(error_class, match=message):
            raise error_class(message)
