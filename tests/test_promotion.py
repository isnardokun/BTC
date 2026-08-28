from btc_quant_lab.research.promotion import assess_promotion


def _champion():
    return {
        "out_of_sample": {
            "aggregate": {
                "trades": 30,
                "expectancy_pct": 1.2,
                "profit_factor": 1.8,
                "profitable_windows_pct": 66.7,
                "max_drawdown_pct": 18.0,
            }
        }
    }


def _holdout():
    return {
        "metrics": {
            "trades": 12,
            "expectancy_pct": 0.8,
            "profit_factor": 1.5,
            "compounded_return_pct": 10.0,
            "max_drawdown_pct": 15.0,
        },
        "vs_buy_hold": {"excess_return_pct_points": 2.0},
        "monte_carlo": {"probability_profitable_pct": 72.0},
    }


def test_promotion_requires_hidden_holdout_and_positive_oos_evidence():
    result = assess_promotion(
        _champion(),
        _holdout(),
        {"holdout_exposed_during_research": False},
        {"plateau": {"interpretation": "broad"}},
    )
    assert result["eligible"] is True
    assert result["status"] == "eligible_for_review"
    assert result["failed_gates"] == []


def test_promotion_rejects_negative_holdout_expectancy():
    holdout = _holdout()
    holdout["metrics"]["expectancy_pct"] = -0.2
    result = assess_promotion(
        _champion(),
        holdout,
        {"holdout_exposed_during_research": False},
    )
    assert result["eligible"] is False
    assert "holdout_expectancy_positive" in result["failed_gates"]


def test_promotion_rejects_if_holdout_was_exposed():
    result = assess_promotion(
        _champion(),
        _holdout(),
        {"holdout_exposed_during_research": True},
    )
    assert result["eligible"] is False
    assert "holdout_was_hidden" in result["failed_gates"]
