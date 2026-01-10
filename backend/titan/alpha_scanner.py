"""
backend/titan/alpha_scanner.py
==============================
TITAN Alpha Scanner Orchestrator (VN100 v3.0 - UPGRADED)

Features:
- Walk-forward scoring to reduce overfitting
- Stability-aware selection (mean alpha - lambda*std)
- Neighborhood smoothing for parameter selection
- Penalize excessive trading
- Transaction cost + slippage realism
"""

import os
from typing import Dict, Optional, List
import numpy as np
import pandas as pd

from .titan_math import TitanMath
from .data_feed import VnStockClient


# Extended Optimization Range (1-40)
DI_LENGTH_MIN = 1
DI_LENGTH_MAX = 40


class AlphaScanner:
    """
    TITAN Alpha Scanner (Upgraded).
    """
    
    def __init__(self):
        """Initialize the Alpha Scanner with performance knobs from environment."""
        self.client = VnStockClient()

        # ---- Optimization / realism knobs (override via env) ----
        # Costs in basis points per side (1 bp = 0.01%)
        self.fee_bps = float(os.getenv('TITAN_FEE_BPS', '15'))          # ~0.15% per side
        self.slippage_bps = float(os.getenv('TITAN_SLIPPAGE_BPS', '5')) # ~0.05% per side

        # Walk-forward settings (daily bars): 252~1y, 63~1q
        self.wf_train_bars = int(os.getenv('TITAN_WF_TRAIN_BARS', '252'))
        self.wf_test_bars = int(os.getenv('TITAN_WF_TEST_BARS', '63'))
        self.wf_step_bars = int(os.getenv('TITAN_WF_STEP_BARS', '63'))
        self.wf_min_folds = int(os.getenv('TITAN_WF_MIN_FOLDS', '3'))

        # Stability + overtrading penalty
        self.stability_lambda = float(os.getenv('TITAN_STABILITY_LAMBDA', '0.7'))
        self.trade_penalty_bps = float(os.getenv('TITAN_TRADE_PENALTY_BPS', '2'))

    def analyze_symbol(self, symbol: str, days: int = 730) -> Optional[Dict]:
        """
        Analyze a single symbol with stability-aware optimization.
        """
        try:
            df = self.client.get_stock_history(symbol, days=days)
            if df.empty or len(df) < 50:
                return None

            # --- Evaluate all DI lengths ---
            per_len: List[Dict] = []

            for length in range(DI_LENGTH_MIN, DI_LENGTH_MAX + 1):
                # Prefer walk-forward (OOS); fallback to in-sample when history is short
                wf = TitanMath.walk_forward_metrics(
                    df,
                    di_length=length,
                    train_bars=self.wf_train_bars,
                    test_bars=self.wf_test_bars,
                    step_bars=self.wf_step_bars,
                    fee_bps=self.fee_bps,
                    slippage_bps=self.slippage_bps,
                    min_folds=self.wf_min_folds,
                )

                if wf.get("folds", 0) >= self.wf_min_folds:
                    alpha_mean = float(wf["alpha_mean"])
                    alpha_std = float(wf.get("alpha_std", 0.0))
                    algo_mean = float(wf.get("algo_ret_mean", 0.0))
                    buy_mean = float(wf.get("buy_hold_mean", 0.0))
                    trades_mean = float(wf.get("trades_mean", 0.0))
                    folds = int(wf.get("folds", 0))
                else:
                    ins = TitanMath.check_alpha_validity(
                        df,
                        di_length=length,
                        fee_bps=self.fee_bps,
                        slippage_bps=self.slippage_bps,
                    )
                    alpha_mean = float(ins.get("alpha", 0.0))
                    alpha_std = 0.0
                    algo_mean = float(ins.get("algo_ret", 0.0))
                    buy_mean = float(ins.get("buy_hold", 0.0))
                    trades_mean = float(ins.get("total_trades", 0))
                    folds = 0

                # Score calculation
                score = (
                    alpha_mean
                    - self.stability_lambda * alpha_std
                    - trades_mean * (self.trade_penalty_bps / 100.0)
                )

                per_len.append({
                    "length": int(length),
                    "alpha": float(alpha_mean),
                    "alpha_std": float(alpha_std),
                    "algo_ret": float(algo_mean),
                    "buy_hold": float(buy_mean),
                    "trades": float(trades_mean),
                    "folds": int(folds),
                    "score": float(score),
                    "is_valid": (algo_mean > 0) and (algo_mean > buy_mean),
                })

            if not per_len:
                return None

            # --- Neighborhood smoothing (avoid single spiky length) ---
            score_map = {d["length"]: d["score"] for d in per_len}

            def smooth_score(L: int) -> float:
                s = score_map.get(L, -1e18)
                s_prev = score_map.get(L - 1, s)
                s_next = score_map.get(L + 1, s)
                return (s_prev + s + s_next) / 3.0

            valid = [d for d in per_len if d["is_valid"]]
            candidates = valid if valid else per_len
            best = max(candidates, key=lambda d: smooth_score(d["length"]))
            best_length = int(best["length"])

            # --- Current signal generation ---
            plus_di, minus_di = TitanMath.calculate_di(df, length=best_length)
            pos_count, neg_count = TitanMath.calculate_trend_count(plus_di, minus_di)

            current_pos = pos_count.iloc[-1]
            previous_pos = pos_count.iloc[-2] if len(pos_count) > 1 else 0
            is_buy_signal = (current_pos == 1) and (previous_pos == 0)

            strength_val = abs(float(plus_di.iloc[-1]) - float(minus_di.iloc[-1]))
            if strength_val > 20:
                trend_strength = "Strong"
            elif strength_val > 10:
                trend_strength = "Mod"
            else:
                trend_strength = "Weak"

            close_price = float(df["Close"].iloc[-1])

            return {
                "symbol": symbol,
                "close_price": close_price,
                "alpha": float(best.get("alpha", 0.0)),
                "algo_ret": float(best.get("algo_ret", 0.0)),
                "buy_hold": float(best.get("buy_hold", 0.0)),
                "total_trades": int(round(float(best.get("trades", 0.0)))),
                "is_valid": bool(best.get("is_valid", False)),
                "is_buy_signal": bool(is_buy_signal),
                "trend_strength": trend_strength,
                "plus_di": float(plus_di.iloc[-1]),
                "minus_di": float(minus_di.iloc[-1]),
                "optimal_length": best_length,
                "scan_range": f"{DI_LENGTH_MIN}-{DI_LENGTH_MAX}",
            }

        except Exception:
            return None

    def scan_vn100(self, days: int = 730) -> List[Dict]:
        tickers = self.client.get_vn100_tickers()
        if not tickers:
            return []
        
        results = []
        for symbol in tickers:
            result = self.analyze_symbol(symbol, days)
            if result:
                results.append(result)
        
        results.sort(key=lambda x: x['alpha'], reverse=True)
        return results

    def inspect_ticker_stability(self, symbol: str, days: int = 730) -> List[Dict]:
        """Deep inspection for the frontend heatmap/stability charts."""
        try:
            df = self.client.get_stock_history(symbol, days=days)
            if df.empty or len(df) < 50:
                return []

            results: List[Dict] = []
            for length in range(DI_LENGTH_MIN, DI_LENGTH_MAX + 1):
                try:
                    wf = TitanMath.walk_forward_metrics(
                        df,
                        di_length=length,
                        train_bars=self.wf_train_bars,
                        test_bars=self.wf_test_bars,
                        step_bars=self.wf_step_bars,
                        fee_bps=self.fee_bps,
                        slippage_bps=self.slippage_bps,
                        min_folds=self.wf_min_folds,
                    )

                    if wf.get("folds", 0) >= self.wf_min_folds:
                        alpha_val = float(wf["alpha_mean"])
                        algo_val = float(wf.get("algo_ret_mean", 0.0))
                        buy_val = float(wf.get("buy_hold_mean", 0.0))
                        trades_val = float(wf.get("trades_mean", 0.0))
                    else:
                        ins = TitanMath.check_alpha_validity(
                            df,
                            di_length=length,
                            fee_bps=self.fee_bps,
                            slippage_bps=self.slippage_bps,
                        )
                        alpha_val = float(ins.get("alpha", 0.0))
                        algo_val = float(ins.get("algo_ret", 0.0))
                        buy_val = float(ins.get("buy_hold", 0.0))
                        trades_val = float(ins.get("total_trades", 0))

                    results.append({
                        "length": int(length),
                        "alpha": float(alpha_val),
                        "is_valid": (algo_val > 0) and (algo_val > buy_val),
                        "algo_ret": float(algo_val),
                        "buy_hold": float(buy_val),
                        "trades": float(trades_val),
                    })
                except Exception:
                    continue

            results.sort(key=lambda x: x["length"])
            return results

        except Exception:
            return []
