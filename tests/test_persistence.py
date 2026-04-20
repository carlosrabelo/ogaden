"""Tests for state persistence in ogaden/persistence.py."""

import json
from pathlib import Path

import pytest

from ogaden.persistence import load_state, save_state


class TestSaveState:
    def test_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        save_state({"position": "BUY"}, path)
        assert path.exists()

    def test_content_is_valid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = {"position": "SELL", "purchase_price": 50000.0}
        save_state(state, path)
        loaded = json.loads(path.read_text())
        assert loaded == state

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        save_state({"position": "BUY"}, path)
        save_state({"position": "SELL", "purchase_price": 45000.0}, path)
        loaded = json.loads(path.read_text())
        assert loaded["position"] == "SELL"

    def test_atomic_write_no_tmp_left_behind(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        save_state({"x": 1}, path)
        tmp = path.with_suffix(".json.tmp")
        assert not tmp.exists()

    def test_write_failure_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save_state must not propagate OSError — it logs a warning instead."""
        path = tmp_path / "state.json"

        def bad_write(self_: object, text: str, **kwargs: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", bad_write)
        save_state({"position": "BUY"}, path)  # should not raise


class TestLoadState:
    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        assert load_state(path) == {}

    def test_returns_persisted_data(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state = {
            "position": "SELL",
            "purchase_price": 60000.0,
            "trailing_balance": 1500.0,
        }
        save_state(state, path)
        loaded = load_state(path)
        assert loaded["position"] == "SELL"
        assert loaded["purchase_price"] == pytest.approx(60000.0)
        assert loaded["trailing_balance"] == pytest.approx(1500.0)

    def test_returns_empty_on_corrupt_json(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        path.write_text("not valid json {{{{")
        assert load_state(path) == {}

    def test_returns_empty_on_read_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "state.json"
        path.write_text("{}")

        def bad_read(self_: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", bad_read)
        assert load_state(path) == {}

    def test_roundtrip_all_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "state.json"
        state: dict[str, object] = {
            "position": "SELL",
            "purchase_price": 98765.12345678,
            "trailing_balance": 12000.5,
            "base_balance": 0.00012345,
            "quote_balance": 500.0,
        }
        save_state(state, path)
        loaded = load_state(path)
        for key, value in state.items():
            assert loaded[key] == pytest.approx(value)


class TestTraderStatePersistence:
    """Integration-style tests: Trader._save_state / _load_state round-trip."""

    def test_save_and_restore_position(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ogaden.trader import Trader

        monkeypatch.setattr("ogaden.broker.Client", lambda *a, **kw: object())

        state_file = tmp_path / "ogaden_state.json"
        monkeypatch.setenv("STATE_FILE", str(state_file))

        # Re-import Loader so STATE_FILE env is picked up
        trader = Trader()
        trader.STATE_FILE = state_file
        trader.position = "SELL"
        trader.purchase_price = 55000.0
        trader.trailing_balance = 1100.0
        trader._save_state()

        # New trader instance loads saved state
        trader2 = Trader()
        trader2.STATE_FILE = state_file
        trader2._load_state()

        assert trader2.position == "SELL"
        assert trader2.purchase_price == pytest.approx(55000.0)
        assert trader2.trailing_balance == pytest.approx(1100.0)

    def test_load_state_missing_file_is_noop(self, tmp_path: Path) -> None:
        from ogaden.trader import Trader

        trader = Trader()
        trader.STATE_FILE = tmp_path / "nonexistent.json"
        original_position = trader.position
        trader._load_state()
        assert trader.position == original_position

    def test_save_and_restore_metrics_with_pnl_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ogaden.trader import Trader

        monkeypatch.setattr("ogaden.broker.Client", lambda *a, **kw: object())

        state_file = tmp_path / "ogaden_state.json"

        trader = Trader()
        trader.STATE_FILE = state_file
        trader.position = "SELL"
        trader.metrics.cycles = 42
        trader.metrics.buys = 20
        trader.metrics.sells = 19
        trader.metrics.fetch_errors = 3
        trader.metrics.order_errors = 1
        trader.metrics.pnl_history = [1.5, -0.8, 2.3, 0.1]
        trader._save_state()

        trader2 = Trader()
        trader2.STATE_FILE = state_file
        trader2._load_state()

        assert trader2.metrics.cycles == 42
        assert trader2.metrics.buys == 20
        assert trader2.metrics.sells == 19
        assert trader2.metrics.fetch_errors == 3
        assert trader2.metrics.order_errors == 1
        assert trader2.metrics.pnl_history == pytest.approx([1.5, -0.8, 2.3, 0.1])
        assert trader2.metrics.total_pnl == pytest.approx(3.1)
        assert trader2.metrics.win_rate == pytest.approx(0.75)
