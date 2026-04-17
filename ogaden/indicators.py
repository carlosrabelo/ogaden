"""Technical indicator calculations — pure math on OHLCV DataFrames."""

from __future__ import annotations

import pandas as pd
import ta


class IndicatorMixin:
    """Calculate technical indicators on :attr:`data`.

    All methods expect ``self.data`` to be a pandas DataFrame with at least the
    columns ``open``, ``high``, ``low``, ``close``, ``volume``.  Configuration
    attributes (``FAST_EMA``, ``RSI_BUY_THRESHOLD``, …) are read from the
    instance so that subclasses or composition can override them at runtime.
    """

    # -- SMA -------------------------------------------------------------------

    def calculate_sma(self) -> None:
        self.data["fast_sma"] = ta.trend.SMAIndicator(
            close=self.data["close"],
            window=self.FAST_SMA,
        ).sma_indicator()
        self.data["slow_sma"] = ta.trend.SMAIndicator(
            close=self.data["close"],
            window=self.SLOW_SMA,
        ).sma_indicator()

    def calculate_sma_signal(self) -> None:
        self.data["signal_sma"] = self.data.apply(
            lambda row: (
                "BUY"
                if row["fast_sma"] > row["slow_sma"]
                else "SELL"
                if row["fast_sma"] < row["slow_sma"]
                else "HOLD"
            ),
            axis=1,
        )

    # -- EMA -------------------------------------------------------------------

    def calculate_ema(self) -> None:
        self.data["fast_ema"] = ta.trend.EMAIndicator(
            close=self.data["close"],
            window=self.FAST_EMA,
        ).ema_indicator()
        self.data["slow_ema"] = ta.trend.EMAIndicator(
            close=self.data["close"],
            window=self.SLOW_EMA,
        ).ema_indicator()

    def calculate_ema_trend(self) -> None:
        self.data["trend_ema"] = ta.trend.EMAIndicator(
            close=self.data["close"],
            window=self.TREND_EMA,
        ).ema_indicator()

    def calculate_ema_signal(self) -> None:
        """Crossover EMA signal: BUY on golden cross, SELL on death cross."""
        self.data["signal_ema"] = "HOLD"
        for i in range(1, len(self.data)):
            prev_fast = self.data["fast_ema"].iloc[i - 1]
            prev_slow = self.data["slow_ema"].iloc[i - 1]
            curr_fast = self.data["fast_ema"].iloc[i]
            curr_slow = self.data["slow_ema"].iloc[i]

            if prev_fast <= prev_slow and curr_fast > curr_slow:
                self.data.at[i, "signal_ema"] = "BUY"
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                self.data.at[i, "signal_ema"] = "SELL"

    def calculate_ema_signal_trend(self) -> None:
        """Trend-filtered EMA signal: only BUY when close > trend EMA (uptrend),
        only SELL when close < trend EMA (downtrend)."""
        self.data["signal_ema_trend"] = "HOLD"
        for i in range(1, len(self.data)):
            fast = self.data["fast_ema"].iloc[i]
            slow = self.data["slow_ema"].iloc[i]
            close = self.data["close"].iloc[i]
            trend = self.data["trend_ema"].iloc[i]

            if pd.notna(fast) and pd.notna(slow) and pd.notna(trend):
                if fast > slow and close > trend:
                    self.data.at[i, "signal_ema_trend"] = "BUY"
                elif fast < slow and close < trend:
                    self.data.at[i, "signal_ema_trend"] = "SELL"

    # -- RSI -------------------------------------------------------------------

    def calculate_rsi(self) -> None:
        self.data["rsi"] = ta.momentum.RSIIndicator(
            close=self.data["close"],
            window=self.RSI_PERIOD,
        ).rsi()

    def calculate_rsi_signal(self) -> None:
        self.data["signal_rsi"] = self.data["rsi"].apply(
            lambda rsi: (
                "BUY"
                if rsi < self.RSI_BUY_THRESHOLD
                else "SELL"
                if rsi > self.RSI_SELL_THRESHOLD
                else "HOLD"
            )
        )

    # -- Volume ----------------------------------------------------------------

    def calculate_volume_indicators(self) -> None:
        """Calculate volume-based indicators for confirmation."""
        # Volume SMA for comparison
        self.data["volume_sma"] = self.data["volume"].rolling(window=20).mean()

        # Volume relative to average (volume ratio)
        self.data["volume_ratio"] = self.data["volume"] / self.data["volume_sma"]

        # On-Balance Volume (OBV)
        self.data["obv"] = (
            self.data["volume"] * (self.data["close"].diff() > 0).astype(int)
            - (self.data["close"].diff() < 0).astype(int)
        ).cumsum()

        # Volume Price Trend (VPT)
        price_change_pct = self.data["close"].pct_change()
        self.data["vpt"] = (self.data["volume"] * price_change_pct).cumsum()

    def calculate_volume_signal(self) -> None:
        """Generate volume-based trading signals."""
        self.data["signal_volume"] = "HOLD"

        # High volume confirmation (1.5x average volume)
        high_volume = self.data["volume_ratio"] > 1.5

        # Volume trend confirmation (OBV and VPT trending up/down)
        obv_trend_up = (
            self.data["obv"].rolling(window=10).mean()
            > self.data["obv"].rolling(window=30).mean()
        )
        vpt_trend_up = (
            self.data["vpt"].rolling(window=10).mean()
            > self.data["vpt"].rolling(window=30).mean()
        )

        # Buy signal: high volume + positive volume trends
        self.data.loc[high_volume & obv_trend_up & vpt_trend_up, "signal_volume"] = (
            "BUY"
        )

        # Sell signal: high volume + negative volume trends
        self.data.loc[high_volume & ~obv_trend_up & ~vpt_trend_up, "signal_volume"] = (
            "SELL"
        )

    # -- ATR -------------------------------------------------------------------

    def calculate_atr(self) -> None:
        """Calculate Average True Range for dynamic stop loss."""
        # True Range calculation
        high_low = self.data["high"] - self.data["low"]
        high_close = abs(self.data["high"] - self.data["close"].shift(1))
        low_close = abs(self.data["low"] - self.data["close"].shift(1))

        self.data["tr"] = pd.concat([high_low, high_close, low_close], axis=1).max(
            axis=1
        )

        # Average True Range
        self.data["atr"] = self.data["tr"].rolling(window=14).mean()

        # Dynamic stop loss levels
        atr_multiplier = 2.0
        self.data["stop_loss_long"] = self.data["close"] - (
            self.data["atr"] * atr_multiplier
        )
        self.data["stop_loss_short"] = self.data["close"] + (
            self.data["atr"] * atr_multiplier
        )

        # Take profit based on ATR (2:1 reward ratio)
        self.data["take_profit_long"] = self.data["close"] + (
            self.data["atr"] * atr_multiplier * 2
        )
        self.data["take_profit_short"] = self.data["close"] - (
            self.data["atr"] * atr_multiplier * 2
        )

    # -- MACD ------------------------------------------------------------------

    def calculate_macd(self) -> None:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = ta.trend.EMAIndicator(
            close=self.data["close"], window=12
        ).ema_indicator()
        ema_slow = ta.trend.EMAIndicator(
            close=self.data["close"], window=26
        ).ema_indicator()

        self.data["macd_line"] = ema_fast - ema_slow
        self.data["macd_signal"] = ta.trend.EMAIndicator(
            close=self.data["macd_line"], window=9
        ).ema_indicator()
        self.data["macd_histogram"] = self.data["macd_line"] - self.data["macd_signal"]

    def calculate_macd_signal(self) -> None:
        """Generate MACD-based trading signals."""
        self.data["signal_macd"] = "HOLD"

        # MACD crossover signals
        macd_above_signal = self.data["macd_line"] > self.data["macd_signal"]
        macd_below_signal = self.data["macd_line"] < self.data["macd_signal"]

        # Histogram momentum
        hist_increasing = self.data["macd_histogram"].diff() > 0

        # Buy signal: MACD crosses above signal line with positive momentum
        buy_condition = macd_above_signal & hist_increasing
        self.data.loc[buy_condition, "signal_macd"] = "BUY"

        # Sell signal: MACD crosses below signal line with negative momentum
        sell_condition = macd_below_signal & ~hist_increasing
        self.data.loc[sell_condition, "signal_macd"] = "SELL"

    # -- Bollinger Bands -------------------------------------------------------

    def calculate_bollinger_bands(self) -> None:
        """Calculate Bollinger Bands."""
        # Middle band (20-period SMA)
        self.data["bb_middle"] = ta.volatility.BollingerBands(
            close=self.data["close"], window=20, window_dev=2
        ).bollinger_mavg()

        # Upper and lower bands
        self.data["bb_upper"] = ta.volatility.BollingerBands(
            close=self.data["close"], window=20, window_dev=2
        ).bollinger_hband()

        self.data["bb_lower"] = ta.volatility.BollingerBands(
            close=self.data["close"], window=20, window_dev=2
        ).bollinger_lband()

        # Band width (volatility measure)
        self.data["bb_width"] = (
            self.data["bb_upper"] - self.data["bb_lower"]
        ) / self.data["bb_middle"]

        # %B (position within bands)
        self.data["bb_percent_b"] = (self.data["close"] - self.data["bb_lower"]) / (
            self.data["bb_upper"] - self.data["bb_lower"]
        )

    def calculate_bollinger_signal(self) -> None:
        """Generate Bollinger Bands-based trading signals."""
        self.data["signal_bb"] = "HOLD"

        # Squeeze detection (low volatility) — compare against historical
        # quantile (shift 1) so the current bar isn't part of its own threshold.
        bb_squeeze = self.data["bb_width"].rolling(window=20).quantile(0.1).shift(1)
        low_volatility = self.data["bb_width"] < bb_squeeze

        # Overbought/Oversold conditions
        overbought = self.data["bb_percent_b"] > 0.95
        oversold = self.data["bb_percent_b"] < 0.05

        # Mean reversion signals
        if low_volatility.iloc[-1]:  # Squeeze mode
            # Breakout signals
            self.data.loc[self.data["close"] > self.data["bb_upper"], "signal_bb"] = (
                "BUY"
            )
            self.data.loc[self.data["close"] < self.data["bb_lower"], "signal_bb"] = (
                "SELL"
            )
        else:  # Normal mode
            # Mean reversion
            self.data.loc[oversold, "signal_bb"] = "BUY"
            self.data.loc[overbought, "signal_bb"] = "SELL"

    # -- Stochastic Oscillator -------------------------------------------------

    def calculate_stochastic(self) -> None:
        """Calculate Stochastic Oscillator."""
        self.data["stoch_k"] = ta.momentum.StochasticOscillator(
            high=self.data["high"],
            low=self.data["low"],
            close=self.data["close"],
            window=14,
            smooth_window=3,
        ).stoch()

        self.data["stoch_d"] = ta.momentum.StochasticOscillator(
            high=self.data["high"],
            low=self.data["low"],
            close=self.data["close"],
            window=14,
            smooth_window=3,
        ).stoch_signal()

    def calculate_stochastic_signal(self) -> None:
        """Generate Stochastic-based trading signals."""
        self.data["signal_stoch"] = "HOLD"

        oversold_k = self.data["stoch_k"] < 30
        overbought_k = self.data["stoch_k"] > 70

        k_above_d = self.data["stoch_k"] > self.data["stoch_d"]

        buy_signal = oversold_k & k_above_d
        self.data.loc[buy_signal, "signal_stoch"] = "BUY"

        sell_signal = overbought_k & ~k_above_d
        self.data.loc[sell_signal, "signal_stoch"] = "SELL"
