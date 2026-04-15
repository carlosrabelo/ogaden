"""Integration-style tests for entry points that are hard to test unit-style."""

from unittest.mock import MagicMock

import pytest


class TestEngine:
    def test_engine_calls_stop_on_shutdown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine should call trader.stop() after the main loop exits."""
        import importlib

        from ogaden import engine

        # Reload module to reset _shutdown_requested to False
        importlib.reload(engine)

        mock_trader = MagicMock()

        def mock_trader_factory():
            return mock_trader

        monkeypatch.setattr("ogaden.engine.Trader", mock_trader_factory)

        call_count = [0]

        def fake_execute():
            call_count[0] += 1
            if call_count[0] >= 1:
                engine._shutdown_requested = True

        mock_trader.execute.side_effect = fake_execute

        engine.main()

        mock_trader.stop.assert_called_once()


class TestDashboard:
    def test_health_endpoint(self) -> None:
        """Dashboard /health should return healthy status."""
        from ogaden.dashboard import health

        result = health()
        assert result == {"status": "healthy", "service": "ogaden-dashboard"}

    def test_dashboard_route_exists(self) -> None:
        """Dashboard should have a / route that renders the template."""
        from ogaden.dashboard import app

        with app.test_client() as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert b"Ogaden" in resp.data


class TestDashboardConnectionTracking:
    def test_connection_counter_increments(self) -> None:
        """_increment_connections should increase the global counter."""
        from ogaden import dashboard

        before = dashboard._connected_count
        dashboard._increment_connections()
        assert dashboard._connected_count == before + 1
        # Reset
        dashboard._decrement_connections()

    def test_connection_counter_decrements(self) -> None:
        """_decrement_connections should decrease the global counter."""
        from ogaden import dashboard

        dashboard._increment_connections()
        before = dashboard._connected_count
        dashboard._decrement_connections()
        assert dashboard._connected_count == before - 1

    def test_has_clients_returns_true_when_connected(self) -> None:
        """_has_clients should return True when connections > 0."""
        from ogaden import dashboard

        dashboard._increment_connections()
        assert dashboard._has_clients() is True
        dashboard._decrement_connections()

    def test_has_clients_returns_false_when_no_clients(self) -> None:
        """_has_clients should return False when no connections."""
        from ogaden import dashboard

        # Ensure clean state
        while dashboard._connected_count > 0:
            dashboard._decrement_connections()
        assert dashboard._has_clients() is False


class TestAnalysis:
    def test_analysis_runs_without_crash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Analysis should fetch data and calculate indicators without crashing."""
        import pandas as pd
        from ogaden.analysis import main

        mock_trader = MagicMock()
        mock_trader.data = pd.DataFrame({
            "close": [100.0, 101.0, 102.0, 99.0, 98.0, 100.0, 103.0, 105.0],
            "high": [101.0, 102.0, 103.0, 100.0, 99.0, 101.0, 104.0, 106.0],
            "low": [99.0, 100.0, 101.0, 98.0, 97.0, 99.0, 102.0, 104.0],
            "open": [100.0, 101.0, 102.0, 99.0, 98.0, 100.0, 103.0, 105.0],
            "volume": [1000.0] * 8,
        })
        monkeypatch.setattr("ogaden.analysis.Trader", lambda: mock_trader)

        main()  # Should not raise

        mock_trader.fetch_data.assert_called_once()
        mock_trader.calculate_sma.assert_called_once()
        mock_trader.calculate_ema.assert_called_once()
        mock_trader.calculate_rsi.assert_called_once()
