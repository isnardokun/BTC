from btc_quant_lab.models import PivotSignal
from btc_quant_lab.research.backtest import reversal_backtest, round_trip_cost_pct


def test_round_trip_cost_is_two_sides_in_percentage_points():
    assert round_trip_cost_pct(fee_bps=5, slippage_bps=5) == 0.2


def test_reversal_backtest_deducts_costs_from_trade_return():
    signals = [
        PivotSignal(
            ts=1,
            direction=1,
            top=100,
            bottom=99,
            candidate_ts=0,
            confirm_price=100,
            bars_to_confirm=1,
        ),
        PivotSignal(
            ts=2,
            direction=-1,
            top=110,
            bottom=109,
            candidate_ts=1,
            confirm_price=110,
            bars_to_confirm=1,
        ),
    ]
    trades, metrics = reversal_backtest(signals, fee_bps=5, slippage_bps=5)
    assert len(trades) == 1
    assert trades[0].gross_return_pct == 10.0
    assert trades[0].cost_pct == 0.2
    assert trades[0].return_pct == 9.8
    assert metrics["execution_cost_sum_pct"] == 0.2
