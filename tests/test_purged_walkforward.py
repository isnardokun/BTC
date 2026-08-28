import polars as pl

from btc_quant_lab.research.walkforward import purged_walk_forward


def _synthetic_daily(n: int = 240) -> pl.DataFrame:
    rows = []
    price = 100.0
    for i in range(n):
        phase = (i // 6) % 2
        move = 1.8 if phase == 0 else -1.6
        open_ = price
        close = max(10.0, open_ + move)
        rows.append(
            {
                "ts": 1_600_000_000_000 + i * 86_400_000,
                "open": open_,
                "high": max(open_, close) + 0.9,
                "low": min(open_, close) - 0.9,
                "close": close,
                "volume": 1000.0 + i,
            }
        )
        price = close
    return pl.DataFrame(rows)


def test_purged_walk_forward_separates_train_and_test_boundaries():
    result = purged_walk_forward(
        _synthetic_daily(),
        train_bars=120,
        test_bars=40,
        purge_bars=5,
        embargo_bars=5,
        step_bars=40,
        min_train_trades=1,
    )

    assert result["method"]["type"] == "purged_embargo_walk_forward"
    assert result["method"]["purge_bars"] == 5
    assert result["method"]["embargo_bars"] == 5
    assert result["windows"]

    for window in result["windows"]:
        assert window["train"]["effective_end"] < window["train"]["nominal_end"]
        assert window["train"]["nominal_end"] < window["test"]["start"]
        assert window["embargo"]["bars"] == 5
        assert window["train"]["purged_bars"] == 5
        assert set(window["selected_config"]) == {
            "motor",
            "range_mode",
            "min_bars",
            "max_pending",
        }
