import math

from btc_quant_lab.models import Trade
from btc_quant_lab.research.backtest import metrics_from_trades, trade_return_pct


def _trade(ret: float, i: int = 0) -> Trade:
    return Trade(
        direction=1,
        entry_ts=i,
        entry=100.0,
        exit_ts=i + 1,
        exit=100.0 * (1.0 + ret / 100.0),
        return_pct=ret,
    )


def test_short_return_is_measured_from_entry_price():
    assert trade_return_pct(-1, 100.0, 90.0) == 10.0
    assert trade_return_pct(-1, 100.0, 110.0) == -10.0


def test_metrics_use_compounded_equity_and_percentage_drawdown():
    metrics = metrics_from_trades([_trade(10.0, 1), _trade(-10.0, 2)])

    assert metrics["net_return_pct"] == 0.0
    assert math.isclose(metrics["compounded_return_pct"], -1.0, abs_tol=1e-9)
    assert math.isclose(metrics["max_drawdown_pct"], 10.0, abs_tol=1e-9)
