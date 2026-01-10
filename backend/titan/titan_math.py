"""
backend/titan/titan_math.py
==========================
TITAN v9.1 Math Logic - UPGRADED

Features:
- Fixed DI Calculation (Wilder's RMA)
- Stateful Trend Count (Impulse Detection)
- Cost-aware Backtesting (Fee + Slippage)
- Walk-forward Optimization Support
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd


class TitanMath:
    """
    TITAN v9.1 Mathematical Engine (Upgraded).
    """
    
    @staticmethod
    def rma(series: pd.Series, length: int) -> pd.Series:
        """Wilder's Relative Moving Average."""
        return series.ewm(alpha=1.0/length, adjust=False).mean()
    
    @staticmethod
    def calculate_di(df: pd.DataFrame, length: int = 9) -> Tuple[pd.Series, pd.Series]:
        """Calculate Directional Indicators (+DI and -DI)."""
        high = df['High']
        low = df['Low']
        close = df['Close']
        prev_close = close.shift(1)
        
        tr = pd.concat([
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        ], axis=1).max(axis=1)
        
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = pd.Series(
            np.where((up_move > down_move) & (up_move > 0), up_move, 0),
            index=high.index
        )
        
        minus_dm = pd.Series(
            np.where((down_move > up_move) & (down_move > 0), down_move, 0),
            index=high.index
        )
        
        tr_smooth = TitanMath.rma(tr, length)
        plus_smooth = TitanMath.rma(plus_dm, length)
        minus_smooth = TitanMath.rma(minus_dm, length)
        
        plus_di = (plus_smooth / tr_smooth.replace(0, np.nan)) * 100
        minus_di = (minus_smooth / tr_smooth.replace(0, np.nan)) * 100
        
        return plus_di.fillna(0), minus_di.fillna(0)
    
    @staticmethod
    def calculate_trend_count(plus_di: pd.Series, minus_di: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Stateful Trend Count (Impulse Detection)."""
        n = len(plus_di)
        positive_count = np.zeros(n)
        negative_count = np.zeros(n)
        
        for i in range(1, n):
            prev_plus = plus_di.iloc[i-1]
            prev_minus = minus_di.iloc[i-1]
            curr_plus = plus_di.iloc[i]
            curr_minus = minus_di.iloc[i]
            
            if curr_plus > prev_plus and curr_plus > curr_minus:
                positive_count[i] = positive_count[i-1] + 1
                negative_count[i] = 0
            elif curr_minus > prev_minus and curr_minus > curr_plus:
                negative_count[i] = negative_count[i-1] + 1
                positive_count[i] = 0
            else:
                positive_count[i] = positive_count[i-1]
                negative_count[i] = negative_count[i-1]
        
        return (
            pd.Series(positive_count, index=plus_di.index),
            pd.Series(negative_count, index=minus_di.index)
        )

    @staticmethod
    def _backtest_di_strategy(
        df: pd.DataFrame,
        di_length: int,
        fee_bps: float = 0.0,
        slippage_bps: float = 0.0,
    ) -> Dict:
        """Backtest the TITAN DI-Impulse strategy on the provided dataframe."""
        if df.empty or len(df) < 10:
            return {'alpha': 0.0, 'algo_ret': 0.0, 'buy_hold': 0.0, 'total_trades': 0}

        plus_di, minus_di = TitanMath.calculate_di(df, di_length)
        pos_count, neg_count = TitanMath.calculate_trend_count(plus_di, minus_di)

        closes = df['Close'].astype(float).values
        n = len(closes)

        cost_roundtrip = 2.0 * (fee_bps + slippage_bps) / 10000.0  # fraction

        in_position = False
        entry_price = 0.0
        algo_return = 0.0  # fraction
        trades = 0

        for i in range(1, n):
            entry_signal = (pos_count.iloc[i] == 1) and (pos_count.iloc[i-1] == 0)
            exit_signal = (neg_count.iloc[i] == 1) and (neg_count.iloc[i-1] == 0)

            if (not in_position) and entry_signal:
                entry_price = closes[i]
                in_position = True
            elif in_position and exit_signal:
                exit_price = closes[i]
                if entry_price > 0:
                    trade_ret = (exit_price / entry_price) - 1.0
                    trade_ret -= cost_roundtrip
                    algo_return += trade_ret
                    trades += 1
                in_position = False
                entry_price = 0.0

        if in_position and entry_price > 0:
            exit_price = closes[-1]
            trade_ret = (exit_price / entry_price) - 1.0
            trade_ret -= cost_roundtrip
            algo_return += trade_ret
            trades += 1

        buy_hold = 0.0
        if closes[0] > 0:
            buy_hold = (closes[-1] / closes[0]) - 1.0
            buy_hold -= cost_roundtrip

        algo_return_pct = algo_return * 100.0
        buy_hold_pct = buy_hold * 100.0
        alpha = algo_return_pct - buy_hold_pct

        return {
            'alpha': float(alpha),
            'algo_ret': float(algo_return_pct),
            'buy_hold': float(buy_hold_pct),
            'total_trades': int(trades),
        }

    @staticmethod
    def walk_forward_metrics(
        df: pd.DataFrame,
        di_length: int,
        train_bars: int = 252,
        test_bars: int = 63,
        step_bars: int = 63,
        fee_bps: float = 0.0,
        slippage_bps: float = 0.0,
        min_folds: int = 2,
    ) -> Dict:
        """Compute out-of-sample (walk-forward) metrics for a FIXED DI length."""
        if df.empty or len(df) < (train_bars + test_bars + 20):
            return {'folds': 0}

        alphas = []
        algo_rets = []
        buy_holds = []
        trades = []

        start = 0
        n = len(df)

        while start + train_bars + test_bars <= n:
            test_df = df.iloc[start + train_bars : start + train_bars + test_bars]
            stats = TitanMath._backtest_di_strategy(
                test_df,
                di_length=di_length,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
            alphas.append(stats['alpha'])
            algo_rets.append(stats['algo_ret'])
            buy_holds.append(stats['buy_hold'])
            trades.append(stats['total_trades'])
            start += step_bars

        folds = len(alphas)
        if folds < min_folds:
            return {'folds': folds}

        alphas_arr = np.array(alphas, dtype=float)
        return {
            'folds': folds,
            'alpha_mean': float(np.mean(alphas_arr)),
            'alpha_std': float(np.std(alphas_arr, ddof=1)) if folds > 1 else 0.0,
            'algo_ret_mean': float(np.mean(np.array(algo_rets, dtype=float))),
            'buy_hold_mean': float(np.mean(np.array(buy_holds, dtype=float))),
            'trades_mean': float(np.mean(np.array(trades, dtype=float))),
        }

    @staticmethod
    def check_alpha_validity(
        df: pd.DataFrame,
        di_length: int = 9,
        fee_bps: float = 0.0,
        slippage_bps: float = 0.0,
    ) -> Dict:
        """Validate alpha on the provided history (single-sample, in-sample)."""
        if len(df) < 50:
            return {
                'is_valid': False,
                'alpha': 0.0,
                'algo_ret': 0.0,
                'buy_hold': 0.0,
                'total_trades': 0,
                'reason': 'Insufficient data'
            }

        stats = TitanMath._backtest_di_strategy(
            df,
            di_length=di_length,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
        )

        algo_return_pct = stats['algo_ret']
        buy_hold_pct = stats['buy_hold']
        alpha = stats['alpha']
        trades = stats['total_trades']

        guardrail_1 = algo_return_pct > 0
        guardrail_2 = algo_return_pct > buy_hold_pct
        is_valid = bool(guardrail_1 and guardrail_2)

        return {
            'is_valid': is_valid,
            'alpha': float(alpha),
            'algo_ret': float(algo_return_pct),
            'buy_hold': float(buy_hold_pct),
            'total_trades': int(trades)
        }
