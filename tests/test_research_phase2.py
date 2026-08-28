import polars as pl

from btc_quant_lab.models import PivotSignal, Trade
from btc_quant_lab.research.features import build_feature_rows, summarize_feature_outcomes
from btc_quant_lab.research.walkforward import walk_forward


def _synthetic_daily(n: int = 220) -> pl.DataFrame:
    rows = []
    price = 100.0
    for i in range(n):
        phase = (i // 7) % 2
        move = 1.5 if phase == 0 else -1.3
        open_ = price
        close = max(10.0, open_ + move)
        rows.append(
            {
                "ts": 1_600_000_000_000 + i * 86_400_000,
                "open": open_,
                "high": max(open_, close) + 0.8,
                "low": min(open_, close) - 0.8,
                "close": close,
                "volume": 1000.0 + (i % 20) * 10,
            }
        )
        price = close
    return pl.DataFrame(rows)


def test_features_use_confirmation_time_and_attach_outcome_label():
    df = _synthetic_daily(220)
    ts = df["ts"].to_list()
    close = df["close"].to_list()
    signal = PivotSignal(
        ts=ts[210],
        direction=1,
        top=close[210] + 1,
        bottom=close[210] - 1,
        candidate_ts=ts[208],
        confirm_price=close[210],
        bars_to_confirm=2,
    )
    trade = Trade(
        direction=1,
        entry_ts=ts[210],
        entry=close[210],
        exit_ts=ts[215],
        exit=close[215],
        return_pct=3.25,
    )
    rows = build_feature_rows(df, [signal], [trade])
    assert len(rows) == 1
    assert rows[0]["ts"] == ts[210]
    assert rows[0]["trade_return_pct"] == 3.25
    assert rows[0]["trend_regime"] in {"bull", "bear", "transition"}
    summary = summarize_feature_outcomes(rows)
    assert summary["labeled_signals"] == 1


def test_walk_forward_never_uses_test_window_for_parameter_selection():
    df = _synthetic_daily(220)
    result = walk_forward(
        df,
        train_bars=120,
        test_bars=40,
        step_bars=40,
        min_train_trades=1,
    )
    assert len(result["windows"]) >= 1
    for window in result["windows"]:
        assert window["train"]["end"] < window["test"]["start"]
        assert set(window["selected_config"]) == {
            "motor",
            "range_mode",
            "min_bars",
            "max_pending",
        }
    assert "aggregate" in result
    assert "selection_frequency" in result
